"""
show_video_post_review_dialog — 视频后期审核 工单处理对话框
从 main_window.py 重构迁移而来，不改变任何业务逻辑。
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.config import BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK, get_feature_enabled
from src.core.database import db_manager
from src.core.notification import send_notification
from src.core.paths import (
    VID_EXTS,
    to_local_path,
)
from src.core.status_sync import has_pending_edit_review, update_status_with_api
from src.ui.dialog_helpers import show_api_update_error
from src.ui.video_preview import VideoPreviewWidget

logger = logging.getLogger(__name__)


def show_video_post_review_dialog(parent, order_data, callbacks):
    """
    处理工单对话框入口。

    Args:
        parent: 父窗口（MainWindow 实例）
        order_data: 工单数据字典
        callbacks: 回调字典，含 update_status / add_file_task / log_action
    """
    def is_video_post_review_enabled() -> bool:
        return get_feature_enabled('video_post_review_enabled')


    # 检查视频后期审核功能开关
    if not is_video_post_review_enabled():
        QMessageBox.information(parent, "功能已关闭",
            "视频后期审核功能当前已关闭。\n如需开启，请管理员前往【系统设置 → 功能设置】进行配置。"
        )
        return
    # 只有状态为「视频后期审核中」才可审核（剪辑分发后的「后期已完成」不可再审，避免状态降级；支持通过配置跳过）
    if not BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK:
        current_status = order_data.get('status', '')
        status_ok = current_status in ['视频后期审核中']
        # 兼容全局状态被 API 回滚的场景：剪辑已提交审核且尚未通过 → 仍可审核
        if not status_ok:
            status_ok = has_pending_edit_review(order_data['id'])
        if not status_ok:
            QMessageBox.information(parent, "提示",
                f"当前工单状态为【{current_status}】\n只有状态为【视频后期审核中】的工单才可进行后期审核。"
            )
            return

    edit_product_path = order_data.get('edit_product_path')
    if edit_product_path:
        edit_product_path = to_local_path(edit_product_path)
    if not edit_product_path or not os.path.exists(edit_product_path):
        QMessageBox.warning(parent, "错误",
            f"找不到该工单的成品路径：\n{edit_product_path}\n请联系剪辑师确认是否已正确选择成品路径并提交。"
        )
        return

    dialog = QDialog(parent)
    dialog.setWindowTitle(f"后期视频审核 - {order_data['id']}")
    dialog.setMinimumWidth(1400)
    dialog.setMinimumHeight(700)
    dialog.resize(1400, 720)
    build_video_post_review_ui(dialog, dialog, parent, order_data, callbacks)
    dialog.exec()


def build_video_post_review_ui(container, dialog, parent, order_data, callbacks):
    """
    构建视频后期审核界面内容（供单独对话框与合并审批界面复用）。

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

    edit_product_path = order_data.get('edit_product_path') or ''
    if edit_product_path:
        edit_product_path = to_local_path(edit_product_path)

    # 设置弹窗样式
    dialog.setStyleSheet("""
        QDialog {
            background-color: #121418;
            color: #e8eaed;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        }
        QLabel {
            color: #e8eaed;
            background: transparent;
            font-size: 13px;
        }
        QGroupBox {
            background-color: #1a1d24;
            border: 1px solid #282c37;
            border-radius: 10px;
            margin-top: 14px;
            font-size: 13px;
            font-weight: bold;
            color: #8b949e;
            padding: 16px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            left: 12px;
            color: #8b949e;
            background: transparent;
        }
        QLineEdit, QTextEdit {
            background-color: #232732;
            border: 1px solid #303646;
            border-radius: 6px;
            padding: 8px 12px;
            color: #e8eaed;
            font-size: 13px;
        }
        QLineEdit:focus, QTextEdit:focus {
            border-color: #4f8ef7;
            background-color: #282c3a;
        }
        QPushButton {
            background-color: #4f8ef7;
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 9px 22px;
            font-size: 13px;
            font-weight: bold;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #6ba3ff;
        }
        QPushButton:pressed {
            background-color: #3a72d6;
        }
        QPushButton[type="cancel"] {
            background-color: #282c37;
            color: #9ba3b0;
        }
        QPushButton[type="cancel"]:hover {
            background-color: #353b49;
            color: #ffffff;
        }
    """)
    main_layout = QVBoxLayout(container)
    main_layout.setSpacing(15)
    main_layout.setContentsMargins(25, 25, 25, 25)

    title_label = QLabel(f"后期视频审核 - {order_data['id']}")
    title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF; padding-bottom: 5px; background: transparent;")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
    basic_layout.addRow("成品路径:", QLabel(edit_product_path))
    left_layout.addWidget(basic_group)

    # 不通过反馈原因输入
    feedback_group = QGroupBox("退回反馈设置")
    feedback_layout = QVBoxLayout(feedback_group)
    reason_edit = QTextEdit()
    reason_edit.setPlaceholderText("选择“退回重剪”时，必须在此输入退回的具体原因...")
    reason_edit.setMinimumHeight(150)
    feedback_layout.addWidget(reason_edit)
    left_layout.addWidget(feedback_group)
    left_layout.addStretch()

    content_layout.addWidget(left_container, 1) # 左侧权重 1（配合 MaximumWidth 360）

    # 右侧素材列表分组
    material_group = QGroupBox("剪辑提交的成品视频列表")
    material_layout = QVBoxLayout(material_group)

    file_table = QTableWidget()
    file_table.setColumnCount(2)
    file_table.setHorizontalHeaderLabels(["选择", "视频文件名"])
    file_table.setColumnWidth(0, 50)
    file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
    file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    files_found = []
    if os.path.exists(edit_product_path):
        try:
            for root, dirs, files in os.walk(edit_product_path):
                if "不通过" in dirs:
                    dirs.remove("不通过")
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in VID_EXTS:
                        full_item_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_item_path, edit_product_path)
                        files_found.append((rel_path, full_item_path))
        except Exception as e:
            logger.error(f"读取成品目录 {edit_product_path} 失败: {e}")

    file_table.setRowCount(len(files_found))
    checkboxes = []
    for idx, (fname, fpath) in enumerate(files_found):
        chk_widget = QWidget()
        chk_layout = QHBoxLayout(chk_widget)
        chk_layout.setContentsMargins(0, 0, 0, 0)
        chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

    # 点击整格任意空白处即可勾选
    def on_table_cell_clicked(row, column):
        if column == 0:
            if row < len(checkboxes):
                chk = checkboxes[row]
                chk.setChecked(not chk.isChecked())
    file_table.cellClicked.connect(on_table_cell_clicked)

    # 操作控制条
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

    # 双击使用系统程序播放文件
    def on_file_double_clicked(row, column):
        if row < len(files_found):
            _, fpath = files_found[row]
            QDesktopServices.openUrl(QUrl.fromLocalFile(fpath))
    file_table.cellDoubleClicked.connect(on_file_double_clicked)

    content_layout.addWidget(material_group, 2)  # 中间素材列表权重提升至 2

    # 右侧预览面板
    preview_panel = QGroupBox("文件预览")
    preview_panel.setMinimumWidth(380)
    preview_panel_layout = QVBoxLayout(preview_panel)
    preview_panel_layout.setSpacing(8)

    # 直接实例化通用混合预览控件
    preview_widget = VideoPreviewWidget(dialog)
    preview_panel_layout.addWidget(preview_widget, 1)

    # 文件名展示
    preview_filename_label = QLabel("")
    preview_filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        fname, fpath = files_found[idx]
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

    # 点击表格行更新预览
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

    reject_btn = QPushButton("退回重剪")
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
        # 更新状态并同步 API（失败时回滚本地状态）；失败即中止，避免"假成功"
        ok, error_msg = update_status_with_api(order_data['id'], '后期审核通过', order_data['status'])
        if not ok:
            show_api_update_error(dialog, error_msg)
            return  # 状态未变更，保留对话框可重试；不写日志/不发通知/不关闭
        # 注意："视频后期审核通过"日志只在成功后写入——失败时写入会使
        # has_pending_edit_review 判定已通过，门禁永久失效导致工单卡死

        parent.refresh_work_orders()
        _log_action("视频后期审核通过", f"工单ID={order_data['id']}, 角色=视频后期审核, 成品路径={edit_product_path}")
        send_notification(
            "工单后期审核通过通知",
            f"### 工单号：{order_data['id']}\n- 角色：视频后期审核\n- 操作：审核通过\n- 状态：后期审核通过\n- 提示：视频后期审核已通过，请剪辑师登录系统进行成品分发！",
            order_data.get('department')
        )
        dialog.accept()
        QMessageBox.information(parent, "成功", "后期视频审核已通过，已通知剪辑师分发！")

    def on_reject():
        reason = reason_edit.toPlainText().strip()
        if not reason:
            QMessageBox.warning(dialog, "提示", "退回重剪必须填写退回原因")
            return

        selected_indices = [i for i, chk in enumerate(checkboxes) if chk.isChecked()]
        if not selected_indices:
            QMessageBox.warning(dialog, "提示", "请选择至少一个不通过的视频文件")
            return

        # 先同步状态（失败即中止，文件保持原位可重试），成功后再移动文件，
        # 避免"文件已移走但状态回滚"的两端不一致
        ok, error_msg = update_status_with_api(order_data['id'], '后期重新剪辑', order_data['status'])
        if not ok:
            show_api_update_error(dialog, error_msg)
            return  # 状态未变更，文件未动，可重试

        fail_count = 0
        for i in selected_indices:
            fname, fpath = files_found[i]
            fail_dir = os.path.join(edit_product_path, "不通过")
            try:
                os.makedirs(fail_dir, exist_ok=True)
                dest_path = os.path.join(fail_dir, fname)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.move(fpath, dest_path)
                # 记录反馈
                db_manager.add_review_feedback(order_data['id'], fname, edit_product_path, reason)
                fail_count += 1
            except Exception as e:
                logger.error(f"退回移动视频 {fname} 失败: {e}")
                QMessageBox.warning(dialog, "错误", f"移动视频 {fname} 失败: {e!s}")

        if fail_count > 0:
            parent.refresh_work_orders()
            _log_action("视频后期审核退回", f"工单ID={order_data['id']}, 角色=视频后期审核, 不通过文件数={fail_count}, 原因={reason}")
            send_notification(
                "工单后期审核退回通知",
                f"### 工单号：{order_data['id']}\n- 角色：视频后期审核\n- 操作：退回重剪\n- 状态：后期重新剪辑\n- 退回数量：{fail_count}个文件\n- 原因：{reason}",
                order_data.get('department')
            )
            dialog.accept()
            QMessageBox.information(parent, "提示", f"已成功将 {fail_count} 个不通过视频移至“不通过”文件夹，并通知剪辑师重新剪辑。")
        else:
            # 状态已变但文件移动全部失败：提示人工处理（状态不可回退，避免误覆盖并发修改）
            QMessageBox.critical(dialog, "失败", "状态已更新为后期重新剪辑，但文件退回移动失败，请手动检查成品目录或联系管理员")

    pass_btn.clicked.connect(on_approve)
    reject_btn.clicked.connect(on_reject)
