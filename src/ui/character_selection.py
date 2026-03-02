import sys
from PySide6.QtWidgets import (QWidget, QPushButton, QLabel, QVBoxLayout,
                             QHBoxLayout, QGroupBox, QRadioButton, QCheckBox,
                             QGridLayout, QDialog, QLineEdit, QMessageBox, QFrame)
from src.core.database import db_manager
import socket
from PySide6.QtCore import Qt

# 从配置文件导入版本号
from src.core.config import APP_VERSION

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
        # 外层居中布局
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addStretch()

        # 居中容器
        center_h = QHBoxLayout()
        center_h.addStretch()

        # 卡片容器
        card = QWidget()
        card.setObjectName("card")
        card.setMinimumWidth(480)
        card.setMaximumWidth(640)
        self.main_layout = QVBoxLayout(card)
        self.main_layout.setContentsMargins(36, 32, 36, 32)
        self.main_layout.setSpacing(18)

        # 品牌标题
        brand_label = QLabel("工单管理系统")
        brand_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #e8eaed; letter-spacing: 1px;")
        brand_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(brand_label)

        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #353840; background-color: #353840; max-height: 1px; margin: 4px 0;")
        self.main_layout.addWidget(divider)

        # 自动获取本机IP
        local_ip = self.get_local_ip()
        user_info = None
        for user in db_manager.get_users():
            if user['ip'] == local_ip:
                user_info = user
                break

        if user_info:
            roles = [r.strip() for r in user_info['role'].split(',') if r.strip()]
            depts = [d.strip() for d in user_info['department'].split(',') if d.strip()]
            selected_role = roles[0] if roles else ''
            self.selected_role = selected_role
            self.user_departments = depts

            # 用户信息区
            name_label = QLabel(user_info['name'])
            name_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #ffffff;")
            name_label.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(name_label)

            # IP + 部门 行
            meta_layout = QHBoxLayout()
            meta_layout.setSpacing(12)
            ip_chip = QLabel(f"  {user_info['ip']}  ")
            ip_chip.setStyleSheet("background:#2e3340; color:#9ba3b0; border-radius:4px; font-size:12px; padding:3px 0;")
            ip_chip.setAlignment(Qt.AlignCenter)
            dept_chip = QLabel(f"  {', '.join(depts)}  ")
            dept_chip.setStyleSheet("background:#2e3340; color:#9ba3b0; border-radius:4px; font-size:12px; padding:3px 0;")
            dept_chip.setAlignment(Qt.AlignCenter)
            meta_layout.addStretch()
            meta_layout.addWidget(ip_chip)
            meta_layout.addWidget(dept_chip)
            meta_layout.addStretch()
            self.main_layout.addLayout(meta_layout)

            # 角色选择（多角色时显示）
            if len(roles) > 1:
                role_group = QGroupBox("请选择角色")
                role_layout = QHBoxLayout()
                role_layout.setSpacing(16)
                self.role_buttons = []
                for role in roles:
                    btn = QRadioButton(role)
                    if role == selected_role:
                        btn.setChecked(True)
                    self.role_buttons.append(btn)
                    role_layout.addWidget(btn)
                role_group.setLayout(role_layout)
                self.main_layout.addWidget(role_group)

            # 提示
            tip_label = QLabel("请确认以上信息。如有误，请核查内网IP或联系管理员。")
            tip_label.setStyleSheet("color: #f59e0b; font-size: 12px; background:transparent;")
            tip_label.setWordWrap(True)
            tip_label.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(tip_label)

            # 按钮区
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(12)
            confirm_btn = QPushButton("确认进入")
            confirm_btn.setFixedHeight(40)
            confirm_btn.clicked.connect(lambda: self.enter_main(user_info))
            admin_btn = QPushButton("管理员登录")
            admin_btn.setObjectName("secondary")
            admin_btn.setFixedHeight(40)
            admin_btn.clicked.connect(self.admin_login)
            btn_layout.addWidget(confirm_btn)
            btn_layout.addWidget(admin_btn)
            self.main_layout.addLayout(btn_layout)
        else:
            err_icon = QLabel("⚠")
            err_icon.setStyleSheet("font-size: 36px; color: #ef4444; background:transparent;")
            err_icon.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(err_icon)

            info_label = QLabel(f"未识别到本机用户\n\nIP：{local_ip}\n\n请确认设备已连接内网，或联系管理员添加此 IP。")
            info_label.setStyleSheet("color: #ef4444; font-size: 14px; background:transparent; line-height: 1.6;")
            info_label.setWordWrap(True)
            info_label.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(info_label)

            admin_btn = QPushButton("管理员登录")
            admin_btn.setFixedHeight(40)
            admin_btn.clicked.connect(self.admin_login)
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            btn_layout.addWidget(admin_btn)
            btn_layout.addStretch()
            self.main_layout.addLayout(btn_layout)

        # 底部信息区（卡片内）
        self.main_layout.addSpacing(8)
        footer_divider = QFrame()
        footer_divider.setFrameShape(QFrame.HLine)
        footer_divider.setStyleSheet("color: #353840; background-color: #353840; max-height: 1px;")
        self.main_layout.addWidget(footer_divider)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(16)
        db_label = QLabel(f"DB: {db_manager.config['database']}@{db_manager.config['host']}")
        db_label.setStyleSheet("color: #ef4444; font-size: 11px; background:transparent;")
        ver_label = QLabel(f"v{APP_VERSION}")
        ver_label.setStyleSheet("color: #6b7280; font-size: 11px; background:transparent;")
        footer_layout.addWidget(db_label)
        footer_layout.addStretch()
        footer_layout.addWidget(ver_label)
        self.main_layout.addLayout(footer_layout)

        center_h.addWidget(card)
        center_h.addStretch()
        outer_layout.addLayout(center_h)
        outer_layout.addStretch()

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
        from src.core.config import ADMIN_PASSWORD
        if password == ADMIN_PASSWORD:  # 管理员密码
            dialog.accept()
            # 以管理员身份进入主窗口
            from src.ui.main_window import MainWindow
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
            
        from src.ui.main_window import MainWindow
        self.main_window = MainWindow(selected_role, selected_departments, logout_callback=self.show)
        self.main_window.show()
        self.hide()  # 隐藏而不是关闭

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1d23;
                color: #e8eaed;
                font-size: 14px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            QWidget#card {
                background-color: #252830;
                border: 1px solid #353840;
                border-radius: 12px;
            }
            QGroupBox {
                border: 1px solid #353840;
                border-radius: 8px;
                margin-top: 12px;
                font-weight: bold;
                color: #9ba3b0;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 12px;
            }
            QRadioButton, QCheckBox {
                spacing: 10px;
                color: #c8cdd5;
                font-size: 14px;
            }
            QRadioButton:hover, QCheckBox:hover {
                color: #ffffff;
            }
            QRadioButton::indicator, QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #454a55;
                border-radius: 9px;
                background-color: #1a1d23;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #4f8ef7;
                border-radius: 9px;
                background-color: #4f8ef7;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #454a55;
                border-radius: 4px;
                background-color: #1a1d23;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #4f8ef7;
                border-radius: 4px;
                background-color: #4f8ef7;
            }
            QPushButton {
                background-color: #4f8ef7;
                color: #FFFFFF;
                border: none;
                padding: 10px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #6ba3ff;
            }
            QPushButton:pressed {
                background-color: #3a72d6;
            }
            QPushButton#secondary {
                background-color: transparent;
                color: #9ba3b0;
                border: 1px solid #454a55;
            }
            QPushButton#secondary:hover {
                background-color: #2e3340;
                color: #e8eaed;
                border-color: #6b7280;
            }
            QLineEdit {
                background-color: #2e3340;
                border: 1px solid #454a55;
                padding: 10px 12px;
                border-radius: 8px;
                color: #e8eaed;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4f8ef7;
                background-color: #333845;
            }
            QListWidget {
                background-color: #2e3340;
                border: 1px solid #454a55;
                border-radius: 6px;
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
        from src.ui.main_window import MainWindow
        # 传递选中角色和所有部门
        self.main_window = MainWindow(role, self.user_departments, is_admin=False, logout_callback=self.show, user_name=user_info['name'])
        self.main_window.show()
        self.hide()