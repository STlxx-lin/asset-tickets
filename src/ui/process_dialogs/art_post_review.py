"""
show_art_post_review_dialog — 美工后期审批 工单处理对话框

美工分发成品后先复制到「美工待审批」中转目录（ART_POST_REVIEW_TRANSIT，
目录下分 01运营 / 02销售 子目录），状态变为「美工后期审核中」；
本对话框审批该中转目录中的成品：
- 审核通过：文件移动（move）到运营/销售目录，状态变为「后期已完成」，通知运营/销售领取
- 退回：勾选文件移入「不通过」文件夹并记录原因，状态变为「美工后期重新制作」，通知美工重做
"""
import logging
import os
import shutil

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (
    QDesktopServices,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.config import get_feature_enabled
from src.core.database import db_manager
from src.core.notification import send_notification
from src.core.paths import (
    ART_DIST_OPS,
    ART_DIST_SALES,
    ART_POST_REVIEW_TRANSIT,
    IMG_EXTS,
    VID_EXTS,
)
from src.core.status_sync import update_local_status_only
from src.ui.video_preview import VideoPreviewWidget

logger = logging.getLogger(__name__)

# 待审批中转目录下的两个子目录，与美工分发运营/销售一一对应
_SUB_DIRS = ("01运营", "02销售")
# 与 _SUB_DIRS 一一对应的侧别显示名（拆分为「运营通过」「销售通过」两个审批按钮）
_SIDE_LABELS = ("运营", "销售")


def show_art_post_review_dialog(parent, order_data, callbacks):
    """
    处理工单对话框入口。

    Args:
        parent: 父窗口（MainWindow 实例）
        order_data: 工单数据字典
        callbacks: 回调字典，含 update_status / add_file_task / log_action
    """
    def is_art_post_review_enabled() -> bool:
        return get_feature_enabled('art_post_review_enabled')

    # 检查美工后期审批功能开关
    if not is_art_post_review_enabled():
        QMessageBox.information(parent, "功能已关闭",
            "美工后期审批功能当前已关闭。\n如需开启，请管理员前往【系统设置 → 功能设置】进行配置。"
        )
        return
    # 只有美工链状态为「美工后期审核中」才可审批（优先读 art_status，兼容旧数据回退全局 status）
    art_status = order_data.get('art_status') or order_data.get('status', '')
    if art_status != '美工后期审核中':
        QMessageBox.information(parent, "提示",
            f"当前美工状态为【{art_status}】\n只有美工状态为【美工后期审核中】的工单才可进行美工后期审批。"
        )
        return

    transit_root = ART_POST_REVIEW_TRANSIT(order_data['department'], order_data['id'], order_data['model'], order_data['name'])
    if not os.path.exists(transit_root):
        QMessageBox.warning(parent, "错误",
            f"找不到该工单的待审批目录：\n{transit_root}\n请联系美工确认是否已分发成品并提交审批。"
        )
        return

    dialog = QDialog(parent)
    dialog.setWindowTitle(f"美工后期审批 - {order_data['id']}")
    dialog.setMinimumWidth(1400)
    dialog.setMinimumHeight(700)
    dialog.resize(1400, 720)
    build_art_post_review_ui(dialog, dialog, parent, order_data, callbacks)
    dialog.exec()


def build_art_post_review_ui(container, dialog, parent, order_data, callbacks):
    """
    构建美工后期审批界面内容（供单独对话框与合并审批界面复用）。

    Args:
        container: UI 挂载容器（单独对话框时为 QDialog 本身，合并界面时为页面容器）
        dialog:    弹窗主体（用于 accept/reject 与消息框父窗口）
        parent:    父窗口（MainWindow 实例）
        order_data: 工单数据字典
        callbacks:  回调字典，含 update_status / add_file_task / log_action
    """
    # ---- 解包 callbacks ----
    _add_file_task = callbacks['add_file_task']
    _log_action    = callbacks['log_action']

    # 待审批中转目录（01运营 / 02销售 子目录）与审批通过后的目标目录
    transit_root = ART_POST_REVIEW_TRANSIT(order_data['department'], order_data['id'], order_data['model'], order_data['name'])
    sub_dirs = [os.path.join(transit_root, name) for name in _SUB_DIRS]
    targets = [
        ART_DIST_OPS(order_data['department'], order_data['id'], order_data['model'], order_data['name']),
        ART_DIST_SALES(order_data['department'], order_data['id'], order_data['model'], order_data['name']),
    ]
    art_status = order_data.get('art_status') or order_data.get('status', '')

    # 设置弹窗样式
    dialog.setStyleSheet("""
        QDialog {
            background-color: #2E2E2E;
            color: #FFFFFF;
        }
        QGroupBox {
            border: 1px solid #555555;
            border-radius: 5px;
            margin-top: 1ex;
            font-size: 14px;
            font-weight: bold;
            color: #FFFFFF;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 10px;
            color: #FFFFFF;
        }
        QLineEdit, QTextEdit, QLabel {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px 12px;
            color: #FFFFFF;
            font-size: 14px;
        }
        QLabel {
            color: #FFFFFF;
            font-size: 14px;
        }
        QPushButton {
            background-color: #0078d4;
            color: #FFFFFF;
            border: none;
            border-radius: 4px;
            padding: 10px 24px;
            font-size: 14px;
            font-weight: bold;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton[type="cancel"] {
            background-color: #555555;
        }
        QPushButton[type="cancel"]:hover {
            background-color: #666666;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            border-radius: 4px;
        }
        QTabBar::tab {
            background-color: #3c3c3c;
            color: #FFFFFF;
            padding: 8px 20px;
            border: 1px solid #555555;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            font-size: 14px;
            font-weight: bold;
        }
        QTabBar::tab:selected {
            background-color: #0078d4;
        }
        QTabBar::tab:hover:!selected {
            background-color: #505050;
        }
    """)
    main_layout = QVBoxLayout(container)
    main_layout.setSpacing(15)
    main_layout.setContentsMargins(25, 25, 25, 25)

    title_label = QLabel(f"美工后期审批 - {order_data['id']}")
    title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF; padding-bottom: 5px;")
    title_label.setAlignment(Qt.AlignCenter)
    main_layout.addWidget(title_label)

    # 左右分栏布局
    content_layout = QHBoxLayout()
    content_layout.setSpacing(20)

    # Left Container & Layout
    left_container = QWidget()
    left_container.setMaximumWidth(360)
    left_layout = QVBoxLayout(left_container)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(15)

    # 工单基本信息
    basic_group = QGroupBox("工单信息")
    basic_layout = QFormLayout(basic_group)
    basic_layout.setSpacing(8)
    basic_layout.addRow("工单ID:", QLabel(order_data['id']))
    basic_layout.addRow("产线/部门:", QLabel(order_data['department']))
    basic_layout.addRow("型号:", QLabel(order_data['model']))
    basic_layout.addRow("名称:", QLabel(order_data['name']))
    basic_layout.addRow("当前状态:", QLabel(order_data.get('status', '')))
    basic_layout.addRow("美工状态:", QLabel(art_status))
    basic_layout.addRow("待审批路径:", QLabel(transit_root))
    left_layout.addWidget(basic_group)

    # 不通过反馈原因输入
    feedback_group = QGroupBox("退回反馈设置")
    feedback_layout = QVBoxLayout(feedback_group)
    reason_edit = QTextEdit()
    reason_edit.setPlaceholderText("选择“退回重做”时，必须在此输入退回的具体原因...")
    reason_edit.setMinimumHeight(150)
    feedback_layout.addWidget(reason_edit)
    left_layout.addWidget(feedback_group)
    left_layout.addStretch()

    content_layout.addWidget(left_container, 1)  # 左侧权重 1（配合 MaximumWidth 360）

    # 中间素材列表分组（运营成品 / 销售成品 两个页签）
    material_group = QGroupBox("美工提交的成品列表")
    material_layout = QVBoxLayout(material_group)

    tool_btn_style = """
        QPushButton {
            background-color: #3c3c3c;
            color: #FFFFFF;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 5px 12px;
            font-size: 13px;
            min-width: 70px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #2b2b2b;
        }
    """
    nav_btn_style = """
        QPushButton {
            background-color: #3c3c3c;
            color: #FFFFFF;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 6px 14px;
            font-size: 13px;
            min-width: 80px;
        }
        QPushButton:hover { background-color: #505050; }
        QPushButton:disabled { background-color: #2b2b2b; color: #555555; border-color: #3a3a3a; }
    """

    def scan_files(root_dir):
        """扫描目录下的图片/视频成品文件（跳过「不通过」目录），返回 [(rel_path, full_path)]"""
        files_found = []
        if os.path.exists(root_dir):
            try:
                for root, dirs, files in os.walk(root_dir):
                    if "不通过" in dirs:
                        dirs.remove("不通过")
                    for file in files:
                        ext = os.path.splitext(file)[1].lower()
                        if ext in IMG_EXTS or ext in VID_EXTS:
                            full_item_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_item_path, root_dir)
                            files_found.append((rel_path, full_item_path))
            except Exception as e:
                logger.error(f"读取待审批目录 {root_dir} 失败: {e}")
        return files_found

    # 各页签的文件列表（与 _SUB_DIRS 一一对应）
    all_files = [scan_files(sub_dir) for sub_dir in sub_dirs]

    tab_widget = QTabWidget()

    # 预览控件（两个页签共用）
    preview_widget = VideoPreviewWidget(dialog)
    preview_filename_label = QLabel("")
    preview_filename_label.setAlignment(Qt.AlignCenter)
    preview_filename_label.setStyleSheet(
        "background-color: transparent; border: none; color: #cccccc; font-size: 12px; padding: 2px;"
    )
    preview_filename_label.setWordWrap(True)

    preview_state = {'index': -1}

    def load_preview(files_found, idx):
        if idx < 0 or idx >= len(files_found):
            return
        preview_state['index'] = idx
        fname, fpath = files_found[idx]
        preview_filename_label.setText(f"[{idx + 1}/{len(files_found)}]  {fname}")
        preview_widget.show_file(fpath)
        # 同步更新「上一个/下一个」按钮状态（此前缺失导致按钮始终禁用、点击无反应）
        prev_file_btn.setEnabled(idx > 0)
        next_file_btn.setEnabled(idx < len(files_found) - 1)
        return len(files_found)

    def build_tab(files_found, title):
        """为单个子目录构建页签：操作条 + 表格，点击行联动预览"""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(8)

        file_table = QTableWidget()
        file_table.setColumnCount(2)
        file_table.setHorizontalHeaderLabels(["选择", "文件名"])
        file_table.setColumnWidth(0, 50)
        file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        file_table.setEditTriggers(QTableWidget.NoEditTriggers)

        checkboxes = []
        file_table.setRowCount(len(files_found))
        for idx, (fname, fpath) in enumerate(files_found):
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk = QCheckBox()
            chk.setStyleSheet("""
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                }
            """)
            chk_layout.addWidget(chk)
            file_table.setCellWidget(idx, 0, chk_widget)
            checkboxes.append(chk)
            file_table.setItem(idx, 1, QTableWidgetItem(fname))

        def on_table_cell_clicked(row, column):
            if column == 0 and row < len(checkboxes):
                chk = checkboxes[row]
                chk.setChecked(not chk.isChecked())

        def on_cell_clicked_with_preview(row, column):
            on_table_cell_clicked(row, column)
            load_preview(files_found, row)

        file_table.cellClicked.connect(on_cell_clicked_with_preview)

        # 双击使用系统程序播放/打开文件
        def on_file_double_clicked(row, column):
            if row < len(files_found):
                _, fpath = files_found[row]
                QDesktopServices.openUrl(QUrl.fromLocalFile(fpath))
        file_table.cellDoubleClicked.connect(on_file_double_clicked)

        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(0, 5, 0, 5)
        select_all_btn = QPushButton("全选")
        deselect_all_btn = QPushButton("取消全选")
        select_all_btn.setStyleSheet(tool_btn_style)
        deselect_all_btn.setStyleSheet(tool_btn_style)
        select_all_btn.clicked.connect(lambda: [chk.setChecked(True) for chk in checkboxes])
        deselect_all_btn.clicked.connect(lambda: [chk.setChecked(False) for chk in checkboxes])
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(select_all_btn)
        top_bar_layout.addWidget(deselect_all_btn)

        page_layout.addLayout(top_bar_layout)
        page_layout.addWidget(file_table)
        tab_widget.addTab(page, title)
        return file_table, checkboxes

    tables_and_checks = []
    for i, sub_name in enumerate(_SUB_DIRS):
        file_table, checkboxes = build_tab(all_files[i], sub_name)
        tables_and_checks.append((file_table, checkboxes))

    material_layout.addWidget(tab_widget)
    content_layout.addWidget(material_group, 2)  # 中间素材列表权重 2

    # 右侧预览面板
    preview_panel = QGroupBox("文件预览")
    preview_panel.setMinimumWidth(380)
    preview_panel_layout = QVBoxLayout(preview_panel)
    preview_panel_layout.setSpacing(8)
    preview_panel_layout.addWidget(preview_widget, 1)
    preview_panel_layout.addWidget(preview_filename_label)

    nav_layout = QHBoxLayout()
    prev_file_btn = QPushButton("▲ 上一个")
    next_file_btn = QPushButton("▼ 下一个")
    prev_file_btn.setStyleSheet(nav_btn_style)
    next_file_btn.setStyleSheet(nav_btn_style)
    prev_file_btn.setEnabled(False)
    next_file_btn.setEnabled(False)
    nav_layout.addWidget(prev_file_btn)
    nav_layout.addWidget(next_file_btn)
    preview_panel_layout.addLayout(nav_layout)

    # 关闭对话框时释放播放器
    dialog.finished.connect(preview_widget.stop)

    def current_tab_files():
        idx = tab_widget.currentIndex()
        if 0 <= idx < len(all_files):
            return all_files[idx]
        return []

    def on_prev_file():
        files_found = current_tab_files()
        load_preview(files_found, preview_state['index'] - 1)

    def on_next_file():
        files_found = current_tab_files()
        load_preview(files_found, preview_state['index'] + 1)

    prev_file_btn.clicked.connect(on_prev_file)
    next_file_btn.clicked.connect(on_next_file)

    # 切换「运营成品/销售成品」页签时重置预览状态
    def on_tab_changed(_index):
        preview_state['index'] = -1
        preview_widget.stop()
        preview_filename_label.setText("")
        prev_file_btn.setEnabled(False)
        next_file_btn.setEnabled(False)

    tab_widget.currentChanged.connect(on_tab_changed)

    content_layout.addWidget(preview_panel, 2)  # 右侧预览权重 2

    main_layout.addLayout(content_layout)

    # 按钮区域
    button_widget = QWidget()
    button_layout = QHBoxLayout(button_widget)
    button_layout.setSpacing(15)

    pass_ops_btn = QPushButton("运营通过")
    pass_ops_btn.setStyleSheet("background-color: #28a745; color: white;")

    pass_sales_btn = QPushButton("销售通过")
    pass_sales_btn.setStyleSheet("background-color: #28a745; color: white;")

    reject_btn = QPushButton("退回重做")
    reject_btn.setStyleSheet("background-color: #dc3545; color: white;")

    cancel_btn = QPushButton("取消")
    cancel_btn.setProperty("type", "cancel")

    button_layout.addWidget(pass_ops_btn)
    button_layout.addWidget(pass_sales_btn)
    button_layout.addWidget(reject_btn)
    button_layout.addStretch()
    button_layout.addWidget(cancel_btn)
    main_layout.addWidget(button_widget)

    cancel_btn.clicked.connect(dialog.reject)

    # 已确认通过的侧（运营/销售），跨两次按钮点击共享，用于判断两侧是否都完成
    approved_sides = set()

    def _side_has_content(side):
        """该侧是否有成品内容（待审批目录有成品，或目标目录已有成品）。"""
        if scan_files(sub_dirs[side]):
            return True
        target = targets[side]
        if os.path.exists(target):
            for _root, _dirs, files in os.walk(target):
                for f in files:
                    if os.path.splitext(f)[1].lower() in IMG_EXTS or os.path.splitext(f)[1].lower() in VID_EXTS:
                        return True
        return False

    def on_approve(side):
        """单侧审批通过：仅处理 01运营(0) / 02销售(1) 对应子目录。

        该侧成品移动/确认通过后，若另一侧也已确认通过，或另一侧完全没有成品内容
        （未分发），则整体置为「美工已完成」并发通知并关闭对话框；否则保持
        「美工后期审核中」，继续审批另一侧。每次点击重新扫描目录（不依赖快照）。
        """
        sub_dir = sub_dirs[side]
        target_dir = targets[side]
        target_label = _SIDE_LABELS[side]

        def _complete_side(side, via_fallback):
            """该侧通过的统一收尾：判定两侧是否都完成；是则置「美工已完成」并关闭对话框。"""
            other_side = 1 - side
            all_done = (other_side in approved_sides) or not _side_has_content(other_side)
            if all_done:
                # 美工链专属状态：审批通过（只写 art_status，不覆盖剪辑链全局状态）；本地字段无 API 同步
                ok, error_msg = update_local_status_only(order_data['id'], {'art_status': '美工已完成'})
                if not ok:
                    try:
                        if dialog.isVisible():
                            QMessageBox.warning(dialog, "提示", error_msg)
                    except RuntimeError:
                        pass
                    return  # 状态未写入，中止后续通知与成功提示
                order_data['art_status'] = '美工已完成'
                parent.refresh_work_orders()
            fallback_note = "，待审批目录无成品(目标目录已有文件), 直接确认通过" if via_fallback else ""
            _log_action(
                "美工后期审批通过",
                f"工单ID={order_data['id']}, 角色=美工后期审批, 分发侧={target_label}{fallback_note}"
            )
            if all_done:
                send_notification(
                    "工单美工后期审批通过通知",
                    f"### 工单号：{order_data['id']}\n- 角色：美工后期审批\n- 操作：审批通过\n- 状态：后期已完成\n- 提示：美工后期审批已通过，成品已分发，请运营/销售同事登录系统领取素材！",
                    order_data.get('department')
                )
            else:
                send_notification(
                    f"工单美工后期审批通过通知-{target_label}",
                    f"### 工单号：{order_data['id']}\n- 角色：美工后期审批\n- 操作：审批通过（{target_label}侧）\n- 提示：{target_label}侧成品已审批通过并分发，请{target_label}同事登录系统领取素材！",
                    order_data.get('department')
                )
            try:
                if dialog.isVisible():
                    if all_done:
                        dialog.accept()
                        QMessageBox.information(parent, "成功", "美工后期审批已通过，成品已分发至运营/销售目录，已通知领取！")
                    else:
                        # 单侧通过不关闭对话框，便于继续审批另一侧
                        QMessageBox.information(parent, "成功",
                                                f"{target_label}侧审批已通过，请继续审批另一侧。")
            except RuntimeError:
                pass

        files_found = scan_files(sub_dir)
        if not files_found or not os.path.exists(sub_dir):
            # 兜底：待审批目录无成品文件，但该侧目标目录已有成品（历史审批已分发但
            # 状态未推进）→ 审批员确认后直接通过，无需重新移动文件
            if not _side_has_content(side):
                QMessageBox.warning(dialog, "提示", f"{target_label}侧没有待审批的成品文件")
                return
            confirm = QMessageBox.question(
                dialog, "确认通过",
                f"{target_label}侧待审批目录没有待审批文件，但目标目录已存在成品：\n{target_dir}\n\n"
                f"这可能是审批已分发但状态未推进。\n确认直接通过本侧审批？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return
            approved_sides.add(side)
            _complete_side(side, via_fallback=True)
            return

        failed = {'count': 0}
        completed = {'count': 0}
        total = 1  # 单侧单任务

        def update_status(task_ok=True, task_errors=None):
            if task_ok:
                completed['count'] += 1
            else:
                failed['count'] += 1
            if failed['count'] > 0 or completed['count'] < total:
                if failed['count'] > 0:
                    try:
                        if dialog.isVisible():
                            QMessageBox.warning(
                                dialog, "审批未完成",
                                f"{target_label}侧文件分发失败，审批未通过，请重试：\n"
                                + "\n".join((task_errors or [])[:5])
                            )
                    except RuntimeError:
                        pass
                return
            # 该侧文件全部分发成功：标记该侧已通过并统一收尾
            approved_sides.add(side)
            _complete_side(side, via_fallback=False)

        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建审批分发目标目录失败: {target_dir}, 错误: {e}")
            QMessageBox.critical(dialog, "错误", f"创建目标目录失败：\n{target_dir}\n原因: {e}")
            return
        rel_files = [rel for rel, _ in files_found]
        _add_file_task(
            name=f"美工后期审批通过分发({target_label}) - 工单{order_data['id']}",
            files=rel_files,
            src_dir=sub_dir,
            dest_dir=target_dir,
            op_type="move",
            update_status_func=update_status
        )

    def on_reject():
        reason = reason_edit.toPlainText().strip()
        if not reason:
            QMessageBox.warning(dialog, "提示", "退回重做必须填写退回原因")
            return

        idx = tab_widget.currentIndex()
        if not (0 <= idx < len(_SUB_DIRS)):
            return
        sub_dir = sub_dirs[idx]
        files_found = all_files[idx]
        _, checkboxes = tables_and_checks[idx]

        selected_indices = [i for i, chk in enumerate(checkboxes) if chk.isChecked()]
        if not selected_indices:
            QMessageBox.warning(dialog, "提示", "请选择至少一个不通过的成品文件")
            return

        fail_count = 0
        for i in selected_indices:
            rel_path, fpath = files_found[i]
            fail_dir = os.path.join(sub_dir, "不通过")
            try:
                os.makedirs(fail_dir, exist_ok=True)
                dest_path = os.path.join(fail_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.move(fpath, dest_path)
                # 记录反馈
                db_manager.add_review_feedback(order_data['id'], rel_path, sub_dir, reason)
                fail_count += 1
            except Exception as e:
                logger.error(f"退回移动文件 {rel_path} 失败: {e}")
                QMessageBox.warning(dialog, "错误", f"移动文件 {rel_path} 失败: {e!s}")

        if fail_count > 0:
            # 美工链专属状态：审批退回（只写 art_status，不覆盖剪辑链全局状态）；本地字段无 API 同步
            ok, error_msg = update_local_status_only(order_data['id'], {'art_status': '美工后期重新制作'})
            if not ok:
                try:
                    if dialog.isVisible():
                        QMessageBox.warning(dialog, "提示", error_msg)
                except RuntimeError:
                    pass
                return  # 状态未写入，中止后续通知与成功提示
            order_data['art_status'] = '美工后期重新制作'
            parent.refresh_work_orders()

            _log_action("美工后期审批退回", f"工单ID={order_data['id']}, 角色=美工后期审批, 不通过文件数={fail_count}, 原因={reason}")
            send_notification(
                "工单美工后期审批退回通知",
                f"### 工单号：{order_data['id']}\n- 角色：美工后期审批\n- 操作：退回重做\n- 状态：美工后期重新制作\n- 退回数量：{fail_count}个文件\n- 原因：{reason}",
                order_data.get('department')
            )
            dialog.accept()
            QMessageBox.information(parent, "提示", f"已成功将 {fail_count} 个不通过成品移至“不通过”文件夹，并通知美工重新制作。")
        else:
            QMessageBox.critical(dialog, "失败", "文件退回移动失败，请重试或联系管理员")

    pass_ops_btn.clicked.connect(lambda: on_approve(0))
    pass_sales_btn.clicked.connect(lambda: on_approve(1))
    reject_btn.clicked.connect(on_reject)
