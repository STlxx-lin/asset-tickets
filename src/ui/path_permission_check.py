"""
path_permission_check.py — 路径权限检查对话框

不同角色检查其业务相关网络路径的读/写权限；管理员检查全部路径。
用于排查网络共享盘连接、读写权限配置问题。

检查的是各环节的「基础目录」（不含具体工单目录），不依赖某个工单存在。
"""
import logging
import os
import time

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.core.paths import (
    ART_ROOT,
    CENTER_ROOT,
    RAW_ROOT,
    VIDEO_ROOT,
    VOLUMES,
)

logger = logging.getLogger(__name__)

# 各角色需要检查的路径（用途, 路径, 需要可写）
# 注意：实际目录结构为 02图像部/01美工部/{产线}/01待审批/{工单}，
#       产线级环节目录用 {dept} 占位符，检查时按用户所属产线展开
ROLE_PATHS = {
    "摄影": [
        ("原始素材-上传根", os.path.join(RAW_ROOT, '01原始素材'), True),
        ("美工待领取-分发", os.path.join(RAW_ROOT, '02美工待领取'), True),
    ],
    "美工": [
        ("美工待领取-领取源", os.path.join(RAW_ROOT, '02美工待领取'), False),
        ("美工部-领取存放", ART_ROOT, True),
        ("美工部-待审批", os.path.join(ART_ROOT, '{dept}', '01待审批'), True),
    ],
    "剪辑": [
        ("美工待领取-视频源", os.path.join(RAW_ROOT, '02美工待领取', '02视频'), False),
        ("视频部-领取存放", VIDEO_ROOT, True),
        ("视频部-待审核", os.path.join(VIDEO_ROOT, '{dept}', '01待审核'), True),
    ],
    "视频审核": [
        ("原始素材-审核源", RAW_ROOT, False),
        ("美工待领取", os.path.join(RAW_ROOT, '02美工待领取'), False),
    ],
    "视频后期审核": [
        ("视频部-待审核", os.path.join(VIDEO_ROOT, '{dept}', '01待审核'), True),
    ],
    "美工后期审批": [
        ("美工部-待审批", os.path.join(ART_ROOT, '{dept}', '01待审批'), True),
    ],
    "运营": [
        ("素材中心-运营部", os.path.join(CENTER_ROOT, '01运营部'), False),
    ],
    "销售": [
        ("素材中心-销售部", os.path.join(CENTER_ROOT, '02销售部'), False),
    ],
    "采购": [
        ("共享盘根", VOLUMES, False),
    ],
}

# 管理员检查全部路径（去重）
ADMIN_PATHS: list = []
_seen = set()
for _paths in ROLE_PATHS.values():
    for label, path, need_write in _paths:
        key = (label, path)
        if key not in _seen:
            _seen.add(key)
            ADMIN_PATHS.append((label, path, need_write))


def _expand_checks(paths: list, departments: list) -> list:
    """将含 {dept} 占位符的路径按用户所属产线展开。

    返回 [(label, path, need_write)]，产线级路径标签附带产线名便于区分。
    """
    expanded = []
    for label, path, need_write in paths:
        if '{dept}' in path:
            for dept in departments:
                expanded.append((f"{label}-{dept}", path.replace('{dept}', dept), need_write))
        else:
            expanded.append((label, path, need_write))
    return expanded


def _check_read(path: str) -> bool:
    """尝试列出目录内容检测读权限"""
    try:
        os.listdir(path)
        return True
    except Exception:
        return False


def _check_write(path: str) -> bool:
    """尝试创建并删除临时文件检测写权限"""
    test_file = os.path.join(path, f'.perm_test_{os.getpid()}_{int(time.time())}')
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        return True
    except Exception:
        return False
    finally:
        try:
            if os.path.exists(test_file):
                os.remove(test_file)
        except Exception:
            pass


def check_path_permission(path: str, need_write: bool) -> tuple:
    """检查单个路径权限，返回 (exists, readable, writable, status)"""
    try:
        if not os.path.exists(path):
            return False, False, False, "不存在"
        readable = _check_read(path)
        writable = True
        if need_write:
            writable = _check_write(path)
        if not readable:
            status = "不可访问"
        elif need_write and not writable:
            status = "只读"
        else:
            status = "正常"
        return True, readable, writable, status
    except Exception as e:
        logger.error(f"检查路径权限失败 {path}: {e}")
        return False, False, False, f"检查失败: {e}"


_STATUS_COLOR = {
    "正常": QColor(40, 167, 69),       # 绿色
    "只读": QColor(255, 140, 0),       # 橙色
    "不可访问": QColor(220, 53, 69),   # 红色
    "不存在": QColor(220, 53, 69),     # 红色
}


class _PermissionScanWorker(QThread):
    """后台权限检查线程：逐项检查并返回结果，避免网络盘超时阻塞界面。"""

    item_done = Signal(int, tuple)  # (row, (exists, readable, writable, status))
    all_done = Signal()

    def __init__(self, checks):
        super().__init__()
        self.checks = checks

    def run(self):
        for row, (label, path, need_write) in enumerate(self.checks):
            # 对话框关闭或用户取消时提前退出，避免线程泄漏与访问已销毁控件
            if self.isInterruptionRequested():
                return
            result = check_path_permission(path, need_write)
            self.item_done.emit(row, result)
        self.all_done.emit()


def show_path_permission_dialog(parent, roles: list, departments: list):
    """显示路径权限检查对话框。

    Args:
        parent: 父窗口（MainWindow 实例）
        roles: 当前角色集合；管理员传 ['管理员'] 时检查全部路径
        departments: 用户所属产线列表（产线级目录按产线展开检查）
    """
    if '管理员' in roles:
        checks = _expand_checks(ADMIN_PATHS, departments)
        title_role = "管理员（全部路径）"
    else:
        checks = []
        for role in roles:
            checks.extend(_expand_checks(ROLE_PATHS.get(role, []), departments))
        title_role = " / ".join(roles) if roles else "未知角色"

    dialog = QDialog(parent)
    dialog.setWindowTitle("路径权限检查")
    dialog.setMinimumSize(900, 520)
    dialog.resize(900, 540)
    dialog.setStyleSheet("""
        QDialog {
            background-color: #23272e;
            color: #ffffff;
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            font-size: 13px;
        }
        QLabel {
            color: #e8eaed;
        }
        QTableWidget {
            background-color: #2a2e37;
            border: 1px solid #3a3f4b;
            border-radius: 6px;
            color: #e8eaed;
            gridline-color: #3a3f4b;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QHeaderView::section {
            background-color: #323742;
            color: #9ba3b0;
            border: none;
            border-right: 1px solid #3a3f4b;
            padding: 6px;
            font-weight: bold;
        }
        QPushButton {
            background-color: #4f8ef7;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #6ba3ff;
        }
        QPushButton[type="cancel"] {
            background-color: #3a3f4b;
        }
        QPushButton[type="cancel"]:hover {
            background-color: #4a5060;
        }
    """)

    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(12)

    title_label = QLabel(f"路径权限检查 - {title_role}")
    title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
    main_layout.addWidget(title_label)

    tip_label = QLabel("检查各环节基础目录的读/写权限（写权限通过创建临时文件验证，检查后自动删除）")
    tip_label.setStyleSheet("color: #9ba3b0;")
    tip_label.setWordWrap(True)
    main_layout.addWidget(tip_label)

    table = QTableWidget()
    table.setColumnCount(6)
    table.setHorizontalHeaderLabels(["路径用途", "路径", "状态", "存在", "可读", "可写"])
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    main_layout.addWidget(table, 1)

    button_layout = QHBoxLayout()
    summary_label = QLabel("")
    summary_label.setStyleSheet("color: #9ba3b0;")
    button_layout.addWidget(summary_label)
    button_layout.addStretch()
    refresh_btn = QPushButton("重新检查")
    close_btn = QPushButton("关闭")
    close_btn.setProperty("type", "cancel")
    button_layout.addWidget(refresh_btn)
    button_layout.addWidget(close_btn)
    main_layout.addLayout(button_layout)

    worker = None
    counts = {'ok': 0, 'warn': 0, 'fail': 0}

    def on_item_done(row, result):
        if row >= len(checks):
            return
        label, path, _need_write = checks[row]
        _exists, _readable, _writable, status = result
        if status == "正常":
            counts['ok'] += 1
        elif status == "只读":
            counts['warn'] += 1
        else:
            counts['fail'] += 1

        items = [
            QTableWidgetItem(label),
            QTableWidgetItem(path),
            QTableWidgetItem(status),
            QTableWidgetItem("✓" if _exists else "✗"),
            QTableWidgetItem("✓" if _readable else "✗"),
            QTableWidgetItem("✓" if _writable else "✗"),
        ]
        color = _STATUS_COLOR.get(status, QColor(220, 53, 69))
        for col, item in enumerate(items):
            item.setForeground(color if col == 2 else QColor(232, 234, 237))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, col, item)
        if status != "正常":
            bg = QColor(60, 30, 35) if status != "只读" else QColor(58, 46, 28)
            for col in range(6):
                table.item(row, col).setBackground(bg)
        summary_label.setText(
            f"检查中… 正常 {counts['ok']} · 只读 {counts['warn']} · 不存在/不可访问 {counts['fail']}"
        )

    def on_all_done():
        dialog.unsetCursor()
        refresh_btn.setEnabled(True)
        summary_label.setText(
            f"共 {len(checks)} 项：正常 {counts['ok']} · 只读 {counts['warn']} · 不存在/不可访问 {counts['fail']}"
        )

    def run_check():
        nonlocal worker
        # 防重复：上一次检查仍在进行时忽略
        if worker is not None and worker.isRunning():
            return
        dialog.setCursor(Qt.CursorShape.WaitCursor)
        refresh_btn.setEnabled(False)
        counts.update(ok=0, warn=0, fail=0)
        table.setRowCount(len(checks))
        # 先立即填充 用途/路径/状态(检查中)
        for row, (label, path, _need_write) in enumerate(checks):
            for col, text in ((0, label), (1, path), (2, "检查中…")):
                item = QTableWidgetItem(text)
                item.setForeground(QColor(150, 155, 165))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, col, item)
        summary_label.setText(f"正在检查 {len(checks)} 项路径…")
        worker = _PermissionScanWorker(checks)
        worker.item_done.connect(on_item_done)
        worker.all_done.connect(on_all_done)
        worker.start()

    refresh_btn.clicked.connect(run_check)
    close_btn.clicked.connect(dialog.reject)

    def stop_worker():
        """关闭对话框时中断并等待后台检查线程，避免 "QThread: Destroyed while thread is still running" 崩溃"""
        nonlocal worker
        if worker is not None and worker.isRunning():
            worker.requestInterruption()
            if not worker.wait(5000):
                logger.warning("权限检查线程在 5 秒内未退出，强制继续关闭对话框")
    dialog.finished.connect(lambda _result: stop_worker())

    run_check()
    dialog.exec()
