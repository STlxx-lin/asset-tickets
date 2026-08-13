"""
path_check.py — 路径文件检查对话框

管理员对单个工单的所有关键网络路径做存在性 / 文件数 / 最后修改时间检查，
用于排查「路径不存在」「找不到文件」等问题。
"""
import logging
import os
import shutil
import time

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.database import db_manager
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


def _inspect_path(path: str) -> dict:
    """单次遍历检查路径，返回结果 dict。

    一次 os.walk 同时完成：文件数、最后修改时间、空文件夹数、
    垃圾文件（名称→数量）与大小、有效文件数（避免重复遍历网络盘）。
    """
    result = {
        'exists': False, 'file_count': 0, 'mtime': '--',
        'empty_dirs': 0, 'garbage': {}, 'garbage_size': 0, 'valid_files': 0,
    }
    try:
        local = to_local_path(path)
        if not local or not os.path.exists(local):
            return result
        result['exists'] = True
        latest_mtime = 0
        if os.path.isdir(local):
            for root, dirs, files in os.walk(local):
                if root != local and not dirs and not files:
                    result['empty_dirs'] += 1
                for f in files:
                    full = os.path.join(root, f)
                    if f in GARBAGE_FILES or f.startswith('._') or f.endswith('.tmp'):
                        result['garbage'][f] = result['garbage'].get(f, 0) + 1
                        try:
                            result['garbage_size'] += os.path.getsize(full)
                        except OSError:
                            pass
                    else:
                        result['valid_files'] += 1
                        result['file_count'] += 1
                    try:
                        m = os.path.getmtime(full)
                        latest_mtime = max(latest_mtime, m)
                    except OSError:
                        pass
        else:
            result['file_count'] = 1
            result['valid_files'] = 1
            try:
                latest_mtime = os.path.getmtime(local)
            except OSError:
                pass
        if latest_mtime:
            result['mtime'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest_mtime))
    except Exception as e:
        logger.error(f"检查路径失败 {path}: {e}")
        result['error'] = str(e)
    return result


def build_path_checks(order_data: dict) -> list:
    """构建工单的所有关键路径检查项 [(label, path, note)]。

    note: 附加说明（如「运营已领取」），非空时用于状态覆盖，避免领取后文件移走被误判为异常。
    """
    dept = order_data['department']
    oid = order_data['id']
    model = order_data['model']
    name = order_data['name']

    # 查询运营/销售领取日志，标注已领取的路径
    art_ops_collected = art_sales_collected = False
    edit_ops_collected = edit_sales_collected = False
    try:
        for log in db_manager.get_logs_by_order_id(oid):
            action = log.get('action_type', '')
            details = log.get('details', '')
            if action in ('运营领取素材', '销售领取素材') and f"工单ID={oid}" in details:
                is_ops = action == '运营领取素材'
                if '02视频' in details:
                    if is_ops:
                        edit_ops_collected = True
                    else:
                        edit_sales_collected = True
                else:
                    if is_ops:
                        art_ops_collected = True
                    else:
                        art_sales_collected = True
    except Exception:
        pass

    checks = []
    # 摄影上传（按摄影师）
    for pg in PHOTOGRAPHERS:
        checks.append((f"摄影上传-{pg}", PHOTOGRAPHY_UPLOAD(pg, dept, oid, model, name), ""))
    # 美工链
    checks.append(("美工领取源", ART_GET_IMG_SRC(dept, oid, model, name), ""))
    checks.append(("美工领取存放", ART_GET_IMG_DEST(dept, oid, model, name), ""))
    transit = ART_POST_REVIEW_TRANSIT(dept, oid, model, name)
    checks.append(("美工待审批", transit, ""))
    checks.append(("美工待审批-01运营", os.path.join(transit, '01运营'), ""))
    checks.append(("美工待审批-02销售", os.path.join(transit, '02销售'), ""))
    checks.append(("美工待审批-01运营-不通过", os.path.join(transit, '01运营', '不通过'), ""))
    checks.append(("美工待审批-02销售-不通过", os.path.join(transit, '02销售', '不通过'), ""))
    checks.append(("美工分发运营", ART_DIST_OPS(dept, oid, model, name), "运营已领取" if art_ops_collected else ""))
    checks.append(("美工分发销售", ART_DIST_SALES(dept, oid, model, name), "销售已领取" if art_sales_collected else ""))
    # 剪辑链
    checks.append(("剪辑领取源", EDIT_GET_VIDEO_SRC(dept, oid, model, name), ""))
    checks.append(("剪辑领取存放", EDIT_GET_VIDEO_DEST(dept, oid, model, name), ""))
    edit_transit = EDIT_POST_REVIEW_TRANSIT(dept, oid, model, name)
    checks.append(("剪辑待审核", edit_transit, ""))
    checks.append(("剪辑待审核-不通过", os.path.join(edit_transit, '不通过'), ""))
    checks.append(("剪辑分发运营", EDIT_DIST_OPS(dept, oid, model, name), "运营已领取" if edit_ops_collected else ""))
    checks.append(("剪辑分发销售", EDIT_DIST_SALES(dept, oid, model, name), "销售已领取" if edit_sales_collected else ""))
    # 运营/销售领取
    checks.append(("运营领取源", OPS_GET_SRC(dept, oid, model, name), "已领取" if (art_ops_collected or edit_ops_collected) else ""))
    checks.append(("销售领取源", SALES_GET_SRC(dept, oid, model, name), "已领取" if (art_sales_collected or edit_sales_collected) else ""))
    # DB 成品路径
    checks.append(("成品路径(DB)", order_data.get('edit_product_path') or '', ""))
    return checks


# 状态 → 显示颜色
_STATUS_COLOR = {
    "正常": QColor(40, 167, 69),       # 绿色
    "已领取": QColor(0, 200, 180),     # 青绿色（文件已被运营/销售领取移走，属正常）
    "空": QColor(255, 140, 0),         # 橙色
    "不存在": QColor(220, 53, 69),     # 红色
}


class _PathScanWorker(QThread):
    """后台路径扫描线程：逐项检查并返回结果，避免阻塞界面。"""

    item_done = Signal(int, dict)  # (row, result)
    all_done = Signal()

    def __init__(self, checks):
        super().__init__()
        self.checks = checks

    def run(self):
        for row, (label, path, note) in enumerate(self.checks):
            result = _inspect_path(path)
            result['note'] = note
            self.item_done.emit(row, result)
        self.all_done.emit()

# 系统垃圾文件（检查时标记为无用内容）
GARBAGE_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini', '.thumbnails', '.localized', '.fseventsd', '.Spotlight-V100'}


def show_path_check_dialog(parent, order_data: dict):
    """显示路径文件检查对话框。

    Args:
        parent: 父窗口（MainWindow 实例）
        order_data: 工单数据字典
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"路径文件检查 - {order_data['id']}")
    dialog.setMinimumSize(1200, 700)
    dialog.resize(1260, 740)
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
    table.setColumnCount(9)
    table.setHorizontalHeaderLabels(["路径用途", "路径", "状态", "文件数", "最后修改", "无用内容", "推荐删除", "打开", "删除"])
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
    # 打开/删除按钮列固定宽度，避免按钮文字显示不全
    table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
    table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
    table.setColumnWidth(7, 110)
    table.setColumnWidth(8, 110)
    # 行高固定，保证按钮完整显示
    table.verticalHeader().setDefaultSectionSize(46)
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    main_layout.addWidget(table, 1)

    # 底部按钮
    button_layout = QHBoxLayout()
    summary_label = QLabel("")
    summary_label.setStyleSheet("color: #9ba3b0;")
    button_layout.addWidget(summary_label)

    # 折叠不存在的路径
    show_missing_cb = QCheckBox("显示不存在的路径")
    show_missing_cb.setStyleSheet("color: #9ba3b0; font-size: 13px;")
    show_missing_cb.setChecked(False)
    button_layout.addWidget(show_missing_cb)

    button_layout.addStretch()
    refresh_btn = QPushButton("🔄 刷新")
    refresh_btn.setStyleSheet(
        "background-color: #4f8ef7; color: white; border: none; border-radius: 6px;"
        " padding: 10px 28px; font-size: 14px; font-weight: bold;"
    )
    close_btn = QPushButton("关闭")
    close_btn.setProperty("type", "cancel")
    button_layout.addWidget(refresh_btn)
    button_layout.addWidget(close_btn)
    main_layout.addLayout(button_layout)

    missing_rows: list = []
    worker = None
    checks: list = []
    counts = {'ok': 0, 'empty': 0, 'missing': 0}
    btn_style = (
        "color: white; border: none; border-radius: 4px;"
        " padding: 7px 18px; font-size: 13px; font-weight: bold; min-width: 60px;"
    )

    def apply_fold():
        """根据勾选状态折叠/展开「不存在」的路径行"""
        show_missing = show_missing_cb.isChecked()
        for r in missing_rows:
            table.setRowHidden(r, not show_missing)

    def on_item_done(row, result):
        """后台线程逐项检查完成后，填充该行完整结果"""
        if row >= len(checks):
            return
        label, path, note = checks[row]

        # 状态判定
        if result.get('error'):
            status = f"检查失败: {result['error']}"
        elif result['exists']:
            status = "正常" if result['file_count'] > 0 else "空"
        else:
            status = "不存在"
        if note and status == "不存在":
            status = "已领取"
        if status in ("正常", "已领取"):
            counts['ok'] += 1
        elif status == "空":
            counts['empty'] += 1
        else:
            counts['missing'] += 1
            missing_rows.append(row)

        # 无用内容 + 推荐删除
        useless_text = "--"
        recommend_text = "--"
        has_useless = False
        recommend_del = False
        if status in ("正常", "空"):
            parts = []
            if result['empty_dirs']:
                parts.append(f"空文件夹×{result['empty_dirs']}")
            for name, cnt in sorted(result['garbage'].items()):
                parts.append(f"{name}×{cnt}")
            if parts:
                if result['garbage_size'] > 0:
                    parts.append(f"共 {result['garbage_size'] / 1024:.1f} KB")
                useless_text = "、".join(parts)
                has_useless = True
            else:
                useless_text = "无"
            if status == "空" or (result['valid_files'] == 0 and (result['empty_dirs'] > 0 or result['garbage'])):
                recommend_text = "推荐"
                recommend_del = True
            elif result['valid_files'] > 0:
                recommend_text = "不推荐"

        items = [
            QTableWidgetItem(label),
            QTableWidgetItem(path),
            QTableWidgetItem(status),
            QTableWidgetItem(str(result['file_count']) if status in ("正常", "空") else "--"),
            QTableWidgetItem(result['mtime']),
            QTableWidgetItem(useless_text),
            QTableWidgetItem(recommend_text),
        ]
        color = _STATUS_COLOR.get(status, QColor(220, 53, 69))
        for col, item in enumerate(items):
            if col == 5 and has_useless:
                item.setForeground(QColor(255, 140, 0))  # 有无用内容,橙色提示
            elif col == 6 and recommend_del:
                item.setForeground(QColor(220, 53, 69))  # 推荐删除,红色提示
            elif col == 6 and recommend_text == "不推荐":
                item.setForeground(QColor(120, 130, 145))  # 不推荐,灰色
            else:
                item.setForeground(color if col in (2,) else QColor(232, 234, 237))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, col, item)
        # 整行状态着色
        if status not in ("正常", "已领取"):
            for col in range(7):
                table.item(row, col).setBackground(QColor(60, 30, 35) if status != "空" else QColor(58, 46, 28))
        elif has_useless or recommend_del:
            for col in range(7):
                table.item(row, col).setBackground(QColor(58, 46, 28))

        # 打开 / 删除 按钮（最右侧两列）
        exists = result['exists']

        def make_open_btn(path):
            btn = QPushButton("打开")
            btn.setStyleSheet(f"background-color: #4f8ef7;{btn_style}")
            btn.setEnabled(exists)
            btn.setToolTip("在资源管理器中打开该路径" if exists else "路径不存在，无法打开")
            btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(path)))
            return btn

        def make_del_btn(row, label, path):
            btn = QPushButton("删除")
            btn.setStyleSheet(f"background-color: #dc3545;{btn_style}")
            btn.setEnabled(exists)
            btn.setToolTip("删除该路径（含全部内容，不可恢复）" if exists else "路径不存在")
            btn.clicked.connect(lambda: on_delete_path(row, label, path))
            return btn

        open_widget = QWidget()
        open_layout = QHBoxLayout(open_widget)
        open_layout.setContentsMargins(4, 2, 4, 2)
        open_layout.setAlignment(Qt.AlignCenter)
        open_layout.addWidget(make_open_btn(path))
        table.setCellWidget(row, 7, open_widget)

        del_widget = QWidget()
        del_layout = QHBoxLayout(del_widget)
        del_layout.setContentsMargins(4, 2, 4, 2)
        del_layout.setAlignment(Qt.AlignCenter)
        del_layout.addWidget(make_del_btn(row, label, path))
        table.setCellWidget(row, 8, del_widget)

        summary_label.setText(
            f"检查中… 正常 {counts['ok']} · 空 {counts['empty']} · 不存在/异常 {counts['missing']}"
        )

    def on_all_done():
        """全部检查完成"""
        dialog.unsetCursor()
        refresh_btn.setEnabled(True)
        summary_label.setText(
            f"共 {len(checks)} 项：正常 {counts['ok']} · 空 {counts['empty']} · 不存在/异常 {counts['missing']}（已折叠）"
        )
        show_missing_cb.setText(f"显示不存在的路径 ({counts['missing']})")
        apply_fold()

    def run_check():
        nonlocal worker
        # 防重复：上一次扫描仍在进行时忽略
        if worker is not None and worker.isRunning():
            return
        dialog.setCursor(Qt.CursorShape.WaitCursor)
        refresh_btn.setEnabled(False)
        counts.update(ok=0, empty=0, missing=0)
        missing_rows.clear()
        checks.clear()
        checks.extend(build_path_checks(order_data))
        table.setRowCount(len(checks))
        # 先立即填充 用途/路径/状态(检查中)，其余列等待后台结果
        for row, (label, path, _note) in enumerate(checks):
            for col, text in ((0, label), (1, path), (2, "检查中…")):
                item = QTableWidgetItem(text)
                item.setForeground(QColor(150, 155, 165))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, col, item)
        summary_label.setText(f"正在检查 {len(checks)} 项路径…")
        worker = _PathScanWorker(checks)
        worker.item_done.connect(on_item_done)
        worker.all_done.connect(on_all_done)
        worker.start()

    def on_delete_path(row, label, path):
        """删除指定路径（目录递归或文件），带二次确认"""
        try:
            if not os.path.exists(path):
                QMessageBox.information(dialog, "提示", f"路径不存在，无需删除：\n{path}")
                return
            # 统计内容数量，供确认框展示
            if os.path.isdir(path):
                total = sum(len(files) for _root, _dirs, files in os.walk(path))
                content_desc = f"共 {total} 个文件"
            else:
                content_desc = "单个文件"
            ret = QMessageBox.warning(
                dialog,
                "确认删除",
                f"确定要删除以下路径吗？\n\n用途：{label}\n路径：{path}\n\n{content_desc}，删除后不可恢复！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                return
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            QMessageBox.information(dialog, "删除成功", f"已删除：\n{path}")
            run_check()  # 刷新检查结果
        except Exception as e:
            logger.error(f"删除路径失败 {path}: {e}")
            QMessageBox.critical(dialog, "删除失败", f"删除路径失败：\n{path}\n原因: {e}")

    # 双击路径单元格 → 资源管理器打开
    def on_cell_double_clicked(row, column):
        if column == 1 and row < table.rowCount():
            item = table.item(row, 1)
            if item:
                p = item.text()
                if os.path.exists(p):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(p))
    table.cellDoubleClicked.connect(on_cell_double_clicked)

    refresh_btn.clicked.connect(run_check)
    close_btn.clicked.connect(dialog.reject)
    show_missing_cb.toggled.connect(lambda _checked: apply_fold())

    run_check()
    dialog.exec()
