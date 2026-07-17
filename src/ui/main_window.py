import sys
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from PySide6.QtWidgets import (QMainWindow, QTableView, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QMessageBox, QHeaderView,
                             QSplitter, QGroupBox, QListWidget, QStackedWidget,
                             QTabWidget, QLineEdit, QDialog, QComboBox, QFormLayout, QDialogButtonBox, QListWidgetItem, QTableWidget, QTableWidgetItem, QFileDialog, QProgressBar, QTextBrowser, QTextEdit, QDateEdit, QScrollArea, QFrame, QProgressDialog, QCheckBox, QGridLayout, QStyledItemDelegate, QStyleOptionProgressBar, QStyle, QApplication)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont, QDesktopServices, QPainter, QPalette, QColor, QPixmap
from PySide6.QtCore import Qt, QThread, Signal, QObject, QUrl, QDate
from src.core.config import BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK
from .video_preview import VideoPreviewWidget
import sys
import os
# 添加项目根目录到Python搜索路径
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.database import db_manager
from .task_manager import Task, TaskManagerDialog
from .work_order_detail import WorkOrderDetailDialog
import datetime
import netifaces
import os
import shutil
import platform
import re
from src.core.api_manager import api_manager
import time

# 导入配置模块
from src.core.config import APP_VERSION, DB_CONFIG, DEFAULT_NOTIFICATION_TYPE

# 为兼容现有调用保留变量名，统一使用配置模块中的单一默认值
NOTIFICATION_TYPE = DEFAULT_NOTIFICATION_TYPE

ADMIN_PASSWORD = "Db65109032"
# 路径常量与工具函数 — 统一由 src.core.paths 提供
from src.core.paths import (
    VOLUMES, RAW_ROOT, ART_ROOT, VIDEO_ROOT, CENTER_ROOT,
    IMG_EXTS, VID_EXTS,
    PHOTOGRAPHY_UPLOAD, PHOTOGRAPHY_DIST_IMG, PHOTOGRAPHY_DIST_VIDEO,
    ART_GET_IMG_SRC, ART_GET_IMG_DEST, ART_DIST_OPS, ART_DIST_SALES,
    EDIT_GET_VIDEO_SRC, EDIT_GET_VIDEO_DEST, EDIT_DIST_OPS, EDIT_DIST_SALES,
    EDIT_POST_REVIEW_TRANSIT, OPS_GET_SRC, SALES_GET_SRC, to_local_path,
)
# 消息推送 — 统一由 src.core.notification 提供
from src.core.notification import (
    DINGTALK_BOTS, WECHAT_WORK_BOTS, LINE_NOTIFICATION_SETTINGS,
    NOTIFICATION_TYPE,
    get_department_line_names, load_notification_settings,
    apply_notification_settings, save_notification_settings,
    send_dingtalk_markdown, send_wechat_work_markdown, send_notification,
)
def is_video_review_enabled() -> bool:
    """读取视频审核功能开关，默认开启（True）。"""
    val = db_manager.get_system_setting('video_review_enabled', default='1')
    return val == '1'

def is_video_post_review_enabled() -> bool:
    """读取视频后期审核功能开关，默认开启（True）。"""
    val = db_manager.get_system_setting('video_post_review_enabled', default='1')
    return val == '1'

class AdminPasswordDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理员验证")
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)
        self.label = QLabel("请输入管理员密码：")
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.label)
        layout.addWidget(self.edit)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    def get_password(self):
        return self.edit.text().strip()

class FileOperationDialog(QDialog):
    def __init__(self, html_content, parent=None, title="确认删除", header_text="⚠️ 警告：此操作不可恢复！将要删除以下路径：", footer_text="是否确认删除上述所有文件及数据库记录？", is_confirmation=True, confirm_button_text="确认删除"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 500)
        
        # Apply dark theme style
        self.setStyleSheet("""
            QDialog {
                background-color: #2E2E2E;
                color: #FFFFFF;
            }
            QTextEdit {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                color: #FFFFFF;
                font-family: Consolas, monospace;
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
                padding: 8px 16px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        if header_text:
            label = QLabel(header_text)
            # Only style as warning if it looks like a warning or is confirmation
            if "警告" in header_text or is_confirmation:
                label.setStyleSheet("color: #ff4d4f; font-weight: bold; font-size: 16px;")
            else:
                label.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 16px;")
            layout.addWidget(label)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(html_content)
        layout.addWidget(text_edit)
        
        if footer_text:
            label_confirm = QLabel(footer_text)
            layout.addWidget(label_confirm)
        
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        if is_confirmation:
            btn_cancel = QPushButton("取消")
            btn_cancel.clicked.connect(self.reject)
            btn_cancel.setStyleSheet("background-color: #555555;")
            
            btn_confirm = QPushButton(confirm_button_text)
            btn_confirm.clicked.connect(self.accept)
            btn_confirm.setStyleSheet("background-color: #d93025;")
            
            buttons.addWidget(btn_cancel)
            buttons.addWidget(btn_confirm)
        else:
            btn_ok = QPushButton("确定")
            btn_ok.clicked.connect(self.accept)
            buttons.addWidget(btn_ok)
        
        layout.addLayout(buttons)

INVALID_PATH_NAME_CHARS = set('#%&*|\\:"<>?/')

def get_invalid_path_name_message(field_label, value):
    if value in {".", ".."}:
        return f"{field_label}不能为“.”或“..”"
    invalid_chars = sorted({ch for ch in value if ch in INVALID_PATH_NAME_CHARS})
    if invalid_chars:
        chars_text = " ".join(invalid_chars)
        return f"{field_label}不能包含以下字符：{chars_text}"
    return None


class CreateWorkOrderDialog(QDialog):
    def __init__(self, role, departments, user_name=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建新工单")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.role = role
        self.departments = departments
        self.user_name = user_name
        # 设置弹窗样式，与主系统保持一致
        self.setStyleSheet("""
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
            QLineEdit, QComboBox, QTextEdit {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 12px;
                color: #FFFFFF;
                font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
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
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        # 标题
        title_label = QLabel("创建新工单")
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
        self.id_field = QLineEdit()
        self.id_field.setText(datetime.datetime.now().strftime("%y%m%d%H%M"))
        self.department_field = QComboBox()
        self.department_field.addItems(self.departments)
        self.model_field = QLineEdit()
        self.model_field.setPlaceholderText("请输入产品型号")
        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("请输入产品名称")
        self.creator_field = QLineEdit()
        self.creator_field.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 12px;
                color: #FFFFFF;
                font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                background-color: #4c4c4c;
            }
        """)
        # 如果提供了用户名，自动填充到发起人字段
        if self.user_name:
            self.creator_field.setText(self.user_name)
            # 允许用户修改发起人字段
            self.creator_field.setReadOnly(False)
        else:
            self.creator_field.setText("")
            self.creator_field.setPlaceholderText("请输入发起人")
        # 添加项目类型选择
        self.project_type_field = QComboBox()
        self.project_type_field.setPlaceholderText("请选择项目类型")
        # 添加项目内容选择
        self.project_content_field = QComboBox()
        self.project_content_field.setPlaceholderText("请选择项目内容")
        # 添加需求人字段
        self.requester_field = QLineEdit()
        self.requester_field.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 12px;
                color: #FFFFFF;
                font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                background-color: #4c4c4c;
            }
        """)
        # 如果提供了用户名，自动填充到需求人字段
        if self.user_name:
            self.requester_field.setText(self.user_name)
        else:
            self.requester_field.setText("")
            self.requester_field.setPlaceholderText("请输入需求人")
        
        # 添加选择需求人的按钮
        self.select_requester_btn = QPushButton("选择")
        self.select_requester_btn.setMaximumWidth(60)
        self.select_requester_btn.clicked.connect(self.select_requester)
        
        # 创建需求人布局，包含输入框和按钮
        self.requester_layout = QHBoxLayout()
        self.requester_layout.addWidget(self.requester_field)
        self.requester_layout.addWidget(self.select_requester_btn)
        
        # 添加备注字段
        self.remarks_field = QLineEdit()
        self.remarks_field.setPlaceholderText("请输入备注信息")
        # 添加字段到布局
        basic_layout.addRow("工单 ID:", self.id_field)
        basic_layout.addRow("产线/部门:", self.department_field)
        basic_layout.addRow("型号:", self.model_field)
        basic_layout.addRow("名称:", self.name_field)
        basic_layout.addRow("发起人:", self.creator_field)
        basic_layout.addRow("需求人:", self.requester_layout)
        basic_layout.addRow("项目类型:", self.project_type_field)
        basic_layout.addRow("项目内容:", self.project_content_field)
        basic_layout.addRow("备注:", self.remarks_field)
        # 将基本信息分组添加到表单布局
        form_layout.addWidget(basic_group)
        # 提示信息
        info_label = QLabel("💡 提示：所有字段均为必填项，请仔细填写后点击确定创建工单")
        info_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #cccccc;
                background-color: #3c3c3c;
                padding: 10px;
                border-radius: 4px;
                border-left: 4px solid #0078d4;
            }
        """)
        form_layout.addWidget(info_label)
        # 将表单部件添加到主布局
        main_layout.addWidget(form_widget)
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("type", "cancel")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        main_layout.addLayout(button_layout)
        # 加载项目类型数据
        self.load_project_types()
        # 绑定项目类型变化事件
        self.project_type_field.currentIndexChanged.connect(self.on_project_type_changed)
        
    def accept(self):
        # 重写accept方法，在用户点击确定按钮时先进行表单验证
        if self.validate_form():
            super().accept()
        else:
            # 验证失败，不关闭对话框
            pass
    
    def load_project_types(self):
        # 从数据库获取项目类型
        project_types = db_manager.get_project_types()
        self.project_type_field.clear()
        self.project_type_field.addItem("请选择项目类型", None)
        for pt in project_types:
            self.project_type_field.addItem(pt['name'], pt['id'])
            
    def on_project_type_changed(self):
        # 项目类型变化时加载对应的项目内容
        type_id = self.project_type_field.currentData()
        self.project_content_field.clear()
        self.project_content_field.addItem("请选择项目内容", None)
        if type_id:
            project_contents = db_manager.get_project_contents_by_type(type_id)
            for pc in project_contents:
                self.project_content_field.addItem(pc['name'], pc['id'])
                
    def validate_form(self):
        # 验证工单ID格式 (yyMMddHHmm)
        id_text = self.id_field.text().strip()
        if not id_text:
            QMessageBox.warning(self, "验证失败", "工单ID不能为空")
            return False
        if not re.match(r'^\d{10}$', id_text):
            QMessageBox.warning(self, "验证失败", "工单ID格式不正确，应为10位数字(yyMMddHHmm)")
            return False

        # 验证部门选择
        if self.department_field.currentIndex() < 0:
            QMessageBox.warning(self, "验证失败", "请选择产线/部门")
            return False

        # 验证型号
        model_text = self.model_field.text().strip()
        if not model_text:
            QMessageBox.warning(self, "验证失败", "请输入产品型号")
            return False
        model_error = get_invalid_path_name_message("产品型号", model_text)
        if model_error:
            QMessageBox.warning(self, "验证失败", model_error)
            return False

        # 验证名称
        name_text = self.name_field.text().strip()
        if not name_text:
            QMessageBox.warning(self, "验证失败", "请输入产品名称")
            return False
        name_error = get_invalid_path_name_message("产品名称", name_text)
        if name_error:
            QMessageBox.warning(self, "验证失败", name_error)
            return False

        # 验证发起人
        if not self.creator_field.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入发起人")
            return False

        # 验证需求人
        if not self.requester_field.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入需求人")
            return False

        # 验证项目类型
        if self.project_type_field.currentIndex() <= 0:
            QMessageBox.warning(self, "验证失败", "请选择项目类型")
            return False

        # 验证项目内容
        if self.project_content_field.currentIndex() <= 0:
            QMessageBox.warning(self, "验证失败", "请选择项目内容")
            return False

        return True

    def get_data(self):
        return {
            "id": self.id_field.text().strip(),
            "department": self.department_field.currentText(),
            "model": self.model_field.text().strip(),
            "name": self.name_field.text().strip(),
            "creator": self.creator_field.text().strip(),
            "requester": self.requester_field.text().strip(),
            "project_type_id": self.project_type_field.currentData(),
            "project_type_name": self.project_type_field.currentText(),
            "project_content_id": self.project_content_field.currentData(),
            "project_content_name": self.project_content_field.currentText(),
            "remarks": self.remarks_field.text().strip()
        }
    
    def select_requester(self):
        """打开用户选择对话框，让用户选择需求人"""
        # 获取所有用户列表
        users = db_manager.get_users()
        if not users:
            QMessageBox.warning(self, "提示", "没有找到可用的用户")
            return
        
        # 创建用户选择对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("选择需求人")
        dialog.resize(300, 400)
        layout = QVBoxLayout(dialog)
        
        # 添加搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("输入用户名或IP搜索")
        search_layout.addWidget(search_edit)
        layout.addLayout(search_layout)
        
        # 创建用户列表
        user_list = QListWidget()
        
        # 存储原始用户列表用于搜索过滤
        all_users = users.copy()
        
        # 初始化用户列表
        def populate_user_list(filter_text=""):
            user_list.clear()
            for user in all_users:
                user_text = f"{user['name']} ({user['ip']})"
                # 搜索过滤逻辑，不区分大小写
                if not filter_text or \
                   filter_text.lower() in user['name'].lower() or \
                   filter_text.lower() in user['ip'].lower():
                    user_item = QListWidgetItem(user_text)
                    user_item.setData(Qt.UserRole, user['name'])
                    user_list.addItem(user_item)
        
        # 初始填充用户列表
        populate_user_list()
        
        # 连接搜索信号
        search_edit.textChanged.connect(populate_user_list)
        
        layout.addWidget(user_list)
        
        # 创建按钮
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        select_btn = QPushButton("确定")
        select_btn.clicked.connect(dialog.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(select_btn)
        layout.addLayout(button_layout)
        
        # 处理选择结果
        if dialog.exec() == QDialog.Accepted:
            selected_items = user_list.selectedItems()
            if selected_items:
                self.requester_field.setText(selected_items[0].data(Qt.UserRole))
from packaging import version

class MainWindow(QMainWindow):
    def show_error_dialog(self, error_content):
        """
        显示自定义错误弹窗
        :param error_content: 错误内容
        """
        # 创建自定义对话框
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("错误")
        msg_box.setText(f"{error_content}\n\n点击复制按钮内容发送给管理员")
        
        # 添加复制按钮
        copy_button = QPushButton("复制")
        msg_box.addButton(copy_button, QMessageBox.ActionRole)
        
        # 添加确定按钮
        ok_button = QPushButton("确定")
        msg_box.addButton(ok_button, QMessageBox.AcceptRole)
        
        # 连接复制按钮信号
        def on_copy_clicked():
            clipboard = QApplication.clipboard()
            clipboard.setText(f"{error_content}")
            # 可以添加一个短暂的提示
            QMessageBox.information(None, "提示", "内容已复制到剪贴板")
        
        copy_button.clicked.connect(on_copy_clicked)
        
        # 执行对话框
        msg_box.exec()
    
    def __init__(self, role, departments, is_admin=False, parent=None, logout_callback=None, user_name=None):
        # 检查版本
        latest_version_info = db_manager.get_latest_version()
        # 只有当数据库版本大于当前版本时才显示过期提示
        if latest_version_info and latest_version_info.get('version') and version.parse(latest_version_info.get('version')) > version.parse(APP_VERSION):
            # 创建自定义对话框
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("版本过期")
            msg_box.setText(f"当前版本：{APP_VERSION}\n最新版本：{latest_version_info.get('version')}")
            
            # 添加下载按钮
            download_button = QPushButton("下载最新版本")
            msg_box.addButton(download_button, QMessageBox.ActionRole)
            
            # 添加退出按钮
            exit_button = QPushButton("退出")
            msg_box.addButton(exit_button, QMessageBox.RejectRole)
            
            # 连接按钮信号
            def on_download_clicked():
                win_url = latest_version_info.get('win_update_url')
                if win_url:
                    QDesktopServices.openUrl(QUrl(win_url))
                msg_box.close()
            
            download_button.clicked.connect(on_download_clicked)
            exit_button.clicked.connect(sys.exit)
            
            # 显示对话框
            msg_box.exec()
            sys.exit(0)
        super().__init__(parent)
        self.role = role
        self.departments = departments
        self.is_admin = is_admin
        self.logout_callback = logout_callback  # 添加注销回调函数
        self.user_name = user_name  # 新增：用户姓名
        self.work_orders_data = []
        self.ip_address = self.get_ip_address()
        self.admin_verified_logs = False
        self.admin_verified_settings = False
        self.task_manager = TaskManagerDialog(self)  # 添加任务管理器
        self.version_label = QLabel(f"版本：{APP_VERSION}")
        self.version_label.setStyleSheet("font-size: 13px; color: #888;")
        self.setWindowTitle(f"工单管理系统 - {role}")
        self.setGeometry(100, 100, 1400, 800)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.header = self.create_header()
        main_layout.addWidget(self.header)
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        self.dashboard_page = self.create_dashboard_page()
        self.reports_page = self.create_reports_page()
        self.logs_page = self.create_logs_page()
        self.settings_page = self.create_settings_page()
        self.stacked_widget.addWidget(self.dashboard_page)
        self.stacked_widget.addWidget(self.reports_page)
        self.stacked_widget.addWidget(self.logs_page)
        self.stacked_widget.addWidget(self.settings_page)
        self.apply_styles()
        self.showMaximized()
        self.log_action("系统启动", "登录成功")
        self.refresh_work_orders()
        self.update_history_list()
        # 只绑定一次双击信号，防止多次弹窗
        self.table_view.doubleClicked.connect(self.on_work_order_row_double_clicked)
        # 2. 在 __init__ 初始化时检测版本
        self.version_label = QLabel(f"版本：{APP_VERSION}")
        self.version_label.setStyleSheet("font-size: 13px; color: #888;")
    def get_ip_address(self):
        ip = db_manager.get_local_ip()
        return "N/A" if ip == "无法获取IP" else ip
    def create_header(self):
        header_widget = QWidget()
        header_widget.setObjectName("Header")
        header_widget.setMinimumHeight(56)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(4)

        # Logo
        logo_label = QLabel("⚡ 工单系统")
        logo_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #4f8ef7;"
            " letter-spacing: 1px; background: transparent; padding-right: 20px;"
        )

        # 菜单按钮（可切换激活状态）
        menu_items = [
            ("仪表盘", lambda: self.dashboard_page),
            ("报表中心", lambda: self.reports_page),
        ]
        if self.is_admin:
            menu_items.extend([
                ("日志中心", lambda: self.logs_page),
                ("系统设置", lambda: self.settings_page),
            ])

        self._nav_buttons = []
        menu_layout = QHBoxLayout()
        menu_layout.setSpacing(2)

        def make_nav_action(get_page, btn):
            def action():
                self.stacked_widget.setCurrentWidget(get_page())
                for b in self._nav_buttons:
                    b.setChecked(b is btn)
            return action

        for name, get_page in menu_items:
            button = QPushButton(name)
            button.setCheckable(True)
            self._nav_buttons.append(button)
            button.clicked.connect(make_nav_action(get_page, button))
            menu_layout.addWidget(button)

        # 默认激活第一个
        if self._nav_buttons:
            self._nav_buttons[0].setChecked(True)

        # 任务列表按钮（管理员）
        if self.is_admin:
            task_btn = QPushButton("📋 任务")
            task_btn.setStyleSheet(
                "background: transparent; color: #9ba3b0; border: 1px solid #2e3340;"
                " border-radius: 7px; padding: 6px 14px; font-size: 13px;"
            )
            task_btn.clicked.connect(lambda: self.task_manager.show())
            menu_layout.addWidget(task_btn)

        # 分割线
        sep = QLabel()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background-color: #2e3340;")
        sep.setFixedHeight(32)

        # 右侧用户信息
        right_layout = QHBoxLayout()
        right_layout.setSpacing(8)

        if self.user_name:
            name_label = QLabel(self.user_name)
            name_label.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #e8eaed; background: transparent;"
            )
            name_label.setSizePolicy(name_label.sizePolicy().horizontalPolicy(), name_label.sizePolicy().verticalPolicy())
            right_layout.addWidget(name_label)

        role_chip = QLabel(self.role)
        role_chip.setStyleSheet(
            "background: #1e3a5f; color: #4f8ef7; border-radius: 5px;"
            " padding: 3px 10px; font-size: 12px; font-weight: bold;"
        )
        role_chip.setToolTip(self.role)
        right_layout.addWidget(role_chip)

        dept_text = ', '.join(self.departments)
        dept_chip = QLabel(dept_text)
        dept_chip.setStyleSheet(
            "background: #252830; color: #9ba3b0; border-radius: 5px;"
            " padding: 3px 10px; font-size: 12px;"
        )
        dept_chip.setToolTip(dept_text)
        right_layout.addWidget(dept_chip)

        self.version_label.setStyleSheet(
            "font-size: 11px; color: #454a55; background: transparent;"
        )
        right_layout.addWidget(self.version_label)

        # 注销按钮
        logout_btn = QPushButton("注销")
        logout_btn.setStyleSheet(
            "background-color: transparent; color: #ef4444; border: 1px solid #4a1a1a;"
            " border-radius: 7px; padding: 6px 14px; font-size: 13px; font-weight: bold;"
        )
        logout_btn.clicked.connect(self.logout)
        right_layout.addWidget(logout_btn)

        header_layout.addWidget(logo_label)
        header_layout.addLayout(menu_layout, 0)   # 菜单不拉伸
        header_layout.addStretch(1)               # 中间弹性空间
        header_layout.addWidget(sep)
        header_layout.addLayout(right_layout, 0)  # 右侧不拉伸，自然尺寸
        return header_widget
    def verify_admin(self):
        dialog = AdminPasswordDialog(self)
        if dialog.exec() == QDialog.Accepted:
            if dialog.get_password() == ADMIN_PASSWORD:
                return True
        return False
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        # 搜索与筛选区
        filter_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索工单（任意字段）")
        # 移除实时搜索，改为点击搜索按钮才执行
        # self.search_edit.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("搜索:"))
        filter_layout.addWidget(self.search_edit)
        # 添加搜索按钮
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.apply_filters)
        filter_layout.addWidget(search_btn)
        # 产线筛选 - 只显示用户所属部门
        self.dept_filter = QComboBox()
        self.dept_filter.addItem("全部产线")
        self.dept_filter.addItems(self.departments)  # 使用用户所属部门列表
        self.dept_filter.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("产线:"))
        filter_layout.addWidget(self.dept_filter)
        # 状态筛选
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态")
        self.status_filter.addItems(["拍摄中", "拍摄完成", "视频审核中", "审核通过", "重新拍摄", "后期待领取", "后期处理中", "视频后期审核中", "后期审核通过", "后期重新剪辑", "后期已完成", "待上架", "已上架"])
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("状态:"))
        filter_layout.addWidget(self.status_filter)
        
        # 发起人筛选
        self.creator_filter = QComboBox()
        self.creator_filter.addItem("全部发起人")
        # 后续在初始化时或数据加载后会填充发起人列表
        self.creator_filter.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("发起人:"))
        filter_layout.addWidget(self.creator_filter)
        
        # 日期筛选
        self.date_start = QDateEdit()
        self.date_end = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_end.setCalendarPopup(True)
        # 设置日期显示格式为 yyyy-MM-dd
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        # 设置日历部件的最小尺寸
        self.date_start.calendarWidget().setMinimumSize(300, 250)
        self.date_end.calendarWidget().setMinimumSize(300, 250)
        today = QDate.currentDate()
        first_day = QDate(today.year(), today.month(), 1)
        self.date_start.setDate(first_day)
        self.date_end.setDate(today)
        self.date_start.dateChanged.connect(self.apply_filters)
        self.date_end.dateChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("起始日期:"))
        filter_layout.addWidget(self.date_start)
        filter_layout.addWidget(QLabel("结束日期:"))
        filter_layout.addWidget(self.date_end)
        # 快捷日期按钮
        btn_this_month = QPushButton("本月")
        btn_31 = QPushButton("近31天")
        btn_year = QPushButton("本年")
        btn_week = QPushButton("本周")
        def set_this_month():
            today = QDate.currentDate()
            first = QDate(today.year(), today.month(), 1)
            self.date_start.setDate(first)
            self.date_end.setDate(today)
        def set_31():
            today = QDate.currentDate()
            self.date_start.setDate(today.addDays(-30))
            self.date_end.setDate(today)
        def set_year():
            today = QDate.currentDate()
            first = QDate(today.year(), 1, 1)
            self.date_start.setDate(first)
            self.date_end.setDate(today)
        def set_week():
            today = QDate.currentDate()
            weekday = today.dayOfWeek()
            monday = today.addDays(1 - weekday)
            self.date_start.setDate(monday)
            self.date_end.setDate(today)
        btn_this_month.clicked.connect(set_this_month)
        btn_31.clicked.connect(set_31)
        btn_year.clicked.connect(set_year)
        btn_week.clicked.connect(set_week)
        for btn in [btn_this_month, btn_31, btn_year, btn_week]:
            btn.setFixedHeight(32)
            btn.clicked.connect(self.apply_filters)
            filter_layout.addWidget(btn)
        layout.addLayout(filter_layout)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        history_group = QGroupBox("实时操作记录")
        history_layout = QVBoxLayout(history_group)
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        splitter.addWidget(history_group)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        self.table_view = QTableView()
        self.model = QStandardItemModel()
        controls_layout = QHBoxLayout()
        # 操作按钮逻辑修正
        # 创建新工单按钮
        if self.role in ["采购", "运营", "销售"]:
            create_button = QPushButton("创建新工单")
            create_button.clicked.connect(self.open_create_work_order_dialog)
            controls_layout.addWidget(create_button)

        # 办理按钮
        if self.role in ["摄影", "美工", "剪辑", "运营", "销售", "视频审核", "视频后期审核"]:
            op_button = QPushButton("办理")
            op_button.clicked.connect(self.handle_process_selected_order)
            controls_layout.addWidget(op_button)

        # 管理员编辑/删除按钮
        if self.is_admin:
            edit_button = QPushButton("编辑")
            edit_button.clicked.connect(self.handle_edit_selected_order)
            controls_layout.addWidget(edit_button)
            
            # 红色区域显示按钮
            red_area_button = QPushButton("创建工单反馈")
            # 设置红色样式
            red_area_button.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
            
            def on_red_area_display():
                # 获取选中的工单
                selected = self.table_view.selectionModel().selectedRows()
                if not selected:
                    QMessageBox.warning(self, "提示", "请先选中要操作的工单")
                    return
                
                row = selected[0].row()
                order_item = self.model.item(row, 0)
                order_data = order_item.data(Qt.UserRole)
                
                # 调用API创建工单反馈
                import sys
                import os
                # 添加根目录到Python路径
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from src.core.api_manager import api_manager
                response = api_manager.create_work_order(order_data)
                
                # 显示操作结果
                if response['success']:
                    QMessageBox.information(self, "成功", response['message'])
                else:
                    self.show_error_dialog(f"失败: {response.get('error', '未知错误')}")
            
            red_area_button.clicked.connect(on_red_area_display)
            controls_layout.addWidget(red_area_button)
            
            # 新增工单按钮（放在编辑按钮旁边）
            add_order_button = QPushButton("新增工单")
            add_order_button.clicked.connect(self.open_create_work_order_dialog)
            controls_layout.addWidget(add_order_button)
            
            delete_button = QPushButton("删除工单")
            def on_delete_order():
                selected = self.table_view.selectionModel().selectedRows()
                if not selected:
                    QMessageBox.warning(self, "提示", "请先选中要删除的工单")
                    return
                row = selected[0].row()
                order_item = self.model.item(row, 0)
                order_data = order_item.data(Qt.UserRole)
                order_id = order_data['id']
                id_ = order_data['id']
                dept = order_data['department']
                model = order_data['model']
                name = order_data['name']
                # 生成所有相关路径
                all_paths = []
                # 摄影上传
                for photographer in ["01阿乐", "02杨钧", "03Peter", "04玉瑞", "05Jessie", "06Candy", "07项项","08Arin"]:
                    path = PHOTOGRAPHY_UPLOAD(photographer, dept, id_, model, name)
                    all_paths.append((path, os.path.exists(path)))
                # 美工/剪辑/运营/销售所有流转路径
                paths = [
                    PHOTOGRAPHY_DIST_IMG(dept, id_, model, name),
                    PHOTOGRAPHY_DIST_VIDEO(dept, id_, model, name),
                    ART_GET_IMG_SRC(dept, id_, model, name),
                    ART_GET_IMG_DEST(dept, id_, model, name),
                    ART_DIST_OPS(dept, id_, model, name),
                    ART_DIST_SALES(dept, id_, model, name),
                    EDIT_GET_VIDEO_SRC(dept, id_, model, name),
                    EDIT_GET_VIDEO_DEST(dept, id_, model, name),
                    EDIT_DIST_OPS(dept, id_, model, name),
                    EDIT_DIST_SALES(dept, id_, model, name),
                    OPS_GET_SRC(dept, id_, model, name),
                    SALES_GET_SRC(dept, id_, model, name)
                ]
                for path in paths:
                    all_paths.append((path, os.path.exists(path)))
                # 构建路径及存在性信息
                rows = []
                for p, exists in all_paths:
                    status_html = f"<span style='color: #4caf50; font-weight: bold;'>存在</span>" if exists else f"<span style='color: #ff4d4f; font-weight: bold;'>不存在</span>"
                    rows.append(f"<tr><td style='padding: 4px; border-bottom: 1px solid #555;'>{p}</td><td style='padding: 4px; border-bottom: 1px solid #555;' width='60' align='center'>{status_html}</td></tr>")
                
                msg = f"<table width='100%' cellspacing='0' cellpadding='0'>{''.join(rows)}</table>"
                
                # 使用自定义对话框显示
                dialog = FileOperationDialog(msg, self)
                if dialog.exec() != QDialog.Accepted:
                    return
                
                # 执行删除操作
                delete_results = []
                for path, exists in all_paths:
                    if exists:
                        try:
                            shutil.rmtree(path, ignore_errors=True)
                            delete_results.append((path, "已删除", "#4caf50"))
                        except Exception as e:
                            delete_results.append((path, f"删除失败: {e}", "#ff4d4f"))
                    else:
                        delete_results.append((path, "不存在", "#ff4d4f"))
                
                # 删除数据库工单
                if db_manager.delete_work_order(order_id):
                    # 构建结果HTML
                    res_rows = []
                    for p, status, color in delete_results:
                        res_rows.append(f"<tr><td style='padding: 4px; border-bottom: 1px solid #555;'>{p}</td><td style='padding: 4px; border-bottom: 1px solid #555;' width='80' align='center'><span style='color: {color}; font-weight: bold;'>{status}</span></td></tr>")
                    
                    result_msg = f"<table width='100%' cellspacing='0' cellpadding='0'>{''.join(res_rows)}</table>"
                    
                    # 显示结果对话框
                    res_dialog = FileOperationDialog(
                        result_msg, 
                        self, 
                        title="删除结果", 
                        header_text=f"工单 {order_id} 及相关文件删除结果：", 
                        footer_text=None, 
                        is_confirmation=False
                    )
                    res_dialog.exec()
                    
                    self.log_action("删除工单", f"ID={order_id}")
                    self.refresh_work_orders()
                else:
                    self.show_error_dialog("失败: 删除工单失败，请重试或联系管理员")
            delete_button.clicked.connect(on_delete_order)
            controls_layout.addWidget(delete_button)
        controls_layout.addStretch()
        refresh_button = QPushButton("刷新工单")
        refresh_button.clicked.connect(self.refresh_work_orders)
        controls_layout.addWidget(refresh_button)
        center_layout.addLayout(controls_layout)
        center_layout.addWidget(self.table_view)
        splitter.addWidget(center_widget)
        stats_group = QGroupBox("工单统计")
        self.stats_layout = QVBoxLayout(stats_group)
        splitter.addWidget(stats_group)
        splitter.setSizes([250, 1150, 200])
        # 初始化发起人下拉框
        self.update_creator_filter()
        
        self.setup_work_orders_table()
        self.update_statistics()
        return page
    def open_create_work_order_dialog(self):
        dialog = CreateWorkOrderDialog(self.role, self.departments, self.user_name, self)
        if dialog.exec():
            data = dialog.get_data()
            # 创建工单时状态直接为"拍摄中"
            data['status'] = "拍摄中"
            if db_manager.add_work_order(data):
                # 调用API创建工单
                api_response = api_manager.create_work_order(data)
                if api_response['success']:
                    logger.info(f"API创建工单成功: {data['id']}")
                else:
                    logger.error(f"API创建工单失败: {data['id']}, 错误: {api_response['error']}")
                
                QMessageBox.information(self, "成功", f"工单 {data['id']} 创建成功。")
                self.log_action("新建工单", f"ID={data['id']}, 名称={data['name']}, 产线={data['department']}, 型号={data['model']}, 发起人={data['creator']}")
                self.refresh_work_orders()
            else:
                QMessageBox.critical(self, "数据库错误", "创建工单失败，请检查ID是否唯一或联系管理员。")
    def log_action(self, action_type, details):
        db_manager.add_log(self.role, action_type, details, self.ip_address, self.user_name)
        self.update_history_list()
    def create_reports_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel("报表中心正在紧锣密鼓开发中...")
        label.setFont(QFont("Arial", 24))
        layout.addWidget(label)
        return page
    def create_logs_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        # 筛选栏
        filter_group = QGroupBox("日志筛选")
        filter_layout = QGridLayout()
        filter_layout.setSpacing(10)

        # 角色
        self.role_filter = QComboBox()
        self.role_filter.addItem("全部角色")
        self.role_filter.addItems(db_manager.get_roles())
        filter_layout.addWidget(QLabel("角色:"), 0, 0)
        filter_layout.addWidget(self.role_filter, 0, 1)

        # 姓名
        self.name_filter = QComboBox()
        self.name_filter.setEditable(True)
        self.name_filter.addItem("全部姓名")
        self.name_filter.addItems(db_manager.get_user_names())
        filter_layout.addWidget(QLabel("姓名:"), 0, 2)
        filter_layout.addWidget(self.name_filter, 0, 3)

        # 操作类型
        self.action_type_filter = QComboBox()
        self.action_type_filter.addItem("全部类型")
        self.action_type_filter.addItems(db_manager.get_action_types())
        filter_layout.addWidget(QLabel("操作类型:"), 0, 4)
        filter_layout.addWidget(self.action_type_filter, 0, 5)

        # IP
        self.ip_filter = QLineEdit()
        self.ip_filter.setPlaceholderText("全部IP")
        filter_layout.addWidget(QLabel("IP地址:"), 0, 6)
        filter_layout.addWidget(self.ip_filter, 0, 7)

        # 时间范围
        self.start_date_filter = QDateEdit()
        self.start_date_filter.setCalendarPopup(True)
        self.start_date_filter.setDisplayFormat("yyyy-MM-dd")
        self.end_date_filter = QDateEdit()
        self.end_date_filter.setCalendarPopup(True)
        self.end_date_filter.setDisplayFormat("yyyy-MM-dd")
        
        # 设置日历部件的最小尺寸
        self.start_date_filter.calendarWidget().setMinimumSize(300, 250)
        self.end_date_filter.calendarWidget().setMinimumSize(300, 250)
        
        today = QDate.currentDate()
        self.start_date_filter.setDate(today.addMonths(-1))
        self.end_date_filter.setDate(today)
        
        filter_layout.addWidget(QLabel("起始日期:"), 1, 0)
        filter_layout.addWidget(self.start_date_filter, 1, 1)
        filter_layout.addWidget(QLabel("结束日期:"), 1, 2)
        filter_layout.addWidget(self.end_date_filter, 1, 3)

        # 筛选按钮
        filter_btn = QPushButton("筛选")
        filter_btn.clicked.connect(self.setup_logs_table)
        reset_btn = QPushButton("重置")
        
        def reset_filters():
            self.role_filter.setCurrentIndex(0)
            self.name_filter.setCurrentIndex(0)
            self.action_type_filter.setCurrentIndex(0)
            self.ip_filter.clear()
            self.start_date_filter.setDate(today.addMonths(-1))
            self.end_date_filter.setDate(today)
            self.setup_logs_table()
            
        reset_btn.clicked.connect(reset_filters)
        
        filter_layout.addWidget(filter_btn, 1, 6)
        filter_layout.addWidget(reset_btn, 1, 7)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        # 分页控制
        self.logs_page_size = 300
        self.logs_page_index = 0
        page_nav_layout = QHBoxLayout()
        self.prev_page_btn = QPushButton("上一页")
        self.next_page_btn = QPushButton("下一页")
        self.page_info_label = QLabel()
        self.prev_page_btn.clicked.connect(self.on_logs_prev_page)
        self.next_page_btn.clicked.connect(self.on_logs_next_page)
        page_nav_layout.addWidget(self.prev_page_btn)
        page_nav_layout.addWidget(self.page_info_label)
        page_nav_layout.addWidget(self.next_page_btn)
        layout.addLayout(page_nav_layout)
        # 日志表格
        self.logs_table = QTableView()
        self.logs_model = QStandardItemModel()
        layout.addWidget(self.logs_table)
        self.setup_logs_table()
        return page

    def setup_logs_table(self):
        self.logs_model.clear()
        self.logs_model.setHorizontalHeaderLabels(['时间', 'IP地址', '角色', '姓名', '操作类型', '详细信息'])
        self.logs_table.setModel(self.logs_model)
        # 获取筛选条件
        role = self.role_filter.currentText()
        if role == "全部角色": role = None
        user_name = self.name_filter.currentText()
        if user_name == "全部姓名": user_name = None
        action_type = self.action_type_filter.currentText()
        if action_type == "全部类型": action_type = None
        ip = self.ip_filter.text().strip() or None
        start_date = self.start_date_filter.date().toString("yyyy-MM-dd")
        end_date = self.end_date_filter.date().toString("yyyy-MM-dd")
        offset = self.logs_page_index * self.logs_page_size
        logs = db_manager.get_logs(
            limit=self.logs_page_size,
            role=role,
            user_name=user_name,
            action_type=action_type,
            ip_address=ip,
            start_time=start_date+" 00:00:00" if start_date else None,
            end_time=end_date+" 23:59:59" if end_date else None,
            offset=offset
        )
        for log in logs:
            items = [
                QStandardItem(log['timestamp'].strftime("%Y-%m-%d %H:%M:%S")),
                QStandardItem(log.get('ip_address', 'N/A')),
                QStandardItem(log['role']),
                QStandardItem(log.get('user_name', '')),
                QStandardItem(log.get('action_type', '')),
                QStandardItem(log.get('details', ''))
            ]
            self.logs_model.appendRow(items)
        self.logs_table.resizeColumnsToContents()
        self.logs_table.setColumnWidth(0, 200)  # 时间
        self.logs_table.setColumnWidth(1, 140)  # IP地址
        self.logs_table.setColumnWidth(2, 100)  # 角色
        self.logs_table.setColumnWidth(3, 120)  # 姓名
        self.logs_table.setColumnWidth(4, 80)   # 操作类型
        self.logs_table.setColumnWidth(5, 400)
        self.logs_table.horizontalHeader().setStretchLastSection(True)
        # 更新分页信息
        self.page_info_label.setText(f"第 {self.logs_page_index+1} 页")
        self.prev_page_btn.setEnabled(self.logs_page_index > 0)
        self.next_page_btn.setEnabled(len(logs) == self.logs_page_size)

    def on_logs_prev_page(self):
        if self.logs_page_index > 0:
            self.logs_page_index -= 1
            self.setup_logs_table()

    def on_logs_next_page(self):
        self.logs_page_index += 1
        self.setup_logs_table()

    def create_settings_page(self):
        page = QWidget()
        outer_layout = QHBoxLayout(page)
        content_widget = QWidget()
        content_widget.setMaximumWidth(1000)
        layout = QVBoxLayout(content_widget)
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        outer_layout.addStretch()
        outer_layout.addWidget(content_widget)
        outer_layout.addStretch()
        roles_tab = QWidget()
        roles_layout = self.create_management_layout("角色", db_manager.get_roles, db_manager.add_role, db_manager.remove_role)
        roles_tab.setLayout(roles_layout)
        depts_tab = QWidget()
        depts_layout = self.create_management_layout("部门", db_manager.get_departments, db_manager.add_department, db_manager.remove_department)
        depts_tab.setLayout(depts_layout)
        # 用户管理Tab
        users_tab = QWidget()
        users_layout = QVBoxLayout(users_tab)
        
        # 添加筛选区域
        filter_group = QGroupBox("用户筛选")
        filter_layout = QGridLayout()
        
        # 筛选输入框
        name_filter = QLineEdit()
        name_filter.setPlaceholderText("输入姓名筛选...")
        ip_filter = QLineEdit()
        ip_filter.setPlaceholderText("输入IP筛选...")
        role_filter = QLineEdit()
        role_filter.setPlaceholderText("输入角色筛选...")
        dept_filter = QLineEdit()
        dept_filter.setPlaceholderText("输入部门筛选...")
        
        # 筛选和重置按钮
        filter_btn = QPushButton("筛选")
        reset_btn = QPushButton("重置")
        
        # 添加到布局
        filter_layout.addWidget(QLabel("姓名:"), 0, 0)
        filter_layout.addWidget(name_filter, 0, 1)
        filter_layout.addWidget(QLabel("IP:"), 0, 2)
        filter_layout.addWidget(ip_filter, 0, 3)
        filter_layout.addWidget(QLabel("角色:"), 1, 0)
        filter_layout.addWidget(role_filter, 1, 1)
        filter_layout.addWidget(QLabel("部门:"), 1, 2)
        filter_layout.addWidget(dept_filter, 1, 3)
        filter_layout.addWidget(filter_btn, 2, 0)
        filter_layout.addWidget(reset_btn, 2, 1)
        
        filter_group.setLayout(filter_layout)
        users_layout.addWidget(filter_group)
        
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels(["ID", "内网IP", "姓名", "角色", "部门"])
        # self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # 注释掉全局拉伸
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setColumnWidth(0, 60)  # ID列窄
        self.users_table.setColumnWidth(1, 180) # IP列宽
        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        for col in range(2, 5):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        # 添加双击事件处理
        self.users_table.cellDoubleClicked.connect(self.on_user_double_clicked)
        users_layout.addWidget(self.users_table)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("新增用户")
        edit_btn = QPushButton("编辑用户")
        del_btn = QPushButton("删除用户")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        users_layout.addLayout(btn_layout)
        
        # 通知配置Tab
        notification_tab = QWidget()
        notification_layout = QVBoxLayout(notification_tab)
        notification_group = QGroupBox("通知接口配置")
        notification_form = QFormLayout()

        # 产线选择器（产线来源于部门表）
        self.notify_line_combo = QComboBox()

        # 通知类型选择器
        self.notify_type_combo = QComboBox()
        self.notify_type_combo.addItem("仅钉钉通知", "dingtalk")
        self.notify_type_combo.addItem("仅企业微信通知", "wechat_work")
        self.notify_type_combo.addItem("钉钉 + 企业微信", "both")

        # 钉钉接口输入框（Webhook + Secret）
        self.dingtalk_webhook_input = QLineEdit()
        self.dingtalk_webhook_input.setPlaceholderText("请输入钉钉机器人 Webhook 地址")
        self.dingtalk_secret_input = QLineEdit()
        self.dingtalk_secret_input.setPlaceholderText("请输入钉钉机器人加签 Secret（可选）")

        # 企业微信接口输入框（Webhook）
        self.wechat_webhook_input = QLineEdit()
        self.wechat_webhook_input.setPlaceholderText("请输入企业微信机器人 Webhook 地址")

        # 将控件放入表单布局，保持设置页排版统一
        notification_form.addRow("产线（部门）：", self.notify_line_combo)
        notification_form.addRow("通知类型：", self.notify_type_combo)
        notification_form.addRow("钉钉 Webhook：", self.dingtalk_webhook_input)
        notification_form.addRow("钉钉 Secret：", self.dingtalk_secret_input)
        notification_form.addRow("企业微信 Webhook：", self.wechat_webhook_input)
        notification_group.setLayout(notification_form)
        notification_layout.addWidget(notification_group)

        # 保存按钮区域
        notification_btn_layout = QHBoxLayout()
        save_notification_btn = QPushButton("保存通知配置")
        notification_btn_layout.addWidget(save_notification_btn)
        notification_btn_layout.addStretch()
        notification_layout.addLayout(notification_btn_layout)
        notification_layout.addStretch()

        tab_widget.addTab(roles_tab, "角色管理")
        tab_widget.addTab(depts_tab, "部门管理")
        tab_widget.addTab(users_tab, "用户管理")
        tab_widget.addTab(notification_tab, "通知配置")

        # ── 功能设置 Tab ──
        features_tab = QWidget()
        features_layout = QVBoxLayout(features_tab)
        features_layout.setContentsMargins(20, 20, 20, 20)
        features_layout.setSpacing(16)

        workflow_group = QGroupBox("工单流程功能")
        workflow_group_layout = QVBoxLayout(workflow_group)
        workflow_group_layout.setSpacing(12)

        # 读取当前开关状态
        _vr_enabled = db_manager.get_system_setting('video_review_enabled', default='1') == '1'
        self.video_review_checkbox = QCheckBox("启用视频审核功能")
        self.video_review_checkbox.setChecked(_vr_enabled)
        self.video_review_checkbox.setStyleSheet("font-size: 14px; color: #e8eaed;")

        vr_desc = QLabel(
            "开启时：摄影师上传素材后，工单状态变为【视频审核中】，需视频审核员审核后方可分发。\n"
            "关闭时：摄影师上传素材后，工单状态直接变为【审核通过】，跳过视频审核环节；\n"
            "        视频审核角色点击'办理'时将提示功能已关闭。"
        )
        vr_desc.setStyleSheet("font-size: 12px; color: #9ba3b0; padding-left: 24px;")
        vr_desc.setWordWrap(True)

        # 读取后期视频审核开关状态
        _vpr_enabled = db_manager.get_system_setting('video_post_review_enabled', default='1') == '1'
        self.video_post_review_checkbox = QCheckBox("启用视频后期审核功能")
        self.video_post_review_checkbox.setChecked(_vpr_enabled)
        self.video_post_review_checkbox.setStyleSheet("font-size: 14px; color: #e8eaed;")

        vpr_desc = QLabel(
            "开启时：剪辑师剪辑完视频后，需视频后期审核员审核通过后方可分发。\n"
            "关闭时：剪辑师处理完直接可分发，跳过视频后期审核环节。"
        )
        vpr_desc.setStyleSheet("font-size: 12px; color: #9ba3b0; padding-left: 24px;")
        vpr_desc.setWordWrap(True)

        workflow_group_layout.addWidget(self.video_review_checkbox)
        workflow_group_layout.addWidget(vr_desc)
        workflow_group_layout.addWidget(self.video_post_review_checkbox)
        workflow_group_layout.addWidget(vpr_desc)
        features_layout.addWidget(workflow_group)

        # 保存按钮
        save_features_btn = QPushButton("保存功能设置")
        save_features_btn.setFixedWidth(160)
        features_layout.addWidget(save_features_btn)
        features_layout.addStretch()

        def on_save_features():
            val = '1' if self.video_review_checkbox.isChecked() else '0'
            val_post = '1' if self.video_post_review_checkbox.isChecked() else '0'
            
            success = db_manager.set_system_setting('video_review_enabled', val) and \
                      db_manager.set_system_setting('video_post_review_enabled', val_post)
                      
            if success:
                QMessageBox.information(self, "保存成功", "功能设置已保存并即时生效。")
            else:
                QMessageBox.critical(self, "保存失败", "写入数据库失败，请检查数据库连接。")

        save_features_btn.clicked.connect(on_save_features)
        tab_widget.addTab(features_tab, "功能设置")

        # 保存筛选控件的引用
        self.settings_name_filter = name_filter
        self.settings_ip_filter = ip_filter
        self.settings_role_filter = role_filter
        self.settings_dept_filter = dept_filter
        self.settings_filter_btn = filter_btn
        self.settings_reset_btn = reset_btn
        
        # 连接筛选和重置按钮的信号
        filter_btn.clicked.connect(self.filter_users)
        reset_btn.clicked.connect(self.reset_user_filters)
        
        self.refresh_users_table()
        add_btn.clicked.connect(self.show_add_user_dialog)
        edit_btn.clicked.connect(self.show_edit_user_dialog)
        del_btn.clicked.connect(self.delete_selected_user)
        save_notification_btn.clicked.connect(self.save_notification_settings)
        self.notify_line_combo.currentIndexChanged.connect(self.on_notification_line_changed)
        self.load_notification_settings_to_form()
        return page


    def on_user_double_clicked(self, row, column):
        """处理用户表格双击事件，打开编辑对话框"""
        # 选中双击的行
        self.users_table.selectRow(row)
        # 调用编辑用户对话框
        self.show_edit_user_dialog()
    
    def refresh_users_table(self, name_filter=None, ip_filter=None, role_filter=None, dept_filter=None):
        users = db_manager.get_users(name=name_filter, ip=ip_filter, role=role_filter, department=dept_filter)
        self.users_table.setRowCount(len(users))
        for row, user in enumerate(users):
            self.users_table.setItem(row, 0, QTableWidgetItem(str(user['id'])))
            self.users_table.setItem(row, 1, QTableWidgetItem(user['ip']))
            self.users_table.setItem(row, 2, QTableWidgetItem(user['name']))
            self.users_table.setItem(row, 3, QTableWidgetItem(user['role']))
            self.users_table.setItem(row, 4, QTableWidgetItem(user['department']))
    
    def filter_users(self):
        """根据筛选条件过滤用户列表"""
        name = self.settings_name_filter.text().strip()
        ip = self.settings_ip_filter.text().strip()
        role = self.settings_role_filter.text().strip()
        dept = self.settings_dept_filter.text().strip()
        
        # 如果所有筛选条件都为空，则显示所有用户
        if not name and not ip and not role and not dept:
            self.refresh_users_table()
        else:
            self.refresh_users_table(name_filter=name, ip_filter=ip, role_filter=role, dept_filter=dept)
    
    def reset_user_filters(self):
        """重置所有筛选条件"""
        self.settings_name_filter.clear()
        self.settings_ip_filter.clear()
        self.settings_role_filter.clear()
        self.settings_dept_filter.clear()
        self.refresh_users_table()

    def load_notification_settings_to_form(self):
        """将所有产线通知配置加载到设置表单。"""
        # 刷新运行时配置缓存，确保界面显示数据库最新数据
        apply_notification_settings(load_notification_settings())

        # 产线严格来源于部门表
        line_names = get_department_line_names()

        # 重建产线下拉框
        self.notify_line_combo.blockSignals(True)
        self.notify_line_combo.clear()
        for line_name in line_names:
            self.notify_line_combo.addItem(line_name, line_name)
        self.notify_line_combo.blockSignals(False)

        # 存在部门时默认选中第一条并回填，不存在时提示
        if self.notify_line_combo.count() > 0:
            self.notify_line_combo.setCurrentIndex(0)
            self.on_notification_line_changed()
        else:
            self.dingtalk_webhook_input.clear()
            self.dingtalk_secret_input.clear()
            self.wechat_webhook_input.clear()

    def on_notification_line_changed(self):
        """切换产线时回填该产线的通知配置。"""
        # 获取当前选中的产线
        line_name = self.notify_line_combo.currentData()
        if not line_name:
            return

        # 先取当前产线配置，若不存在则回退到 default 行
        settings = LINE_NOTIFICATION_SETTINGS.get(line_name, LINE_NOTIFICATION_SETTINGS.get("default", {}))

        # 回填通知类型
        notify_type = settings.get("notification_type", NOTIFICATION_TYPE)
        combo_index = self.notify_type_combo.findData(notify_type)
        if combo_index >= 0:
            self.notify_type_combo.setCurrentIndex(combo_index)

        # 回填接口输入框
        self.dingtalk_webhook_input.setText(settings.get("dingtalk_webhook", ""))
        self.dingtalk_secret_input.setText(settings.get("dingtalk_secret", ""))
        self.wechat_webhook_input.setText(settings.get("wechat_work_webhook", ""))

    def save_notification_settings(self):
        """保存当前选中产线的通知接口配置并即时生效。"""
        # 获取当前选中的产线
        line_name = self.notify_line_combo.currentData()
        if not line_name:
            QMessageBox.warning(self, "保存失败", "请先在部门中维护产线，再配置通知接口。")
            return

        # 收集用户输入并进行基础清洗
        settings = {
            "notification_type": self.notify_type_combo.currentData(),
            "dingtalk_webhook": self.dingtalk_webhook_input.text().strip(),
            "dingtalk_secret": self.dingtalk_secret_input.text().strip(),
            "wechat_work_webhook": self.wechat_webhook_input.text().strip()
        }

        # 针对不同通知模式做最小必填校验，避免保存后发送必然失败
        if settings["notification_type"] in ("dingtalk", "both") and not settings["dingtalk_webhook"]:
            QMessageBox.warning(self, "配置不完整", "当前通知类型包含钉钉，请填写钉钉 Webhook。")
            return
        if settings["notification_type"] in ("wechat_work", "both") and not settings["wechat_work_webhook"]:
            QMessageBox.warning(self, "配置不完整", "当前通知类型包含企业微信，请填写企业微信 Webhook。")
            return

        try:
            # 先持久化到数据库，再应用到运行时，确保下次启动也能保持配置
            if not save_notification_settings(line_name, settings):
                QMessageBox.critical(self, "保存失败", "通知配置写入数据库失败，请检查数据库连接。")
                return

            # 保存后刷新全量配置并重新应用，确保发送路由立刻使用最新值
            apply_notification_settings(load_notification_settings())
            QMessageBox.information(self, "保存成功", f"产线【{line_name}】通知配置已保存并即时生效。")
        except Exception as error:
            QMessageBox.critical(self, "保存失败", f"通知配置保存失败：{error}")

    def show_add_user_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("新增用户")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(500)
        
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
            QLineEdit, QListWidget, QLabel {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 12px;
                color: #FFFFFF;
                font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus, QListWidget:focus {
                border-color: #0078d4;
                background-color: #4c4c4c;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #444444;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                border: none;
                background-color: transparent;
            }
            QPushButton {
                background-color: #0078d4;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                min-width: 60px;
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
            QPushButton[type="remove"] {
                background-color: #d83b01;
            }
            QPushButton[type="remove"]:hover {
                background-color: #e13400;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 用户基本信息区域
        info_group = QGroupBox("用户基本信息")
        info_layout = QFormLayout(info_group)
        
        ip_edit = QLineEdit()
        name_edit = QLineEdit()
        
        info_layout.addRow("内网IP:", ip_edit)
        info_layout.addRow("姓名:", name_edit)
        
        main_layout.addWidget(info_group)
        
        # 角色权限区域
        role_group = QGroupBox("角色权限")
        role_layout = QHBoxLayout(role_group)
        
        # 左侧：已有角色
        left_role_layout = QVBoxLayout()
        left_role_layout.addWidget(QLabel("已有角色:"))
        current_roles_list = QListWidget()
        current_roles_list.setMaximumHeight(150)
        left_role_layout.addWidget(current_roles_list)
        
        # 角色移除按钮
        remove_role_btn = QPushButton("移除选中角色")
        remove_role_btn.setProperty("type", "remove")
        def remove_selected_role():
            selected_items = current_roles_list.selectedItems()
            for item in selected_items:
                role_name = item.text()
                current_roles_list.takeItem(current_roles_list.row(item))
                role_exists = False
                for i in range(roles_container_layout.count()):
                    widget = roles_container_layout.itemAt(i).widget()
                    if widget and widget.layout():
                        label = widget.layout().itemAt(0).widget()
                        if label and isinstance(label, QLabel) and label.text() == role_name:
                            role_exists = True
                            break
                if role_exists:
                    continue
                role_row = QHBoxLayout()
                role_label = QLabel(role_name)
                role_label.setStyleSheet("border: none;")
                add_role_btn = QPushButton("添加")
                add_role_btn.setMaximumWidth(60)
                def add_role_func(checked=False, current_role=role_name):
                    existing_roles = [current_roles_list.item(i).text() for i in range(current_roles_list.count())]
                    if current_role in existing_roles:
                        return
                    current_roles_list.addItem(current_role)
                    for j in range(roles_container_layout.count()):
                        available_widget = roles_container_layout.itemAt(j).widget()
                        if available_widget and available_widget.layout():
                            available_label = available_widget.layout().itemAt(0).widget()
                            if available_label and isinstance(available_label, QLabel) and available_label.text() == current_role:
                                available_widget.hide()
                                available_widget.deleteLater()
                                break
                add_role_btn.clicked.connect(add_role_func)
                role_row.addWidget(role_label)
                role_row.addWidget(add_role_btn)
                role_row.addStretch()
                role_widget = QWidget()
                role_widget.setLayout(role_row)
                roles_container_layout.addWidget(role_widget)
        remove_role_btn.clicked.connect(remove_selected_role)
        left_role_layout.addWidget(remove_role_btn)
        
        # 右侧：可添加角色
        right_role_layout = QVBoxLayout()
        right_role_layout.addWidget(QLabel("可添加角色:"))
        
        # 获取所有角色
        all_roles = db_manager.get_roles()
        
        # 创建可添加角色的滚动区域
        scroll_area_roles = QScrollArea()
        scroll_area_roles.setWidgetResizable(True)
        scroll_area_roles.setMaximumHeight(150)
        scroll_area_roles.setStyleSheet("""
            QScrollArea {
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #3c3c3c;
            }
        """)
        
        roles_container = QWidget()
        roles_container_layout = QVBoxLayout(roles_container)
        roles_container_layout.setSpacing(5)
        
        # 为每个可添加角色创建一个带添加按钮的行
        for role in all_roles:
            role_row = QHBoxLayout()
            role_label = QLabel(role)
            role_label.setStyleSheet("border: none;")
            add_role_btn = QPushButton("添加")
            add_role_btn.setMaximumWidth(60)
            
            # 添加角色的函数
            def add_role_func(checked=False, current_role=str(role)):
                existing_roles = [current_roles_list.item(i).text() for i in range(current_roles_list.count())]
                if current_role in existing_roles:
                    return
                current_roles_list.addItem(current_role)
                # 添加后从右侧移除
                for i in range(roles_container_layout.count()):
                    widget = roles_container_layout.itemAt(i).widget()
                    if widget and widget.layout():
                        label = widget.layout().itemAt(0).widget()
                        if label and isinstance(label, QLabel) and label.text() == current_role:
                            widget.hide()
                            widget.deleteLater()
                            break
            
            add_role_btn.clicked.connect(add_role_func)
            role_row.addWidget(role_label)
            role_row.addWidget(add_role_btn)
            role_row.addStretch()
            
            role_widget = QWidget()
            role_widget.setLayout(role_row)
            roles_container_layout.addWidget(role_widget)
        
        scroll_area_roles.setWidget(roles_container)
        right_role_layout.addWidget(scroll_area_roles)
        
        # 添加到角色布局
        role_layout.addLayout(left_role_layout)
        role_layout.addLayout(right_role_layout)
        
        main_layout.addWidget(role_group)
        
        # 部门权限区域
        dept_group = QGroupBox("部门权限")
        dept_layout = QHBoxLayout(dept_group)
        
        # 左侧：已有部门
        left_dept_layout = QVBoxLayout()
        left_dept_layout.addWidget(QLabel("已有部门:"))
        current_depts_list = QListWidget()
        current_depts_list.setMaximumHeight(150)
        left_dept_layout.addWidget(current_depts_list)
        
        # 部门移除按钮
        remove_dept_btn = QPushButton("移除选中部门")
        remove_dept_btn.setProperty("type", "remove")
        def remove_selected_dept():
            selected_items = current_depts_list.selectedItems()
            for item in selected_items:
                dept_name = item.text()
                current_depts_list.takeItem(current_depts_list.row(item))
                dept_exists = False
                for i in range(depts_container_layout.count()):
                    widget = depts_container_layout.itemAt(i).widget()
                    if widget and widget.layout():
                        label = widget.layout().itemAt(0).widget()
                        if label and isinstance(label, QLabel) and label.text() == dept_name:
                            dept_exists = True
                            break
                if dept_exists:
                    continue
                dept_row = QHBoxLayout()
                dept_label = QLabel(dept_name)
                dept_label.setStyleSheet("border: none;")
                add_dept_btn = QPushButton("添加")
                add_dept_btn.setMaximumWidth(60)
                def add_dept_func(checked=False, current_dept=dept_name):
                    existing_depts = [current_depts_list.item(i).text() for i in range(current_depts_list.count())]
                    if current_dept in existing_depts:
                        return
                    current_depts_list.addItem(current_dept)
                    for j in range(depts_container_layout.count()):
                        available_widget = depts_container_layout.itemAt(j).widget()
                        if available_widget and available_widget.layout():
                            available_label = available_widget.layout().itemAt(0).widget()
                            if available_label and isinstance(available_label, QLabel) and available_label.text() == current_dept:
                                available_widget.hide()
                                available_widget.deleteLater()
                                break
                add_dept_btn.clicked.connect(add_dept_func)
                dept_row.addWidget(dept_label)
                dept_row.addWidget(add_dept_btn)
                dept_row.addStretch()
                dept_widget = QWidget()
                dept_widget.setLayout(dept_row)
                depts_container_layout.addWidget(dept_widget)
        remove_dept_btn.clicked.connect(remove_selected_dept)
        left_dept_layout.addWidget(remove_dept_btn)
        
        # 右侧：可添加部门
        right_dept_layout = QVBoxLayout()
        right_dept_layout.addWidget(QLabel("可添加部门:"))
        
        # 获取所有部门
        all_depts = db_manager.get_departments()
        
        # 创建可添加部门的滚动区域
        scroll_area_depts = QScrollArea()
        scroll_area_depts.setWidgetResizable(True)
        scroll_area_depts.setMaximumHeight(150)
        scroll_area_depts.setStyleSheet("""
            QScrollArea {
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #3c3c3c;
            }
        """)
        
        depts_container = QWidget()
        depts_container_layout = QVBoxLayout(depts_container)
        depts_container_layout.setSpacing(5)
        
        # 为每个可添加部门创建一个带添加按钮的行
        for dept in all_depts:
            dept_row = QHBoxLayout()
            dept_label = QLabel(dept)
            dept_label.setStyleSheet("border: none;")
            add_dept_btn = QPushButton("添加")
            add_dept_btn.setMaximumWidth(60)
            
            # 添加部门的函数
            def add_dept_func(checked=False, current_dept=str(dept)):
                existing_depts = [current_depts_list.item(i).text() for i in range(current_depts_list.count())]
                if current_dept in existing_depts:
                    return
                current_depts_list.addItem(current_dept)
                # 添加后从右侧移除
                for i in range(depts_container_layout.count()):
                    widget = depts_container_layout.itemAt(i).widget()
                    if widget and widget.layout():
                        label = widget.layout().itemAt(0).widget()
                        if label and isinstance(label, QLabel) and label.text() == current_dept:
                            widget.hide()
                            widget.deleteLater()
                            break
            
            add_dept_btn.clicked.connect(add_dept_func)
            dept_row.addWidget(dept_label)
            dept_row.addWidget(add_dept_btn)
            dept_row.addStretch()
            
            dept_widget = QWidget()
            dept_widget.setLayout(dept_row)
            depts_container_layout.addWidget(dept_widget)
        
        scroll_area_depts.setWidget(depts_container)
        right_dept_layout.addWidget(scroll_area_depts)
        
        # 添加到部门布局
        dept_layout.addLayout(left_dept_layout)
        dept_layout.addLayout(right_dept_layout)
        
        main_layout.addWidget(dept_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("type", "cancel")
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(btn_layout)
        
        # 按钮事件
        def save_user():
            ip = ip_edit.text().strip()
            name = name_edit.text().strip()
            roles = [current_roles_list.item(i).text() for i in range(current_roles_list.count())]
            depts = [current_depts_list.item(i).text() for i in range(current_depts_list.count())]
            
            if ip and name and roles and depts:
                db_manager.add_user(ip, name, ','.join(roles), ','.join(depts))
                self.refresh_users_table()
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "提示", "所有字段均为必填项且角色/部门至少选一个！")
        
        save_btn.clicked.connect(save_user)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec_()

    def show_edit_user_dialog(self):
        selected = self.users_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "提示", "请先选择要编辑的用户！")
            return
        user_id = int(self.users_table.item(selected, 0).text())
        ip = self.users_table.item(selected, 1).text()
        name = self.users_table.item(selected, 2).text()
        roles = self.users_table.item(selected, 3).text().split(',')
        depts = self.users_table.item(selected, 4).text().split(',')
        
        # 过滤掉空字符串
        roles = [role for role in roles if role.strip()]
        depts = [dept for dept in depts if dept.strip()]
        
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑用户")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(500)
        
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
            QLineEdit, QListWidget, QLabel {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 12px;
                color: #FFFFFF;
                font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus, QListWidget:focus {
                border-color: #0078d4;
                background-color: #4c4c4c;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #444444;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                border: none;
                background-color: transparent;
            }
            QPushButton {
                background-color: #0078d4;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                min-width: 60px;
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
            QPushButton[type="remove"] {
                background-color: #d83b01;
            }
            QPushButton[type="remove"]:hover {
                background-color: #e13400;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 用户基本信息区域
        info_group = QGroupBox("用户基本信息")
        info_layout = QFormLayout(info_group)
        
        ip_edit = QLineEdit(ip)
        name_edit = QLineEdit(name)
        
        info_layout.addRow("内网IP:", ip_edit)
        info_layout.addRow("姓名:", name_edit)
        
        main_layout.addWidget(info_group)
        
        # 角色权限区域
        role_group = QGroupBox("角色权限")
        role_layout = QHBoxLayout(role_group)
        
        # 左侧：已有角色
        left_role_layout = QVBoxLayout()
        left_role_layout.addWidget(QLabel("已有角色:"))
        current_roles_list = QListWidget()
        current_roles_list.setMaximumHeight(150)
        for role in roles:
            current_roles_list.addItem(role)
        left_role_layout.addWidget(current_roles_list)
        
        # 角色移除按钮
        remove_role_btn = QPushButton("移除选中角色")
        remove_role_btn.setProperty("type", "remove")
        def remove_selected_role():
            selected_items = current_roles_list.selectedItems()
            for item in selected_items:
                role_name = item.text()
                current_roles_list.takeItem(current_roles_list.row(item))
                role_exists = False
                for i in range(roles_container_layout.count()):
                    widget = roles_container_layout.itemAt(i).widget()
                    if widget and widget.layout():
                        label = widget.layout().itemAt(0).widget()
                        if label and isinstance(label, QLabel) and label.text() == role_name:
                            role_exists = True
                            break
                if role_exists:
                    continue
                role_row = QHBoxLayout()
                role_label = QLabel(role_name)
                role_label.setStyleSheet("border: none;")
                add_role_btn = QPushButton("添加")
                add_role_btn.setMaximumWidth(60)
                def add_role_func(checked=False, current_role=role_name):
                    existing_roles = [current_roles_list.item(i).text() for i in range(current_roles_list.count())]
                    if current_role in existing_roles:
                        return
                    current_roles_list.addItem(current_role)
                    for j in range(roles_container_layout.count()):
                        available_widget = roles_container_layout.itemAt(j).widget()
                        if available_widget and available_widget.layout():
                            available_label = available_widget.layout().itemAt(0).widget()
                            if available_label and isinstance(available_label, QLabel) and available_label.text() == current_role:
                                available_widget.hide()
                                available_widget.deleteLater()
                                break
                add_role_btn.clicked.connect(add_role_func)
                role_row.addWidget(role_label)
                role_row.addWidget(add_role_btn)
                role_row.addStretch()
                role_widget = QWidget()
                role_widget.setLayout(role_row)
                roles_container_layout.addWidget(role_widget)
        remove_role_btn.clicked.connect(remove_selected_role)
        left_role_layout.addWidget(remove_role_btn)
        
        # 右侧：可添加角色
        right_role_layout = QVBoxLayout()
        right_role_layout.addWidget(QLabel("可添加角色:"))
        
        # 获取所有角色并过滤掉已有的
        all_roles = db_manager.get_roles()
        available_roles = [role for role in all_roles if role not in roles]
        
        # 创建可添加角色的滚动区域
        scroll_area_roles = QScrollArea()
        scroll_area_roles.setWidgetResizable(True)
        scroll_area_roles.setMaximumHeight(150)
        scroll_area_roles.setStyleSheet("""
            QScrollArea {
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #3c3c3c;
            }
        """)
        
        roles_container = QWidget()
        roles_container_layout = QVBoxLayout(roles_container)
        roles_container_layout.setSpacing(5)
        
        # 为每个可添加角色创建一个带添加按钮的行
        for role in available_roles:
            role_row = QHBoxLayout()
            role_label = QLabel(role)
            role_label.setStyleSheet("border: none;")
            add_role_btn = QPushButton("添加")
            add_role_btn.setMaximumWidth(60)
            
            # 添加角色的函数
            def add_role_func(checked=False, current_role=str(role)):
                existing_roles = [current_roles_list.item(i).text() for i in range(current_roles_list.count())]
                if current_role in existing_roles:
                    return
                current_roles_list.addItem(current_role)
                # 添加后从右侧移除
                for i in range(roles_container_layout.count()):
                    widget = roles_container_layout.itemAt(i).widget()
                    if widget and widget.layout():
                        label = widget.layout().itemAt(0).widget()
                        if label and isinstance(label, QLabel) and label.text() == current_role:
                            widget.hide()
                            widget.deleteLater()
                            break
            
            add_role_btn.clicked.connect(add_role_func)
            role_row.addWidget(role_label)
            role_row.addWidget(add_role_btn)
            role_row.addStretch()
            
            role_widget = QWidget()
            role_widget.setLayout(role_row)
            roles_container_layout.addWidget(role_widget)
        
        scroll_area_roles.setWidget(roles_container)
        right_role_layout.addWidget(scroll_area_roles)
        
        # 添加到角色布局
        role_layout.addLayout(left_role_layout)
        role_layout.addLayout(right_role_layout)
        
        main_layout.addWidget(role_group)
        
        # 部门权限区域
        dept_group = QGroupBox("部门权限")
        dept_layout = QHBoxLayout(dept_group)
        
        # 左侧：已有部门
        left_dept_layout = QVBoxLayout()
        left_dept_layout.addWidget(QLabel("已有部门:"))
        current_depts_list = QListWidget()
        current_depts_list.setMaximumHeight(150)
        for dept in depts:
            current_depts_list.addItem(dept)
        left_dept_layout.addWidget(current_depts_list)
        
        # 部门移除按钮
        remove_dept_btn = QPushButton("移除选中部门")
        remove_dept_btn.setProperty("type", "remove")
        def remove_selected_dept():
            selected_items = current_depts_list.selectedItems()
            for item in selected_items:
                dept_name = item.text()
                current_depts_list.takeItem(current_depts_list.row(item))
                dept_exists = False
                for i in range(depts_container_layout.count()):
                    widget = depts_container_layout.itemAt(i).widget()
                    if widget and widget.layout():
                        label = widget.layout().itemAt(0).widget()
                        if label and isinstance(label, QLabel) and label.text() == dept_name:
                            dept_exists = True
                            break
                if dept_exists:
                    continue
                dept_row = QHBoxLayout()
                dept_label = QLabel(dept_name)
                dept_label.setStyleSheet("border: none;")
                add_dept_btn = QPushButton("添加")
                add_dept_btn.setMaximumWidth(60)
                def add_dept_func(checked=False, d=dept_name):
                    current_depts_list.addItem(d)
                    for j in range(depts_container_layout.count()):
                        available_widget = depts_container_layout.itemAt(j).widget()
                        if available_widget and available_widget.layout():
                            available_label = available_widget.layout().itemAt(0).widget()
                            if available_label and isinstance(available_label, QLabel) and available_label.text() == d:
                                available_widget.hide()
                                available_widget.deleteLater()
                                break
                add_dept_btn.clicked.connect(add_dept_func)
                dept_row.addWidget(dept_label)
                dept_row.addWidget(add_dept_btn)
                dept_row.addStretch()
                dept_widget = QWidget()
                dept_widget.setLayout(dept_row)
                depts_container_layout.addWidget(dept_widget)
        remove_dept_btn.clicked.connect(remove_selected_dept)
        left_dept_layout.addWidget(remove_dept_btn)
        
        # 右侧：可添加部门
        right_dept_layout = QVBoxLayout()
        right_dept_layout.addWidget(QLabel("可添加部门:"))
        
        # 获取所有部门并过滤掉已有的
        all_depts = db_manager.get_departments()
        available_depts = [dept for dept in all_depts if dept not in depts]
        
        # 创建可添加部门的滚动区域
        scroll_area_depts = QScrollArea()
        scroll_area_depts.setWidgetResizable(True)
        scroll_area_depts.setMaximumHeight(150)
        scroll_area_depts.setStyleSheet("""
            QScrollArea {
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #3c3c3c;
            }
        """)
        
        depts_container = QWidget()
        depts_container_layout = QVBoxLayout(depts_container)
        depts_container_layout.setSpacing(5)
        
        # 为每个可添加部门创建一个带添加按钮的行
        for dept in available_depts:
            dept_row = QHBoxLayout()
            dept_label = QLabel(dept)
            dept_label.setStyleSheet("border: none;")
            add_dept_btn = QPushButton("添加")
            add_dept_btn.setMaximumWidth(60)
            
            # 添加部门的函数
            def add_dept_func(checked=False, d=dept):
                current_depts_list.addItem(d)
                # 添加后从右侧移除
                for i in range(depts_container_layout.count()):
                    widget = depts_container_layout.itemAt(i).widget()
                    if widget and widget.layout():
                        label = widget.layout().itemAt(0).widget()
                        if label and isinstance(label, QLabel) and label.text() == d:
                            widget.hide()
                            widget.deleteLater()
                            break
            
            add_dept_btn.clicked.connect(add_dept_func)
            dept_row.addWidget(dept_label)
            dept_row.addWidget(add_dept_btn)
            dept_row.addStretch()
            
            dept_widget = QWidget()
            dept_widget.setLayout(dept_row)
            depts_container_layout.addWidget(dept_widget)
        
        scroll_area_depts.setWidget(depts_container)
        right_dept_layout.addWidget(scroll_area_depts)
        
        # 添加到部门布局
        dept_layout.addLayout(left_dept_layout)
        dept_layout.addLayout(right_dept_layout)
        
        main_layout.addWidget(dept_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("type", "cancel")
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(btn_layout)
        
        # 按钮事件
        def save_user():
            new_ip = ip_edit.text().strip()
            new_name = name_edit.text().strip()
            new_roles = [current_roles_list.item(i).text() for i in range(current_roles_list.count())]
            new_depts = [current_depts_list.item(i).text() for i in range(current_depts_list.count())]
            
            if new_ip and new_name and new_roles and new_depts:
                db_manager.update_user(user_id, new_ip, new_name, ','.join(new_roles), ','.join(new_depts))
                self.refresh_users_table()
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "提示", "所有字段均为必填项且角色/部门至少选一个！")
        
        save_btn.clicked.connect(save_user)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec_()

    def delete_selected_user(self):
        selected = self.users_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "提示", "请先选择要删除的用户！")
            return
        user_id = int(self.users_table.item(selected, 0).text())
        reply = QMessageBox.question(self, "确认删除", "确定要删除该用户吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            db_manager.delete_user(user_id)
            self.refresh_users_table()
    def create_management_layout(self, title, get_func, add_func, remove_func):
        layout = QHBoxLayout()
        list_widget = QListWidget()
        list_widget.addItems(get_func())
        controls_layout = QVBoxLayout()
        input_field = QLineEdit()
        input_field.setPlaceholderText(f"输入新的{title}...")
        def add_item():
            new_item = input_field.text().strip()
            if new_item and add_func(new_item):
                list_widget.addItem(new_item)
                input_field.clear()
            else:
                QMessageBox.warning(self, "错误", f"添加{title}失败。可能是重复或无效输入。")
        def remove_item():
            selected = list_widget.currentItem()
            if selected and remove_func(selected.text()):
                list_widget.takeItem(list_widget.row(selected))
            else:
                QMessageBox.warning(self, "错误", f"删除{title}失败。")
        add_button = QPushButton(f"添加{title}")
        add_button.clicked.connect(add_item)
        remove_button = QPushButton(f"删除选中{title}")
        remove_button.clicked.connect(remove_item)
        controls_layout.addWidget(QLabel(f"管理{title}列表:"))
        controls_layout.addWidget(input_field)
        controls_layout.addWidget(add_button)
        controls_layout.addWidget(remove_button)
        controls_layout.addStretch()
        layout.addWidget(list_widget)
        layout.addLayout(controls_layout)
        return layout
    def update_statistics(self):
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        total_orders = len(self.work_orders_data)
        status_counts = {}
        for order in self.work_orders_data:
            status = order.get('status', '未知')
            status_counts[status] = status_counts.get(status, 0) + 1
        self.stats_layout.addWidget(QLabel(f"<b>总工单数:</b> {total_orders}"))
        self.stats_layout.addSpacing(15)
        for status, count in status_counts.items():
            self.stats_layout.addWidget(QLabel(f"<b>状态 '{status}':</b> {count}"))
        self.stats_layout.addStretch()
    def update_history_list(self):
        self.history_list.clear()
        logs = db_manager.get_logs(limit=100)
        for log in logs:
            timestamp = log['timestamp'].strftime("%m-%d %H:%M:%S")
            action_type = log.get('action_type', '')
            details = log.get('details', '')
            self.history_list.insertItem(0, f"[{timestamp}] {action_type} - {details}")
    def show_edit_order_dialog(self, order_data):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"编辑工单 - {order_data['id']}")
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
        title_label = QLabel(f"编辑工单 - {order_data['id']}")
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
        dept_combo = QComboBox()
        dept_combo.addItems(self.departments)
        dept_combo.setCurrentText(order_data['department'])
        model_edit = QLineEdit(order_data['model'])
        model_edit.setPlaceholderText("请输入产品型号")
        name_edit = QLineEdit(order_data['name'])
        name_edit.setPlaceholderText("请输入产品名称")
        creator_edit = QLineEdit(order_data['creator'])
        creator_edit.setPlaceholderText("请输入发起人")
        # 添加选择发起人的按钮
        select_creator_btn = QPushButton("选择")
        select_creator_btn.setMaximumWidth(60)
        
        # 创建发起人布局，包含输入框和按钮
        creator_layout = QHBoxLayout()
        creator_layout.addWidget(creator_edit)
        creator_layout.addWidget(select_creator_btn)
        
        # 定义选择发起人函数
        def select_creator():
            """打开用户选择对话框，让用户选择发起人"""
            # 获取所有用户列表
            users = db_manager.get_users()
            if not users:
                QMessageBox.warning(dialog, "提示", "没有找到可用的用户")
                return
            
            # 创建用户选择对话框
            user_dialog = QDialog(dialog)
            user_dialog.setWindowTitle("选择发起人")
            user_dialog.resize(300, 400)
            layout = QVBoxLayout(user_dialog)
            
            # 添加搜索框
            search_layout = QHBoxLayout()
            search_layout.addWidget(QLabel("搜索:"))
            search_edit = QLineEdit()
            search_edit.setPlaceholderText("输入用户名或IP搜索")
            search_layout.addWidget(search_edit)
            layout.addLayout(search_layout)
            
            # 创建用户列表
            user_list = QListWidget()
            
            # 存储原始用户列表用于搜索过滤
            all_users = users.copy()
            
            # 初始化用户列表
            def populate_user_list(filter_text=""):
                user_list.clear()
                for user in all_users:
                    user_text = f"{user['name']} ({user['ip']})"
                    # 搜索过滤逻辑，不区分大小写
                    if not filter_text or \
                       filter_text.lower() in user['name'].lower() or \
                       filter_text.lower() in user['ip'].lower():
                        user_item = QListWidgetItem(user_text)
                        user_item.setData(Qt.UserRole, user['name'])
                        user_list.addItem(user_item)
            
            # 初始填充用户列表
            populate_user_list()
            
            # 连接搜索信号
            search_edit.textChanged.connect(populate_user_list)
            
            layout.addWidget(user_list)
            
            # 创建按钮
            button_layout = QHBoxLayout()
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(user_dialog.reject)
            select_btn = QPushButton("确定")
            select_btn.clicked.connect(user_dialog.accept)
            
            button_layout.addWidget(cancel_btn)
            button_layout.addWidget(select_btn)
            layout.addLayout(button_layout)
            
            # 处理选择结果
            if user_dialog.exec() == QDialog.Accepted:
                selected_items = user_list.selectedItems()
                if selected_items:
                    creator_edit.setText(selected_items[0].data(Qt.UserRole))
        
        # 连接选择按钮信号
        select_creator_btn.clicked.connect(select_creator)
        # 添加字段到布局
        basic_layout.addRow("工单ID:", id_label)
        basic_layout.addRow("产线/部门:", dept_combo)
        basic_layout.addRow("型号:", model_edit)
        basic_layout.addRow("名称:", name_edit)
        basic_layout.addRow("发起人:", creator_layout)
        
        # 添加更多可编辑字段
        # 需求人字段
        requester_edit = QLineEdit(order_data.get('requester', ''))
        requester_edit.setPlaceholderText("请输入需求人")
        
        # 添加选择需求人的按钮
        select_requester_btn = QPushButton("选择")
        select_requester_btn.setMaximumWidth(60)
        
        # 创建需求人布局，包含输入框和按钮
        requester_layout = QHBoxLayout()
        requester_layout.addWidget(requester_edit)
        requester_layout.addWidget(select_requester_btn)
        
        # 定义选择需求人函数
        def select_requester():
            """打开用户选择对话框，让用户选择需求人"""
            # 获取所有用户列表
            users = db_manager.get_users()
            if not users:
                QMessageBox.warning(dialog, "提示", "没有找到可用的用户")
                return
            
            # 创建用户选择对话框
            user_dialog = QDialog(dialog)
            user_dialog.setWindowTitle("选择需求人")
            user_dialog.resize(300, 400)
            layout = QVBoxLayout(user_dialog)
            
            # 添加搜索框
            search_layout = QHBoxLayout()
            search_layout.addWidget(QLabel("搜索:"))
            search_edit = QLineEdit()
            search_edit.setPlaceholderText("输入用户名或IP搜索")
            search_layout.addWidget(search_edit)
            layout.addLayout(search_layout)
            
            # 创建用户列表
            user_list = QListWidget()
            
            # 存储原始用户列表用于搜索过滤
            all_users = users.copy()
            
            # 初始化用户列表
            def populate_user_list(filter_text=""):
                user_list.clear()
                for user in all_users:
                    user_text = f"{user['name']} ({user['ip']})"
                    # 搜索过滤逻辑，不区分大小写
                    if not filter_text or \
                       filter_text.lower() in user['name'].lower() or \
                       filter_text.lower() in user['ip'].lower():
                        user_item = QListWidgetItem(user_text)
                        user_item.setData(Qt.UserRole, user['name'])
                        user_list.addItem(user_item)
            
            # 初始填充用户列表
            populate_user_list()
            
            # 连接搜索信号
            search_edit.textChanged.connect(populate_user_list)
            
            layout.addWidget(user_list)
            
            # 创建按钮
            button_layout = QHBoxLayout()
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(user_dialog.reject)
            select_btn = QPushButton("确定")
            select_btn.clicked.connect(user_dialog.accept)
            
            button_layout.addWidget(cancel_btn)
            button_layout.addWidget(select_btn)
            layout.addLayout(button_layout)
            
            # 处理选择结果
            if user_dialog.exec() == QDialog.Accepted:
                selected_items = user_list.selectedItems()
                if selected_items:
                    requester_edit.setText(selected_items[0].data(Qt.UserRole))
        
        # 连接选择按钮信号
        select_requester_btn.clicked.connect(select_requester)
        
        # 项目类型选择
        project_type_combo = QComboBox()
        project_types = db_manager.get_project_types()
        project_type_combo.addItem("请选择项目类型", None)
        project_type_id = None
        for pt in project_types:
            project_type_combo.addItem(pt['name'], pt['id'])
            if 'project_type_id' in order_data and order_data['project_type_id'] == pt['id']:
                project_type_combo.setCurrentIndex(project_type_combo.count() - 1)
                project_type_id = pt['id']
        
        # 项目内容选择
        project_content_combo = QComboBox()
        project_content_combo.addItem("请选择项目内容", None)
        if project_type_id:
            project_contents = db_manager.get_project_contents_by_type(project_type_id)
            for pc in project_contents:
                project_content_combo.addItem(pc['name'], pc['id'])
                if 'project_content_id' in order_data and order_data['project_content_id'] == pc['id']:
                    project_content_combo.setCurrentIndex(project_content_combo.count() - 1)
        
        # 项目类型变化时更新项目内容
        def on_project_type_changed():
            type_id = project_type_combo.currentData()
            project_content_combo.clear()
            project_content_combo.addItem("请选择项目内容", None)
            if type_id:
                project_contents = db_manager.get_project_contents_by_type(type_id)
                for pc in project_contents:
                    project_content_combo.addItem(pc['name'], pc['id'])
        
        project_type_combo.currentIndexChanged.connect(on_project_type_changed)
        
        # 备注字段
        remarks_edit = QLineEdit(order_data.get('remarks', ''))
        remarks_edit.setPlaceholderText("请输入备注信息")
        
        # 添加新增字段到布局
        basic_layout.addRow("需求人:", requester_layout)
        basic_layout.addRow("项目类型:", project_type_combo)
        basic_layout.addRow("项目内容:", project_content_combo)
        basic_layout.addRow("备注:", remarks_edit)
        form_layout.addWidget(basic_group)
        # 提示信息
        info_label = QLabel("💡 提示：型号、名称、发起人为必填项，修改后点击确定保存更改")
        info_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #cccccc;
                background-color: #3c3c3c;
                padding: 10px;
                border-radius: 4px;
                border-left: 4px solid #f39c12;
            }
        """)
        form_layout.addWidget(info_label)
        main_layout.addWidget(form_widget)
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("type", "cancel")
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn = QPushButton("确定")
        def on_ok():
            new_dept = dept_combo.currentText()
            new_model = model_edit.text().strip()
            new_name = name_edit.text().strip()
            new_creator = creator_edit.text().strip()
            new_requester = requester_edit.text().strip()
            new_project_type = project_type_combo.currentText()
            new_project_content = project_content_combo.currentText()
            new_project_type_id = project_type_combo.currentData()
            new_project_content_id = project_content_combo.currentData()
            new_remarks = remarks_edit.text().strip()
            if not new_model or not new_name or not new_creator:
                QMessageBox.warning(dialog, "错误", "型号、名称、发起人不能为空")
                return
            model_error = get_invalid_path_name_message("型号", new_model)
            if model_error:
                QMessageBox.warning(dialog, "错误", model_error)
                return
            name_error = get_invalid_path_name_message("名称", new_name)
            if name_error:
                QMessageBox.warning(dialog, "错误", name_error)
                return
            old_dept = order_data['department']
            old_model = order_data['model']
            old_name = order_data['name']
            id_ = order_data['id']
            # 生成所有相关路径的原-新映射
            path_pairs = []
            # 摄影上传
            for photographer in ["01阿乐", "02杨钧", "03Peter", "04玉瑞", "05Jessie", "06Candy", "07项项","08Arin"]:
                old_path = PHOTOGRAPHY_UPLOAD(photographer, old_dept, id_, old_model, old_name)
                new_path = PHOTOGRAPHY_UPLOAD(photographer, new_dept, id_, new_model, new_name)
                path_pairs.append((old_path, new_path))
            # 美工/剪辑/运营/销售所有流转路径
            path_templates = [
                PHOTOGRAPHY_DIST_IMG, PHOTOGRAPHY_DIST_VIDEO,
                ART_GET_IMG_SRC, ART_GET_IMG_DEST,
                ART_DIST_OPS, ART_DIST_SALES,
                EDIT_GET_VIDEO_SRC, EDIT_GET_VIDEO_DEST,
                EDIT_DIST_OPS, EDIT_DIST_SALES,
                OPS_GET_SRC, SALES_GET_SRC
            ]
            for tpl in path_templates:
                old_path = tpl(old_dept, id_, old_model, old_name)
                new_path = tpl(new_dept, id_, new_model, new_name)
                path_pairs.append((old_path, new_path))
            # 检查路径状态并构建确认列表（先检测原路径，再检测目标路径）
            path_checks = []
            for old_path, new_path in path_pairs:
                if old_path == new_path:
                    continue
                old_exists = os.path.exists(old_path)
                new_exists = os.path.exists(new_path)
                path_checks.append((old_path, new_path, old_exists, new_exists))
            if not path_checks:
                # 没有需要移动/重命名的路径，直接保存
                if db_manager.update_work_order_full(
                order_data['id'], new_dept, new_model, new_name, new_creator,
                new_project_type, new_project_content, new_project_type_id, new_project_content_id, new_remarks
            ):
                    self.log_action("编辑工单", f"ID={order_data['id']}（无路径变更）")
                    self.refresh_work_orders()
                    dialog.accept()
                else:
                    QMessageBox.critical(dialog, "失败", "更新工单失败")
                return
            # 使用与删除检测一致的表格弹窗确认
            check_rows = []
            check_rows.append("<tr><th style='padding: 4px; border-bottom: 1px solid #555; text-align:left;'>路径</th><th style='padding: 4px; border-bottom: 1px solid #555;' width='80' align='center'>原路径</th><th style='padding: 4px; border-bottom: 1px solid #555;' width='80' align='center'>目标路径</th></tr>")
            for old_path, new_path, old_exists, new_exists in path_checks:
                old_status_html = f"<span style='color: #4caf50; font-weight: bold;'>存在</span>" if old_exists else f"<span style='color: #ff4d4f; font-weight: bold;'>不存在</span>"
                new_status_html = f"<span style='color: #4caf50; font-weight: bold;'>存在</span>" if new_exists else f"<span style='color: #ff4d4f; font-weight: bold;'>不存在</span>"
                display_path = f"{old_path} → {new_path}"
                check_rows.append(f"<tr><td style='padding: 4px; border-bottom: 1px solid #555;'>{display_path}</td><td style='padding: 4px; border-bottom: 1px solid #555;' width='80' align='center'>{old_status_html}</td><td style='padding: 4px; border-bottom: 1px solid #555;' width='80' align='center'>{new_status_html}</td></tr>")
            check_msg = f"<table width='100%' cellspacing='0' cellpadding='0'>{''.join(check_rows)}</table>"
            confirm_dialog = FileOperationDialog(
                check_msg,
                dialog,
                title="确认保存",
                header_text="⚠️ 警告：将要移动/重命名以下路径：",
                footer_text="是否确认执行上述路径变更并保存工单？",
                is_confirmation=True,
                confirm_button_text="确认保存"
            )
            if confirm_dialog.exec() != QDialog.Accepted:
                return
            # 执行移动/重命名
            move_results = []
            for old_path, new_path, old_exists, _ in path_checks:
                if old_exists:
                    try:
                        if os.path.exists(new_path):
                            shutil.rmtree(new_path, ignore_errors=True)
                        os.makedirs(os.path.dirname(new_path), exist_ok=True)
                        shutil.move(old_path, new_path)
                        move_results.append((f"{old_path} → {new_path}", "已移动/重命名", "#4caf50"))
                        self.log_action("工单路径变更", f"{old_path} → {new_path} 已移动/重命名")
                    except Exception as e:
                        move_results.append((f"{old_path} → {new_path}", f"失败（{e}）", "#ff4d4f"))
                        self.log_action("工单路径变更失败", f"{old_path} → {new_path} 失败：{e}")
                else:
                    move_results.append((f"{old_path} → {new_path}", "不存在", "#ff4d4f"))
            # 保存工单信息
            if db_manager.update_work_order_full(
                order_data['id'], new_dept, new_model, new_name, new_creator,
                new_project_type, new_project_content, new_project_type_id, new_project_content_id, new_remarks
            ):
                self.log_action("编辑工单", f"ID={order_data['id']}，产线/型号/名称变更")
                # 使用与删除检测一致的结果展示
                result_rows = []
                for p, status, color in move_results:
                    result_rows.append(f"<tr><td style='padding: 4px; border-bottom: 1px solid #555;'>{p}</td><td style='padding: 4px; border-bottom: 1px solid #555;' width='100' align='center'><span style='color: {color}; font-weight: bold;'>{status}</span></td></tr>")
                result_msg = f"<table width='100%' cellspacing='0' cellpadding='0'>{''.join(result_rows)}</table>"
                # 钉钉推送
                # 生成推送内容
                changes = []
                if old_dept != new_dept:
                    changes.append(f"产线/部门：{old_dept} → {new_dept}")
                if old_model != new_model:
                    changes.append(f"型号：{old_model} → {new_model}")
                if old_name != new_name:
                    changes.append(f"名称：{old_name} → {new_name}")
                change_text = "\n".join(changes) if changes else "无字段变更"
                # 已领取素材的重命名提示
                rename_tips = []
                for old_path, new_path in path_pairs:
                    if old_path != new_path and os.path.exists(new_path):
                        rename_tips.append(f"{old_path} → {new_path}")
                # 新的重命名提示格式
                rename_text = f"{order_data['id']} {new_model} {new_name}"
                push_text = f"工单 {order_data['id']} 信息已修改：\n{change_text}\n\n如已领取素材，请将相关文件夹重命名为：{rename_text}"
                send_notification("工单信息变更通知", push_text)
                result_dialog = FileOperationDialog(
                    result_msg,
                    dialog,
                    title="保存结果",
                    header_text=f"工单 {order_data['id']} 路径操作结果：",
                    footer_text=None,
                    is_confirmation=False
                )
                result_dialog.exec()
                self.refresh_work_orders()
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "失败", "更新工单失败")
        ok_btn.clicked.connect(on_ok)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        main_layout.addLayout(button_layout)
        dialog.exec()
    def show_process_order_dialog(self, order_data):
        """将工单处理对话框路由到 process_dialogs 包中对应的角色模块。"""
        from src.ui.process_dialogs import show_process_order_dialog as _dispatch
        callbacks = {
            'update_status': self.update_work_order_status_and_ui,
            'add_file_task': self.add_file_task,
            'log_action':    self.log_action,
        }
        _dispatch(self, order_data, callbacks)
    def handle_field_button(self, field, order_data):
        if field == "上传素材":
            parent_dialog = self.sender().parent()
            photographer = None
            # 优先查找下拉框
            photographer_combo = parent_dialog.findChild(QComboBox, 'photographer_combo')
            if photographer_combo:
                val = photographer_combo.currentText()
                if val and val.strip():
                    photographer = val.strip()
            # 查找输入框
            if not photographer:
                photographer_edit = parent_dialog.findChild(QLineEdit, 'photographer_edit')
                if photographer_edit:
                    val = photographer_edit.text()
                    if val and val.strip():
                        photographer = val.strip()
            # 兜底：遍历所有QLineEdit和QComboBox
            if not photographer:
                for w in parent_dialog.findChildren(QLineEdit):
                    val = w.text()
                    if val and val.strip():
                        photographer = val.strip()
                        break
            if not photographer:
                for cb in parent_dialog.findChildren(QComboBox):
                    val = cb.currentText()
                    if val and val.strip():
                        photographer = val.strip()
                        break
            if not photographer:
                QMessageBox.warning(self, "提示", "请先选择摄影师")
                return
            files, _ = QFileDialog.getOpenFileNames(self, "选择要上传的素材")
            if not files:
                return
            department = order_data.get('department', '')
            if platform.system() == 'Windows':
                base_dir = r'\\dabadoc\01原始素材\01原始素材'
            else:
                base_dir = '/Volumes/01原始素材/01原始素材'
            target_dir = os.path.join(base_dir, photographer, department, f"{order_data['id']} {order_data['model']} {order_data['name']}")
            os.makedirs(target_dir, exist_ok=True)
            # 使用任务管理器处理文件上传
            task_name = f"上传素材 - 工单{order_data['id']}"
            self.add_file_task(
                name=task_name,
                files=[os.path.basename(f) for f in files],
                src_dir=os.path.dirname(files[0]),
                dest_dir=target_dir,
                op_type="copy"
            )
        else:
            QMessageBox.information(self, "操作", f"点击了按钮：{field}")
    def on_get_material(self, src, dest, order_data, role):
        """领取素材通用方法"""
        if not os.path.exists(src):
            QMessageBox.warning(self, "提示", f"素材文件夹不存在: {src}")
            return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # 使用任务管理器处理文件移动
        task_name = f"{role}领取素材 - 工单{order_data['id']}"
        # 根据角色设置不同的状态更新
        new_status = '后期处理中' if role in ['美工', '剪辑'] else '待上架'
        def update_status():
            self.update_work_order_status_and_ui(order_data['id'], new_status)
            self.log_action(f"{role}领取素材", f"工单ID={order_data['id']}, 角色={role}, 源路径={src}, 目标路径={dest}")
            # 显示完成消息
            msg = QMessageBox(self)
            msg.setWindowTitle("领取完成")
            msg.setText(f"素材已移动到：\n{dest}")
            open_btn = msg.addButton("打开", QMessageBox.ActionRole)
            msg.addButton("确定", QMessageBox.AcceptRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
        self.add_file_task(
            name=task_name,
            files=os.listdir(src),
            src_dir=src,
            dest_dir=dest,
            op_type="move",
            update_status_func=update_status
        )
    def on_distribute_files(self, src, dest, order_data, role, file_filter=None, new_status=None):
        """分发文件通用方法"""
        if not os.path.exists(src):
            QMessageBox.warning(self, "提示", f"源文件夹不存在: {src}")
            return
        os.makedirs(dest, exist_ok=True)
        # 使用任务管理器处理文件复制
        task_name = f"{role}分发文件 - 工单{order_data['id']}"
        def update_status():
            if new_status:
                self.update_work_order_status_and_ui(order_data['id'], new_status)
            self.log_action(f"{role}分发文件", f"工单ID={order_data['id']}, 角色={role}, 源路径={src}, 目标路径={dest}")
            # 显示完成消息
            msg = QMessageBox(self)
            msg.setWindowTitle("分发完成")
            msg.setText(f"成功分发到：\n{dest}")
            open_btn = msg.addButton("打开", QMessageBox.ActionRole)
            msg.addButton("确定", QMessageBox.AcceptRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
        self.add_file_task(
            name=task_name,
            files=os.listdir(src),
            src_dir=src,
            dest_dir=dest,
            file_filter=file_filter,
            op_type="copy",
            update_status_func=update_status
        )
    def handle_edit_selected_order(self):
        index = self.table_view.currentIndex()
        if not index.isValid():
            QMessageBox.warning(self, "提示", "请先选中一个工单")
            return
        item = self.model.item(index.row(), 0)
        if not item:
            QMessageBox.warning(self, "提示", "选中工单无效")
            return
        order_data = item.data(Qt.UserRole)
        self.show_edit_order_dialog(order_data)
    def handle_process_selected_order(self):
        index = self.table_view.currentIndex()
        if not index.isValid():
            QMessageBox.warning(self, "提示", "请先选中一个工单")
            return
        item = self.model.item(index.row(), 0)
        if not item:
            QMessageBox.warning(self, "提示", "选中工单无效")
            return
        order_data = item.data(Qt.UserRole)
        self.show_process_order_dialog(order_data)
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1d23;
                color: #e8eaed;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 14px;
            }
            QGroupBox {
                border: 1px solid #2e3340;
                border-radius: 8px;
                margin-top: 14px;
                font-size: 12px;
                font-weight: bold;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 12px;
            }
            QPushButton {
                background-color: #4f8ef7;
                color: #ffffff;
                border: none;
                padding: 8px 18px;
                border-radius: 7px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #6ba3ff;
            }
            QPushButton:pressed {
                background-color: #3a72d6;
            }
            QPushButton:disabled {
                background-color: #2e3340;
                color: #6b7280;
            }
            QTableView {
                gridline-color: #252830;
                border: none;
                background-color: #1f232b;
                selection-background-color: #1e3a5f;
                selection-color: #ffffff;
                font-size: 13px;
                alternate-background-color: #22262f;
            }
            QTableView::item {
                padding: 10px 8px;
                border-bottom: 1px solid #252830;
            }
            QTableView::item:selected {
                background-color: #1e3a5f;
                color: #ffffff;
            }
            QTableView::item:hover {
                background-color: #262b35;
            }
            QTableView::item:selected:hover {
                background-color: #254d7a;
            }
            QHeaderView::section {
                background-color: #252830;
                color: #9ba3b0;
                padding: 10px 8px;
                border: none;
                border-right: 1px solid #2e3340;
                border-bottom: 1px solid #2e3340;
                font-weight: bold;
                font-size: 12px;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QListWidget {
                background-color: #1f232b;
                border: none;
                font-size: 13px;
                color: #9ba3b0;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
                margin: 2px 4px;
            }
            QListWidget::item:hover {
                background-color: #262b35;
                color: #e8eaed;
            }
            QListWidget::item:selected {
                background-color: #1e3a5f;
                color: #ffffff;
            }
            QLabel {
                color: #e8eaed;
                font-size: 14px;
                background: transparent;
            }
            QLineEdit {
                background-color: #252830;
                border: 1px solid #353840;
                padding: 9px 12px;
                border-radius: 7px;
                color: #e8eaed;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #4f8ef7;
                background-color: #2a2f3d;
            }
            QLineEdit:disabled {
                background-color: #1f232b;
                color: #6b7280;
            }
            QComboBox {
                background-color: #252830;
                border: 1px solid #353840;
                padding: 8px 12px;
                border-radius: 7px;
                color: #e8eaed;
                font-size: 13px;
            }
            QComboBox:focus {
                border-color: #4f8ef7;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #252830;
                border: 1px solid #353840;
                selection-background-color: #1e3a5f;
                color: #e8eaed;
                padding: 4px;
            }
            QDateEdit {
                background-color: #252830;
                border: 1px solid #353840;
                padding: 8px 12px;
                border-radius: 7px;
                color: #e8eaed;
            }
            QTextEdit, QTextBrowser {
                background-color: #1f232b;
                border: 1px solid #2e3340;
                border-radius: 7px;
                color: #e8eaed;
                padding: 8px;
                font-size: 13px;
            }
            QSplitter::handle {
                background-color: #2e3340;
            }
            QSplitter::handle:horizontal {
                width: 1px;
            }
            QSplitter::handle:vertical {
                height: 1px;
            }
            QScrollBar:vertical {
                border: none;
                background: #1a1d23;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #3a3f4d;
                min-height: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4f8ef7;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar:horizontal {
                border: none;
                background: #1a1d23;
                height: 8px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #3a3f4d;
                min-width: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #4f8ef7;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
            }
            QWidget#Header {
                background-color: #13151a;
                border-bottom: 1px solid #252830;
            }
            QWidget#Header QLabel {
                color: #e8eaed;
                font-size: 14px;
                background: transparent;
            }
            QWidget#Header QPushButton {
                background-color: transparent;
                border: none;
                padding: 8px 14px;
                color: #9ba3b0;
                font-size: 14px;
                border-radius: 7px;
                font-weight: normal;
            }
            QWidget#Header QPushButton:hover {
                background-color: #252830;
                color: #e8eaed;
            }
            QWidget#Header QPushButton:checked {
                background-color: #1e3a5f;
                color: #4f8ef7;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #2e3340;
                border-top: none;
                background-color: #1a1d23;
            }
            QTabBar::tab {
                background-color: #1f232b;
                color: #6b7280;
                padding: 10px 24px;
                border: 1px solid #2e3340;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 13px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #1a1d23;
                color: #ffffff;
                border-bottom: 2px solid #4f8ef7;
                font-weight: bold;
            }
            QTabBar::tab:!selected:hover {
                background-color: #252830;
                color: #c8cdd5;
            }
            QCheckBox {
                spacing: 8px;
                color: #c8cdd5;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #454a55;
                background: #1a1d23;
            }
            QCheckBox::indicator:checked {
                background: #4f8ef7;
                border-color: #4f8ef7;
            }
            QProgressBar {
                border: 1px solid #2e3340;
                border-radius: 5px;
                background: #252830;
                text-align: center;
                color: #e8eaed;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f8ef7, stop:1 #7ab4ff);
                border-radius: 4px;
            }
            QDialog {
                background-color: #1f232b;
                border: 1px solid #2e3340;
            }
            QMessageBox {
                background-color: #1f232b;
            }
        """)
    def showMaximized(self):
        super().showMaximized()
        self.centralWidget().findChild(QSplitter).setSizes([250, int(self.width() * 0.6), 200]) 
    def logout(self):
        # 注销，回到角色选择窗口
        self.log_action("注销", "用户注销")
        self.close()
        if self.logout_callback:
            self.logout_callback()  # 调用回调函数显示角色选择窗口
    def apply_filters(self):
        # 获取所有筛选条件
        keyword = self.search_edit.text().strip()
        dept = self.dept_filter.currentText()
        status = self.status_filter.currentText()
        creator = self.creator_filter.currentText()
        date_start = self.date_start.date().toPython()
        date_end = self.date_end.date().toPython()
        # 重新拉取用户部门的工单（不进行额外筛选）
        all_orders = db_manager.get_work_orders(self.departments)
        filtered = []
        for order in all_orders:
            # 日期筛选
            created = order.get('created_at')
            if created:
                if isinstance(created, str):
                    created = datetime.datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                if created.date() < date_start or created.date() > date_end:
                    continue
            # 产线筛选（只筛选用户部门内的产线）
            if dept != "全部产线" and order.get('department') != dept:
                continue
            # 状态筛选
            if status != "全部状态" and order.get('status') != status:
                continue
            # 发起人筛选
            if creator != "全部发起人" and order.get('creator') != creator:
                continue
            # 关键字搜索
            if keyword:
                found = False
                for v in order.values():
                    if keyword.lower() in str(v).lower():
                        found = True
                        break
                if not found:
                    continue
            filtered.append(order)
        # 更新筛选后的数据
        # 若仅日期条件导致结果为空（无关键字/状态/产线/发起人额外筛选），回退显示最新30条
        if (not filtered and not keyword
                and dept == "全部产线"
                and status == "全部状态"
                and creator == "全部发起人"):
            filtered = all_orders[:30]
        self.work_orders_data = filtered
        # 重新设置表格数据
        self.setup_work_orders_table()
        # 更新统计信息
        self.update_statistics()
    def show_task_manager(self):
        """显示任务管理器窗口"""
        self.task_manager.show()
        self.task_manager.raise_()
        self.task_manager.activateWindow()
    def update_work_order_status_and_ui(self, order_id, new_status):
        db_manager.update_work_order_status(order_id, new_status)
        self.refresh_work_orders()

    def add_file_task(self, name, files, src_dir, dest_dir, file_filter=None, op_type="copy", update_status_func=None):
        """添加文件操作任务到任务管理器
        Args:
            name: 任务名称
            files: 文件列表
            src_dir: 源目录
            dest_dir: 目标目录
            file_filter: 文件过滤函数
            op_type: 操作类型，"copy"或"move"
            update_status_func: 更新状态的回调函数
        """
        task = Task(name, files, src_dir, dest_dir, file_filter, op_type, update_status_func)
        self.task_manager.add_task(task)
        self.show_task_manager()
    def refresh_work_orders(self):
        self.log_action("刷新工单", "刷新了工单列表")
        # 重置筛选条件
        self.search_edit.clear()
        self.dept_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        
        # 重新获取所有数据
        self.work_orders_data = db_manager.get_work_orders(self.departments)
        
        # 更新发起人下拉框
        self.update_creator_filter()
        
        self.setup_work_orders_table()
        self.update_statistics()
    
    def update_creator_filter(self):
        """更新发起人筛选下拉框的选项"""
        # 保存当前选中的发起人
        current_creator = self.creator_filter.currentText()
        
        # 清除现有选项（保留"全部发起人"）
        self.creator_filter.clear()
        self.creator_filter.addItem("全部发起人")
        
        # 获取所有发起人，并去重
        creators = set()
        for order in self.work_orders_data:
            creator = order.get('creator')
            if creator:
                creators.add(creator)
        
        # 添加发起人选项
        for creator in sorted(creators):
            self.creator_filter.addItem(creator)
        
        # 尝试恢复之前选中的发起人
        index = self.creator_filter.findText(current_creator)
        if index >= 0:
            self.creator_filter.setCurrentIndex(index)
    def setup_work_orders_table(self):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['ID', '产线', '型号', '名称', '发起人', '需求人', '状态'])
        self.table_view.setModel(self.model)
        # 使用当前筛选后的数据，如果没有则从数据库获取用户所属部门的工单
        if not hasattr(self, 'work_orders_data') or self.work_orders_data is None:
            self.work_orders_data = db_manager.get_work_orders(self.departments)
        for order in self.work_orders_data:
            # 对需求人字段进行特殊处理，None值显示为"没有设置"
            items = []
            for k in ['id', 'department', 'model', 'name', 'creator', 'requester', 'status']:
                value = order.get(k, '')
                # 当字段是requester且值为None或空字符串时，显示"没有设置"
                if k == 'requester' and (value is None or value == ''):
                    items.append(QStandardItem("没有设置"))
                else:
                    items.append(QStandardItem(str(value)))
            items[0].setData(order, Qt.UserRole)
            self.model.appendRow(items)
        self.table_view.setColumnWidth(0, 160)
        self.table_view.setColumnWidth(1, 150)
        self.table_view.setColumnWidth(2, 120)
        self.table_view.setColumnWidth(4, 100)
        self.table_view.setColumnWidth(5, 100)
        self.table_view.setColumnWidth(6, 180)
        self.table_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_view.setEditTriggers(QTableView.NoEditTriggers)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        # 设置状态列自定义委托
        self.table_view.setItemDelegateForColumn(6, StatusProgressDelegate(self.table_view))
        self.expanded_row = None
    def on_work_order_row_double_clicked(self, index):
        row = index.row()
        order_item = self.model.item(row, 0)
        order_data = order_item.data(Qt.UserRole)
        logs = db_manager.get_logs_by_order_id(order_data['id'])
        
        # 使用新的详情窗口
        dialog = WorkOrderDetailDialog(order_data, logs, is_admin=self.is_admin, parent=self)
        dialog.exec()

    def check_path_collected_status(self, order_data, path_type):
        """检查路径是否已被领取
        
        Args:
            order_data: 工单数据
            path_type: 路径类型 ('dist_img', 'dist_video', 'art_dist_ops', 'art_dist_sales', 'edit_dist_ops', 'edit_dist_sales')
        
        Returns:
            dict: 包含领取状态、用户名、时间的信息
        """
        # 根据路径类型确定要查找的操作类型
        action_mapping = {
            'dist_img': '美工领取素材',
            'dist_video': '剪辑领取素材', 
            'art_dist_ops': '运营领取素材',
            'art_dist_sales': '销售领取素材',
            'edit_dist_ops': '运营领取素材',
            'edit_dist_sales': '销售领取素材'
        }
        
        action_type = action_mapping.get(path_type)
        if not action_type:
            return {'collected': False, 'user': '', 'time': ''}
        
        # 查询数据库获取操作记录
        logs = db_manager.get_logs_by_order_id(order_data['id'])
        
        # 检查是否有领取记录
        collected_log = None
        for log in logs:
            if (log.get('action_type') == action_type and 
                f"工单ID={order_data['id']}" in log.get('details', '')):
                collected_log = log
                break
        
        # 对于摄影分发的路径，还需要检查是否有重新分发
        if path_type in ['dist_img', 'dist_video']:
            # 查找摄影分发操作
            distribute_action = '摄影分发图片' if path_type == 'dist_img' else '摄影分发视频'
            distribute_logs = []
            for log in logs:
                if (log.get('action_type') == distribute_action and 
                    f"工单ID={order_data['id']}" in log.get('details', '')):
                    distribute_logs.append(log)
            
            # 如果有领取记录，检查最后一次摄影分发是否在领取之后
            if collected_log and distribute_logs:
                last_distribute = max(distribute_logs, key=lambda x: x.get('timestamp', ''))
                if last_distribute.get('timestamp') > collected_log.get('timestamp'):
                    # 摄影重新分发了新素材，应该显示完整路径
                    return {'collected': False, 'user': '', 'time': ''}
        
        # 如果有领取记录，返回已领取状态
        if collected_log:
            return {
                'collected': True,
                'user': collected_log.get('role', ''),
                'time': collected_log.get('timestamp', '').strftime('%Y-%m-%d %H:%M:%S') if collected_log.get('timestamp') else ''
            }
        
        return {'collected': False, 'user': '', 'time': ''}

    def create_path_status_label(self, path, tooltip_text, order_data, path_type):
        """创建路径状态标签，根据领取状态显示不同内容"""
        # 检查领取状态
        status = self.check_path_collected_status(order_data, path_type)
        
        if status['collected']:
            # 已领取状态
            label_text = f"✅ {status['user']}已领取 ({status['time']})"
            label = QLabel(label_text)
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
            # 未领取状态
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

# 状态进度条委托
class StatusProgressDelegate(QStyledItemDelegate):
    STATUS_ORDER = ["拍摄中", "拍摄完成", "审核通过", "重新拍摄", "后期待领取", "后期处理中", "后期已完成", "待上架", "已上架"]
    def paint(self, painter, option, index):
        status = index.data()
        # 计算进度百分比
        if status in self.STATUS_ORDER:
            start_idx = 0
            if status in ["后期待领取", "后期处理中", "后期已完成", "待上架", "已上架"]:
                start_idx = self.STATUS_ORDER.index("后期待领取")
            total_steps = len(self.STATUS_ORDER) - start_idx
            try:
                current_idx = self.STATUS_ORDER.index(status)
            except ValueError:
                current_idx = 0
            progress = max(0, current_idx - start_idx + 1)
            percent = int(progress / total_steps * 100)
        else:
            percent = 0
        # 进度条区域与单元格一样高
        bar_rect = option.rect
        painter.save()
        radius = bar_rect.height() // 2
        bg_color = option.palette.window()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(bar_rect, radius, radius)
        # 绘制进度条填充
        if percent > 0:
            fill_rect = bar_rect.adjusted(0, 0, int((percent-100)*bar_rect.width()/100), 0)
            fill_color = option.palette.color(QPalette.Highlight)
            painter.setBrush(fill_color)
            painter.drawRoundedRect(fill_rect, radius, radius)
        # 绘制状态文字（居中覆盖在进度条上）
        color_map = {
            "拍摄中": (255, 170, 0),      # 橙色
            "拍摄完成": (0, 200, 255),    # 亮蓝色
            "视频审核中": (245, 158, 11),  # 驼升黄
            "审核通过": (40, 167, 69),     # 绿色
            "重新拍摄": (220, 53, 69),     # 红色
            "后期待领取": (255, 140, 0),  # 深橙色
            "后期处理中": (180, 80, 255), # 紫色
            "视频后期审核中": (245, 158, 11), # 驼升黄
            "后期审核通过": (40, 167, 69),     # 绿色
            "后期重新剪辑": (220, 53, 69),     # 红色
            "后期已完成": (0, 220, 120),  # 绿色
            "待上架": (255, 215, 0),      # 金色
            "已上架": (0, 255, 255)       # 亮青色
        }
        rgb = color_map.get(status, (255,255,255))
        painter.setPen(QColor(*rgb))
        font = painter.font()
        font.setBold(True)
        size = font.pointSize()
        if size <= 0:
            size = 12
        font.setPointSize(size + 1)
        painter.setFont(font)
        painter.drawText(bar_rect, Qt.AlignCenter, status)
        painter.restore()
