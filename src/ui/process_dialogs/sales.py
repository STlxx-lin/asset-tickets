"""
show_sales_dialog — 销售 工单处理对话框
从 main_window.py 重构迁移而来，不改变任何业务逻辑。
"""
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (
    QDesktopServices,
)
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.paths import (
    SALES_GET_SRC,
)
from src.ui.dialog_helpers import show_path_result


def show_sales_dialog(parent, order_data, callbacks):
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

    def get_sales_get_src():
        return SALES_GET_SRC(order_data['department'], order_data['id'], order_data['model'], order_data['name'])


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
            background: transparent;
        }
    """)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_layout.addWidget(title_label)
    # 表单区域
    form_widget = QWidget()
    form_layout = QVBoxLayout(form_widget)
    form_layout.setSpacing(15)
    # 工单基本信息分组
    basic_group = QGroupBox("工单基本信息")
    basic_layout = QFormLayout(basic_group)
    basic_layout.setSpacing(12)
    basic_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
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
    path_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    # 创建可双击的路径标签
    def create_clickable_path_label(path, tooltip_text):
        label = QLabel(path)
        label.setStyleSheet("""
            QLabel {
                color: #4f8ef7;
                text-decoration: underline;
                cursor: pointer;
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
        show_path_result(dialog, "已选择", f"存放路径：\n{dir_path}", dir_path)
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
        try:
            src_files = os.listdir(src)
        except OSError as e:
            QMessageBox.warning(dialog, "提示", f"无法读取素材目录：\n{src}\n{e}")
            return
        if not src_files:
            # 空目录领取会以"0 文件移动"假成功推进状态，必须拦截
            QMessageBox.warning(dialog, "提示", f"素材目录中没有可领取的文件：\n{src}")
            return
        def update_status(task_ok=True, task_errors=None):
            # 任务失败时不显示"领取完成"成功提示
            if not task_ok:
                try:
                    if dialog.isVisible():
                        QMessageBox.warning(dialog, "任务失败", f"文件操作失败：\n" + "\n".join((task_errors or [])[:5]))
                except RuntimeError:
                    pass
                return
            # 日志为核心业务，不依赖对话框是否可见（异步任务完成时对话框可能已被关闭）
            _log_action("销售领取素材", f"工单ID={order_data['id']}, 角色=销售, 源路径={src}, 目标路径={dest}")
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
