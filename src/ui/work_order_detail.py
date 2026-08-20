import html
import os

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    CardWidget,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    Theme,
    setTheme,
    setThemeColor,
)


class CollapsibleBox(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setStyleSheet("""
            QToolButton {
                border: none;
                color: #4f8ef7;
                font-weight: bold;
                font-size: 15px;
                background-color: #1a1d24;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
            }
            QToolButton:hover {
                background-color: #242933;
            }
            QToolButton:checked {
                color: #4f8ef7;
            }
        """)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.toggled.connect(self.on_toggled)

        self.content_area = QWidget()
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 8, 10, 8)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(4)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_area)
        
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(240)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def on_toggled(self, checked):
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.content_area.adjustSize()
        content_height = self.content_layout.sizeHint().height()
        if content_height == 0 and self.content_layout.count() > 0:
             content_height = self.content_area.sizeHint().height()

        self.animation.stop()
        self.animation.setStartValue(0 if checked else content_height)
        self.animation.setEndValue(content_height if checked else 0)
        self.animation.start()

    def setContentLayout(self, layout):
        old_layout = self.content_area.layout()
        if old_layout:
            QWidget().setLayout(old_layout)
        self.content_layout = layout
        self.content_area.setLayout(layout)

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
        
    def expand(self):
        if not self.toggle_button.isChecked():
            self.toggle_button.setChecked(True)


class WorkOrderDetailDialog(QDialog):
    def __init__(self, order_data, logs, is_admin=False, parent=None):
        super().__init__(parent)
        self.order_data = order_data
        self.logs = logs
        self.is_admin = is_admin
        self.setWindowTitle(f"工单详细信息 - {order_data['id']}")
        self.resize(920, 800)
        self.setMinimumSize(640, 520)
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(14)
        self.main_layout.setContentsMargins(16, 16, 16, 16)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(14)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)

        # 1. 核心信息概览 (始终显示，不折叠)
        self.setup_header_section()

        # 展示审核退回提示（如有）
        self.setup_review_feedback_section()

        # 2. 详细信息分组 (可折叠)
        self.setup_detail_groups()

        scroll.setWidget(self.scroll_widget)
        self.main_layout.addWidget(scroll, 1)

        # 底部确定按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_button = PrimaryPushButton(FIF.ACCEPT, "确定")
        ok_button.setFixedSize(120, 36)
        ok_button.clicked.connect(self.accept)
        btn_layout.addWidget(ok_button)
        self.main_layout.addLayout(btn_layout)

    def setup_review_feedback_section(self):
        """展示审核退回提示"""
        from src.core.database import db_manager
        feedbacks = db_manager.get_review_feedback(self.order_data['id'])
        if feedbacks:
            feedback_card = CardWidget()
            layout = QVBoxLayout(feedback_card)
            layout.setContentsMargins(16, 14, 16, 14)
            layout.setSpacing(10)

            art_status = self.order_data.get('art_status', '')
            if art_status == '美工后期重新制作':
                title_text = "⚠️ 美工审核退回提示"
            elif self.order_data.get('status') == '后期重新剪辑':
                title_text = "⚠️ 剪辑审核退回提示"
            else:
                title_text = "⚠️ 退回提示"
            title_label = QLabel(title_text)
            title_label.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 15px;")
            layout.addWidget(title_label)

            for fb in feedbacks:
                item_label = QLabel(f"• <b>文件</b>: {fb['file_name']}<br/>  <b>所在目录</b>: {fb['directory']}<br/>  <b>原因</b>: <span style='color: #fca5a5;'>{fb['reason']}</span>")
                item_label.setStyleSheet("color: #e8eaed; font-size: 13px; line-height: 1.5;")
                item_label.setWordWrap(True)
                item_label.setTextFormat(Qt.TextFormat.RichText)
                layout.addWidget(item_label)

            self.scroll_layout.addWidget(feedback_card)

    def setup_header_section(self):
        """核心信息概览卡片"""
        header_card = CardWidget()
        layout = QVBoxLayout(header_card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # 顶部行：状态徽章 + 标题 + 复制ID按钮
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        status = self.order_data.get('status', '未知')
        art_status = self.order_data.get('art_status')
        if art_status:
            art_display_map = {
                '美工设计中': '美工设计中',
                '美工待分发': '美工待分发',
                '美工后期审核中': '美工待审批',
                '美工后期重新制作': '美工重新制作',
                '美工已完成': '美工已完成',
            }
            status = art_display_map.get(art_status, art_status)
        status_label = QLabel(status)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_color = self.get_status_color(status)
        status_label.setStyleSheet(f"""
            background-color: {status_color};
            color: white;
            font-weight: bold;
            font-size: 12px;
            border-radius: 6px;
            padding: 4px 12px;
        """)
        status_label.setFixedHeight(28)
        top_row.addWidget(status_label)

        title_text = f"{self.order_data.get('model', '')} {self.order_data.get('name', '')}".strip() or "工单详情"
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 17px; font-weight: bold; color: #FFFFFF; background: transparent;")
        title_label.setWordWrap(True)
        top_row.addWidget(title_label, 1)

        copy_id_btn = PushButton(FIF.COPY, "复制ID")
        copy_id_btn.setFixedHeight(28)
        def on_copy_id():
            oid = str(self.order_data.get('id', ''))
            QApplication.clipboard().setText(oid)
            InfoBar.success(
                title="已复制",
                content=f"工单ID {oid} 已存入剪贴板",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000,
                parent=self
            )
        copy_id_btn.clicked.connect(on_copy_id)
        top_row.addWidget(copy_id_btn)

        layout.addLayout(top_row)

        # 底部元信息行
        meta_row = QHBoxLayout()
        meta_row.setSpacing(16)

        id_lbl = QLabel(f"工单ID: <span style='color: #4f8ef7; font-weight: bold;'>{self.order_data.get('id', '')}</span>")
        id_lbl.setStyleSheet("color: #9ba3b0; font-size: 12px; background: transparent;")
        id_lbl.setTextFormat(Qt.TextFormat.RichText)
        meta_row.addWidget(id_lbl)

        created_at = str(self.order_data.get('created_at', '') or '--')
        created_lbl = QLabel(f"创建时间: {created_at}")
        created_lbl.setStyleSheet("color: #9ba3b0; font-size: 12px; background: transparent;")
        meta_row.addWidget(created_lbl)

        dept_name = str(self.order_data.get('department', '') or '--')
        dept_lbl = QLabel(f"所属产线: <span style='color: #e8eaed;'>{dept_name}</span>")
        dept_lbl.setStyleSheet("color: #9ba3b0; font-size: 12px; background: transparent;")
        dept_lbl.setTextFormat(Qt.TextFormat.RichText)
        meta_row.addWidget(dept_lbl)

        meta_row.addStretch()
        layout.addLayout(meta_row)

        self.scroll_layout.addWidget(header_card)

    def setup_detail_groups(self):
        """设置详细信息与流转进度分组"""
        self.setup_detail_section()
        self.setup_progress_section()
        self.setup_logs_section()

    def setup_detail_section(self):
        """业务详细信息"""
        detail_card = CardWidget()
        main_vbox = QVBoxLayout(detail_card)
        main_vbox.setContentsMargins(18, 16, 18, 16)
        main_vbox.setSpacing(14)

        card_title = QLabel("📋 业务工单信息")
        card_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4f8ef7;")
        main_vbox.addWidget(card_title)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)

        fields = [
            ("工单ID:", self.order_data.get('id', '')),
            ("所属产线:", self.order_data.get('department', '')),
            ("产品型号:", self.order_data.get('model', '')),
            ("产品全称:", self.order_data.get('name', '')),
            ("项目类型:", self.order_data.get('project_type', '')),
            ("项目内容:", self.order_data.get('project_content', '')),
            ("需求方:", self.order_data.get('requester', '')),
            ("发起人:", self.order_data.get('creator', '')),
            ("创建时间:", str(self.order_data.get('created_at', ''))),
            ("期望完成:", str(self.order_data.get('expected_at', '') or '未指定')),
        ]

        for i, (label_text, val_text) in enumerate(fields):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #9ba3b0; font-size: 13px; font-weight: bold;")
            val = QLabel(str(val_text))
            val.setStyleSheet("color: #e8eaed; font-size: 13px;")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row = i // 2
            col = (i % 2) * 2
            grid.addWidget(lbl, row, col)
            grid.addWidget(val, row, col + 1)

        main_vbox.addLayout(grid)

        # 快捷操作栏
        action_divider = QFrame()
        action_divider.setFrameShape(QFrame.Shape.HLine)
        action_divider.setStyleSheet("background-color: #2e3340; max-height: 1px;")
        main_vbox.addWidget(action_divider)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)
        action_bar.addWidget(QLabel("快捷操作:"))

        copy_name_btn = PushButton(FIF.COPY, "复制产品全称")
        copy_name_btn.setFixedHeight(28)
        def on_copy_name():
            text = f"{self.order_data.get('model', '')} {self.order_data.get('name', '')}".strip()
            QApplication.clipboard().setText(text)
            InfoBar.success("已复制", f"已复制产品全称：{text}", orient=Qt.Orientation.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=2000, parent=self)
        copy_name_btn.clicked.connect(on_copy_name)
        action_bar.addWidget(copy_name_btn)

        open_dir_btn = PushButton(FIF.FOLDER, "打开素材根目录")
        open_dir_btn.setFixedHeight(28)
        def on_open_dir():
            from src.core.paths import RAW_ROOT, to_local_path
            dept = self.order_data.get('department', '')
            dept_path = to_local_path(os.path.join(RAW_ROOT, dept)) if dept else to_local_path(RAW_ROOT)
            if dept_path and os.path.exists(dept_path):
                os.startfile(dept_path)
            elif to_local_path(RAW_ROOT) and os.path.exists(to_local_path(RAW_ROOT)):
                os.startfile(to_local_path(RAW_ROOT))
            else:
                InfoBar.warning("提示", f"素材根目录不存在: {dept_path}", orient=Qt.Orientation.Horizontal, isClosable=True, position=InfoBarPosition.TOP_RIGHT, duration=2500, parent=self)
        open_dir_btn.clicked.connect(on_open_dir)
        action_bar.addWidget(open_dir_btn)

        action_bar.addStretch()
        main_vbox.addLayout(action_bar)

        self.scroll_layout.addWidget(detail_card)

    def setup_progress_section(self):
        """流转进度条"""
        progress_card = CardWidget()
        progress_main_layout = QVBoxLayout(progress_card)
        progress_main_layout.setContentsMargins(18, 16, 18, 16)
        progress_main_layout.setSpacing(14)

        card_title = QLabel("🚀 处理流转进度")
        card_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #4f8ef7;")
        progress_main_layout.addWidget(card_title)

        art_finished, edit_finished = self.calculate_role_finished_steps()

        # 1. 美工进度行
        art_layout = QHBoxLayout()
        art_title = QLabel("美工后期:")
        art_title.setStyleSheet("font-weight: bold; color: #4fc3f7; font-size: 13px; min-width: 70px;")
        art_layout.addWidget(art_title)

        art_steps = ["美工待领取", "正在设计", "设计完成", "美工分发", "美工审批", "已被领取"]
        for i, step in enumerate(art_steps):
            step_widget = QWidget()
            step_vbox = QVBoxLayout(step_widget)
            step_vbox.setSpacing(4)
            step_vbox.setContentsMargins(0, 0, 0, 0)

            is_done = step in art_finished
            dot_text = "✓" if is_done else str(i+1)
            dot_color = "#10b981" if is_done else "#374151"
            text_color = "#10b981" if is_done else "#9ba3b0"
            font_weight = "bold" if is_done else "normal"

            dot = QLabel(dot_text)
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedSize(22, 22)
            dot.setStyleSheet(f"""
                background-color: {dot_color};
                color: white;
                border-radius: 11px;
                font-weight: bold;
                font-size: 11px;
            """)

            label = QLabel(step)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"color: {text_color}; font-weight: {font_weight}; font-size: 12px;")

            step_vbox.addWidget(dot, 0, Qt.AlignmentFlag.AlignCenter)
            step_vbox.addWidget(label, 0, Qt.AlignmentFlag.AlignCenter)
            art_layout.addWidget(step_widget)

            if i < len(art_steps) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFixedHeight(2)
                line.setStyleSheet(f"background-color: {dot_color};")
                art_layout.addWidget(line)

        # 2. 剪辑进度行
        edit_layout = QHBoxLayout()
        edit_title = QLabel("剪辑后期:")
        edit_title.setStyleSheet("font-weight: bold; color: #c084fc; font-size: 13px; min-width: 70px;")
        edit_layout.addWidget(edit_title)

        edit_steps = ["剪辑待领取", "正在剪辑", "视频审核中", "后期审完", "剪辑分发", "已被领取"]
        for i, step in enumerate(edit_steps):
            step_widget = QWidget()
            step_vbox = QVBoxLayout(step_widget)
            step_vbox.setSpacing(4)
            step_vbox.setContentsMargins(0, 0, 0, 0)

            is_done = step in edit_finished
            dot_text = "✓" if is_done else str(i+1)
            dot_color = "#10b981" if is_done else "#374151"
            text_color = "#10b981" if is_done else "#9ba3b0"
            font_weight = "bold" if is_done else "normal"

            dot = QLabel(dot_text)
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedSize(22, 22)
            dot.setStyleSheet(f"""
                background-color: {dot_color};
                color: white;
                border-radius: 11px;
                font-weight: bold;
                font-size: 11px;
            """)

            label = QLabel(step)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"color: {text_color}; font-weight: {font_weight}; font-size: 12px;")

            step_vbox.addWidget(dot, 0, Qt.AlignmentFlag.AlignCenter)
            step_vbox.addWidget(label, 0, Qt.AlignmentFlag.AlignCenter)
            edit_layout.addWidget(step_widget)

            if i < len(edit_steps) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFixedHeight(2)
                line.setStyleSheet(f"background-color: {dot_color};")
                edit_layout.addWidget(line)

        progress_main_layout.addLayout(art_layout)
        progress_main_layout.addLayout(edit_layout)
        self.scroll_layout.addWidget(progress_card)

    def setup_logs_section(self):
        """操作日志"""
        logs_box = CollapsibleBox("📝 操作日志")
        logs_widget = QWidget()
        logs_layout = QVBoxLayout(logs_widget)
        logs_layout.setSpacing(10)
        logs_layout.setContentsMargins(0, 4, 0, 4)
        
        if not self.logs:
            empty_label = QLabel("暂无操作日志")
            empty_label.setStyleSheet("color: #888888; padding: 16px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logs_layout.addWidget(empty_label)
        else:
            for log in self.logs:
                log_card = CardWidget()
                item_layout = QVBoxLayout(log_card)
                item_layout.setSpacing(6)
                item_layout.setContentsMargins(12, 10, 12, 10)
                
                header_layout = QHBoxLayout()
                header_layout.setSpacing(10)
                
                role_text = str(log.get('role') or '')
                user_name = log.get('user_name', '')
                action_type = log.get('action_type', '未知操作')
                timestamp = str(log.get('timestamp', ''))
                
                if self.is_admin and user_name:
                    user_label = QLabel(user_name)
                    user_label.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
                    header_layout.addWidget(user_label)
                    
                    role_label = QLabel(role_text)
                    role_label.setStyleSheet("color: #4f8ef7; font-weight: bold; font-size: 12px;")
                    header_layout.addWidget(role_label)
                else:
                    display_role = role_text.split(' ')[0] if ' ' in role_text else role_text
                    role_label = QLabel(display_role)
                    role_label.setStyleSheet("color: #4f8ef7; font-weight: bold; font-size: 13px;")
                    header_layout.addWidget(role_label)

                action_label = QLabel(action_type)
                action_label.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 13px;")
                header_layout.addWidget(action_label)
                
                header_layout.addStretch()
                
                time_label = QLabel(timestamp)
                time_label.setStyleSheet("color: #9ba3b0; font-size: 12px;")
                header_layout.addWidget(time_label)
                
                item_layout.addLayout(header_layout)
                
                details_text = log.get('details', '')
                formatted_details = self.format_log_details(details_text)
                
                if formatted_details:
                    line = QFrame()
                    line.setFrameShape(QFrame.Shape.HLine)
                    line.setStyleSheet("background-color: #2e3340; max-height: 1px;")
                    item_layout.addWidget(line)

                    details_label = QLabel(formatted_details)
                    details_label.setStyleSheet("color: #d1d5db; font-size: 12px; margin-top: 2px;")
                    details_label.setWordWrap(True)
                    details_label.setTextFormat(Qt.TextFormat.RichText)
                    details_label.setOpenExternalLinks(True)
                    item_layout.addWidget(details_label)
                
                logs_layout.addWidget(log_card)
                
        logs_box.addWidget(logs_widget)
        self.scroll_layout.addWidget(logs_box)

    def format_log_details(self, details):
        if not details:
            return ""
            
        ignore_keys = {'工单ID', '角色', 'action_type', 'user_name', 'timestamp'}
        styles = {
            'key': 'color: #9ba3b0; font-weight: normal;',
            'value': 'color: #e8eaed;',
            'highlight': 'color: #f59e0b; font-weight: bold;',
            'path': 'color: #34d399; font-family: Consolas, monospace;',
            'link': 'color: #4f8ef7; text-decoration: none;'
        }
        
        parts = details.split(', ')
        formatted_rows = []
        
        for part in parts:
            if '=' not in part:
                continue
            
            try:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key in ignore_keys or not value:
                    continue

                key = html.escape(key)
                value = html.escape(value)
                row_html = ""
                
                if key == 'URL':
                    if value.startswith(('http://', 'https://')):
                        row_html = f'<span style="{styles["key"]}">{key}:</span> <a href="{value}" style="{styles["link"]}">{value}</a>'
                    else:
                        row_html = f'<span style="{styles["key"]}">{key}:</span> <span style="{styles["value"]}">{value}</span>'
                elif key in ['源路径', '目标路径']:
                    row_html = f'<div style="margin-bottom: 3px;"><span style="{styles["key"]}">{key}:</span> <br><span style="{styles["path"]}">{value}</span></div>'
                elif key in ['产品标题', '关键词']:
                    row_html = f'<div style="margin-bottom: 3px;"><span style="{styles["key"]}">{key}:</span> <span style="{styles["highlight"]}">{value}</span></div>'
                else:
                    row_html = f'<span style="{styles["key"]}">{key}:</span> <span style="{styles["value"]}">{value}</span>'
                
                formatted_rows.append(row_html)
            except (KeyError, TypeError, ValueError):
                continue
                
        if not formatted_rows:
            return html.escape(details)
            
        return "".join([f"<div style='margin-bottom: 2px;'>{row}</div>" for row in formatted_rows])

    def setup_footer(self):
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        close_btn = PrimaryPushButton(FIF.ACCEPT, "确定")
        close_btn.setFixedHeight(34)
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        
        footer_layout.addWidget(close_btn)
        self.main_layout.addLayout(footer_layout)

    def add_field(self, layout, row, col, label_text, value_text, colspan=1):
        label = QLabel(label_text)
        label.setStyleSheet("color: #9ba3b0; font-size: 12px;")
        
        value = str(value_text) if value_text else "--"
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #e8eaed; font-size: 13px; font-weight: 500;")
        value_label.setWordWrap(True)
        
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(2)
        vbox.addWidget(label)
        vbox.addWidget(value_label)
        
        layout.addWidget(container, row, col, 1, colspan)

    def get_status_color(self, status):
        colors = {
            "拍摄中": "#f59e0b",
            "拍摄完成": "#3b82f6",
            "视频审核中": "#f59e0b",
            "视频后期审核中": "#f59e0b",
            "美工后期审核中": "#f59e0b",
            "审核通过": "#10b981",
            "后期审核通过": "#10b981",
            "重新拍摄": "#ef4444",
            "后期重新剪辑": "#ef4444",
            "美工后期重新制作": "#ef4444",
            "美工设计": "#3b82f6",
            "视频剪辑": "#8b5cf6",
            "已完成": "#10b981",
            "已取消": "#ef4444"
        }
        return colors.get(status, "#6b7280")

    def calculate_role_finished_steps(self):
        art_finished = set()
        edit_finished = set()
        
        status = self.order_data.get('status', '')
        art_status = self.order_data.get('art_status')
        art_start = self.order_data.get('art_start_time')
        art_end = self.order_data.get('art_end_time')
        edit_start = self.order_data.get('edit_start_time')
        
        is_post_phase = status not in ['拍摄中', '重新拍摄', '视频审核中', '拍摄完成', '审核通过']
        
        if is_post_phase:
            art_finished.add("美工待领取")
        if art_start:
            art_finished.add("正在设计")
        if art_end:
            art_finished.add("设计完成")
            
        if is_post_phase:
            edit_finished.add("剪辑待领取")
        if edit_start:
            edit_finished.add("正在剪辑")

        has_art_dist = False
        has_edit_dist = False
        has_art_ops_collected = False
        has_art_sales_collected = False
        has_edit_ops_collected = False
        has_edit_sales_collected = False
        has_art_approved = False
        has_edit_submit = False
        has_edit_approved = False

        for log in self.logs:
            role = log.get('role') or ''
            action = log.get('action_type') or ''
            details = log.get('details') or ''
            content = action + details

            if action in ('美工分发运营', '美工分发销售'):
                has_art_dist = True
            if action == '美工后期审批通过':
                has_art_approved = True
            if action in ('剪辑分发运营', '剪辑分发销售'):
                has_edit_dist = True
            if action == '提交视频后期审核':
                has_edit_submit = True
            if action == '视频后期审核通过':
                has_edit_approved = True
                
            if ("运营" in role or "销售" in role) and "领取" in content and f"工单ID={self.order_data['id']}" in details:
                if "02视频" in details:
                    if "运营" in role:
                        has_edit_ops_collected = True
                    else:
                        has_edit_sales_collected = True
                else:
                    if "运营" in role:
                        has_art_ops_collected = True
                    else:
                        has_art_sales_collected = True

        if status in ['后期已完成', '待上架', '已上架']:
            if art_status in ('美工后期审核中', '美工已完成'):
                has_art_dist = True

        if has_art_dist:
            art_finished.add("美工分发")
        if has_edit_dist:
            edit_finished.add("剪辑分发")

        if art_status == '美工后期审核中' or status == '美工后期审核中' or has_art_approved:
            art_finished.add("美工审批")

        if has_art_ops_collected or has_art_sales_collected or status in ['待上架', '已上架']:
            art_finished.add("已被领取")
            
        if has_edit_ops_collected or has_edit_sales_collected or status in ['待上架', '已上架']:
            edit_finished.add("已被领取")

        if status == '视频后期审核中' or has_edit_submit:
            edit_finished.add("视频审核中")
        if status == '后期审核通过' or has_edit_approved:
            edit_finished.add("视频审核中")
            edit_finished.add("后期审完")

        return art_finished, edit_finished

    def format_time(self, time_str):
        if not time_str:
            return "--"
        return str(time_str)

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1e222a;
                color: #e8eaed;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #16191f;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #374151;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4f8ef7;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
