"""
show_sales_dialog — 销售 工单处理对话框
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


def show_sales_dialog(parent, order_data, callbacks):
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

    def get_sales_get_src():
        return SALES_GET_SRC(order_data['department'], order_data['id'], order_data['model'], order_data['name'])


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
    src_path = get_sales_get_src()
    store_path_label = QLabel("请选择存放路径")
    # 创建路径标签
    src_label = create_clickable_path_label(src_path, "素材源路径")
    # 添加路径到布局
    path_layout.addRow("素材源路径:", src_label)
    path_layout.addRow("存放路径:", store_path_label)
    form_layout.addWidget(path_group)
    # 提示信息
    info_label = QLabel("💡 提示：请先选择存放路径，然后领取素材")
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
    select_store_btn = QPushButton("选择存放路径")
    get_material_btn = QPushButton("领取素材")
    parent.store_dir = None
    def on_select_store():
        dir_path = QFileDialog.getExistingDirectory(dialog, "选择存放路径")
        if not dir_path:
            return
        parent.store_dir = dir_path
        store_path_label.setText(dir_path)
        msg = QMessageBox(dialog)
        msg.setWindowTitle("已选择")
        msg.setText(f"存放路径：\n{dir_path}")
        open_btn = msg.addButton("打开", QMessageBox.ActionRole)
        msg.addButton("确定", QMessageBox.AcceptRole)
        msg.exec()
        if msg.clickedButton() == open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))
    def on_get_material():
        src = get_sales_get_src()
        if not parent.store_dir:
            QMessageBox.warning(dialog, "提示", "请先选择存放路径")
            return
        dest = os.path.join(parent.store_dir, f"{order_data['id']} {order_data['model']} {order_data['name']}")
        if not os.path.exists(src):
            QMessageBox.warning(dialog, "提示", f"素材文件夹不存在: {src}")
            return
        # 统一为创建上级目录
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # 使用任务管理器处理文件移动
        task_name = f"销售领取素材 - 工单{order_data['id']}"
        def update_status():
            _log_action("销售领取素材", f"工单ID={order_data['id']}, 角色=销售, 源路径={src}, 目标路径={dest}")
            # 更新工单状态为“已领取”并刷新UI
            # _update_status(order_data['id'], '已领取')
            # 显示完成消息
            msg = QMessageBox(dialog)
            msg.setWindowTitle("领取完成")
            msg.setText(f"素材已领取到：\n{dest}")
            open_btn = msg.addButton("打开", QMessageBox.ActionRole)
            msg.addButton("确定", QMessageBox.AcceptRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
            # 以销售领取素材为例：
            # send_dingtalk_markdown(
            #     "工单状态变更通知",
            #     f"### 工单号：{order_data['id']}\n- 角色：销售\n- 操作：领取素材\n- 状态：已领取\n- 目标路径：{dest}"
            # )
        _add_file_task(
            name=task_name,
            files=os.listdir(src),
            src_dir=src,
            dest_dir=dest,
            op_type="move",
            update_status_func=update_status
        )
    select_store_btn.clicked.connect(on_select_store)
    get_material_btn.clicked.connect(on_get_material)
    button_layout.addWidget(select_store_btn)
    button_layout.addWidget(get_material_btn)
    button_layout.addStretch()
    main_layout.addWidget(button_widget)
    dialog.exec()
