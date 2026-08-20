"""
show_photography_dialog — 采购/摄影 工单处理对话框
从 main_window.py 重构迁移而来，不改变任何业务逻辑。
"""
import datetime
import logging
import os
import shutil

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (
    QDesktopServices,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.api_manager import api_manager
from src.core.config import get_feature_enabled
from src.core.database import db_manager
from src.core.notification import send_notification
from src.core.paths import (
    IMG_EXTS,
    PHOTOGRAPHERS,
    PHOTOGRAPHY_DIST_IMG,
    PHOTOGRAPHY_DIST_VIDEO,
    PHOTOGRAPHY_UPLOAD,
    VID_EXTS,
)
from src.core.status_sync import update_status_with_api
from src.ui.dialog_helpers import show_api_update_error, show_path_result

logger = logging.getLogger(__name__)


def show_photography_dialog(parent, order_data, callbacks):
    """
    处理工单对话框入口。

    Args:
        parent: 父窗口（MainWindow 实例）
        order_data: 工单数据字典
        callbacks: 回调字典，含 update_status / add_file_task / log_action
    """
    # ---- 解包 callbacks ----
    _add_file_task = callbacks['add_file_task']
    _log_action    = callbacks['log_action']

    def is_video_review_enabled() -> bool:
        return get_feature_enabled('video_review_enabled')


    def get_photographer():
        photographer_combo = dialog.findChild(QComboBox, 'photographer_combo')
        if photographer_combo and photographer_combo.currentText().strip():
            return photographer_combo.currentText().strip()
        return ""

    def get_upload_dir():
        return PHOTOGRAPHY_UPLOAD(get_photographer(), order_data['department'], order_data['id'], order_data['model'], order_data['name'])

    def get_dist_img_dir():
        return PHOTOGRAPHY_DIST_IMG(order_data['department'], order_data['id'], order_data['model'], order_data['name'])

    def get_dist_video_dir():
        return PHOTOGRAPHY_DIST_VIDEO(order_data['department'], order_data['id'], order_data['model'], order_data['name'])


    dialog = QDialog(parent)
    dialog.setWindowTitle(f"办理工单 - {order_data['id']}")
    dialog.setMinimumWidth(650)
    dialog.setMinimumHeight(550)
    # 设置弹窗样式，与主系统 Fluent 视觉规范保持一致
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
        QLineEdit, QComboBox {
            background-color: #232732;
            border: 1px solid #303646;
            border-radius: 6px;
            padding: 8px 12px;
            color: #e8eaed;
            font-size: 13px;
            min-height: 20px;
        }
        QLineEdit:focus, QComboBox:focus {
            border-color: #4f8ef7;
            background-color: #282c3a;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox QAbstractItemView {
            background-color: #1a1d24;
            border: 1px solid #282c37;
            color: #e8eaed;
            selection-background-color: #4f8ef7;
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
    # 主布局
    main_layout = QVBoxLayout(dialog)
    main_layout.setSpacing(20)
    main_layout.setContentsMargins(30, 30, 30, 30)
    # 标题
    title_label = QLabel(f"办理工单 - {order_data['id']}")
    title_label.setStyleSheet("""
        QLabel {
            font-size: 24px;
            font-weight: bold;
            color: #FFFFFF;
            padding: 10px 0;
        }
    """)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_layout.addWidget(title_label)

    # 获取不通过反馈
    feedbacks = db_manager.get_review_feedback(order_data['id'])
    dialog.setMinimumWidth(820)
    dialog.setMinimumHeight(880)

    # ── 如果有退回明细，在标题下方添加 Tab 切换按钮 ──
    stacked = None
    if feedbacks:
        tab_bar = QWidget()
        tab_bar_layout = QHBoxLayout(tab_bar)
        tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        tab_bar_layout.setSpacing(0)

        tab_btn_style_active = """
            QPushButton {
                background-color: #0078d4;
                color: #FFFFFF;
                border: none;
                border-radius: 0px;
                border-bottom: 2px solid #005fa3;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }
        """
        tab_btn_style_inactive = """
            QPushButton {
                background-color: #3c3c3c;
                color: #aaaaaa;
                border: none;
                border-radius: 0px;
                border-bottom: 2px solid #555555;
                padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #505050;
                color: #ffffff;
            }
        """
        tab_order_btn = QPushButton("📋 办理工单")
        tab_order_btn.setStyleSheet(tab_btn_style_active)
        tab_return_btn = QPushButton(f"⚠️ 退回明细（{len(feedbacks)} 条）")
        tab_return_btn.setStyleSheet(tab_btn_style_inactive)

        tab_bar_layout.addWidget(tab_order_btn)
        tab_bar_layout.addWidget(tab_return_btn)
        tab_bar_layout.addStretch()
        main_layout.addWidget(tab_bar)

        stacked = QStackedWidget()
        stacked.setContentsMargins(0, 0, 0, 0)

        def switch_to_order():
            stacked.setCurrentIndex(0)
            tab_order_btn.setStyleSheet(tab_btn_style_active)
            tab_return_btn.setStyleSheet(tab_btn_style_inactive)

        def switch_to_return():
            stacked.setCurrentIndex(1)
            tab_return_btn.setStyleSheet(tab_btn_style_active)
            tab_order_btn.setStyleSheet(tab_btn_style_inactive)

        tab_order_btn.clicked.connect(switch_to_order)
        tab_return_btn.clicked.connect(switch_to_return)

    # ── Page 0: 表单区域 ──
    form_widget = QWidget()
    form_layout = QVBoxLayout(form_widget)
    form_layout.setSpacing(15)
    # 工单基本信息分组
    basic_group = QGroupBox("工单基本信息")
    basic_layout = QFormLayout(basic_group)
    basic_layout.setSpacing(12)
    basic_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    id_label = QLabel(order_data['id'])
    dept_label = QLabel(order_data['department'])
    model_label = QLabel(order_data['model'])
    name_label = QLabel(order_data['name'])
    creator_label = QLabel(order_data['creator'])
    basic_layout.addRow("工单ID:", id_label)
    basic_layout.addRow("产线/部门:", dept_label)
    basic_layout.addRow("型号:", model_label)
    basic_layout.addRow("名称:", name_label)
    basic_layout.addRow("发起人:", creator_label)
    form_layout.addWidget(basic_group)
    # 操作设置分组
    operation_group = QGroupBox("操作设置")
    operation_layout = QFormLayout(operation_group)
    operation_layout.setSpacing(12)
    operation_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    photographer_combo = QComboBox()
    photographer_combo.addItem("")
    # 摄影师列表统一引用 paths.PHOTOGRAPHERS（单一来源，新增摄影师只改一处）
    photographer_combo.addItems(PHOTOGRAPHERS)
    photographer_combo.setObjectName('photographer_combo')
    photographer_combo.setPlaceholderText("请选择摄影师")
    operation_layout.addRow("摄影师:", photographer_combo)
    form_layout.addWidget(operation_group)
    # 路径信息分组
    path_group = QGroupBox("路径信息")
    path_layout = QFormLayout(path_group)
    path_layout.setSpacing(12)
    path_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    def create_clickable_path_label(path, tooltip_text):
        label = QLabel(path)
        label.setStyleSheet("""
            QLabel {
                color: #0078d4;
                text-decoration: underline;
                cursor: pointer;
                padding: 4px 8px;
                border-radius: 3px;
            }
            QLabel:hover {
                background-color: #3c3c3c;
                color: #106ebe;
            }
        """)
        label.setToolTip(f"双击打开：{tooltip_text}")
        def on_mouse_press(event):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        label.mousePressEvent = on_mouse_press
        return label
    upload_path = get_upload_dir()
    dist_img_path = get_dist_img_dir()
    dist_video_path = get_dist_video_dir()
    upload_label = create_clickable_path_label(upload_path, "上传素材路径")
    dist_img_label = parent.create_path_status_label(dist_img_path, "分发图片路径", order_data, 'dist_img')
    dist_video_label = parent.create_path_status_label(dist_video_path, "分发视频路径", order_data, 'dist_video')
    path_layout.addRow("上传素材路径:", upload_label)
    path_layout.addRow("分发图片路径:", dist_img_label)
    path_layout.addRow("分发视频路径:", dist_video_label)
    form_layout.addWidget(path_group)
    def update_path_display():
        photographer = get_photographer()
        if photographer:
            new_upload_path = PHOTOGRAPHY_UPLOAD(photographer, order_data['department'], order_data['id'], order_data['model'], order_data['name'])
            upload_label.setText(new_upload_path)
            upload_label.setToolTip("双击打开：上传素材路径")
            def on_mouse_press_updated(event):
                QDesktopServices.openUrl(QUrl.fromLocalFile(new_upload_path))
            upload_label.mousePressEvent = on_mouse_press_updated
    photographer_combo.currentTextChanged.connect(update_path_display)
    info_label = QLabel("💡 提示：请先选择摄影师，然后进行相应的操作")
    info_label.setStyleSheet("""
        QLabel {
            font-size: 13px;
            color: #cccccc;
            padding: 8px 0;
        }
    """)
    form_layout.addWidget(info_label)

    if stacked is not None:
        stacked.addWidget(form_widget)  # index 0: 表单页

        # ── Page 1: 退回明细页 ──
        feedback_page = QWidget()
        feedback_page_layout = QVBoxLayout(feedback_page)
        feedback_page_layout.setContentsMargins(0, 8, 0, 0)
        feedback_page_layout.setSpacing(8)

        fb_table = QTableWidget()
        fb_table.setColumnCount(3)
        fb_table.setHorizontalHeaderLabels(["文件名", "素材目录", "退回原因"])
        fb_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        fb_table.setRowCount(len(feedbacks))
        fb_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        fb_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        fb_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        fb_table.setColumnWidth(0, 200)
        fb_table.setColumnWidth(1, 140)
        fb_table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                color: #FFFFFF;
                gridline-color: #555555;
                border: 1px solid #555555;
                border-radius: 4px;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #FFFFFF;
                padding: 6px 4px;
                border: 1px solid #555555;
                font-weight: bold;
            }
        """)

        for idx, fb in enumerate(feedbacks):
            fb_table.setItem(idx, 0, QTableWidgetItem(fb['file_name']))
            dir_name = os.path.basename(fb['directory']) if fb['directory'] else ""
            dir_item = QTableWidgetItem(dir_name)
            dir_item.setToolTip(fb['directory'])
            fb_table.setItem(idx, 1, dir_item)
            reason_item = QTableWidgetItem(fb['reason'])
            fb_table.setItem(idx, 2, reason_item)

        def on_edit_fb_double_clicked(row, column):
            if row < len(feedbacks):
                fb = feedbacks[row]
                # 路径候选：1) directory/file_name  2) directory/不通过/file_name
                candidates = [
                    os.path.join(fb.get('directory', ''), fb.get('file_name', '')),
                    os.path.join(fb.get('directory', ''), '不通过', fb.get('file_name', '')),
                ]
                opened = False
                for p in candidates:
                    if p and os.path.exists(p):
                        QDesktopServices.openUrl(QUrl.fromLocalFile(p))
                        opened = True
                        break
                if not opened:
                    d = fb.get('directory', '')
                    if d and os.path.exists(d):
                        QDesktopServices.openUrl(QUrl.fromLocalFile(d))
                    else:
                        QMessageBox.warning(dialog, '提示',
                            f"文件不存在，请确认素材已上传到以下路径：\n{candidates[0]}")
        fb_table.cellDoubleClicked.connect(on_edit_fb_double_clicked)

        hint_lbl = QLabel("💡 双击任意行可用系统默认程序打开对应文件")
        hint_lbl.setStyleSheet("color: #888888; font-size: 12px; padding: 4px 0;")
        feedback_page_layout.addWidget(fb_table)
        feedback_page_layout.addWidget(hint_lbl)
        stacked.addWidget(feedback_page)  # index 1: 明细页
        main_layout.addWidget(stacked)
    else:
        main_layout.addWidget(form_widget)
    # 按钮区域
    button_widget = QWidget()
    button_layout = QHBoxLayout(button_widget)
    button_layout.setSpacing(15)
    upload_btn = QPushButton("上传素材")
    distribute_img_btn = QPushButton("分发图片")
    distribute_vid_btn = QPushButton("分发视频")

    gray_style = "background-color: #444444; color: #888888; border: none; border-radius: 4px; padding: 10px 24px; font-size: 14px; font-weight: bold; min-width: 80px;"

    def refresh_button_states():
        """根据当前状态与开关，解耦刷新「分发图片」与「分发视频」按钮的可用性及提示。"""
        current_status = order_data.get('status', '')
        vr_enabled = is_video_review_enabled()

        # 1. 分发图片（美工链）：不受视频审核限制，只要不是退回重拍状态均可分发
        img_allowed = current_status != '重新拍摄'
        distribute_img_btn.setEnabled(img_allowed)
        if img_allowed:
            distribute_img_btn.setStyleSheet("")
            distribute_img_btn.setToolTip("分发图片素材给美工")
        else:
            distribute_img_btn.setStyleSheet(gray_style)
            distribute_img_btn.setToolTip("工单已被退回重拍，请重新上传素材后再分发")

        # 2. 分发视频（剪辑链）：若启用视频审核，需审核通过或已进入后期阶段；若未启用视频审核，只要不是退回重拍即可分发
        if vr_enabled:
            post_approved_statuses = {
                '审核通过', '后期待领取', '后期处理中', '正在剪辑',
                '视频后期审核中', '后期审核通过', '后期已完成', '美工已完成'
            }
            vid_allowed = current_status in post_approved_statuses
            vid_tooltip = "分发视频素材给剪辑" if vid_allowed else "需要视频审核通过后方可分发"
        else:
            vid_allowed = current_status != '重新拍摄'
            vid_tooltip = "分发视频素材给剪辑" if vid_allowed else "工单已被退回重拍，请重新上传素材后再分发"

        distribute_vid_btn.setEnabled(vid_allowed)
        if vid_allowed:
            distribute_vid_btn.setStyleSheet("")
            distribute_vid_btn.setToolTip(vid_tooltip)
        else:
            distribute_vid_btn.setStyleSheet(gray_style)
            distribute_vid_btn.setToolTip(vid_tooltip)

    # 初始刷新按钮状态
    refresh_button_states()

    def on_upload_material():
        # 验证摄影师是否已选择
        photographer = get_photographer()
        if not photographer:
              QMessageBox.warning(dialog, "提示", "请先选择摄影师")
              return
        upload_dir = get_upload_dir()
        try:
            os.makedirs(upload_dir, exist_ok=True)
        except OSError as e:
            if getattr(e, 'winerror', None) in [5, 1326]:  # 添加错误代码5 (拒绝访问) 的处理，非 Windows 平台 winerror 不存在
                parent.show_error_dialog(f"权限错误: 没有素材库访问权限，请联系系统管理员获取相应权限。\n错误详情: {e!s}")
                return
            else:
                raise
        files, _ = QFileDialog.getOpenFileNames(dialog, "选择要上传的素材")
        if not files:
            return
    
        # 使用任务管理器处理文件上传
        task_name = f"上传素材 - 工单{order_data['id']}"
        def update_status(task_ok=True, task_errors=None):
            if not task_ok:
                try:
                    if dialog.isVisible():
                        QMessageBox.warning(dialog, "任务失败", f"素材上传失败，工单状态未更新：\n" + "\n".join((task_errors or [])[:5]))
                except RuntimeError:
                    pass
                return
            # 状态更新/日志为核心业务，不依赖对话框是否可见（异步任务完成时对话框可能已被关闭）
            _log_action("上传素材", f"工单ID={order_data['id']}, 角色={parent.role}, 摄影师={photographer}, 目标路径={upload_dir}, 文件数={len(files)}")

            # 仅在上传复制成功后才清理"不通过"目录与反馈记录（避免复制失败时反馈数据永久丢失）
            fail_dir = os.path.join(upload_dir, "不通过")
            if os.path.exists(fail_dir):
                try:
                    shutil.rmtree(fail_dir)
                    logger.info(f"摄影师重新上传成功，已物理删除不通过文件夹: {fail_dir}")
                except Exception as e:
                    logger.error(f"物理删除不通过文件夹失败: {e}")
                    try:
                        if dialog.isVisible():
                            QMessageBox.warning(dialog, "提示", f"素材已上传，但删除不通过文件夹失败：\n{e}")
                    except RuntimeError:
                        pass
            db_manager.delete_review_feedback(order_data['id'])
        
            # 记录当前时间作为摄影师结束时间
            current_time = datetime.datetime.now()
        
            # 摄影师时间仅同步外部系统（本地表无对应列），失败弹窗提示
            api_response = api_manager.update_work_order_time(order_data['id'], 'photographer_end_time', current_time.strftime('%Y-%m-%d %H:%M:%S'))
            if api_response['success']:
                logger.info(f"API更新工单{order_data['id']}摄影师结束时间成功")
            else:
                error_msg = f"API更新工单{order_data['id']}摄影师结束时间失败: {api_response['error']}"
                logger.error(error_msg)
                try:
                    if dialog.isVisible():
                        show_api_update_error(dialog, error_msg)
                except RuntimeError:
                    pass
        
            if is_video_review_enabled():
                new_status = '视频审核中'
                status_str = "视频审核中"
            else:
                new_status = '审核通过'
                status_str = "审核通过"
            # 状态同步（API 失败时回滚本地状态）；失败即中止，不发通知/不报成功
            ok, error_msg = update_status_with_api(order_data['id'], new_status, order_data['status'])
            if not ok:
                try:
                    if dialog.isVisible():
                        show_api_update_error(dialog, error_msg)
                except RuntimeError:
                    pass
                return
            # 仅成功后同步内存快照（失败时本地已回滚，内存必须保持旧值，避免分发门禁误放行）
            order_data['status'] = new_status
            # 刷新按钮状态（对话框已关闭时跳过 UI 操作）
            try:
                if dialog.isVisible():
                    refresh_button_states()
            except RuntimeError:
                pass
            parent.refresh_work_orders()
        
            # 显示完成消息（对话框已关闭时跳过 UI 提示）
            try:
                if dialog.isVisible():
                    show_path_result(dialog, "上传完成", f"成功上传 {len(files)} 个文件到：\n{upload_dir}", upload_dir)
            except RuntimeError:
                pass
            # 发送通知
            send_notification(
                "工单状态变更通知",
                f"### 工单号：{order_data['id']}\n- 角色：{parent.role}\n- 操作：上传素材\n- 状态：{status_str}\n- 目标路径：{upload_dir}"
            )
        _add_file_task(
            name=task_name,
            files=[os.path.basename(f) for f in files],
            src_dir=os.path.dirname(files[0]),
            dest_dir=upload_dir,
            op_type="copy",
            update_status_func=update_status
        )
    def get_src_files_when_type_available(src_dir, exts, type_label):
        """校验源目录存在且包含指定扩展名的文件，返回全量文件列表。

        按分发目标类型分别校验（图片分发校验 IMG_EXTS、视频分发校验 VID_EXTS），
        避免"混合目录下视频任务被过滤为空仍假成功推进状态"。
        """
        try:
            src_files = os.listdir(src_dir)
        except FileNotFoundError:
            QMessageBox.warning(dialog, "提示", f"素材目录不存在：\n{src_dir}")
            return None
        except OSError as e:
            QMessageBox.warning(dialog, "提示", f"无法读取素材目录：\n{src_dir}\n{e}")
            return None
        matched = [f for f in src_files if os.path.splitext(f)[1].lower() in exts]
        if not matched:
            QMessageBox.warning(dialog, "提示", f"素材目录中没有{type_label}，无法分发。")
            return None
        return src_files
    def on_distribute_img():
        status = order_data.get('status')
        if status == '重新拍摄':
            QMessageBox.warning(dialog, "提示", "工单已被退回重拍，请先重新上传素材后再分发！")
            return
        src_dir = get_upload_dir()
        target_dir = get_dist_img_dir()
        src_files = get_src_files_when_type_available(src_dir, IMG_EXTS, "图片")
        if src_files is None:
            return
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as e:
            if getattr(e, 'winerror', None) == 1326:
                QMessageBox.warning(parent, "权限错误", "没有素材库访问权限，请联系系统管理员获取相应权限")
                return
            raise
        # 使用任务管理器处理图片分发
        task_name = f"分发图片 - 工单{order_data['id']}"
        def update_status(task_ok=True, task_errors=None):
            # 任务失败时不推进状态/发通知，避免状态与磁盘文件不一致
            if not task_ok:
                try:
                    if dialog.isVisible():
                        QMessageBox.warning(dialog, "任务失败", f"图片分发失败，工单状态未更新：\n" + "\n".join((task_errors or [])[:5]))
                except RuntimeError:
                    pass
                return
            # 状态更新/日志为核心业务，不依赖对话框是否可见（异步任务完成时对话框可能已被关闭）
            _log_action("分发图片", f"工单ID={order_data['id']}, 角色={parent.role}, 源路径={src_dir}, 目标路径={target_dir}")
            
            # 若当前处于前期阶段，推进为「后期待领取」；若已在后续状态（如剪辑/美工已处理或补发）则保持
            current_s = order_data.get('status')
            if current_s in ['审核通过', '视频审核中', '拍摄完成', '拍摄中']:
                ok, error_msg = update_status_with_api(order_data['id'], '后期待领取', current_s)
                if not ok:
                    try:
                        if dialog.isVisible():
                            show_api_update_error(dialog, error_msg)
                    except RuntimeError:
                        pass
                    return
                order_data['status'] = '后期待领取'

            # 刷新按钮状态（避免分发图片后锁死分发视频按钮）
            try:
                if dialog.isVisible():
                    refresh_button_states()
            except RuntimeError:
                pass

            parent.refresh_work_orders()
            # 发送通知：摄影分发图片
            send_notification(
                "工单状态变更通知",
                f"{order_data['id']} {order_data['model']} {order_data['name']}原始图片已分发，请美工同事在工作时间段1小时内登录'工单管理'系统领取原始图片并进行处理！",
                order_data.get('department')
            )
            # 显示完成消息（对话框已关闭时跳过 UI 提示）
            try:
                if dialog.isVisible():
                    show_path_result(dialog, "分发完成", f"成功分发图片到：\n{target_dir}", target_dir)
            except RuntimeError:
                pass
        _add_file_task(
            name=task_name,
            files=src_files,
            src_dir=src_dir,
            dest_dir=target_dir,
            file_filter=lambda f: os.path.splitext(f)[1].lower() in IMG_EXTS,
            op_type="copy",
            update_status_func=update_status
        )
    def on_distribute_vid():
        status = order_data.get('status')
        vr_enabled = is_video_review_enabled()
        post_approved_statuses = {
            '审核通过', '后期待领取', '后期处理中', '正在剪辑',
            '视频后期审核中', '后期审核通过', '后期已完成', '美工已完成'
        }
        if status == '重新拍摄':
            QMessageBox.warning(dialog, "提示", "工单已被退回重拍，请先重新上传素材后再分发！")
            return
        if vr_enabled and status not in post_approved_statuses:
            QMessageBox.warning(dialog, "提示", "需要视频审核通过后方可分发视频！")
            return
        src_dir = get_upload_dir()
        target_dir = get_dist_video_dir()
        src_files = get_src_files_when_type_available(src_dir, VID_EXTS, "视频")
        if src_files is None:
            return
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as e:
            if getattr(e, 'winerror', None) == 1326:
                QMessageBox.warning(parent, "权限错误", "没有素材库访问权限，请联系系统管理员获取相应权限")
                return
            raise
        # 使用任务管理器处理视频分发
        task_name = f"分发视频 - 工单{order_data['id']}"
        def update_status(task_ok=True, task_errors=None):
            # 任务失败时不推进状态/发通知，避免状态与磁盘文件不一致
            if not task_ok:
                try:
                    if dialog.isVisible():
                        QMessageBox.warning(dialog, "任务失败", f"视频分发失败，工单状态未更新：\n" + "\n".join((task_errors or [])[:5]))
                except RuntimeError:
                    pass
                return
            # 状态更新/日志为核心业务，不依赖对话框是否可见（异步任务完成时对话框可能已被关闭）
            _log_action("分发视频", f"工单ID={order_data['id']}, 角色={parent.role}, 源路径={src_dir}, 目标路径={target_dir}")
            
            # 若当前处于前期状态，推进为「后期待领取」；若已在后续状态（如补发）则保持
            current_s = order_data.get('status')
            if current_s in ['审核通过', '视频审核中', '拍摄完成', '拍摄中']:
                ok, error_msg = update_status_with_api(order_data['id'], '后期待领取', current_s)
                if not ok:
                    try:
                        if dialog.isVisible():
                            show_api_update_error(dialog, error_msg)
                    except RuntimeError:
                        pass
                    return
                order_data['status'] = '后期待领取'

            # 刷新按钮状态
            try:
                if dialog.isVisible():
                    refresh_button_states()
            except RuntimeError:
                pass

            parent.refresh_work_orders()
            # 发送通知：摄影分发视频
            send_notification(
                "工单状态变更通知",
                f"{order_data['id']} {order_data['model']} {order_data['name']}原始视频已分发，请剪辑同事在工作时间段1小时内登录'工单管理'系统领取原始视频并进行处理！",
                order_data.get('department')
            )
            # 显示完成消息（对话框已关闭时跳过 UI 提示）
            try:
                if dialog.isVisible():
                    show_path_result(dialog, "分发完成", f"成功分发视频到：\n{target_dir}", target_dir)
            except RuntimeError:
                pass
        _add_file_task(
            name=task_name,
            files=src_files,
            src_dir=src_dir,
            dest_dir=target_dir,
            file_filter=lambda f: os.path.splitext(f)[1].lower() in VID_EXTS,
            op_type="copy",
            update_status_func=update_status
        )
    upload_btn.clicked.connect(on_upload_material)
    distribute_img_btn.clicked.connect(on_distribute_img)
    distribute_vid_btn.clicked.connect(on_distribute_vid)
    button_layout.addWidget(upload_btn)
    button_layout.addWidget(distribute_img_btn)
    button_layout.addWidget(distribute_vid_btn)
    button_layout.addStretch()
    main_layout.addWidget(button_widget)
    dialog.exec()
