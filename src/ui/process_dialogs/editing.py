"""
show_editing_dialog — 剪辑 工单处理对话框
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
import os
import shutil
import re


def show_editing_dialog(parent, order_data, callbacks):
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

    def is_video_post_review_enabled() -> bool:
        val = db_manager.get_system_setting('video_post_review_enabled', default='1')
        return val == '1'


    def get_edit_get_video_src():
        return EDIT_GET_VIDEO_SRC(order_data['department'], order_data['id'], order_data['model'], order_data['name'])

    def get_edit_get_video_dest():
        return EDIT_GET_VIDEO_DEST(order_data['department'], order_data['id'], order_data['model'], order_data['name'])

    def get_edit_dist_ops():
        return EDIT_DIST_OPS(order_data['department'], order_data['id'], order_data['model'], order_data['name'])

    def get_edit_dist_sales():
        return EDIT_DIST_SALES(order_data['department'], order_data['id'], order_data['model'], order_data['name'])


    dialog = QDialog(parent)
    dialog.setWindowTitle(f"办理工单 - {order_data['id']}")
    dialog.setMinimumWidth(650)
    dialog.setMinimumHeight(550)
    # 设置弹窗样式，与主系统保持一致
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
        QLineEdit, QComboBox, QLabel {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px 12px;
            color: #FFFFFF;
            font-size: 14px;
            min-height: 20px;
        }
        QLineEdit:focus, QComboBox:focus {
            border-color: #0078d4;
            background-color: #4c4c4c;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #FFFFFF;
            margin-right: 5px;
        }
        QComboBox QAbstractItemView {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            color: #FFFFFF;
            selection-background-color: #0078d4;
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
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QPushButton[type="cancel"] {
            background-color: #555555;
        }
        QPushButton[type="cancel"]:hover {
            background-color: #666666;
        }
        QPushButton[type="cancel"]:pressed {
            background-color: #444444;
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
    title_label.setAlignment(Qt.AlignCenter)
    main_layout.addWidget(title_label)
    # 表单区域
    form_widget = QWidget()
    form_layout = QVBoxLayout(form_widget)
    form_layout.setSpacing(15)
    # 工单基本信息分组
    basic_group = QGroupBox("工单基本信息")
    basic_layout = QFormLayout(basic_group)
    basic_layout.setSpacing(12)
    basic_layout.setLabelAlignment(Qt.AlignRight)
    # 创建字段
    id_label = QLabel(order_data['id'])
    dept_label = QLabel(order_data['department'])
    model_label = QLabel(order_data['model'])
    name_label = QLabel(order_data['name'])
    creator_label = QLabel(order_data['creator'])
    # 添加字段到布局
    basic_layout.addRow("工单ID:", id_label)
    basic_layout.addRow("产线/部门:", dept_label)
    basic_layout.addRow("型号:", model_label)
    basic_layout.addRow("名称:", name_label)
    basic_layout.addRow("发起人:", creator_label)
    form_layout.addWidget(basic_group)
    # 路径信息分组
    path_group = QGroupBox("路径信息")
    path_layout = QFormLayout(path_group)
    path_layout.setSpacing(12)
    path_layout.setLabelAlignment(Qt.AlignRight)
    # 创建可双击的路径标签
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
        label.mousePressEvent = lambda event: QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        return label
    # 获取路径信息
    get_src = get_edit_get_video_src()
    get_dest = get_edit_get_video_dest()
    ops_path = get_edit_dist_ops()
    sales_path = get_edit_dist_sales()
    # 创建路径标签
    get_src_label = create_clickable_path_label(get_src, "领取源路径")
    get_dest_label = create_clickable_path_label(get_dest, "领取存放路径")
    ops_label = parent.create_path_status_label(ops_path, "分发运营路径", order_data, 'edit_dist_ops')
    sales_label = parent.create_path_status_label(sales_path, "分发销售路径", order_data, 'edit_dist_sales')

    # 检查成品路径状态
    parent.product_dir = order_data.get('edit_product_path')
    if parent.product_dir:
        parent.product_dir = to_local_path(parent.product_dir)

    # 根据是否有成品路径决定显示内容
    if parent.product_dir:
        product_label = QLabel(parent.product_dir)
        product_label.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 3px;
                background-color: #1a3d1a;
            }
        """)
    else:
        product_label = QLabel("")
        product_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-style: italic;
            }
        """)
    # 添加路径到布局
    path_layout.addRow("领取源路径:", get_src_label)
    path_layout.addRow("领取存放路径:", get_dest_label)
    path_layout.addRow("成品路径:", product_label)
    path_layout.addRow("分发运营路径:", ops_label)
    path_layout.addRow("分发销售路径:", sales_label)
    form_layout.addWidget(path_group)
    # 提示信息
    info_label = QLabel("💡 提示：请先领取素材，然后选择成品路径，最后进行提交审核或分发操作")
    info_label.setStyleSheet("""
        QLabel {
            font-size: 13px;
            color: #cccccc;
            padding: 8px 0;
        }
    """)
    form_layout.addWidget(info_label)
    main_layout.addWidget(form_widget)
    # 按钮区域
    button_widget = QWidget()
    button_layout = QHBoxLayout(button_widget)
    button_layout.setSpacing(15)
    get_material_btn = QPushButton("领取素材")
    select_product_btn = QPushButton("成品路径")
    submit_review_btn = QPushButton("提交审核")
    distribute_ops_btn = QPushButton("分发运营")
    distribute_sales_btn = QPushButton("分发销售")

    # 控制按钮启用状态与 ToolTip
    current_status = order_data.get('status', '')
    post_review_enabled = is_video_post_review_enabled()

    if post_review_enabled:
        if current_status == '后期审核通过':
            submit_review_btn.setEnabled(False)
            submit_review_btn.setToolTip("成品视频已通过后期审核，可直接分发")
            distribute_ops_btn.setEnabled(True)
            distribute_sales_btn.setEnabled(True)
            distribute_ops_btn.setToolTip("")
            distribute_sales_btn.setToolTip("")
        else:
            submit_review_btn.setEnabled(True)
            distribute_ops_btn.setEnabled(False)
            distribute_sales_btn.setEnabled(False)
            distribute_ops_btn.setToolTip("需要后期视频审核通过后方可分发")
            distribute_sales_btn.setToolTip("需要后期视频审核通过后方可分发")
            # 使用置灰的样式
            gray_style = "background-color: #444444; color: #888888; border: none; border-radius: 4px; padding: 10px 24px; font-size: 14px; font-weight: bold; min-width: 80px;"
            distribute_ops_btn.setStyleSheet(gray_style)
            distribute_sales_btn.setStyleSheet(gray_style)
    else:
        submit_review_btn.setVisible(False)
        distribute_ops_btn.setEnabled(True)
        distribute_sales_btn.setEnabled(True)
        distribute_ops_btn.setToolTip("")
        distribute_sales_btn.setToolTip("")
    def on_get_material():
        src = get_edit_get_video_src()
        dest = get_edit_get_video_dest()
        if not os.path.exists(src):
            QMessageBox.warning(dialog, "提示", f"素材文件夹不存在: {src}")
            return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # 使用任务管理器处理文件移动
        task_name = f"剪辑领取素材 - 工单{order_data['id']}"
        def update_status():
            _log_action("剪辑领取素材", f"工单ID={order_data['id']}, 角色=剪辑, 源路径={src}, 目标路径={dest}")
            db_manager.update_work_order_status(order_data['id'], '后期处理中')
            # 记录剪辑开始时间
            current_time = datetime.datetime.now()
            formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
            db_manager.update_work_order_time_field(order_data['id'], 'edit_start_time', current_time)
        
            # 调用API更新时间
            api_response = api_manager.update_work_order_time(order_data['id'], 'edit_start_time', formatted_time)
            if api_response['success']:
                logger.info(f"API更新工单{order_data['id']}剪辑开始时间成功")
            else:
                error_msg = f"API更新工单{order_data['id']}剪辑开始时间失败: {api_response['error']}"
                logger.error(error_msg)
                QMessageBox.warning(dialog, "API更新失败", error_msg)
            parent.refresh_work_orders()
            # 显示完成消息
            msg = QMessageBox(dialog)
            msg.setWindowTitle("领取完成")
            msg.setText(f"素材已移动到：\n{dest}")
            open_btn = msg.addButton("打开", QMessageBox.ActionRole)
            msg.addButton("确定", QMessageBox.AcceptRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
            # 更新路径显示
            get_src_label.setText(dest)
            get_dest_label.setText(dest)
            # 以剪辑领取素材为例：
            # send_dingtalk_markdown(
            #     "工单状态变更通知",
            #     f"### 工单号：{order_data['id']}\n- 角色：剪辑\n- 操作：领取素材\n- 状态：后期处理中\n- 目标路径：{dest}"
            # )
    
        # 获取源路径中的所有内容（文件和文件夹）
        all_items = []
        if os.path.exists(src):
            for item in os.listdir(src):
                item_path = os.path.join(src, item)
                all_items.append(item)
    
        _add_file_task(
            name=task_name,
            files=all_items,
            src_dir=src,
            dest_dir=dest,
            op_type="move",
            update_status_func=update_status
        )
    def on_select_product():
        dir_path = QFileDialog.getExistingDirectory(dialog, "选择成品文件夹")
        if not dir_path:
            return
        parent.product_dir = dir_path
        # 记录剪辑结束时间
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
        db_manager.update_work_order_time_field(order_data['id'], 'edit_end_time', current_time)
    
        # 调用API更新时间
        api_response = api_manager.update_work_order_time(order_data['id'], 'edit_end_time', formatted_time)
        if api_response['success']:
            logger.info(f"API更新工单{order_data['id']}剪辑结束时间成功")
        else:
            error_msg = f"API更新工单{order_data['id']}剪辑结束时间失败: {api_response['error']}"
            logger.error(error_msg)
            QMessageBox.warning(dialog, "API更新失败", error_msg)
        product_label.setText(dir_path)
        msg = QMessageBox(dialog)
        msg.setWindowTitle("已选择")
        msg.setText(f"成品路径：\n{dir_path}")
        open_btn = msg.addButton("打开", QMessageBox.ActionRole)
        msg.addButton("确定", QMessageBox.AcceptRole)
        msg.exec()
        if msg.clickedButton() == open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))

    def on_submit_review():
        if not parent.product_dir or not os.path.exists(parent.product_dir):
            QMessageBox.warning(dialog, "提示", "请先选择有效的成品路径！")
            return
    
        src = parent.product_dir
        # 计算中转目标目录
        try:
            transit_dir = EDIT_POST_REVIEW_TRANSIT(order_data['department'], order_data['id'], order_data['model'], order_data['name'])
            os.makedirs(transit_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(dialog, "错误", f"创建网络中转文件夹失败，请检查网络共享盘连接！\n原因: {e}")
            return

        # 获取源路径中的所有内容（文件和文件夹）
        all_items = []
        if os.path.exists(src):
            for item in os.listdir(src):
                all_items.append(item)
    
        if not all_items:
            QMessageBox.warning(dialog, "提示", "成品路径为空，没有视频可以上传！")
            return

        # 使用任务管理器异步复制视频到中转路径
        task_name = f"上传成品视频 - 工单{order_data['id']}"
    
        def update_status():
            # 上传成功后，将中转路径写入数据库成品路径
            db_manager.update_work_order_product_path(order_data['id'], transit_dir)
            parent.product_dir = transit_dir
            product_label.setText(transit_dir)
        
            # 更新工单状态为 视频后期审核中
            new_status = '视频后期审核中'
            _update_status(order_data['id'], new_status)
        
            # 调用API更新工单状态
            api_response = api_manager.update_work_order_status(order_data['id'], new_status)
            if api_response['success']:
                logger.info(f"API更新工单{order_data['id']}状态为视频后期审核中成功")
            else:
                error_msg = f"API更新工单{order_data['id']}状态为视频后期审核中失败: {api_response['error']}"
                logger.error(error_msg)
                QMessageBox.warning(dialog, "API更新失败", error_msg)
        
            # 记录日志
            _log_action("提交视频后期审核", f"工单ID={order_data['id']}, 角色=剪辑, 成品路径={transit_dir}, 原路径={src}")
        
            # 发送通知
            send_notification(
                "工单后期审核提请通知",
                f"### 工单号：{order_data['id']}\n- 角色：剪辑\n- 操作：提请后期审核\n- 状态：视频后期审核中\n- 成品路径：{transit_dir}\n- 提示：剪辑已完成视频并成功上传至中转路径，请视频后期审核员登录系统进行审核！",
                order_data.get('department')
            )
        
            parent.refresh_work_orders()
            QMessageBox.information(dialog, "提示", f"成品视频已成功上传中转并提请审核！\n中转路径：\n{transit_dir}")
            dialog.accept()

        _add_file_task(
            name=task_name,
            files=all_items,
            src_dir=src,
            dest_dir=transit_dir,
            file_filter=lambda f: not (os.path.isdir(os.path.join(src, f)) and "源文件" in f),
            op_type="copy",
            update_status_func=update_status
        )
    def on_distribute_ops():
        if not parent.product_dir:
            QMessageBox.warning(dialog, "提示", "请先选择成品路径")
            return
        src = parent.product_dir
        dest = get_edit_dist_ops()
        os.makedirs(dest, exist_ok=True)
        # 使用任务管理器处理文件复制
        task_name = f"剪辑分发运营 - 工单{order_data['id']}"
        def update_status():
            _log_action("剪辑分发运营", f"工单ID={order_data['id']}, 角色=剪辑, 源路径={src}, 目标路径={dest}")
            db_manager.update_work_order_status(order_data['id'], '后期已完成')
            # 调用API更新工单状态
            api_response = api_manager.update_work_order_status(order_data['id'], '后期已完成')
            if api_response['success']:
                logger.info(f"API更新工单{order_data['id']}状态成功")
            else:
                error_msg = f"API更新工单{order_data['id']}状态失败: {api_response['error']}"
                logger.error(error_msg)
                QMessageBox.warning(dialog, "API更新失败", error_msg)
            parent.refresh_work_orders()
            # 发送通知：剪辑分发运营
            department = order_data.get('department') or order_data.get('部门') or order_data.get('产线') or '相关'
            send_notification(
                "工单状态变更通知",
                f"{order_data['id']} {order_data['model']} {order_data['name']}，剪辑已完成视频处理，成品视频已分发，请{department}运营同事在工作时间段1小时内登录'工单管理'系统领取图片并进行上架！",
                order_data.get('department')
            )
            # 显示完成消息
            msg = QMessageBox(dialog)
            msg.setWindowTitle("分发完成")
            msg.setText(f"成功分发到运营部：\n{dest}")
            open_btn = msg.addButton("打开", QMessageBox.ActionRole)
            msg.addButton("确定", QMessageBox.AcceptRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
    
        # 获取源路径中的所有内容（文件和文件夹）
        all_items = []
        if os.path.exists(src):
            for item in os.listdir(src):
                item_path = os.path.join(src, item)
                all_items.append(item)
    
        _add_file_task(
            name=task_name,
            files=all_items,
            src_dir=src,
            dest_dir=dest,
            file_filter=lambda f: not (os.path.isdir(os.path.join(src, f)) and "源文件" in f),
            op_type="copy",
            update_status_func=update_status
        )
    def on_distribute_sales():
        if not parent.product_dir:
            QMessageBox.warning(dialog, "提示", "请先选择成品路径")
            return
        src = parent.product_dir
        dest = get_edit_dist_sales()
        os.makedirs(dest, exist_ok=True)
        # 使用任务管理器处理文件复制
        task_name = f"剪辑分发销售 - 工单{order_data['id']}"
        def update_status():
            _log_action("剪辑分发销售", f"工单ID={order_data['id']}, 角色=剪辑, 源路径={src}, 目标路径={dest}")
            db_manager.update_work_order_status(order_data['id'], '后期已完成')
            # 调用API更新工单状态
            api_response = api_manager.update_work_order_status(order_data['id'], '后期已完成')
            if api_response['success']:
                logger.info(f"API更新工单{order_data['id']}状态成功")
            else:
                error_msg = f"API更新工单{order_data['id']}状态失败: {api_response['error']}"
                logger.error(error_msg)
                QMessageBox.warning(dialog, "API更新失败", error_msg)
            parent.refresh_work_orders()
            # 发送通知：剪辑分发销售
            department = order_data.get('department') or order_data.get('部门') or order_data.get('产线') or '相关'
            send_notification(
                "工单状态变更通知",
                f"{order_data['id']} {order_data['model']} {order_data['name']}，剪辑已完成视频处理，成品视频已分发，请{department}销售同事在工作时间段1小时内登录'工单管理'系统领取视频！",
                order_data.get('department')
            )
            # 显示完成消息
            msg = QMessageBox(dialog)
            msg.setWindowTitle("分发完成")
            msg.setText(f"成功分发到销售部：\n{dest}")
            open_btn = msg.addButton("打开", QMessageBox.ActionRole)
            msg.addButton("确定", QMessageBox.AcceptRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
    
        # 获取源路径中的所有内容（文件和文件夹）
        all_items = []
        if os.path.exists(src):
            for item in os.listdir(src):
                item_path = os.path.join(src, item)
                all_items.append(item)
    
        _add_file_task(
            name=task_name,
            files=all_items,
            src_dir=src,
            dest_dir=dest,
            file_filter=lambda f: not (os.path.isdir(os.path.join(src, f)) and ("源文件" in f or "精修" in f or "详情页" in f)),
            op_type="copy",
            update_status_func=update_status
        )
    get_material_btn.clicked.connect(on_get_material)
    select_product_btn.clicked.connect(on_select_product)
    submit_review_btn.clicked.connect(on_submit_review)
    distribute_ops_btn.clicked.connect(on_distribute_ops)
    distribute_sales_btn.clicked.connect(on_distribute_sales)
    button_layout.addWidget(get_material_btn)
    button_layout.addWidget(select_product_btn)
    button_layout.addWidget(submit_review_btn)
    button_layout.addWidget(distribute_ops_btn)
    button_layout.addWidget(distribute_sales_btn)
    button_layout.addStretch()
    main_layout.addWidget(button_widget)
    dialog.exec()
            # 运营弹窗
