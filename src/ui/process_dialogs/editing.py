"""
show_editing_dialog — 剪辑 工单处理对话框
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

from src.core.config import get_blocked_dir_keywords, get_feature_enabled
from src.core.database import db_manager
from src.core.notification import send_notification
from src.core.paths import (
    EDIT_DIST_OPS,
    EDIT_DIST_SALES,
    EDIT_GET_VIDEO_DEST,
    EDIT_GET_VIDEO_SRC,
    EDIT_POST_REVIEW_TRANSIT,
    to_local_path,
)
from src.core.status_sync import update_status_with_api, update_time_with_api
from src.ui.dialog_helpers import show_api_update_error, show_path_result

logger = logging.getLogger(__name__)


def show_editing_dialog(parent, order_data, callbacks):
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

    def is_video_post_review_enabled() -> bool:
        return get_feature_enabled('video_post_review_enabled')


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
        elif current_status == '后期已完成':
            # 已分发完成：允许补发另一通道（运营/销售），禁止再次提交审核
            submit_review_btn.setEnabled(False)
            submit_review_btn.setToolTip("成品视频已分发完成，无需再次提交审核")
            distribute_ops_btn.setEnabled(True)
            distribute_sales_btn.setEnabled(True)
            distribute_ops_btn.setToolTip("")
            distribute_sales_btn.setToolTip("")
        elif current_status == '视频后期审核中':
            # 已提交待审：禁止重复提交，避免覆盖已审核状态（曾导致审核通过后被误覆盖回滚）
            submit_review_btn.setEnabled(False)
            submit_review_btn.setToolTip("已提交视频后期审核，请等待审核结果")
            distribute_ops_btn.setEnabled(False)
            distribute_sales_btn.setEnabled(False)
            distribute_ops_btn.setToolTip("需要后期视频审核通过后方可分发")
            distribute_sales_btn.setToolTip("需要后期视频审核通过后方可分发")
            # 使用置灰的样式
            gray_style = "background-color: #444444; color: #888888; border: none; border-radius: 4px; padding: 10px 24px; font-size: 14px; font-weight: bold; min-width: 80px;"
            submit_review_btn.setStyleSheet(gray_style)
            distribute_ops_btn.setStyleSheet(gray_style)
            distribute_sales_btn.setStyleSheet(gray_style)
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
            _log_action("剪辑领取素材", f"工单ID={order_data['id']}, 角色=剪辑, 源路径={src}, 目标路径={dest}")
            status_before = order_data['status']
            # 记录剪辑开始时间并推进状态（status + edit_start_time 单条原子写入，API 失败整体回滚）
            current_time = datetime.datetime.now()
            ok, error_msg = update_time_with_api(order_data['id'], 'edit_start_time', current_time,
                                                 status_before=status_before, status_new='后期处理中')
            if ok:
                # 同步内存快照，供提交审核/分发作为正确的回滚目标
                order_data['status'] = '后期处理中'
            else:
                try:
                    if dialog.isVisible():
                        show_api_update_error(dialog, error_msg)
                except RuntimeError:
                    pass
                return  # 状态未写入，不显示"领取完成"，保留对话框可重试
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
        if not all_items:
            # 空目录领取会以"0 文件移动"假成功推进状态，必须拦截
            QMessageBox.warning(dialog, "提示", f"素材目录中没有可领取的文件：\n{src}")
            return

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
        # 命中管理员配置的禁止目录关键字（如源文件/原始素材）时拒绝选择
        blocked_hits = [k for k in get_blocked_dir_keywords() if k.lower() in dir_path.lower()]
        if blocked_hits:
            QMessageBox.warning(
                dialog, "禁止的目录",
                f"所选路径包含禁止的目录关键字：{', '.join(blocked_hits)}\n\n"
                "请选择成品目录，不要选择源文件等指定目录！"
            )
            return
        parent.product_dir = dir_path
        # 记录剪辑结束时间（API 失败时回滚时间字段）
        current_time = datetime.datetime.now()
        ok, error_msg = update_time_with_api(order_data['id'], 'edit_end_time', current_time)
        if not ok:
            show_api_update_error(dialog, error_msg)
        product_label.setText(dir_path)
        show_path_result(dialog, "已选择", f"成品路径：\n{dir_path}", dir_path)

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

        # 获取源路径中的所有文件（包含子文件夹）
        all_items = []
        if os.path.exists(src):
            for root, dirs, files in os.walk(src):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), src)
                    all_items.append(rel_path)
    
        if not all_items:
            QMessageBox.warning(dialog, "提示", "成品路径为空，没有视频可以上传！")
            return

        # 使用任务管理器异步复制视频到中转路径
        task_name = f"上传成品视频 - 工单{order_data['id']}"
    
        def update_status(task_ok=True, task_errors=None):
            # 任务失败时不推进状态/发通知，避免状态与磁盘文件不一致
            if not task_ok:
                try:
                    if dialog.isVisible():
                        QMessageBox.warning(dialog, "任务失败", f"视频上传失败，工单状态未更新：\n" + "\n".join((task_errors or [])[:5]))
                except RuntimeError:
                    pass
                return
            # 状态更新/日志/通知为核心业务，不依赖对话框是否可见（异步任务完成时对话框可能已被关闭）
            # 上传成功后，将中转路径写入数据库成品路径
            product_path_before = order_data.get('edit_product_path')
            db_manager.update_work_order_product_path(order_data['id'], transit_dir)
            parent.product_dir = transit_dir
            try:
                if dialog.isVisible():
                    product_label.setText(transit_dir)
            except RuntimeError:
                pass

            # 更新工单状态为 视频后期审核中（API 失败时整体回滚状态与成品路径）
            new_status = '视频后期审核中'
            ok, error_msg = update_status_with_api(order_data['id'], new_status, order_data['status'], product_path_before=product_path_before)
            if ok:
                # 同步内存快照，供分发步骤作为正确的回滚目标
                order_data['status'] = new_status
            else:
                try:
                    if dialog.isVisible():
                        show_api_update_error(dialog, error_msg)
                except RuntimeError:
                    pass
                return  # 状态未变更，中止后续日志/通知/成功提示，保留对话框可重试

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
            # 排除「源文件」子目录与「不通过」退回目录中的文件，避免旧视频/源素材被重复上传
            file_filter=lambda f: not any(k in f for k in ["源文件", "不通过"]),
            op_type="copy",
            update_status_func=update_status
        )
    def on_distribute_ops():
        if not parent.product_dir:
            QMessageBox.warning(dialog, "提示", "请先选择成品路径")
            return
        if not os.path.exists(parent.product_dir):
            QMessageBox.warning(dialog, "提示", f"成品路径不存在：\n{parent.product_dir}")
            return
        src = parent.product_dir
        dest = get_edit_dist_ops()
        # 分发前向用户明确展示目标目录，确认后才执行复制（防止分发到错误位置）
        confirm = QMessageBox.question(
            dialog, "确认分发",
            f"成品源目录：\n{src}\n\n分发目标目录：\n{dest}\n\n确认将成品分发到该目标目录？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        os.makedirs(dest, exist_ok=True)
        # 使用任务管理器处理文件复制
        task_name = f"剪辑分发运营 - 工单{order_data['id']}"
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
            _log_action("剪辑分发运营", f"工单ID={order_data['id']}, 角色=剪辑, 源路径={src}, 目标路径={dest}")
            ok, error_msg = update_status_with_api(order_data['id'], '后期已完成', order_data['status'])
            if ok:
                order_data['status'] = '后期已完成'
            else:
                try:
                    if dialog.isVisible():
                        show_api_update_error(dialog, error_msg)
                except RuntimeError:
                    pass
                return  # 状态未变更，中止后续通知与成功提示
            parent.refresh_work_orders()
            # 发送通知：剪辑分发运营
            department = order_data.get('department') or order_data.get('部门') or order_data.get('产线') or '相关'
            send_notification(
                "工单状态变更通知",
                f"{order_data['id']} {order_data['model']} {order_data['name']}，剪辑已完成视频处理，成品视频已分发，请{department}运营同事在工作时间段1小时内登录'工单管理'系统领取图片并进行上架！",
                order_data.get('department')
            )
            # 显示完成消息（对话框已关闭时跳过 UI 提示）
            try:
                if dialog.isVisible():
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
        if not all_items:
            # 过滤后无文件时禁止空分发推进状态（task_manager 空任务会"假成功"）
            QMessageBox.warning(dialog, "提示", f"成品目录中没有可分发的文件：\n{src}")
            return

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
        if not os.path.exists(parent.product_dir):
            QMessageBox.warning(dialog, "提示", f"成品路径不存在：\n{parent.product_dir}")
            return
        src = parent.product_dir
        dest = get_edit_dist_sales()
        # 分发前向用户明确展示目标目录，确认后才执行复制（防止分发到错误位置）
        confirm = QMessageBox.question(
            dialog, "确认分发",
            f"成品源目录：\n{src}\n\n分发目标目录：\n{dest}\n\n确认将成品分发到该目标目录？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        os.makedirs(dest, exist_ok=True)
        # 使用任务管理器处理文件复制
        task_name = f"剪辑分发销售 - 工单{order_data['id']}"
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
            _log_action("剪辑分发销售", f"工单ID={order_data['id']}, 角色=剪辑, 源路径={src}, 目标路径={dest}")
            ok, error_msg = update_status_with_api(order_data['id'], '后期已完成', order_data['status'])
            if ok:
                order_data['status'] = '后期已完成'
            else:
                try:
                    if dialog.isVisible():
                        show_api_update_error(dialog, error_msg)
                except RuntimeError:
                    pass
                return  # 状态未变更，中止后续通知与成功提示
            parent.refresh_work_orders()
            # 发送通知：剪辑分发销售
            department = order_data.get('department') or order_data.get('部门') or order_data.get('产线') or '相关'
            send_notification(
                "工单状态变更通知",
                f"{order_data['id']} {order_data['model']} {order_data['name']}，剪辑已完成视频处理，成品视频已分发，请{department}销售同事在工作时间段1小时内登录'工单管理'系统领取视频！",
                order_data.get('department')
            )
            # 显示完成消息（对话框已关闭时跳过 UI 提示）
            try:
                if dialog.isVisible():
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
        if not all_items:
            # 过滤后无文件时禁止空分发推进状态（task_manager 空任务会"假成功"）
            QMessageBox.warning(dialog, "提示", f"成品目录中没有可分发的文件：\n{src}")
            return

        _add_file_task(
            name=task_name,
            files=all_items,
            src_dir=src,
            dest_dir=dest,
            file_filter=lambda f: not any(k in f for k in ["源文件", "精修", "详情页"]),
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
