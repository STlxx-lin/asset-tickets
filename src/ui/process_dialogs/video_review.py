"""
show_video_review_dialog — 视频审核 工单处理对话框
从 main_window.py 重构迁移而来，不改变任何业务逻辑。
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QMessageBox, QHeaderView, QSplitter, QGroupBox, QListWidget,
    QTabWidget, QLineEdit, QComboBox, QFormLayout, QDialogButtonBox,
    QListWidgetItem, QTableWidget, QTableWidgetItem, QFileDialog,
    QProgressBar, QTextBrowser, QTextEdit, QDateEdit, QScrollArea,
    QFrame, QProgressDialog, QCheckBox, QGridLayout, QApplication,
)
from PySide6.QtGui import (
    QStandardItemModel, QStandardItem, QFont, QDesktopServices,
    QPainter, QColor, QPixmap,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QUrl, QDate
from src.core.paths import (
    VOLUMES, IMG_EXTS, VID_EXTS,
    PHOTOGRAPHY_UPLOAD, PHOTOGRAPHY_DIST_IMG, PHOTOGRAPHY_DIST_VIDEO,
    ART_GET_IMG_SRC, ART_GET_IMG_DEST, ART_DIST_OPS, ART_DIST_SALES,
    EDIT_GET_VIDEO_SRC, EDIT_GET_VIDEO_DEST, EDIT_DIST_OPS, EDIT_DIST_SALES,
    EDIT_POST_REVIEW_TRANSIT, OPS_GET_SRC, SALES_GET_SRC, to_local_path,
)
from src.core.database import db_manager
from src.core.notification import send_notification
from src.core.api_manager import api_manager
import datetime
from src.core.config import BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK
from src.ui.video_preview import VideoPreviewWidget
import logging
import os
import shutil
import re

logger = logging.getLogger(__name__)


def show_video_review_dialog(parent, order_data, callbacks):
    """
    处理工单对话框入口。

    Args:
        parent: 父窗口（MainWindow 实例）
        order_data: 工单数据字典
        callbacks: 回调字典，含 update_status / add_file_task / log_action
    """
    # ---- 解包 callbacks ----
    _update_status = callbacks['update_status']
    _add_file_task = callbacks['add_file_task']
    _log_action    = callbacks['log_action']

    def is_video_review_enabled() -> bool:
        val = db_manager.get_system_setting('video_review_enabled', default='1')
        return val == '1'


    # 检查视频审核功能开关
    if not is_video_review_enabled():
        QMessageBox.information(parent, "功能已关闭",
            "视频审核功能当前已关闭。\n如需开启，请管理员前往【系统设置 → 功能设置】进行配置。"
        )
        return
    # 「视频审核中」或「拍摄完成」状态均可审核
    current_status = order_data.get('status', '')
    if current_status not in ['视频审核中', '拍摄完成']:
        QMessageBox.information(parent, "提示",
            f"当前工单状态为【{current_status}】\n只有状态为【视频审核中】或【拍摄完成】的工单才可进行审核。"
        )
        return
    dialog = QDialog(parent)

    dialog.setWindowTitle(f"审核工单素材 - {order_data['id']}")
    dialog.setMinimumWidth(1400)
    dialog.setMinimumHeight(700)
    dialog.resize(1400, 720)
    # 设置弹窗样式
    dialog.setStyleSheet(parent.styleSheet() + """
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
    """)
    main_layout = QVBoxLayout(dialog)
    main_layout.setSpacing(15)
    main_layout.setContentsMargins(25, 25, 25, 25)

    title_label = QLabel(f"审核工单素材 - {order_data['id']}")
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
    basic_layout.addRow("发起人:", QLabel(order_data['creator']))
    basic_layout.addRow("当前状态:", QLabel(order_data.get('status', '')))
    left_layout.addWidget(basic_group)

    # 不通过反馈原因输入
    feedback_group = QGroupBox("退回反馈设置")
    feedback_layout = QVBoxLayout(feedback_group)
    reason_edit = QTextEdit()
    reason_edit.setPlaceholderText("选择“重新拍摄”时，必须在此输入退回的具体原因...")
    reason_edit.setMinimumHeight(150)
    feedback_layout.addWidget(reason_edit)
    left_layout.addWidget(feedback_group)
    left_layout.addStretch()

    content_layout.addWidget(left_container, 1) # 左侧权重 1（配合 MaximumWidth 360）

    # 右侧素材列表分组
    material_group = QGroupBox("摄影上传的素材列表")
    material_layout = QVBoxLayout(material_group)

    file_table = QTableWidget()
    file_table.setColumnCount(3)
    file_table.setHorizontalHeaderLabels(["选择", "文件名", "摄影师"])
    # 优化列宽占比，选择列固定 50px，摄影师固定 90px，文件名自适应拉伸
    file_table.setColumnWidth(0, 50)
    file_table.setColumnWidth(2, 90)
    file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
    file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
    file_table.setEditTriggers(QTableWidget.NoEditTriggers)

    files_found = []
    photographers = ["01阿乐", "02杨钧", "03Peter", "04玉瑞", "05Jessie", "06Candy", "07项项","08Arin"]
    for pg in photographers:
        upload_dir = PHOTOGRAPHY_UPLOAD(pg, order_data['department'], order_data['id'], order_data['model'], order_data['name'])
        if os.path.exists(upload_dir):
            try:
                for root, dirs, files in os.walk(upload_dir):
                    if "不通过" in dirs:
                        dirs.remove("不通过")
                    for file in files:
                        full_item_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_item_path, upload_dir)
                        files_found.append((rel_path, pg, full_item_path, upload_dir))
            except Exception as e:
                logger.error(f"读取摄影上传目录 {upload_dir} 失败: {e}")

    file_table.setRowCount(len(files_found))
    checkboxes = []
    for idx, (fname, pg_name, fpath, udir) in enumerate(files_found):
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
        file_table.setItem(idx, 2, QTableWidgetItem(pg_name))

    # 解决不好点击：点击表格“选择”列（第一列）整格任意空白处即可勾选
    def on_table_cell_clicked(row, column):
        if column == 0:
            if row < len(checkboxes):
                chk = checkboxes[row]
                chk.setChecked(not chk.isChecked())
    file_table.cellClicked.connect(on_table_cell_clicked)

    # 新增：操作控制条（全选/取消全选）
    top_bar_layout = QHBoxLayout()
    top_bar_layout.setContentsMargins(0, 5, 0, 5)

    select_all_btn = QPushButton("全选")
    deselect_all_btn = QPushButton("取消全选")

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
    select_all_btn.setStyleSheet(tool_btn_style)
    deselect_all_btn.setStyleSheet(tool_btn_style)

    # 绑定全选与取消全选事件
    def select_all_files():
        for chk in checkboxes:
            chk.setChecked(True)

    def deselect_all_files():
        for chk in checkboxes:
            chk.setChecked(False)
        
    select_all_btn.clicked.connect(select_all_files)
    deselect_all_btn.clicked.connect(deselect_all_files)

    top_bar_layout.addStretch()
    top_bar_layout.addWidget(select_all_btn)
    top_bar_layout.addWidget(deselect_all_btn)

    material_layout.addLayout(top_bar_layout)
    material_layout.addWidget(file_table)

    # 绑定双击事件：使用系统默认程序（如播放器或看图软件）打开/播放文件
    def on_file_double_clicked(row, column):
        if row < len(files_found):
            _, _, fpath, _ = files_found[row]
            QDesktopServices.openUrl(QUrl.fromLocalFile(fpath))
    file_table.cellDoubleClicked.connect(on_file_double_clicked)

    content_layout.addWidget(material_group, 2)  # 中间素材列表权重提升至 2

    # ── 右侧预览面板 ──
    preview_panel = QGroupBox("文件预览")
    preview_panel.setMinimumWidth(380)
    preview_panel_layout = QVBoxLayout(preview_panel)
    preview_panel_layout.setSpacing(8)

    # 直接实例化通用混合预览控件
    preview_widget = VideoPreviewWidget(dialog)
    preview_panel_layout.addWidget(preview_widget, 1)

    # 文件名展示标签
    preview_filename_label = QLabel("")
    preview_filename_label.setAlignment(Qt.AlignCenter)
    preview_filename_label.setStyleSheet(
        "background-color: transparent; border: none; color: #cccccc; font-size: 12px; padding: 2px;"
    )
    preview_filename_label.setWordWrap(True)
    preview_panel_layout.addWidget(preview_filename_label)

    nav_layout = QHBoxLayout()
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

    preview_state = {'index': -1}

    def load_preview(idx):
        if idx < 0 or idx >= len(files_found):
            return
        preview_state['index'] = idx
        file_table.selectRow(idx)
        fname, pg_name, fpath, udir = files_found[idx]
        preview_filename_label.setText(f"[{idx + 1}/{len(files_found)}]  {fname}")
    
        # 直接交给通用预览组件去渲染/播放
        preview_widget.show_file(fpath)
    
        prev_file_btn.setEnabled(idx > 0)
        next_file_btn.setEnabled(idx < len(files_found) - 1)

    def on_prev_file():
        load_preview(preview_state['index'] - 1)

    def on_next_file():
        load_preview(preview_state['index'] + 1)

    prev_file_btn.clicked.connect(on_prev_file)
    next_file_btn.clicked.connect(on_next_file)

    # 点击表格行更新预览（与已有的 checkbox 点击共存）
    original_cell_clicked = on_table_cell_clicked
    def on_cell_clicked_with_preview(row, column):
        original_cell_clicked(row, column)
        load_preview(row)
    file_table.cellClicked.disconnect(on_table_cell_clicked)
    file_table.cellClicked.connect(on_cell_clicked_with_preview)

    content_layout.addWidget(preview_panel, 2)  # 右侧预览权重 2

    main_layout.addLayout(content_layout)

    # 按钮区域
    button_widget = QWidget()
    button_layout = QHBoxLayout(button_widget)
    button_layout.setSpacing(15)

    pass_btn = QPushButton("审核通过")
    pass_btn.setStyleSheet("background-color: #28a745; color: white;")

    reject_btn = QPushButton("重新拍摄")
    reject_btn.setStyleSheet("background-color: #dc3545; color: white;")

    cancel_btn = QPushButton("取消")
    cancel_btn.setProperty("type", "cancel")

    button_layout.addWidget(pass_btn)
    button_layout.addWidget(reject_btn)
    button_layout.addStretch()
    button_layout.addWidget(cancel_btn)
    main_layout.addWidget(button_widget)

    cancel_btn.clicked.connect(dialog.reject)

    def on_approve():
        new_status = '审核通过'
        _update_status(order_data['id'], new_status)
        api_response = api_manager.update_work_order_status(order_data['id'], new_status)
        if api_response['success']:
            logger.info(f"API更新工单{order_data['id']}状态为审核通过成功")
        else:
            logger.error(f"API更新工单状态失败: {api_response['error']}")
    
        _log_action("视频审核通过", f"工单ID={order_data['id']}, 角色=视频审核")
        send_notification(
            "工单状态变更通知",
            f"### 工单号：{order_data['id']}\n- 角色：视频审核\n- 操作：审核通过\n- 状态：审核通过\n- 提示：视频审核已通过，摄影师现在可以分发素材了！",
            order_data.get('department')
        )
        dialog.accept()
        QMessageBox.information(parent, "成功", "工单已审核通过！")

    def on_reject():
        reason = reason_edit.toPlainText().strip()
        if not reason:
            QMessageBox.warning(dialog, "提示", "重新拍摄必须填写不通过原因")
            return
    
        selected_indices = [i for i, chk in enumerate(checkboxes) if chk.isChecked()]
        if not selected_indices:
            QMessageBox.warning(dialog, "提示", "请选择至少一个不通过的素材文件")
            return

        fail_count = 0
        for i in selected_indices:
            fname, pg_name, fpath, udir = files_found[i]
            fail_dir = os.path.join(udir, "不通过")
            try:
                os.makedirs(fail_dir, exist_ok=True)
                dest_path = os.path.join(fail_dir, fname)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.move(fpath, dest_path)
                db_manager.add_review_feedback(order_data['id'], fname, udir, reason)
                fail_count += 1
            except Exception as e:
                logger.error(f"退回移动文件 {fname} 失败: {e}")
                QMessageBox.warning(dialog, "错误", f"移动文件 {fname} 失败: {str(e)}")

        if fail_count > 0:
            new_status = '重新拍摄'
            _update_status(order_data['id'], new_status)
            api_response = api_manager.update_work_order_status(order_data['id'], new_status)
            if api_response['success']:
                logger.info(f"API更新工单{order_data['id']}状态为重新拍摄成功")
            else:
                logger.error(f"API更新工单状态失败: {api_response['error']}")
            
            _log_action("视频审核退回", f"工单ID={order_data['id']}, 角色=视频审核, 不通过文件数={fail_count}, 原因={reason}")
            send_notification(
                "工单状态变更通知",
                f"### 工单号：{order_data['id']}\n- 角色：视频审核\n- 操作：退回重拍\n- 状态：重新拍摄\n- 退回数量：{fail_count}个文件\n- 原因：{reason}",
                order_data.get('department')
            )
            dialog.accept()
            QMessageBox.information(parent, "提示", f"已成功将 {fail_count} 个不通过素材移至“不通过”文件夹，并通知摄影师重新拍摄。")
        else:
            QMessageBox.critical(dialog, "失败", "文件退回移动失败，请重试或联系管理员")

    pass_btn.clicked.connect(on_approve)
    reject_btn.clicked.connect(on_reject)
    dialog.exec()
            # 视频后期审核弹窗
