"""
status_sync.py — 状态/时间同步与回滚封装。

统一「本地写库 → 外部工单系统 API 同步 → 失败回滚本地」模式，
解决各流程对话框 17 处复制粘贴中回滚不完整的问题：
- 只回滚全局 status、不回滚 art_status / product_path / 时间字段
- 时间类调用失败完全无回滚
"""
import logging

from src.core.api_manager import api_manager
from src.core.database import db_manager

logger = logging.getLogger(__name__)


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
    db_manager.update_work_order_status(order_id, new_status)
    api_response = api_manager.update_work_order_status(order_id, new_status)
    if api_response['success']:
        logger.info(f"API更新工单{order_id}状态为{new_status}成功")
        return True, ""
    error_msg = f"API更新工单{order_id}状态为{new_status}失败: {api_response['error']}"
    logger.error(error_msg)
    # 回滚本地改动，保持两端一致
    db_manager.update_work_order_status(order_id, old_status)
    if art_status_before is not None:
        db_manager.update_work_order_art_status(order_id, art_status_before)
    if product_path_before is not None:
        db_manager.update_work_order_product_path(order_id, product_path_before)
    return False, error_msg


def update_time_with_api(order_id: str, time_field: str, time_value,
                         status_before: str | None = None,
                         art_status_before: str | None = None) -> tuple:
    """本地更新时间字段并同步外部系统；失败时完整回滚本地改动。

    Args:
        order_id: 工单ID
        time_field: 时间字段名（art_start_time/edit_end_time 等）
        time_value: datetime 对象（DB 写入）或时间字符串（API 转换）
        status_before: 本次改动前的全局状态（若本次操作会写全局 status）
        art_status_before: 本次改动前的美工链状态（若本次操作会写 art_status）

    Returns:
        (ok, error_msg): 同 update_status_with_api。
    """
    import datetime

    db_manager.update_work_order_time_field(order_id, time_field, time_value)
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
    # 回滚本地改动，保持两端一致
    # 时间字段无"旧值快照"语义，回滚到 NULL（写入失败即视为未发生）
    if time_field in ('art_start_time', 'art_end_time', 'edit_start_time', 'edit_end_time',
                      'photographer_start_time', 'photographer_end_time', 'start_time', 'end_time'):
        db_manager.update_work_order_time_field(order_id, time_field, None)
    if status_before is not None:
        db_manager.update_work_order_status(order_id, status_before)
    if art_status_before is not None:
        db_manager.update_work_order_art_status(order_id, art_status_before)
    return False, error_msg


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
    except Exception:
        return False
