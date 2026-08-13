"""
path_check.py — 路径文件检查对话框

管理员对单个工单的所有关键网络路径做存在性 / 文件数 / 最后修改时间检查，
用于排查「路径不存在」「找不到文件」等问题。
"""
import logging
import os
import time

from PySide6.QtCore import Qt
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
    ART_DIST_OPS,
    ART_DIST_SALES,
    ART_GET_IMG_DEST,
    ART_GET_IMG_SRC,
    ART_POST_REVIEW_TRANSIT,
    EDIT_DIST_OPS,
    EDIT_DIST_SALES,
    EDIT_GET_VIDEO_DEST,
    EDIT_GET_VIDEO_SRC,
    EDIT_POST_REVIEW_TRANSIT,
    OPS_GET_SRC,
    PHOTOGRAPHERS,
    PHOTOGRAPHY_UPLOAD,
    SALES_GET_SRC,
    to_local_path,
)

logger = logging.getLogger(__name__)


def _check_path(path: str) -> tuple:
    """检查单个路径，返回 (status, file_count, mtime_str)。

    status: 正常 / 空 / 不存在 / 检查失败:xxx
    """
    try:
        local = to_local_path(path)
        if not local or not os.path.exists(local):
            return "不存在", 0, "--"
        file_count = 0
        latest_mtime = 0
        if os.path.isdir(local):
            for root, _dirs, files in os.walk(local):
                file_count += len(files)
                for f in files:
                    try:
                        m = os.path.getmtime(os.path.join(root, f))
                        latest_mtime = max(latest_mtime, m)
                    except OSError:
                        pass
        else:
            file_count = 1
            try:
                latest_mtime = os.path.getmtime(local)
            except OSError:
                pass
        status = "正常" if file_count > 0 else "空"
        mtime_str = "--"
        if latest_mtime:
            mtime_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest_mtime))
        return status, file_count, mtime_str
    except Exception as e:
        logger.error(f"检查路径失败 {path}: {e}")
        return f"检查失败: {e}", 0, "--"


def build_path_checks(order_data: dict) -> list:
    """构建工单的所有关键路径检查项 [(label, path)]"""
    dept = order_data['department']
    oid = order_data['id']
    model = order_data['model']
    name = order_data['name']

    checks = []
    # 摄影上传（按摄影师）
    for pg in PHOTOGRAPHERS:
        checks.append((f"摄影上传-{pg}", PHOTOGRAPHY_UPLOAD(pg, dept, oid, model, name)))
    # 美工链
    checks.append(("美工领取源", ART_GET_IMG_SRC(dept, oid, model, name)))
    checks.append(("美工领取存放", ART_GET_IMG_DEST(dept, oid, model, name)))
    transit = ART_POST_REVIEW_TRANSIT(dept, oid, model, name)
    checks.append(("美工待审批", transit))
    checks.append(("美工待审批-01运营", os.path.join(transit, '01运营')))
    checks.append(("美工待审批-02销售", os.path.join(transit, '02销售')))
    checks.append(("美工分发运营", ART_DIST_OPS(dept, oid, model, name)))
    checks.append(("美工分发销售", ART_DIST_SALES(dept, oid, model, name)))
    # 剪辑链
    checks.append(("剪辑领取源", EDIT_GET_VIDEO_SRC(dept, oid, model, name)))
    checks.append(("剪辑领取存放", EDIT_GET_VIDEO_DEST(dept, oid, model, name)))
    checks.append(("剪辑待审核", EDIT_POST_REVIEW_TRANSIT(dept, oid, model, name)))
    checks.append(("剪辑分发运营", EDIT_DIST_OPS(dept, oid, model, name)))
    checks.append(("剪辑分发销售", EDIT_DIST_SALES(dept, oid, model, name)))
    # 运营/销售领取
    checks.append(("运营领取源", OPS_GET_SRC(dept, oid, model, name)))
    checks.append(("销售领取源", SALES_GET_SRC(dept, oid, model, name)))
    # DB 成品路径
    checks.append(("成品路径(DB)", order_data.get('edit_product_path') or ''))
    return checks


# 状态 → 显示颜色
_STATUS_COLOR = {
    "正常": QColor(40, 167, 69),       # 绿色
    "空": QColor(255, 140, 0),         # 橙色
    "不存在": QColor(220, 53, 69),     # 红色
}


def show_path_check_dialog(parent, order_data: dict):
    """显示路径文件检查对话框。

    Args:
        parent: 父窗口（MainWindow 实例）
        order_data: 工单数据字典
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"路径文件检查 - {order_data['id']}")
    dialog.setMinimumSize(950, 600)
    dialog.resize(950, 620)
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

    # 标题与工单信息
    title_label = QLabel(
        f"路径文件检查 - {order_data['id']}  {order_data.get('model', '')} {order_data.get('name', '')}"
    )
    title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
    main_layout.addWidget(title_label)

    info_label = QLabel(
        f"产线: {order_data.get('department', '')}    状态: {order_data.get('status', '')}    "
        f"美工状态: {order_data.get('art_status') or '--'}"
    )
    info_label.setStyleSheet("color: #9ba3b0;")
    main_layout.addWidget(info_label)

    # 结果表格
    table = QTableWidget()
    table.setColumnCount(5)
    table.setHorizontalHeaderLabels(["路径用途", "路径", "状态", "文件数", "最后修改"])
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    main_layout.addWidget(table, 1)

    # 底部按钮
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

    def run_check():
        # 网络盘检查可能耗时，显示等待光标
        dialog.setCursor(Qt.CursorShape.WaitCursor)
        try:
            checks = build_path_checks(order_data)
            table.setRowCount(len(checks))
            ok_count = empty_count = missing_count = 0
            for row, (label, path) in enumerate(checks):
                status, file_count, mtime_str = _check_path(path)
                if status == "正常":
                    ok_count += 1
                elif status == "空":
                    empty_count += 1
                else:
                    missing_count += 1

                items = [
                    QTableWidgetItem(label),
                    QTableWidgetItem(path),
                    QTableWidgetItem(status),
                    QTableWidgetItem(str(file_count) if status in ("正常", "空") else "--"),
                    QTableWidgetItem(mtime_str),
                ]
                color = _STATUS_COLOR.get(status, QColor(220, 53, 69))
                for col, item in enumerate(items):
                    item.setForeground(color if col in (2,) else QColor(232, 234, 237))
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row, col, item)
                # 整行状态着色
                if status != "正常":
                    for col in range(5):
                        table.item(row, col).setBackground(QColor(60, 30, 35) if status != "空" else QColor(58, 46, 28))
            summary_label.setText(
                f"共 {len(checks)} 项：正常 {ok_count} · 空 {empty_count} · 不存在/异常 {missing_count}"
            )
        finally:
            dialog.unsetCursor()

    refresh_btn.clicked.connect(run_check)
    close_btn.clicked.connect(dialog.reject)

    run_check()
    dialog.exec()
