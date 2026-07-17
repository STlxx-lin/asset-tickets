"""
process_dialogs 包入口。

对外只暴露一个调度函数 show_process_order_dialog，
MainWindow 通过此函数将工单处理分发给对应角色模块。
"""
from .dispatcher import show_process_order_dialog  # noqa: F401

__all__ = ['show_process_order_dialog']
