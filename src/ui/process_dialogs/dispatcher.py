"""
dispatcher.py — 工单处理对话框路由器。

根据 parent.role（及 parent.roles 角色集合）将调用分发到对应角色模块的顶层函数。
不包含任何业务逻辑，仅做路由。
"""
from PySide6.QtWidgets import QMessageBox

from src.core.database import db_manager


def show_process_order_dialog(parent, order_data, callbacks):
    """
    工单处理对话框统一入口。

    Args:
        parent:     父窗口（MainWindow 实例），用于 QDialog parent 与读取 parent.role
        order_data: 工单数据字典
        callbacks:  回调字典，含以下键：
                      'update_status' -> Callable[[str, str], None]
                      'add_file_task' -> Callable[..., None]
                      'log_action'    -> Callable[[str, str], None]
    """
    # 办理前从数据库重新查询工单最新状态（列表数据可能已过期：
    # 如审核在其他客户端已完成、状态被回滚等），避免对话框基于快照做出错误的按钮/门禁判断
    fresh = db_manager.get_work_order_by_id(order_data['id'])
    if fresh is None:
        QMessageBox.warning(parent, "提示",
                            f"工单 {order_data['id']} 不存在（可能已被删除），无法办理")
        return
    order_data = fresh

    role = parent.role
    # 支持多角色（角色合并登录时为列表，如 ['视频后期审核', '美工后期审批']）
    roles = getattr(parent, 'roles', None) or ([role] if role else [])

    # 同时拥有「视频后期审核」+「美工后期审批」（登录合并为「后期审批」）→ 合并审批界面
    if role == "后期审批" or ("视频后期审核" in roles and "美工后期审批" in roles):
        from .post_review_combined import show_post_review_combined_dialog
        show_post_review_combined_dialog(parent, order_data, callbacks)

    elif role in ["采购", "摄影"]:
        from .photography import show_photography_dialog
        show_photography_dialog(parent, order_data, callbacks)

    elif role == "视频审核":
        from .video_review import show_video_review_dialog
        show_video_review_dialog(parent, order_data, callbacks)

    elif role == "视频后期审核":
        from .video_post_review import show_video_post_review_dialog
        show_video_post_review_dialog(parent, order_data, callbacks)

    elif role == "美工后期审批":
        from .art_post_review import show_art_post_review_dialog
        show_art_post_review_dialog(parent, order_data, callbacks)

    elif role == "美工":
        from .art import show_art_dialog
        show_art_dialog(parent, order_data, callbacks)

    elif role == "剪辑":
        from .editing import show_editing_dialog
        show_editing_dialog(parent, order_data, callbacks)

    elif role == "运营":
        from .ops import show_ops_dialog
        show_ops_dialog(parent, order_data, callbacks)

    elif role == "销售":
        from .sales import show_sales_dialog
        show_sales_dialog(parent, order_data, callbacks)
