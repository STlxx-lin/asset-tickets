"""
show_ops_dialog — 运营 工单处理对话框
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


def show_ops_dialog(parent, order_data, callbacks):
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

    def get_ops_get_src():
        return OPS_GET_SRC(order_data['department'], order_data['id'], order_data['model'], order_data['name'])


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
    src_path = get_ops_get_src()
    store_path_label = QLabel("请选择存放路径")
    # 创建路径标签
    src_label = create_clickable_path_label(src_path, "素材源路径")
    # 添加路径到布局
    path_layout.addRow("素材源路径:", src_label)
    path_layout.addRow("存放路径:", store_path_label)
    form_layout.addWidget(path_group)
    # 产品上架信息分组
    product_group = QGroupBox("产品上架信息")
    product_layout = QVBoxLayout(product_group)
    product_layout.setSpacing(12)
    # 产品信息输入区域 - 横向排列
    input_widget = QWidget()
    input_layout = QHBoxLayout(input_widget)
    input_layout.setSpacing(6)  # 减少间距
    input_layout.setContentsMargins(5, 5, 5, 5)  # 减少边距
    # 创建输入框和标签
    title_label = QLabel("产品标题:")
    title_label.setMinimumWidth(60)  # 设置标签最小宽度
    title_edit = QLineEdit()
    title_edit.setPlaceholderText("请输入产品标题")
    title_edit.setMinimumWidth(120)  # 减少最小宽度
    title_edit.setMaximumWidth(150)  # 设置最大宽度
    keywords_label = QLabel("关键词:")
    keywords_label.setMinimumWidth(50)  # 设置标签最小宽度
    keywords_edit = QLineEdit()
    keywords_edit.setPlaceholderText("关键词，用逗号分隔")
    keywords_edit.setMinimumWidth(120)  # 减少最小宽度
    keywords_edit.setMaximumWidth(150)  # 设置最大宽度
    url_label = QLabel("URL:")
    url_label.setMinimumWidth(30)  # 设置标签最小宽度
    url_edit = QLineEdit()
    url_edit.setPlaceholderText("请输入产品URL")
    url_edit.setMinimumWidth(150)  # 减少最小宽度
    url_edit.setMaximumWidth(200)  # 设置最大宽度
    # 添加输入框到布局
    input_layout.addWidget(title_label)
    input_layout.addWidget(title_edit)
    input_layout.addWidget(keywords_label)
    input_layout.addWidget(keywords_edit)
    input_layout.addWidget(url_label)
    input_layout.addWidget(url_edit)
    input_layout.addStretch()  # 添加弹性空间
    product_layout.addWidget(input_widget)
    # 按钮区域 - 横向排列
    button_widget = QWidget()
    button_layout = QHBoxLayout(button_widget)
    button_layout.setSpacing(15)
    # 添加按钮
    add_btn = QPushButton("添加产品信息")
    add_btn.setStyleSheet("""
        QPushButton {
            background-color: #28a745;
            color: #FFFFFF;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: bold;
            min-width: 100px;
        }
        QPushButton:hover {
            background-color: #218838;
        }
        QPushButton:pressed {
            background-color: #1e7e34;
        }
    """)
    # 删除按钮
    delete_selected_btn = QPushButton("删除选中")
    delete_selected_btn.setStyleSheet("""
        QPushButton {
            background-color: #dc3545;
            color: #FFFFFF;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: bold;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #c82333;
        }
        QPushButton:pressed {
            background-color: #bd2130;
        }
        QPushButton:disabled {
            background-color: #6c757d;
            color: #adb5bd;
        }
    """)
    delete_selected_btn.setEnabled(False)  # 初始状态禁用
    button_layout.addWidget(add_btn)
    button_layout.addStretch()  # 添加弹性空间
    button_layout.addWidget(delete_selected_btn)
    product_layout.addWidget(button_widget)
    # 产品信息列表
    list_widget = QWidget()
    list_layout = QVBoxLayout(list_widget)
    list_layout.setSpacing(8)
    list_label = QLabel("已添加的产品信息：")
    list_label.setStyleSheet("""
        QLabel {
            font-size: 13px;
            color: #cccccc;
            padding: 4px 0;
        }
    """)
    list_layout.addWidget(list_label)
    # 创建滚动区域来显示产品信息
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setMinimumHeight(150)  # 增加最小高度
    scroll_area.setMaximumHeight(300)  # 增加最大高度
    scroll_area.setStyleSheet("""
        QScrollArea {
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #2a2a2a;
        }
        QScrollBar:vertical {
            background-color: #3c3c3c;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
    """)
    # 创建容器widget来存放产品信息项
    products_container = QWidget()
    products_layout = QVBoxLayout(products_container)
    products_layout.setSpacing(8)
    products_layout.setContentsMargins(10, 10, 10, 10)
    products_layout.addStretch()  # 添加弹性空间
    scroll_area.setWidget(products_container)
    list_layout.addWidget(scroll_area)
    product_layout.addWidget(list_widget)
    # 将整个产品上架信息分组放在滚动区域中
    product_scroll_area = QScrollArea()
    product_scroll_area.setWidgetResizable(True)
    product_scroll_area.setMinimumHeight(400)  # 设置整个分组的最小高度
    product_scroll_area.setMaximumHeight(500)  # 设置整个分组的最大高度
    product_scroll_area.setStyleSheet("""
        QScrollArea {
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #2a2a2a;
        }
        QScrollBar:vertical {
            background-color: #3c3c3c;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
    """)
    product_scroll_area.setWidget(product_group)
    form_layout.addWidget(product_scroll_area)
    # 存储产品信息的列表
    products_list = []
    selected_products = set()  # 存储选中的产品索引
    def validate_url(url):
        """验证URL格式"""
        # 简单的URL验证正则表达式
        url_pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP地址
            r'(?::\d+)?'  # 可选的端口
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))
    def update_delete_button():
        """更新删除按钮状态"""
        delete_selected_btn.setEnabled(len(selected_products) > 0)
    def add_product_info():
        title = title_edit.text().strip()
        keywords = keywords_edit.text().strip()
        url = url_edit.text().strip()
        if not title or not keywords or not url:
            QMessageBox.warning(dialog, "提示", "请填写完整的产品信息")
            return
        if not validate_url(url):
            QMessageBox.warning(dialog, "提示", "请输入有效的URL地址")
            return
        # 创建产品信息项
        product_item = QWidget()
        item_layout = QHBoxLayout(product_item)
        item_layout.setContentsMargins(8, 6, 8, 6)
        item_layout.setSpacing(10)
        # 复选框用于选中
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #555555;
                border-radius: 3px;
                background-color: #2a2a2a;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QCheckBox::indicator:checked::after {
                content: "✓";
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        # 产品信息标签 - 支持双击打开链接
        info_text = f"标题: {title} | 关键词: {keywords} | URL: {url}"
        info_label = QLabel(info_text)
        info_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #3c3c3c;
                border-radius: 3px;
                border: 1px solid #555555;
            }
            QLabel:hover {
                background-color: #4a4a4a;
                border: 1px solid #0078d4;
                cursor: pointer;
            }
        """)
        info_label.setWordWrap(True)
        info_label.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手型光标
        # 双击打开链接
        def open_url():
            try:
                QDesktopServices.openUrl(QUrl(url))
                _log_action("打开产品链接", f"工单ID={order_data['id']}, 角色=运营, URL={url}")
            except Exception as e:
                QMessageBox.warning(dialog, "错误", f"无法打开链接: {str(e)}")
        info_label.mouseDoubleClickEvent = lambda event: open_url()
        # 删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: #FFFFFF;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
                min-width: 40px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        item_layout.addWidget(checkbox)
        item_layout.addWidget(info_label, 1)
        item_layout.addWidget(delete_btn)
        # 添加到容器
        products_layout.insertWidget(products_layout.count() - 1, product_item)
        product_index = len(products_list)
        products_list.append({
            'widget': product_item,
            'title': title,
            'keywords': keywords,
            'url': url,
            'checkbox': checkbox
        })
        # 清空输入框
        title_edit.clear()
        keywords_edit.clear()
        url_edit.clear()
        # 复选框选中事件
        def on_checkbox_changed(checked):
            if checked:
                selected_products.add(product_index)
            else:
                selected_products.discard(product_index)
            update_delete_button()
        checkbox.toggled.connect(on_checkbox_changed)
        # 删除按钮事件
        def delete_product():
            products_layout.removeWidget(product_item)
            product_item.deleteLater()
            products_list.remove({
                'widget': product_item,
                'title': title,
                'keywords': keywords,
                'url': url,
                'checkbox': checkbox
            })
            selected_products.discard(product_index)
            update_delete_button()
        delete_btn.clicked.connect(delete_product)
        # 记录日志
        _log_action("添加产品信息", f"工单ID={order_data['id']}, 角色=运营, 产品标题={title}, 关键词={keywords}, URL={url}")
        # 自动变更状态为"已上架"
        db_manager.update_work_order_status(order_data['id'], '已上架')
        parent.refresh_work_orders()
    def delete_selected_products():
        """删除选中的产品信息"""
        if not selected_products:
            return
        # 按索引倒序删除，避免索引变化
        for index in sorted(selected_products, reverse=True):
            if index < len(products_list):
                product = products_list[index]
                products_layout.removeWidget(product['widget'])
                product['widget'].deleteLater()
                products_list.pop(index)
        selected_products.clear()
        update_delete_button()
        # 记录日志
        _log_action("删除产品信息", f"工单ID={order_data['id']}, 角色=运营, 删除数量={len(selected_products)}")
    add_btn.clicked.connect(add_product_info)
    delete_selected_btn.clicked.connect(delete_selected_products)
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
        src = get_ops_get_src()
        if not parent.store_dir:
            QMessageBox.warning(dialog, "提示", "请先选择存放路径")
            return
        dest = os.path.join(parent.store_dir, f"{order_data['id']} {order_data['model']} {order_data['name']}")
        if not os.path.exists(src):
            QMessageBox.warning(dialog, "提示", f"素材文件夹不存在: {src}")
            return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # 使用任务管理器处理文件移动
        task_name = f"运营领取素材 - 工单{order_data['id']}"
        def update_status():
            _log_action("运营领取素材", f"工单ID={order_data['id']}, 角色=运营, 源路径={src}, 目标路径={dest}")
            # 自动变更状态为"待上架"
            db_manager.update_work_order_status(order_data['id'], '待上架')
            parent.refresh_work_orders()
            # 显示完成消息
            msg = QMessageBox(dialog)
            msg.setWindowTitle("领取完成")
            msg.setText(f"素材已领取到：\n{dest}")
            open_btn = msg.addButton("打开", QMessageBox.ActionRole)
            msg.addButton("确定", QMessageBox.AcceptRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
            # 以运营领取素材为例：
            # send_dingtalk_markdown(
            #     "工单状态变更通知",
            #     f"### 工单号：{order_data['id']}\n- 角色：运营\n- 操作：领取素材\n- 状态：待上架\n- 目标路径：{dest}"
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
            # 销售弹窗
