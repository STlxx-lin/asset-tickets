"""
show_post_review_combined_dialog — 后期审批合并对话框（视频后期审核 + 美工后期审批）

当用户同时拥有「视频后期审核」和「美工后期审批」角色时，登录界面合并为「后期审批」，
办理工单时打开本对话框。顶部提供「切换审批」按钮，可在两种审批模式间切换；
仅当工单状态到达对应流程时，对应审批模式才可用。
"""
import logging
import os

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.config import BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK
from src.core.database import db_manager
from src.core.paths import ART_POST_REVIEW_TRANSIT, to_local_path

logger = logging.getLogger(__name__)


def show_post_review_combined_dialog(parent, order_data, callbacks):
    """
    处理工单对话框入口（双审批角色合并时调用）。

    Args:
        parent: 父窗口（MainWindow 实例）
        order_data: 工单数据字典
        callbacks: 回调字典，含 update_status / add_file_task / log_action
    """
    status = order_data.get('status', '')
    # 美工链状态优先读 art_status（与全局 status 解耦，不受剪辑链状态覆盖影响），兼容旧数据回退全局 status
    art_status = order_data.get('art_status') or status

    # 各审批模式可用性：功能开关 + 工单状态到达对应流程
    video_feature_on = db_manager.get_system_setting('video_post_review_enabled', default='1') == '1'
    art_feature_on = db_manager.get_system_setting('art_post_review_enabled', default='1') == '1'

    if BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK:
        video_status_ok = True
    else:
        video_status_ok = status in ('视频后期审核中', '后期已完成')
    art_status_ok = art_status == '美工后期审核中'

    video_enabled = video_feature_on and video_status_ok
    art_enabled = art_feature_on and art_status_ok

    # 路径可用性补充校验
    if video_enabled:
        edit_product_path = order_data.get('edit_product_path')
        if edit_product_path:
            edit_product_path = to_local_path(edit_product_path)
        if not edit_product_path or not os.path.exists(edit_product_path):
            video_enabled = False
    if art_enabled:
        transit_root = ART_POST_REVIEW_TRANSIT(order_data['department'], order_data['id'], order_data['model'], order_data['name'])
        if not os.path.exists(transit_root):
            art_enabled = False

    if not video_enabled and not art_enabled:
        QMessageBox.information(parent, "提示",
            f"当前工单状态为【{status}】\n该工单未到达视频后期审核或美工后期审批流程（或对应成品路径不存在），无法进行审批。"
        )
        return

    dialog = QDialog(parent)
    dialog.setWindowTitle(f"后期审批 - {order_data['id']}")
    dialog.setMinimumWidth(1400)
    dialog.setMinimumHeight(760)
    dialog.resize(1400, 760)
    dialog.setStyleSheet("""
        QDialog {
            background-color: #2E2E2E;
            color: #FFFFFF;
        }
    """)

    main_layout = QVBoxLayout(dialog)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)

    # 切换审批按钮组
    switch_layout = QHBoxLayout()
    switch_layout.setSpacing(12)
    switch_label = QLabel("切换审批:")
    switch_label.setStyleSheet("color: #9ba3b0; font-size: 14px; background: transparent; border: none;")
    switch_layout.addWidget(switch_label)

    switch_btn_style = """
        QPushButton {
            background-color: #3c3c3c;
            color: #FFFFFF;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px 22px;
            font-size: 14px;
            font-weight: bold;
            min-width: 120px;
        }
        QPushButton:hover { background-color: #505050; }
        QPushButton:disabled { background-color: #2b2b2b; color: #666666; border-color: #3a3a3a; }
        QPushButton:checked { background-color: #0078d4; border-color: #0078d4; }
    """
    video_btn = QPushButton("视频后期审批")
    video_btn.setCheckable(True)
    video_btn.setStyleSheet(switch_btn_style)
    art_btn = QPushButton("美工后期审批")
    art_btn.setCheckable(True)
    art_btn.setStyleSheet(switch_btn_style)
    switch_layout.addWidget(video_btn)
    switch_layout.addWidget(art_btn)
    switch_layout.addStretch()
    main_layout.addLayout(switch_layout)

    # 不可用的审批模式禁用并提示原因
    if not video_enabled:
        video_btn.setEnabled(False)
        video_btn.setToolTip(f"当前工单状态【{status}】未到视频后期审核流程（需【视频后期审核中】或【后期已完成】）")
    if not art_enabled:
        art_btn.setEnabled(False)
        art_btn.setToolTip(f"当前工单状态【{status}】未到美工后期审批流程（需【美工后期审核中】）")

    stacked = QStackedWidget()
    main_layout.addWidget(stacked, 1)

    video_page = QWidget()
    art_page = QWidget()
    stacked.addWidget(video_page)
    stacked.addWidget(art_page)

    from .art_post_review import build_art_post_review_ui
    from .video_post_review import build_video_post_review_ui
    build_video_post_review_ui(video_page, dialog, parent, order_data, callbacks)
    build_art_post_review_ui(art_page, dialog, parent, order_data, callbacks)

    def switch_to(index):
        stacked.setCurrentIndex(index)
        video_btn.setChecked(index == 0)
        art_btn.setChecked(index == 1)

    video_btn.clicked.connect(lambda: switch_to(0))
    art_btn.clicked.connect(lambda: switch_to(1))

    # 默认选中第一个可用的审批模式
    if video_enabled:
        switch_to(0)
    elif art_enabled:
        switch_to(1)

    dialog.exec()
