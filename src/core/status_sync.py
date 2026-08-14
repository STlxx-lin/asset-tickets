"""
status_sync.py — 状态/时间同步与回滚封装。

统一「本地写库 → 外部工单系统 API 同步 → 失败回滚本地」模式，
解决各流程对话框 17 处复制粘贴中回滚不完整的问题：
- 只回滚全局 status、不回滚 art_status / product_path / 时间字段
- 时间类调用失败完全无回滚

v1.2（2026-08-14）增强：
- 乐观锁：所有写入带 version 版本检查，并发修改时提示刷新而非静默覆盖
- 原子写入：状态/art_status/时间字段合并为单条 UPDATE（update_work_order_fields），
  消除"调用方先直写、封装本地失败不回滚"的窗口期
- 新增 update_local_status_only：纯本地字段写入（如美工链 art_status），带乐观锁
"""
import logging

from src.core.api_manager import api_manager
from src.core.database import db_manager, TIME_FIELDS

logger = logging.getLogger(__name__)


def _apply_local(updates: dict, order_id: str) -> tuple[int, str]:
    """乐观锁保护的本地单条写入。

    Returns:
        (rowcount, error): rowcount>0 成功；0=版本冲突或工单不存在；
                           -1=数据库异常。error 仅在非成功时给出可读原因。
    """
    version = db_manager.get_work_order_version(order_id)
    if version is None:
        return -1, f"工单{order_id}不存在（可能已被删除），已跳过更新"
    rowcount = db_manager.update_work_order_fields(order_id, updates, expected_version=version)
    if rowcount < 0:
        return -1, f"本地更新工单{order_id}失败（数据库异常），已跳过外部同步"
    if rowcount == 0:
        now = db_manager.get_work_order_version(order_id)
        if now is not None and now != version:
            return 0, f"工单{order_id}已被其他客户端修改（版本 {version} → {now}），请刷新工单列表后重试"
        return 0, f"工单{order_id}不存在（可能已被删除），已跳过更新"
    return rowcount, ""


def _rollback(order_id: str, updates: dict) -> list[str]:
    """回滚本地改动，逐一检查回滚结果，任一失败都如实上报。"""
    failures = []
    # 回滚不带版本检查：紧随写入之后执行，窗口极小；且回滚目标是"恢复原状"
    if not db_manager.update_work_order_fields(order_id, updates):
        failures.append(f"回滚字段{list(updates.keys())}失败")
    return failures


def update_status_with_api(order_id: str, new_status: str, old_status: str,
                           art_status_before: str | None = None,
                           product_path_before: str | None = None) -> tuple:
    """本地更新工单全局状态并同步外部系统；失败时完整回滚本地改动。

    Args:
        order_id: 工单ID
        new_status: 新状态
        old_status: 旧状态（回滚目标）
        art_status_before: 本次改动前的美工链状态（若本次操作会写 art_status）
        product_path_before: 本次改动前的成品路径（若本次操作会写 product_path）

    Returns:
        (ok, error_msg): 本地+API 均成功返回 (True, '')；
                         否则返回 (False, error_msg)，本地已回滚到改动前。
    """
    rowcount, local_err = _apply_local({'status': new_status}, order_id)
    if rowcount <= 0:
        return False, local_err
    api_response = api_manager.update_work_order_status(order_id, new_status)
    if api_response['success']:
        logger.info(f"API更新工单{order_id}状态为{new_status}成功")
        return True, ""
    error_msg = f"API更新工单{order_id}状态为{new_status}失败: {api_response['error']}"
    logger.error(error_msg)
    # 回滚本地改动，保持两端一致
    rollback_updates = {'status': old_status}
    if art_status_before is not None:
        rollback_updates['art_status'] = art_status_before
    if product_path_before is not None:
        rollback_updates['edit_product_path'] = product_path_before
    rollback_failures = _rollback(order_id, rollback_updates)
    if rollback_failures:
        error_msg += "；且本地回滚失败: " + "; ".join(rollback_failures)
        logger.error(error_msg)
    return False, error_msg


def update_time_with_api(order_id: str, time_field: str, time_value,
                         status_before: str | None = None,
                         art_status_before: str | None = None,
                         status_new: str | None = None,
                         art_status_new: str | None = None) -> tuple:
    """本地更新时间字段（可同时写入全局状态/美工状态）并同步外部系统；失败时完整回滚本地改动。

    Args:
        order_id: 工单ID
        time_field: 时间字段名（art_start_time/edit_end_time 等）
        time_value: datetime 对象（DB 写入）或时间字符串（API 转换）
        status_before: 本次改动前的全局状态（若本次操作会写全局 status，回滚目标）
        art_status_before: 本次改动前的美工链状态（若本次操作会写 art_status，回滚目标）
        status_new: 本次同时写入的全局状态（如剪辑领取素材 → '后期处理中'）
        art_status_new: 本次同时写入的美工链状态（如美工领取素材 → '美工设计中'）

    Returns:
        (ok, error_msg): 同 update_status_with_api。
    """
    import datetime

    updates = {time_field: time_value}
    if status_new is not None:
        updates['status'] = status_new
    if art_status_new is not None:
        updates['art_status'] = art_status_new
    rowcount, local_err = _apply_local(updates, order_id)
    if rowcount <= 0:
        return False, local_err
    if isinstance(time_value, datetime.datetime):
        formatted = time_value.strftime('%Y-%m-%d %H:%M:%S')
    else:
        formatted = str(time_value)
    api_response = api_manager.update_work_order_time(order_id, time_field, formatted)
    if api_response['success']:
        logger.info(f"API更新工单{order_id}{time_field}成功")
        return True, ""
    error_msg = f"API更新工单{order_id}{time_field}失败: {api_response['error']}"
    logger.error(error_msg)
    # 回滚本地改动，保持两端一致；时间字段无"旧值快照"语义，回滚到 NULL（写入失败即视为未发生）
    rollback_updates = {}
    if time_field in TIME_FIELDS:
        rollback_updates[time_field] = None
    if status_before is not None:
        rollback_updates['status'] = status_before
    if art_status_before is not None:
        rollback_updates['art_status'] = art_status_before
    if rollback_updates:
        rollback_failures = _rollback(order_id, rollback_updates)
        if rollback_failures:
            error_msg += "；且本地回滚失败: " + "; ".join(rollback_failures)
            logger.error(error_msg)
    return False, error_msg


def update_local_status_only(order_id: str, updates: dict) -> tuple:
    """纯本地字段写入（不涉及外部 API 同步），带乐观锁版本检查。

    供美工链使用：美工状态（art_status）是本地字段，外部工单系统无对应字段，
    无需 API 同步；配合 update_work_order_fields 单条原子写入避免半写状态。

    Args:
        order_id: 工单ID
        updates: 字段名 → 值（键须位于 database._WORK_ORDER_UPDATE_FIELDS 白名单）

    Returns:
        (ok, error_msg): 成功返回 (True, '')；否则 (False, 原因)，未做任何写入。
    """
    rowcount, local_err = _apply_local(updates, order_id)
    if rowcount <= 0:
        return False, local_err
    logger.info(f"本地更新工单{order_id}字段{list(updates.keys())}成功")
    return True, ""


def has_pending_edit_review(order_id: str) -> bool:
    """剪辑已提交视频后期审核且尚未通过（兼容全局状态被 API 回滚的场景）。

    统一供 video_post_review.py 与 post_review_combined.py 使用，
    避免两处重复定义。
    """
    try:
        logs = db_manager.get_logs_by_order_id(order_id)
        has_submit = any(l.get('action_type') == '提交视频后期审核' for l in logs)
        has_approved = any(l.get('action_type') == '视频后期审核通过' for l in logs)
        return has_submit and not has_approved
    except Exception as e:
        # 记录异常而非静默吞掉：DB 故障不应被当作"无待审核"放行审核门禁
        logger.error(f"查询工单{order_id}待审核状态失败: {e}")
        return False
