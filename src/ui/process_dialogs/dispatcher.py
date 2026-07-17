"""
dispatcher.py — 工单处理对话框路由器。

根据 parent.role 将调用分发到对应角色模块的顶层函数。
不包含任何业务逻辑，仅做路由。
"""


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
    role = parent.role

    if role in ["采购", "摄影"]:
        from .photography import show_photography_dialog
        show_photography_dialog(parent, order_data, callbacks)

    elif role == "视频审核":
        from .video_review import show_video_review_dialog
        show_video_review_dialog(parent, order_data, callbacks)

    elif role == "视频后期审核":
        from .video_post_review import show_video_post_review_dialog
        show_video_post_review_dialog(parent, order_data, callbacks)

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
