"""对话框辅助模块 — 统一错误/完成弹窗，避免各流程对话框重复实现。"""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox


def show_api_update_error(parent, error_msg):
    """API 更新失败提示框。

    Args:
        parent: 父窗口
        error_msg: 错误详情
    """
    QMessageBox.warning(parent, "API更新失败", error_msg)


def show_path_result(parent, title, text, open_path):
    """带“打开”按钮的结果提示框，点击“打开”时用系统资源管理器打开指定路径。

    Args:
        parent: 父窗口
        title: 窗口标题
        text: 提示内容
        open_path: “打开”按钮打开的路径
    """
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    open_btn = msg.addButton("打开", QMessageBox.ActionRole)
    msg.addButton("确定", QMessageBox.AcceptRole)
    msg.exec()
    if msg.clickedButton() == open_btn and open_path:
        QDesktopServices.openUrl(QUrl.fromLocalFile(open_path))
