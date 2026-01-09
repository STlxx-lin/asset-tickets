import sys
from PySide6.QtWidgets import (QWidget, QPushButton, QLabel, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QRadioButton, QCheckBox, 
                             QGridLayout, QDialog, QLineEdit, QMessageBox)
from database import db_manager
import socket
from PySide6.QtCore import Qt

# 从配置文件导入版本号
from config import APP_VERSION

class CharacterSelection(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("角色选择")
        self.roles = db_manager.get_roles()
        self.departments = db_manager.get_departments()
        self.setGeometry(100, 100, 600, 400)
        self.main_window = None
        self.setup_ui()
        self.apply_styles()

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '无法获取IP'

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        # 自动获取本机IP
        local_ip = self.get_local_ip()
        user_info = None
        for user in db_manager.get_users():
            if user['ip'] == local_ip:
                user_info = user
                break
        if user_info:
            info_text = f"<b>姓名：</b>{user_info['name']}<br>"
            # 角色处理
            roles = [r.strip() for r in user_info['role'].split(',') if r.strip()]
            depts = [d.strip() for d in user_info['department'].split(',') if d.strip()]
            selected_role = roles[0] if roles else ''
            self.selected_role = selected_role
            self.user_departments = depts
            info_text += f"<b>内网IP：</b>{user_info['ip']}<br>"
            info_label = QLabel(info_text)
            info_label.setStyleSheet("font-size: 18px; color: #fff; margin-bottom: 20px;")
            info_label.setTextFormat(Qt.RichText)
            self.main_layout.addWidget(info_label)
            # 角色选择
            if len(roles) > 1:
                role_group = QGroupBox("请选择你的角色")
                role_layout = QHBoxLayout()
                self.role_buttons = []
                for role in roles:
                    btn = QRadioButton(role)
                    if role == selected_role:
                        btn.setChecked(True)
                    self.role_buttons.append(btn)
                    role_layout.addWidget(btn)
                role_group.setLayout(role_layout)
                self.main_layout.addWidget(role_group)
            # 部门显示
            dept_label = QLabel(f"<b>所属部门：</b>{', '.join(depts)}")
            dept_label.setStyleSheet("font-size: 16px; color: #fff; margin-bottom: 10px;")
            dept_label.setTextFormat(Qt.RichText)
            self.main_layout.addWidget(dept_label)
            tip_label = QLabel("请确认以上信息是否正确。\n如有误：\n1. 请确认当前设备内网IP和座位是否正确\n2. 联系管理员")
            tip_label.setStyleSheet("color: #f59e0b; font-size: 14px; margin-bottom: 10px;")
            self.main_layout.addWidget(tip_label)
            # 按钮区
            btn_layout = QHBoxLayout()
            confirm_btn = QPushButton("确认")
            confirm_btn.clicked.connect(lambda: self.enter_main(user_info))
            admin_btn = QPushButton("管理员登录")
            admin_btn.clicked.connect(self.admin_login)
            btn_layout.addStretch()
            btn_layout.addWidget(confirm_btn)
            btn_layout.addWidget(admin_btn)
            self.main_layout.addLayout(btn_layout)
        else:
            info_label = QLabel(f"未找到本机IP（{local_ip}）的用户信息！\n请在公司内网环境下使用。\n如果已在内网，请检查IP和座位是否正确或联系网络管理员。")
            info_label.setStyleSheet("color: #dc2626; font-size: 16px; margin-bottom: 20px;")
            info_label.setWordWrap(True)
            self.main_layout.addWidget(info_label)
            admin_btn = QPushButton("管理员登录")
            admin_btn.clicked.connect(self.admin_login)
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            btn_layout.addWidget(admin_btn)
            self.main_layout.addLayout(btn_layout)
        # 底部显示IP
        ip_label = QLabel(f"本机IP：{local_ip}")
        ip_label.setStyleSheet("color: #888; font-size: 13px;")
        self.main_layout.addWidget(ip_label)
        
        # 底部显示数据库信息
        db_info_label = QLabel(f"数据库名称：{db_manager.config['database']} | 数据库地址：{db_manager.config['host']}")
        db_info_label.setStyleSheet("color: #dc2626; font-size: 13px; font-weight: bold;")  # 红色显示
        self.main_layout.addWidget(db_info_label)
        
        # 底部显示版本号
        version_label = QLabel(f"版本：{APP_VERSION}")
        version_label.setStyleSheet("color: #888; font-size: 13px;")
        self.main_layout.addWidget(version_label)

    def admin_login(self):
        """管理员登录"""
        dialog = QDialog(self)
        dialog.setWindowTitle("管理员登录")
        dialog.setFixedSize(300, 150)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        
        # 密码输入框
        password_label = QLabel("请输入管理员密码：")
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        password_edit.setPlaceholderText("请输入密码")
        
        # 按钮布局
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        
        ok_button.clicked.connect(lambda: self.verify_admin_password(dialog, password_edit.text()))
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addWidget(password_label)
        layout.addWidget(password_edit)
        layout.addLayout(button_layout)
        
        # 设置样式
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2E2E2E;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #444;
                border: 1px solid #555;
                padding: 8px;
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 14px;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777777;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
        """)
        
        dialog.exec()
    
    def verify_admin_password(self, dialog, password):
        """验证管理员密码"""
        from config import ADMIN_PASSWORD
        if password == ADMIN_PASSWORD:  # 管理员密码
            dialog.accept()
            # 以管理员身份进入主窗口
            from ui.main_window import MainWindow
            self.main_window = MainWindow("管理员", self.departments, is_admin=True, logout_callback=self.show)
            self.main_window.show()
            self.hide()  # 隐藏而不是关闭
        else:
            QMessageBox.warning(dialog, "错误", "密码错误！")
        
    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def update_character_widgets(self):
        self.clear_layout(self.main_layout)
        
        roles_group = QGroupBox("选择你的角色")
        self.roles_layout = QGridLayout()
        for i, role in enumerate(self.roles):
            radio_button = QRadioButton(role)
            self.roles_layout.addWidget(radio_button, i // 3, i % 3)
        roles_group.setLayout(self.roles_layout)

        departments_group = QGroupBox("选择你所属的部门 (可多选)")
        self.departments_layout = QGridLayout()
        for i, dept in enumerate(self.departments):
            checkbox = QCheckBox(dept)
            self.departments_layout.addWidget(checkbox, i // 3, i % 3)
        departments_group.setLayout(self.departments_layout)

        buttons_layout = QHBoxLayout()
        submit_button = QPushButton("确定")
        submit_button.clicked.connect(self.submit_selection)
        
        # 管理员按钮
        admin_button = QPushButton("管理员登录")
        admin_button.clicked.connect(self.admin_login)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(submit_button)
        buttons_layout.addWidget(admin_button)
        
        self.main_layout.addWidget(roles_group)
        self.main_layout.addWidget(departments_group)
        self.main_layout.addLayout(buttons_layout)

    def submit_selection(self):
        selected_role = None
        for i in range(self.roles_layout.count()):
            widget = self.roles_layout.itemAt(i).widget()
            if isinstance(widget, QRadioButton) and widget.isChecked():
                selected_role = widget.text()
                break

        selected_departments = []
        for i in range(self.departments_layout.count()):
            widget = self.departments_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                selected_departments.append(widget.text())

        if not selected_role:
            QMessageBox.warning(self, "提示", "请选择一个角色！")
            return
            
        if not selected_departments:
            QMessageBox.warning(self, "提示", "请至少选择一个部门！")
            return
            
        from ui.main_window import MainWindow
        self.main_window = MainWindow(selected_role, selected_departments, logout_callback=self.show)
        self.main_window.show()
        self.hide()  # 隐藏而不是关闭

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E;
                color: #FFFFFF;
                font-size: 14px;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
            }
            QRadioButton, QCheckBox {
                spacing: 10px;
            }
            QRadioButton::indicator, QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #555555;
                border-radius: 9px;
                background-color: #2E2E2E;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #0078d4;
                border-radius: 9px;
                background-color: #0078d4;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #555555;
                border-radius: 3px;
                background-color: #2E2E2E;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #0078d4;
                border-radius: 3px;
                background-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                color: #FFFFFF;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QLineEdit {
                background-color: #444;
                border: 1px solid #555;
                padding: 8px;
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 14px;
            }
            QListWidget {
                background-color: #444;
                border: 1px solid #555;
            }
        """)

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        # 如果主窗口存在，先关闭主窗口
        if self.main_window:
            self.main_window.close()
        # 退出整个应用程序
        from PySide6.QtWidgets import QApplication
        QApplication.quit() 

    def enter_main(self, user_info):
        # 角色选择（如有多个）
        role = user_info['role']
        if hasattr(self, 'role_buttons'):
            for btn in self.role_buttons:
                if btn.isChecked():
                    role = btn.text()
                    break
        from ui.main_window import MainWindow
        # 传递选中角色和所有部门
        self.main_window = MainWindow(role, self.user_departments, is_admin=False, logout_callback=self.show, user_name=user_info['name'])
        self.main_window.show()
        self.hide()