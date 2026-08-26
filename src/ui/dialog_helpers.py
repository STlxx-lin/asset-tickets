"""对话框辅助模块 — 统一错误/完成弹窗及跨平台安全交互控件，避免各流程对话框重复实现。"""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QMessageBox


class ClickablePathLabel(QLabel):
    """支持点击通过系统文件管理器打开路径的标签组件（跨平台安全，避免 monkey-patching mousePressEvent）。"""

    def __init__(self, path: str = "", tooltip_prefix: str = "点击打开：", parent=None):
        super().__init__(path, parent)
        self._path = path
        self._tooltip_prefix = tooltip_prefix
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QLabel {
                color: #4f8ef7;
                text-decoration: underline;
                padding: 4px 8px;
                border-radius: 3px;
            }
            QLabel:hover {
                background-color: #232732;
                color: #6ba3ff;
            }
        """)
        self._update_tooltip()

    def setPath(self, new_path: str):
        self._path = new_path
        self.setText(new_path)
        self._update_tooltip()

    def _update_tooltip(self):
        if self._path:
            self.setToolTip(f"{self._tooltip_prefix}{self._path}" if self._tooltip_prefix else self._path)
        else:
            self.setToolTip("")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._path))
        super().mousePressEvent(event)


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
    open_btn = msg.addButton("打开", QMessageBox.ButtonRole.ActionRole)
    msg.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
    msg.exec()
    if msg.clickedButton() == open_btn and open_path:
        QDesktopServices.openUrl(QUrl.fromLocalFile(open_path))

