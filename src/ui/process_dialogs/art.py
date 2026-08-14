"""
show_art_dialog — 美工 工单处理对话框
从 main_window.py 重构迁移而来，不改变任何业务逻辑。
"""
import datetime
import logging
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

from src.core.config import get_feature_enabled
from src.core.database import db_manager
from src.core.notification import send_notification
from src.core.paths import (
    ART_DIST_OPS,
    ART_DIST_SALES,
    ART_GET_IMG_DEST,
    ART_GET_IMG_SRC,
    ART_POST_REVIEW_TRANSIT,
)
from src.core.status_sync import update_status_with_api, update_time_with_api
from src.ui.dialog_helpers import show_api_update_error, show_path_result

logger = logging.getLogger(__name__)


def show_art_dialog(parent, order_data, callbacks):
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

    def get_art_get_img_src():
        return ART_GET_IMG_SRC(order_data['department'], order_data['id'], order_data['model'], order_data['name'])

    def get_art_get_img_dest():
        return ART_GET_IMG_DEST(order_data['department'], order_data['id'], order_data['model'], order_data['name'])

    def get_art_dist_ops():
        return ART_DIST_OPS(order_data['department'], order_data['id'], order_data['model'], order_data['name'])

    def get_art_dist_sales():
        return ART_DIST_SALES(order_data['department'], order_data['id'], order_data['model'], order_data['name'])

    def get_art_transit():
        return ART_POST_REVIEW_TRANSIT(order_data['department'], order_data['id'], order_data['model'], order_data['name'])

    def is_art_post_review_enabled() -> bool:
        return get_feature_enabled('art_post_review_enabled')

    # 美工后期审批开启时，分发目标为「美工待审批」中转目录（01运营/02销售），审批通过后才到运营/销售
    art_post_review_on = is_art_post_review_enabled()


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
    get_src = get_art_get_img_src()
    get_dest = get_art_get_img_dest()
    # 美工后期审批开启时，分发路径显示为待审批中转子目录
    if art_post_review_on:
        ops_path = os.path.join(get_art_transit(), '01运营')
        sales_path = os.path.join(get_art_transit(), '02销售')
    else:
        ops_path = get_art_dist_ops()
        sales_path = get_art_dist_sales()
    # 检查领取状态
    def check_collected_status():
        """检查是否已领取素材"""
        logs = db_manager.get_logs_by_order_id(order_data['id'])
        for log in logs:
            if (log.get('action_type') == '美工领取素材' and 
                f"工单ID={order_data['id']}" in log.get('details', '')):
                return {
                    'collected': True,
                    'user': log.get('role', ''),
                    'time': log.get('timestamp', '').strftime('%Y-%m-%d %H:%M:%S') if log.get('timestamp') else ''
                }
        return {'collected': False, 'user': '', 'time': ''}

    # 优化分发路径显示逻辑
    def create_distribute_path_label(path, tooltip_text, order_data, path_type):
        # 检查领取状态
        status = parent.check_path_collected_status(order_data, path_type)
        if status['collected']:
            label = QLabel(f"✅ {status['user']}已领取 ({status['time']})")
            label.setStyleSheet("""
                QLabel {
                    color: #00ff00;
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 3px;
                    background-color: #1a3d1a;
                }
            """)
            label.setToolTip(f"已领取 - {tooltip_text}")
        else:
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

    # 创建路径标签
    collected_status = check_collected_status()
    if collected_status['collected']:
        get_src_label = QLabel(f"✅ {collected_status['user']}已领取 ({collected_status['time']})")
        get_src_label.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 3px;
                background-color: #1a3d1a;
            }
        """)
        get_dest_label = QLabel(f"✅ {collected_status['user']}已领取 ({collected_status['time']})")
        get_dest_label.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 3px;
                background-color: #1a3d1a;
            }
        """)
    else:
        get_src_label = create_clickable_path_label(get_src, "领取源路径")
        get_dest_label = create_clickable_path_label(get_dest, "领取存放路径")

    ops_label = create_distribute_path_label(ops_path, "分发运营路径", order_data, 'art_dist_ops')
    sales_label = create_distribute_path_label(sales_path, "分发销售路径", order_data, 'art_dist_sales')

    # 检查成品路径状态
    def check_product_path_status():
        """检查成品路径是否有操作记录，返回路径信息"""
        logs = db_manager.get_logs_by_order_id(order_data['id'])
        distribute_actions = ['美工分发运营', '美工分发销售']
    
        for log in logs:
            if log.get('action_type') in distribute_actions and f"工单ID={order_data['id']}" in log.get('details', ''):
                # 从日志详情中提取路径信息
                details = log.get('details', '')
                if '源路径=' in details:
                    path_start = details.find('源路径=') + 4
                    path_end = details.find(',', path_start)
                    if path_end == -1:
                        path_end = details.find('目标路径=')
                    if path_end != -1:
                        return details[path_start:path_end].strip()
        return None

    # 根据是否有操作记录决定显示内容
    product_path = check_product_path_status()
    if product_path:
        # 有设置过，显示完整路径
        product_label = QLabel(product_path)
        product_label.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 3px;
                background-color: #1a3d1a;
            }
        """)
        product_label.setToolTip("双击打开路径")
        product_label.mousePressEvent = lambda event: QDesktopServices.openUrl(QUrl.fromLocalFile(product_path))
    else:
        # 未设置过，显示为空
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
    info_label = QLabel("💡 提示：请先领取素材，然后选择成品路径，最后进行分发操作")
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
    distribute_ops_btn = QPushButton("分发运营")
    distribute_sales_btn = QPushButton("分发销售")
    parent.product_dir = None
    def on_get_material():
        src = get_art_get_img_src()
        dest = get_art_get_img_dest()
        if not os.path.exists(src):
            QMessageBox.warning(dialog, "提示", f"素材文件夹不存在: {src}")
            return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # 使用任务管理器处理文件移动
        task_name = f"美工领取素材 - 工单{order_data['id']}"
        def update_status(task_ok=True, task_errors=None):
            # 任务失败时不推进状态/发通知，避免状态与磁盘文件不一致
            if not task_ok:
                try:
                    if dialog.isVisible():
                        QMessageBox.warning(dialog, "任务失败", f"文件操作失败，工单状态未更新：\n" + "\n".join((task_errors or [])[:5]))
                except RuntimeError:
                    pass
                return
            # 状态更新/日志为核心业务，不依赖对话框是否可见（异步任务完成时对话框可能已被关闭）
            _log_action("美工领取素材", f"工单ID={order_data['id']}, 角色=美工, 源路径={src}, 目标路径={dest}")
            # 美工链专属状态：领取素材后进入设计中（与全局 status 解耦）
            art_before = order_data.get('art_status')
            db_manager.update_work_order_art_status(order_data['id'], '美工设计中')
            # 记录美工开始时间（API 失败时整体回滚 art_status 与时间字段）
            current_time = datetime.datetime.now()
            ok, error_msg = update_time_with_api(order_data['id'], 'art_start_time', current_time, art_status_before=art_before)
            if not ok:
                try:
                    if dialog.isVisible():
                        show_api_update_error(dialog, error_msg)
                except RuntimeError:
                    pass
            parent.refresh_work_orders()
            # 显示完成消息（对话框已关闭时跳过 UI 提示）
            try:
                if dialog.isVisible():
                    show_path_result(dialog, "领取完成", f"素材已移动到：\n{dest}", dest)
                    # 更新路径显示
                    get_src_label.setText(dest)
                    get_dest_label.setText(dest)
            except RuntimeError:
                pass
    
        # 获取源路径中的所有文件（包含子文件夹）
        all_items = []
        if os.path.exists(src):
            for root, dirs, files in os.walk(src):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), src)
                    all_items.append(rel_path)
    
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
        # 美工链专属状态：已选成品，待分发
        art_before = order_data.get('art_status')
        db_manager.update_work_order_art_status(order_data['id'], '美工待分发')
        # 记录美工结束时间（API 失败时整体回滚 art_status 与时间字段）
        current_time = datetime.datetime.now()
        ok, error_msg = update_time_with_api(order_data['id'], 'art_end_time', current_time, art_status_before=art_before)
        if not ok:
            show_api_update_error(dialog, error_msg)
        # 更新成品路径显示
        product_label.setText(dir_path)
        product_label.setStyleSheet("""
            QLabel {
                color: #00ff00;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 3px;
                background-color: #1a3d1a;
            }
        """)
        product_label.setToolTip("双击打开路径")
        product_label.mousePressEvent = lambda event: QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))
        show_path_result(dialog, "已选择", f"成品路径：\n{dir_path}", dir_path)
    def on_distribute_ops():
        if not parent.product_dir:
            QMessageBox.warning(dialog, "提示", "请先选择成品路径")
            return
        src = parent.product_dir
        review_on = is_art_post_review_enabled()
        dest = os.path.join(get_art_transit(), '01运营') if review_on else get_art_dist_ops()
        os.makedirs(dest, exist_ok=True)
        # 使用任务管理器处理文件复制
        task_name = f"美工分发运营 - 工单{order_data['id']}"
        def update_status(task_ok=True, task_errors=None):
            # 任务失败时不推进状态/发通知，避免状态与磁盘文件不一致
            if not task_ok:
                try:
                    if dialog.isVisible():
                        QMessageBox.warning(dialog, "任务失败", f"文件操作失败，工单状态未更新：\n" + "\n".join((task_errors or [])[:5]))
                except RuntimeError:
                    pass
                return
            # 状态更新/日志/通知为核心业务，不依赖对话框是否可见（异步任务完成时对话框可能已被关闭）
            _log_action("美工分发运营", f"工单ID={order_data['id']}, 角色=美工, 源路径={src}, 目标路径={dest}")
            review_now = is_art_post_review_enabled()
            new_status = '美工后期审核中' if review_now else '后期已完成'
            # 美工链专属状态：分发后进入审批中（或审批功能关闭时已完成）；API 失败时整体回滚
            art_before = order_data.get('art_status')
            db_manager.update_work_order_art_status(order_data['id'], '美工后期审核中' if review_now else '美工已完成')
            ok, error_msg = update_status_with_api(order_data['id'], new_status, order_data['status'], art_status_before=art_before)
            if not ok:
                try:
                    if dialog.isVisible():
                        show_api_update_error(dialog, error_msg)
                except RuntimeError:
                    pass
            parent.refresh_work_orders()
            # 发送通知：美工分发运营
            department = order_data.get('department') or order_data.get('部门') or order_data.get('产线') or '相关'
            if review_now:
                send_notification(
                    "工单美工审批提请通知",
                    f"### 工单号：{order_data['id']}\n- 角色：美工\n- 操作：分发运营并提请审批\n- 状态：美工后期审核中\n- 提示：美工已完成后期处理，成品图片已提交审批，请美工后期审批员登录系统进行审批！",
                    order_data.get('department')
                )
            else:
                send_notification(
                    "工单状态变更通知",
                    f"{order_data['id']} {order_data['model']} {order_data['name']}，美工已完成后期处理，成品图片已分发，请{department}运营同事在工作时间段1小时内登录'工单管理'系统领取图片并进行上架！",
                    order_data.get('department')
                )
            # 显示完成消息（对话框已关闭时跳过 UI 提示）
            try:
                if dialog.isVisible():
                    if review_now:
                        show_path_result(dialog, "已提交审批", f"成品已提交美工后期审批：\n{dest}", dest)
                    else:
                        show_path_result(dialog, "分发完成", f"成功分发到运营部：\n{dest}", dest)
            except RuntimeError:
                pass
    
        # 获取源路径中的所有文件（包含子文件夹）
        all_items = []
        if os.path.exists(src):
            for root, dirs, files in os.walk(src):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), src)
                    all_items.append(rel_path)
    
        _add_file_task(
            name=task_name,
            files=all_items,
            src_dir=src,
            dest_dir=dest,
            file_filter=lambda f: "源文件" not in f,
            op_type="copy",
            update_status_func=update_status
        )
    def on_distribute_sales():
        if not parent.product_dir:
            QMessageBox.warning(dialog, "提示", "请先选择成品路径")
            return
        src = parent.product_dir
        review_on = is_art_post_review_enabled()
        dest = os.path.join(get_art_transit(), '02销售') if review_on else get_art_dist_sales()
        os.makedirs(dest, exist_ok=True)
        # 使用任务管理器处理文件复制
        task_name = f"美工分发销售 - 工单{order_data['id']}"
        def update_status(task_ok=True, task_errors=None):
            # 任务失败时不推进状态/发通知，避免状态与磁盘文件不一致
            if not task_ok:
                try:
                    if dialog.isVisible():
                        QMessageBox.warning(dialog, "任务失败", f"文件操作失败，工单状态未更新：\n" + "\n".join((task_errors or [])[:5]))
                except RuntimeError:
                    pass
                return
            # 状态更新/日志/通知为核心业务，不依赖对话框是否可见（异步任务完成时对话框可能已被关闭）
            _log_action(f"{parent.role}分发销售", f"工单ID={order_data['id']}, 角色={parent.role}, 源路径={src}, 目标路径={dest}")
            review_now = is_art_post_review_enabled()
            new_status = '美工后期审核中' if review_now else '后期已完成'
            # 美工链专属状态：分发后进入审批中（或审批功能关闭时已完成）；API 失败时整体回滚
            art_before = order_data.get('art_status')
            db_manager.update_work_order_art_status(order_data['id'], '美工后期审核中' if review_now else '美工已完成')
            ok, error_msg = update_status_with_api(order_data['id'], new_status, order_data['status'], art_status_before=art_before)
            if not ok:
                try:
                    if dialog.isVisible():
                        show_api_update_error(dialog, error_msg)
                except RuntimeError:
                    pass
            parent.refresh_work_orders()
            # 发送通知：美工分发销售
            department = order_data.get('department') or order_data.get('部门') or order_data.get('产线') or '相关'
            if review_now:
                send_notification(
                    "工单美工审批提请通知",
                    f"### 工单号：{order_data['id']}\n- 角色：美工\n- 操作：分发销售并提请审批\n- 状态：美工后期审核中\n- 提示：美工已完成后期处理，成品图片已提交审批，请美工后期审批员登录系统进行审批！",
                    order_data.get('department')
                )
            else:
                send_notification(
                    "工单状态变更通知",
                    f"{order_data['id']} {order_data['model']} {order_data['name']}，美工已完成后期处理，成品图片已分发，请{department}销售同事在工作时间段1小时内登录'工单管理'系统领取图片！",
                    order_data.get('department')
                )
            # 显示完成消息（对话框已关闭时跳过 UI 提示）
            try:
                if dialog.isVisible():
                    if review_now:
                        show_path_result(dialog, "已提交审批", f"成品已提交美工后期审批：\n{dest}", dest)
                    else:
                        show_path_result(dialog, "分发完成", f"成功分发到销售部：\n{dest}", dest)
            except RuntimeError:
                pass
    
        # 获取源路径中的所有文件（包含子文件夹）
        all_items = []
        if os.path.exists(src):
            for root, dirs, files in os.walk(src):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), src)
                    all_items.append(rel_path)
    
        _add_file_task(
            name=task_name,
            files=all_items,
            src_dir=src,
            dest_dir=dest,
            file_filter=lambda f: "源文件" not in f,
            op_type="copy",
            update_status_func=update_status
        )
    get_material_btn.clicked.connect(on_get_material)
    select_product_btn.clicked.connect(on_select_product)
    distribute_ops_btn.clicked.connect(on_distribute_ops)
    distribute_sales_btn.clicked.connect(on_distribute_sales)
    button_layout.addWidget(get_material_btn)
    button_layout.addWidget(select_product_btn)
    button_layout.addWidget(distribute_ops_btn)
    button_layout.addWidget(distribute_sales_btn)
    button_layout.addStretch()
    main_layout.addWidget(button_widget)
    dialog.exec()
            # 剪辑弹窗
