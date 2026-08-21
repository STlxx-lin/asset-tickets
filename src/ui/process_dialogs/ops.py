"""
show_ops_dialog — 运营 工单处理对话框
从 main_window.py 重构迁移而来，不改变任何业务逻辑。
"""
import os
import re

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (
    QDesktopServices,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    CardWidget,
    FluentIcon as FIF,
    LineEdit,
    PrimaryPushButton,
    PushButton,
)

from src.core.database import db_manager
from src.core.paths import (
    OPS_GET_SRC,
)
from src.core.status_sync import update_status_with_api
from src.ui.dialog_helpers import show_api_update_error, show_path_result


def show_ops_dialog(parent, order_data, callbacks):
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

    def get_ops_get_src():
        return OPS_GET_SRC(order_data['department'], order_data['id'], order_data['model'], order_data['name'])


    dialog = QDialog(parent)
    dialog.setWindowTitle(f"办理工单 - {order_data['id']}")
    dialog.setMinimumWidth(860)
    dialog.resize(880, 560)
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
    main_layout.setSpacing(12)
    main_layout.setContentsMargins(20, 16, 20, 16)
    # 标题
    title_label = QLabel(f"办理工单 - {order_data['id']}")
    title_label.setStyleSheet("""
        QLabel {
            font-size: 18px;
            font-weight: bold;
            color: #FFFFFF;
            padding: 4px 0;
            background: transparent;
        }
    """)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_layout.addWidget(title_label)
    # 表单区域
    form_widget = QWidget()
    form_layout = QVBoxLayout(form_widget)
    form_layout.setContentsMargins(4, 4, 4, 4)
    form_layout.setSpacing(10)

    # 1. 工单基本信息卡片
    basic_card = CardWidget()
    basic_vbox = QVBoxLayout(basic_card)
    basic_vbox.setContentsMargins(14, 10, 14, 10)
    basic_vbox.setSpacing(6)

    basic_title = QLabel("📋 工单基本信息")
    basic_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #4f8ef7; background: transparent;")
    basic_vbox.addWidget(basic_title)

    basic_layout = QFormLayout()
    basic_layout.setSpacing(6)
    basic_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    id_label = QLabel(order_data['id'])
    dept_label = QLabel(order_data['department'])
    model_label = QLabel(order_data['model'])
    name_label = QLabel(order_data['name'])
    creator_label = QLabel(order_data['creator'])
    for lbl in [id_label, dept_label, model_label, name_label, creator_label]:
        lbl.setStyleSheet("color: #e8eaed; background: transparent;")
    basic_layout.addRow("工单ID:", id_label)
    basic_layout.addRow("产线/部门:", dept_label)
    basic_layout.addRow("型号:", model_label)
    basic_layout.addRow("名称:", name_label)
    basic_layout.addRow("发起人:", creator_label)
    basic_vbox.addLayout(basic_layout)
    form_layout.addWidget(basic_card)

    # 2. 路径信息卡片
    path_card = CardWidget()
    path_vbox = QVBoxLayout(path_card)
    path_vbox.setContentsMargins(14, 10, 14, 10)
    path_vbox.setSpacing(6)

    path_title = QLabel("📁 路径信息")
    path_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #4f8ef7; background: transparent;")
    path_vbox.addWidget(path_title)

    path_layout = QFormLayout()
    path_layout.setSpacing(6)
    path_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    # 创建可双击的路径标签
    def create_clickable_path_label(path, tooltip_text):
        label = QLabel(path)
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        label.setStyleSheet("""
            QLabel {
                color: #4f8ef7;
                text-decoration: underline;
                padding: 4px 8px;
                border-radius: 3px;
            }
            QLabel:hover {
                background-color: #232732;
                color: #6ba3ff;
            }
        """)
        label.setToolTip(f"点击打开：{tooltip_text}")
        def on_press(event):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        label.mousePressEvent = on_press
        return label
    # 获取路径信息
    src_path = get_ops_get_src()
    store_path_label = QLabel("请选择存放路径")
    store_path_label.setStyleSheet("color: #9ba3b0; background: transparent;")
    # 创建路径标签
    src_label = create_clickable_path_label(src_path, "素材源路径")
    # 添加路径到布局
    path_layout.addRow("素材源路径:", src_label)
    path_layout.addRow("存放路径:", store_path_label)
    path_vbox.addLayout(path_layout)
    form_layout.addWidget(path_card)

    # 3. 产品上架信息卡片
    product_card = CardWidget()
    product_layout = QVBoxLayout(product_card)
    product_layout.setContentsMargins(16, 14, 16, 14)
    product_layout.setSpacing(10)

    prod_title = QLabel("📦 产品上架信息")
    prod_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4f8ef7; background: transparent;")
    product_layout.addWidget(prod_title)

    # 产品信息输入区域 - 横向排列
    input_widget = QWidget()
    input_layout = QHBoxLayout(input_widget)
    input_layout.setSpacing(8)
    input_layout.setContentsMargins(0, 4, 0, 4)
    # 创建输入框和标签
    title_label = QLabel("产品标题:")
    title_label.setStyleSheet("color: #e8eaed; background: transparent;")
    title_edit = LineEdit()
    title_edit.setPlaceholderText("请输入产品标题")
    title_edit.setFixedHeight(32)
    keywords_label = QLabel("关键词:")
    keywords_label.setStyleSheet("color: #e8eaed; background: transparent;")
    keywords_edit = LineEdit()
    keywords_edit.setPlaceholderText("关键词，逗号分隔")
    keywords_edit.setFixedHeight(32)
    url_label = QLabel("URL:")
    url_label.setStyleSheet("color: #e8eaed; background: transparent;")
    url_edit = LineEdit()
    url_edit.setPlaceholderText("请输入产品URL")
    url_edit.setFixedHeight(32)
    # 添加输入框到布局
    input_layout.addWidget(title_label)
    input_layout.addWidget(title_edit, 2)
    input_layout.addWidget(keywords_label)
    input_layout.addWidget(keywords_edit, 2)
    input_layout.addWidget(url_label)
    input_layout.addWidget(url_edit, 3)
    product_layout.addWidget(input_widget)
    # 按钮区域 - 横向排列
    button_widget = QWidget()
    button_layout = QHBoxLayout(button_widget)
    button_layout.setContentsMargins(0, 0, 0, 0)
    button_layout.setSpacing(10)
    # 添加按钮
    add_btn = PrimaryPushButton(FIF.ADD, "添加产品信息")
    add_btn.setFixedHeight(32)
    # 删除按钮
    delete_selected_btn = PushButton(FIF.DELETE, "删除选中")
    delete_selected_btn.setFixedHeight(32)
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
    form_layout.addWidget(product_card)
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
                background-color: #232732;
                border: 1px solid #4f8ef7;
            }
        """)
        info_label.setWordWrap(True)
        info_label.setCursor(Qt.CursorShape.PointingHandCursor)  # 鼠标悬停时显示手型光标
        # 双击打开链接
        def on_double_click(event):
            try:
                QDesktopServices.openUrl(QUrl(url))
                _log_action("打开产品链接", f"工单ID={order_data['id']}, 角色=运营, URL={url}")
            except Exception as e:
                QMessageBox.warning(dialog, "错误", f"无法打开链接: {e!s}")
        info_label.mouseDoubleClickEvent = on_double_click
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
        # 业务顺序门禁：领取素材 → 待上架(95%) → 添加产品信息 → 已上架(100%)，
        # 状态单调递增不回退（此前无条件置"已上架"，先上架后领取会把状态降级）
        if order_data['status'] != '待上架':
            QMessageBox.warning(dialog, "提示",
                f"当前工单状态为【{order_data['status']}】，请先领取素材（状态变为待上架）后再添加产品信息上架。")
            return
        # 自动变更状态为"已上架"（本地+外部 API 同步，失败时回滚）
        ok, error_msg = update_status_with_api(order_data['id'], '已上架', order_data['status'])
        if not ok:
            show_api_update_error(dialog, error_msg)
            return
        # 成功后同步内存快照，避免二次添加时用陈旧回滚目标覆盖已上架状态
        order_data['status'] = '已上架'
        parent.refresh_work_orders()
    def delete_selected_products():
        """删除选中的产品信息"""
        if not selected_products:
            return
        deleted_count = len(selected_products)
        # 按索引倒序删除，避免索引变化
        for index in sorted(selected_products, reverse=True):
            if index < len(products_list):
                product = products_list[index]
                products_layout.removeWidget(product['widget'])
                product['widget'].deleteLater()
                products_list.pop(index)
        # 记录日志（需在 clear 之前记录数量）
        _log_action("删除产品信息", f"工单ID={order_data['id']}, 角色=运营, 删除数量={deleted_count}")
        selected_products.clear()
        update_delete_button()
    add_btn.clicked.connect(add_product_info)
    delete_selected_btn.clicked.connect(delete_selected_products)
    main_layout.addWidget(form_widget)
    # 按钮区域
    button_widget = QWidget()
    button_layout = QHBoxLayout(button_widget)
    button_layout.setSpacing(12)
    select_store_btn = PushButton(FIF.FOLDER, "选择存放路径")
    select_store_btn.setFixedHeight(34)
    get_material_btn = PrimaryPushButton(FIF.FOLDER_ADD, "领取素材")
    get_material_btn.setFixedHeight(34)
    parent.store_dir = None
    def on_select_store():
        dir_path = QFileDialog.getExistingDirectory(dialog, "选择存放路径")
        if not dir_path:
            return
        parent.store_dir = dir_path
        store_path_label.setText(dir_path)
        show_path_result(dialog, "已选择", f"存放路径：\n{dir_path}", dir_path)
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
        src_files = os.listdir(src)
        if not src_files:
            # 空目录领取会以"0 文件移动"假成功推进状态，必须拦截
            QMessageBox.warning(dialog, "提示", f"素材目录中没有可领取的文件：\n{src}")
            return
        def update_status(task_ok=True, task_errors=None):
            # 任务失败时不推进状态，避免状态与磁盘不一致
            if not task_ok:
                try:
                    if dialog.isVisible():
                        QMessageBox.warning(dialog, "任务失败", f"文件操作失败，工单状态未更新：\n" + "\n".join((task_errors or [])[:5]))
                except RuntimeError:
                    pass
                return
            # 日志/状态更新为核心业务，不依赖对话框是否可见（异步任务完成时对话框可能已被关闭）
            _log_action("运营领取素材", f"工单ID={order_data['id']}, 角色=运营, 源路径={src}, 目标路径={dest}")
            # 自动变更状态为"待上架"（本地+外部 API 同步，失败时回滚；对话框可能已关闭，UI 提示需保护）
            ok, error_msg = update_status_with_api(order_data['id'], '待上架', order_data['status'])
            if ok:
                # 成功后同步内存快照，避免二次添加产品信息时用陈旧回滚目标覆盖已上架状态
                order_data['status'] = '待上架'
            else:
                try:
                    if dialog.isVisible():
                        show_api_update_error(dialog, error_msg)
                except RuntimeError:
                    pass
                return  # 状态未写入，不显示"领取完成"
            parent.refresh_work_orders()
            # 显示完成消息（对话框已关闭时跳过 UI 提示）
            try:
                if dialog.isVisible():
                    show_path_result(dialog, "领取完成", f"素材已领取到：\n{dest}", dest)
            except RuntimeError:
                pass
        _add_file_task(
            name=task_name,
            files=src_files,
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
