import os
import sys
import time
from typing import Any

from PySide6.QtCore import QObject, QPoint, QRect, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CardWidget,
    IndeterminateProgressBar,
    ProgressBar,
    Theme,
    setTheme,
    setThemeColor,
)

from src.core.config import APP_VERSION
from src.core.database import db_manager


class StartupLoaderWorker(QThread):
    """
    后台启动预加载线程：
    并发初始化数据库连接、局域网 IP 识别与角色/部门/用户数据拉取，
    彻底解除启动阶段对 UI 主线程的阻塞。
    """
    progress_changed = Signal(int, str)  # 进度(0-100), 状态描述
    finished_loading = Signal(dict)      # 预加载好的初始数据字典

    def run(self):
        loaded_data: dict[str, Any] = {
            "roles": [],
            "departments": [],
            "local_ip": "",
            "users": [],
            "db_connected": False,
        }

        # 1. 探测数据库连接
        self.progress_changed.emit(20, "正在连接数据库...")
        try:
            connected = db_manager.connect()
            loaded_data["db_connected"] = connected
        except Exception:
            loaded_data["db_connected"] = False

        # 2. 获取本机网络 IP
        self.progress_changed.emit(45, "正在识别本机局域网环境...")
        try:
            local_ip = db_manager.get_local_ip()
            loaded_data["local_ip"] = local_ip
        except Exception:
            loaded_data["local_ip"] = "无法获取IP"

        # 3. 获取角色与部门
        self.progress_changed.emit(70, "正在加载角色与组织架构...")
        try:
            if loaded_data["db_connected"]:
                loaded_data["roles"] = db_manager.get_roles()
                loaded_data["departments"] = db_manager.get_departments()
                loaded_data["users"] = db_manager.get_users()
        except Exception:
            pass

        # 4. 加载完成
        self.progress_changed.emit(100, "准备就绪")
        time.sleep(0.15)  # 微小延时确保平滑过渡
        self.finished_loading.emit(loaded_data)


class SplashScreen(QWidget):
    """
    优雅的 Fluent 风格无边框启动闪屏卡片
    """
    def __init__(self, icon_path: str = ""):
        super().__init__()
        setTheme(Theme.DARK)
        setThemeColor('#4f8ef7')

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(460, 240)

        # 主卡片容器
        card = CardWidget(self)
        card.setGeometry(0, 0, 460, 240)
        card.setObjectName("splash_card")
        card.setStyleSheet("""
            CardWidget#splash_card {
                background-color: #1a1d24;
                border: 1px solid #2e3442;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)

        # 顶部品牌行（Logo + 标题 + 版本号）
        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)

        logo_label = QLabel()
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(
                48, 48,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("📋")
            logo_label.setStyleSheet("font-size: 32px; color: #4f8ef7; background: transparent;")

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_label = QLabel("素材工单管理系统")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; background: transparent;")
        sub_label = QLabel(f"版本 {APP_VERSION} · 启动中...")
        sub_label.setStyleSheet("font-size: 12px; color: #8b949e; background: transparent;")
        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)

        header_layout.addWidget(logo_label)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        layout.addLayout(header_layout)
        layout.addSpacing(6)

        # 状态文字
        self.status_label = QLabel("正在启动应用...")
        self.status_label.setStyleSheet("font-size: 12px; color: #cbd5e1; background: transparent;")
        layout.addWidget(self.status_label)

        # 动态进度条
        self.progress_bar = IndeterminateProgressBar()
        self.progress_bar.setFixedHeight(4)
        layout.addWidget(self.progress_bar)

        # 居中显示在屏幕中央
        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2 + geo.x()
            y = (geo.height() - self.height()) // 2 + geo.y()
            self.move(x, y)

    def set_progress(self, value: int, message: str):
        self.status_label.setText(message)

    def finish(self):
        try:
            self.progress_bar.setVisible(False)
        except Exception:
            pass
        self.hide()
        self.close()
        self.deleteLater()
