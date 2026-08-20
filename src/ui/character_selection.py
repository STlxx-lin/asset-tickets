from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)
import hmac

from qfluentwidgets import (
    CardWidget,
    FluentIcon as FIF,
    LineEdit as FluentLineEdit,
    PrimaryPushButton,
    PushButton,
    Theme,
    setTheme,
    setThemeColor,
)

# 从配置文件导入版本号
from src.core.config import APP_VERSION
from src.core.database import db_manager


class CharacterSelection(QWidget):
    def __init__(self):
        super().__init__()
        setTheme(Theme.DARK)
        setThemeColor('#4f8ef7')
        self.setWindowTitle("角色选择 - 工单管理系统")
        self.roles = db_manager.get_roles()
        self.departments = db_manager.get_departments()
        self.setGeometry(100, 100, 640, 480)
        self.main_window = None
        self.outer_layout = QVBoxLayout(self)
        self.setup_ui()
        self.apply_styles()

    def get_local_ip(self):
        return db_manager.get_local_ip()

    def setup_ui(self):
        # 重建UI时重置角色按钮列表与布局，避免残留已销毁的控件引用
        self.role_buttons = []
        self.clear_layout(self.outer_layout)
            
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setSpacing(0)
        self.outer_layout.addStretch()

        # 居中容器
        center_h = QHBoxLayout()
        center_h.addStretch()

        # Fluent 卡片容器
        card = CardWidget()
        card.setObjectName("card")
        card.setMinimumWidth(500)
        card.setMaximumWidth(640)
        self.main_layout = QVBoxLayout(card)
        self.main_layout.setContentsMargins(36, 32, 36, 32)
        self.main_layout.setSpacing(18)

        # 品牌标题
        brand_label = QLabel("工单管理系统")
        brand_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff; letter-spacing: 1px; background: transparent;")
        brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(brand_label)

        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #282c37; max-height: 1px; margin: 4px 0;")
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
            # 同时拥有「视频后期审核」+「美工后期审批」时合并显示为单个「后期审批」选项
            if '视频后期审核' in roles and '美工后期审批' in roles:
                display_roles = [r for r in roles if r not in ('视频后期审核', '美工后期审批')]
                display_roles.append('后期审批')
            else:
                display_roles = list(roles)
            selected_role = display_roles[0] if display_roles else ''
            self.selected_role = selected_role
            self.user_departments = depts

            # 用户信息区
            name_label = QLabel(user_info['name'])
            name_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff; background: transparent; padding: 2px 0;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.main_layout.addWidget(name_label)

            # IP + 部门 行
            meta_layout = QHBoxLayout()
            meta_layout.setSpacing(10)
            ip_chip = QLabel(f"IP: {user_info['ip']}")
            ip_chip.setStyleSheet("background: #232732; color: #4f8ef7; border-radius: 6px; font-size: 12px; font-weight: bold; padding: 5px 12px; border: 1px solid #303646;")
            ip_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            dept_text = "、".join(depts) if depts else "未分配部门"
            dept_chip = QLabel(f"部门: {dept_text}")
            dept_chip.setStyleSheet("background: #232732; color: #cbd5e1; border-radius: 6px; font-size: 12px; padding: 5px 12px; border: 1px solid #303646;")
            dept_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            meta_layout.addStretch()
            meta_layout.addWidget(ip_chip)
            meta_layout.addWidget(dept_chip)
            meta_layout.addStretch()
            self.main_layout.addLayout(meta_layout)

            # 角色选择（多角色时显示）
            if len(display_roles) > 1:
                role_group = QGroupBox("请选择当前登录角色")
                role_layout = QGridLayout()
                role_layout.setContentsMargins(14, 16, 14, 14)
                role_layout.setHorizontalSpacing(18)
                role_layout.setVerticalSpacing(12)
                for i, role in enumerate(display_roles):
                    btn = QRadioButton(role)
                    if role == selected_role:
                        btn.setChecked(True)
                    self.role_buttons.append(btn)
                    role_layout.addWidget(btn, i // 4, i % 4)
                role_group.setLayout(role_layout)
                self.main_layout.addWidget(role_group)

            # 提示
            tip_label = QLabel("💡 请确认以上身份信息。如有误，请核查内网 IP 或联系管理员。")
            tip_label.setStyleSheet("color: #eab308; font-size: 12px; background: transparent; padding: 4px 0;")
            tip_label.setWordWrap(True)
            tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.main_layout.addWidget(tip_label)

            # 按钮区
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(12)
            confirm_btn = PrimaryPushButton(FIF.ACCEPT, "确认进入")
            confirm_btn.setFixedHeight(40)
            confirm_btn.clicked.connect(lambda: self.enter_main(user_info))
            admin_btn = PushButton(FIF.SETTING, "管理员登录")
            admin_btn.setFixedHeight(40)
            admin_btn.clicked.connect(self.admin_login)
            btn_layout.addWidget(confirm_btn)
            btn_layout.addWidget(admin_btn)
            self.main_layout.addLayout(btn_layout)
        else:
            err_icon = QLabel("⚠")
            err_icon.setStyleSheet("font-size: 36px; color: #ef4444; background: transparent;")
            err_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.main_layout.addWidget(err_icon)

            info_label = QLabel(f"未识别到本机用户\n\nIP：{local_ip}\n\n请确认设备已连接内网，或联系管理员添加此 IP。")
            info_label.setStyleSheet("color: #ef4444; font-size: 14px; background: transparent; line-height: 1.6;")
            info_label.setWordWrap(True)
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.main_layout.addWidget(info_label)

            admin_btn = PrimaryPushButton(FIF.SETTING, "管理员登录")
            admin_btn.setFixedHeight(40)
            admin_btn.clicked.connect(self.admin_login)
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            btn_layout.addWidget(admin_btn)
            btn_layout.addStretch()
            self.main_layout.addLayout(btn_layout)

        # 底部信息区（卡片内）
        self.main_layout.addSpacing(4)
        footer_divider = QFrame()
        footer_divider.setFrameShape(QFrame.Shape.HLine)
        footer_divider.setStyleSheet("background-color: #282c37; max-height: 1px;")
        self.main_layout.addWidget(footer_divider)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(16)
        db_label = QLabel(f"DB: {db_manager.config['database']}@{db_manager.config['host']}")
        db_label.setStyleSheet("color: #ef4444; font-size: 11px; background: transparent;")
        ver_label = QLabel(f"v{APP_VERSION}")
        ver_label.setStyleSheet("color: #6b7280; font-size: 11px; background: transparent;")
        footer_layout.addWidget(db_label)
        footer_layout.addStretch()
        footer_layout.addWidget(ver_label)
        self.main_layout.addLayout(footer_layout)

        center_h.addWidget(card)
        center_h.addStretch()
        self.outer_layout.addLayout(center_h)
        self.outer_layout.addStretch()

    def admin_login(self):
        """管理员登录"""
        dialog = QDialog(self)
        dialog.setWindowTitle("管理员登录")
        dialog.setFixedSize(340, 180)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1a1d24;
                color: #e8eaed;
            }
            QLabel {
                color: #e8eaed;
                font-size: 13px;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        # 密码输入框
        password_label = QLabel("请输入管理员密码：")
        password_edit = FluentLineEdit()
        password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        password_edit.setPlaceholderText("请输入密码")
        password_edit.setFixedHeight(32)
        password_edit.setFocus()
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        cancel_button = PushButton("取消")
        cancel_button.setFixedHeight(32)
        ok_button = PrimaryPushButton(FIF.ACCEPT, "确定")
        ok_button.setFixedHeight(32)
        
        ok_button.clicked.connect(lambda: self.verify_admin_password(dialog, password_edit.text()))
        password_edit.returnPressed.connect(lambda: self.verify_admin_password(dialog, password_edit.text()))
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        
        layout.addWidget(password_label)
        layout.addWidget(password_edit)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def verify_admin_password(self, dialog, password):
        """验证管理员密码"""
        from src.core.config import ADMIN_PASSWORD
        # 安全：未配置 ADMIN_PASSWORD 或输入为空时一律拒绝，避免空密码绕过管理员认证
        if not ADMIN_PASSWORD or not password:
            QMessageBox.warning(dialog, "错误", "请输入密码！" if not password else "未配置管理员密码！")
            return
        if hmac.compare_digest(password.encode('utf-8'), ADMIN_PASSWORD.encode('utf-8')):
            dialog.accept()
            try:
                # 以管理员身份进入主窗口
                from src.ui.main_window import MainWindow
                depts = getattr(self, 'departments', None) or db_manager.get_departments()
                self.main_window = MainWindow("管理员", depts, is_admin=True, logout_callback=self.show, user_name="管理员", roles=["管理员"])
                self.main_window.show()
                self.hide()
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "启动失败", f"进入管理员主窗口失败：{e}")
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

    def apply_styles(self):
        self.setStyleSheet("""
            CharacterSelection {
                background-color: #121418;
            }
            QLabel {
                background: transparent;
                color: #e8eaed;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            CardWidget#card {
                background-color: #1a1d24;
                border: 1px solid #282c37;
                border-radius: 14px;
            }
            QGroupBox {
                background-color: #14161c;
                border: 1px solid #282c37;
                border-radius: 8px;
                margin-top: 14px;
                font-weight: bold;
                color: #8b949e;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 12px;
                color: #8b949e;
                background: transparent;
            }
            QRadioButton {
                background: transparent;
                spacing: 8px;
                color: #d1d5db;
                font-size: 13px;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            QRadioButton:hover {
                color: #4f8ef7;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #374151;
                background-color: #14161c;
            }
            QRadioButton::indicator:unchecked:hover {
                border-color: #4f8ef7;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #4f8ef7;
                background-color: #4f8ef7;
            }
        """)

    def showEvent(self, event):
        """窗口显示时重新加载数据并刷新UI"""
        super().showEvent(event)
        self.roles = db_manager.get_roles()
        self.departments = db_manager.get_departments()
        self.setup_ui()

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        # 如果主窗口存在，先关闭主窗口
        if self.main_window:
            self.main_window.close()
        # 退出整个应用程序
        from PySide6.QtWidgets import QApplication
        QApplication.quit() 

    def enter_main(self, user_info):
        # 角色选择：单选按钮存在时以选中项为准；无单选按钮时（单角色，
        # 或双审批角色合并显示为「后期审批」）用 setup_ui 已计算好的 selected_role。
        # 修复：此前取 user_info['role'] 原始逗号串，双审批合并场景下
        # role=='后期审批' 判断失败 → 主窗口无办理按钮且 dispatcher 无法分发
        role = getattr(self, 'selected_role', '')
        if hasattr(self, 'role_buttons'):
            for btn in self.role_buttons:
                if btn.isChecked():
                    role = btn.text()
                    break
        # 角色集合：合并的「后期审批」拆回两个审批角色，供主窗口/审批路由使用
        if role == '后期审批':
            selected_roles = ['视频后期审核', '美工后期审批']
        else:
            selected_roles = [role] if role else []
        from src.ui.main_window import MainWindow
        # 传递选中角色和所有部门
        self.main_window = MainWindow(role, self.user_departments, is_admin=False, logout_callback=self.show, user_name=user_info['name'], roles=selected_roles)
        self.main_window.show()
        self.hide()