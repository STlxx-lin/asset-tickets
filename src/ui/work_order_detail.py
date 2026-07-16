from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
                             QGroupBox, QScrollArea, QGridLayout, QPushButton, QFrame, 
                             QToolButton, QSizePolicy, QApplication)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
from PySide6.QtGui import QColor, QPalette

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
                color: #4fc3f7;
                font-weight: bold;
                font-size: 16px;
                background-color: #2E2E2E;
                padding: 5px;
                text-align: left;
            }
            QToolButton:hover {
                background-color: #3E3E3E;
            }
            QToolButton:checked {
                color: #4fc3f7;
            }
        """)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.toggled.connect(self.on_toggled)

        self.content_area = QWidget()
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 5, 10, 5)  # Reduced vertical margins
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_area)
        
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

    def on_toggled(self, checked):
        self.toggle_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        
        # Calculate height
        self.content_area.adjustSize()
        content_height = self.content_layout.sizeHint().height()
        
        # Ensure proper height calculation for grid layouts
        if content_height == 0 and self.content_layout.count() > 0:
             content_height = self.content_area.sizeHint().height()

        self.animation.stop()
        self.animation.setStartValue(0 if checked else content_height)
        self.animation.setEndValue(content_height if checked else 0)
        self.animation.start()

    def setContentLayout(self, layout):
        # Remove old layout
        old_layout = self.content_area.layout()
        if old_layout:
            QWidget().setLayout(old_layout) # Delete old layout
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
        self.resize(900, 800)
        self.setMinimumSize(600, 500)
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(10)  # Reduced spacing
        self.main_layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(10)  # Reduced spacing
        self.scroll_layout.setContentsMargins(0, 0, 0, 0) # Remove internal margins

        # 1. 核心信息概览 (始终显示，不折叠)
        self.setup_header_section()

        # 展示审核退回提示（如有）
        self.setup_review_feedback_section()

        # 2. 详细信息分组 (可折叠)
        self.setup_detail_groups()

        # 3. 流转进度 (始终显示)
        self.setup_progress_section()

        # 4. 操作日志 (可折叠)
        self.setup_logs_section()

        self.scroll_layout.addStretch()
        scroll.setWidget(self.scroll_widget)
        self.main_layout.addWidget(scroll)

        # 底部关闭按钮
        self.setup_footer()

    def setup_review_feedback_section(self):
        """展示重新拍摄或后期重新剪辑（不通过）的反馈原因"""
        from src.core.database import db_manager
        current_status = self.order_data.get('status')
        if current_status not in ['重新拍摄', '后期重新剪辑']:
            return
            
        feedbacks = db_manager.get_review_feedback(self.order_data['id'])
        if feedbacks:
            feedback_widget = QWidget()
            feedback_widget.setObjectName("ReviewFeedbackPanel")
            # 暗红色背景、鲜红边框，白字/淡红字高亮
            feedback_widget.setStyleSheet("""
                QWidget#ReviewFeedbackPanel {
                    background-color: #3d1c1c;
                    border: 1px solid #ef4444;
                    border-radius: 8px;
                }
            """)
            layout = QVBoxLayout(feedback_widget)
            layout.setContentsMargins(15, 12, 15, 12)
            layout.setSpacing(8)

            title_text = "⚠️ 视频审核退回提示（需要重新拍摄）" if current_status == '重新拍摄' else "⚠️ 视频后期审核退回提示（需要重新剪辑）"
            title_label = QLabel(title_text)
            title_label.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 15px;")
            layout.addWidget(title_label)

            # 添加退回的文件详情
            for i, fb in enumerate(feedbacks):
                item_label = QLabel(f"• <b>文件</b>: {fb['file_name']}<br/>  <b>所在目录</b>: {fb['directory']}<br/>  <b>原因</b>: <span style='color: #ff8888;'>{fb['reason']}</span>")
                item_label.setStyleSheet("color: #e8eaed; font-size: 13px; line-height: 1.4;")
                item_label.setWordWrap(True)
                item_label.setTextFormat(Qt.RichText)
                layout.addWidget(item_label)

            self.scroll_layout.addWidget(feedback_widget)

    def setup_header_section(self):
        """核心信息概览"""
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #333333; border-radius: 8px;")
        layout = QGridLayout(header_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 状态标签
        status = self.order_data.get('status', '未知')
        status_label = QLabel(status)
        status_label.setAlignment(Qt.AlignCenter)
        status_color = self.get_status_color(status)
        status_label.setStyleSheet(f"""
            background-color: {status_color};
            color: white;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
            padding: 4px 8px;
        """)
        status_label.setFixedSize(80, 26)

        # 标题/型号/名称
        title_text = f"{self.order_data.get('model', '')} {self.order_data.get('name', '')}"
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        title_label.setWordWrap(True)

        # ID 和 时间信息 (放在一行显示，节省空间)
        meta_info_layout = QHBoxLayout()
        meta_info_layout.setSpacing(15)
        
        id_label = QLabel(f"ID: {self.order_data['id']}")
        id_label.setStyleSheet("color: #AAAAAA; font-size: 13px;")
        
        created_at = self.format_time(self.order_data.get('created_at'))
        updated_at = self.format_time(self.order_data.get('updated_at'))
        
        time_label = QLabel(f"创建: {created_at}  |  更新: {updated_at}")
        time_label.setStyleSheet("color: #777777; font-size: 12px;")
        
        meta_info_layout.addWidget(id_label)
        meta_info_layout.addWidget(time_label)
        meta_info_layout.addStretch()

        # 布局
        # Row 0: 状态 | 标题
        layout.addWidget(status_label, 0, 0, Qt.AlignTop)
        layout.addWidget(title_label, 0, 1)
        
        # Row 1: 空 | Meta Info
        layout.addLayout(meta_info_layout, 1, 1)
        
        # 调整列比例
        layout.setColumnStretch(1, 1)

        self.scroll_layout.addWidget(header_widget)

    def setup_detail_groups(self):
        """分组展示详细信息 - 更紧凑的布局"""
        
        # 合并业务详情和人员信息到一个更紧凑的视图
        business_box = CollapsibleBox("📋 详细信息")
        business_layout = QGridLayout()
        business_layout.setSpacing(15) # 适中的间距
        business_layout.setContentsMargins(5, 10, 5, 10)
        
        # 使用4列布局 (Label-Value 垂直堆叠算作1个单元格)
        # Row 0
        self.add_field(business_layout, 0, 0, "项目类型", self.order_data.get('project_type'))
        self.add_field(business_layout, 0, 1, "所属部门", self.order_data.get('department'))
        self.add_field(business_layout, 0, 2, "优先级", "普通") 
        self.add_field(business_layout, 0, 3, "发起人", self.order_data.get('creator'))
        
        # Row 1
        self.add_field(business_layout, 1, 0, "需求人", self.order_data.get('requester'))
        self.add_field(business_layout, 1, 1, "项目内容", self.order_data.get('project_content'), colspan=3)
        
        # Row 2: 备注
        remarks = self.order_data.get('remarks', '')
        if remarks:
             self.add_field(business_layout, 2, 0, "备注", remarks, colspan=4)

        # 设置列宽均匀
        for i in range(4):
            business_layout.setColumnStretch(i, 1)

        business_box.setContentLayout(business_layout)
        business_box.expand()
        self.scroll_layout.addWidget(business_box)

        # 移除了单独的“人员与部门”和“时间节点”分组，整合到上方或头部

    def setup_progress_section(self):
        """流转进度条"""
        progress_group = QGroupBox("处理进度")
        progress_layout = QHBoxLayout(progress_group)
        progress_layout.setContentsMargins(5, 15, 5, 15) # Reduced vertical margins
        
        # 计算已完成的步骤
        finished_steps = self.calculate_finished_steps()
        step_names = ["拍摄完成", "美工分发", "剪辑分发", "销售领取", "运营领取", "运营上架"]
        
        for i, step in enumerate(step_names):
            # 步骤容器
            step_widget = QWidget()
            step_vbox = QVBoxLayout(step_widget)
            step_vbox.setSpacing(4) # Tighter spacing
            step_vbox.setContentsMargins(0, 0, 0, 0)
            
            # 图标/圆点
            is_done = step in finished_steps
            dot_text = "✓" if is_done else str(i+1)
            dot_color = "#4caf50" if is_done else "#555555"
            text_color = "#4caf50" if is_done else "#888888"
            font_weight = "bold" if is_done else "normal"
            
            dot = QLabel(dot_text)
            dot.setAlignment(Qt.AlignCenter)
            dot.setFixedSize(22, 22) # Slightly smaller
            dot.setStyleSheet(f"""
                background-color: {dot_color};
                color: white;
                border-radius: 11px;
                font-weight: bold;
                font-size: 12px;
            """)
            
            # 文字
            label = QLabel(step)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(f"color: {text_color}; font-weight: {font_weight}; font-size: 12px;")
            
            step_vbox.addWidget(dot, 0, Qt.AlignCenter)
            step_vbox.addWidget(label, 0, Qt.AlignCenter)
            progress_layout.addWidget(step_widget)
            
            # 箭头 (除了最后一个)
            if i < len(step_names) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFixedHeight(2)
                line.setStyleSheet(f"background-color: {dot_color};")
                progress_layout.addWidget(line)

        self.scroll_layout.addWidget(progress_group)

    def setup_logs_section(self):
        """操作日志"""
        logs_box = CollapsibleBox("📝 操作日志")
        logs_widget = QWidget()
        logs_layout = QVBoxLayout(logs_widget)
        logs_layout.setSpacing(15)
        
        if not self.logs:
            empty_label = QLabel("暂无操作日志")
            empty_label.setStyleSheet("color: #888888; padding: 20px;")
            empty_label.setAlignment(Qt.AlignCenter)
            logs_layout.addWidget(empty_label)
        else:
            for log in self.logs:
                log_item = QWidget()
                log_item.setStyleSheet("background-color: #333333; border-radius: 6px; padding: 12px;")
                item_layout = QVBoxLayout(log_item)
                item_layout.setSpacing(8)
                item_layout.setContentsMargins(10, 10, 10, 10)
                
                # 头部: 角色 - 动作 - 时间
                header_layout = QHBoxLayout()
                header_layout.setSpacing(10)
                
                role_text = log.get('role', '')
                user_name = log.get('user_name', '')
                action_type = log.get('action_type', '未知操作')
                timestamp = str(log.get('timestamp', ''))
                
                # 角色与用户显示逻辑
                if self.is_admin and user_name:
                    # 管理员: 用户名(橙) + 角色(蓝)
                    user_label = QLabel(user_name)
                    user_label.setStyleSheet("color: #ffab40; font-weight: bold; font-size: 14px;")
                    header_layout.addWidget(user_label)
                    
                    role_label = QLabel(role_text)
                    role_label.setStyleSheet("color: #4fc3f7; font-weight: bold; font-size: 13px;")
                    header_layout.addWidget(role_label)
                else:
                    # 普通用户: 仅显示角色(蓝)
                    display_role = role_text.split(' ')[0] if ' ' in role_text else role_text
                    role_label = QLabel(display_role)
                    role_label.setStyleSheet("color: #4fc3f7; font-weight: bold; font-size: 14px;")
                    header_layout.addWidget(role_label)

                # 动作类型
                action_label = QLabel(action_type)
                action_label.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 14px;")
                header_layout.addWidget(action_label)
                
                header_layout.addStretch()
                
                # 时间
                time_label = QLabel(timestamp)
                time_label.setStyleSheet("color: #888888; font-size: 12px;")
                header_layout.addWidget(time_label)
                
                item_layout.addLayout(header_layout)
                
                # 详情解析与高亮
                details_text = log.get('details', '')
                formatted_details = self.format_log_details(details_text)
                
                if formatted_details:
                    # 分割线
                    line = QFrame()
                    line.setFrameShape(QFrame.HLine)
                    line.setStyleSheet("background-color: #444444; max-height: 1px;")
                    item_layout.addWidget(line)

                    details_label = QLabel(formatted_details)
                    details_label.setStyleSheet("color: #DDDDDD; font-size: 13px; margin-top: 5px;")
                    details_label.setWordWrap(True)
                    details_label.setTextFormat(Qt.RichText)
                    details_label.setOpenExternalLinks(True)
                    item_layout.addWidget(details_label)
                
                logs_layout.addWidget(log_item)
                
        logs_box.addWidget(logs_widget)
        # 默认不展开日志，除非最近有操作
        # logs_box.expand() 
        self.scroll_layout.addWidget(logs_box)

    def format_log_details(self, details):
        if not details:
            return ""
            
        ignore_keys = {'工单ID', '角色', 'action_type', 'user_name', 'timestamp'}
        
        # 样式定义
        styles = {
            'key': 'color: #888888; font-weight: normal;',
            'value': 'color: #DDDDDD;',
            'highlight': 'color: #ffab40; font-weight: bold;', # 橙色高亮
            'path': 'color: #81c784; font-family: Consolas, monospace;', # 绿色路径
            'link': 'color: #4fc3f7; text-decoration: none;' # 蓝色链接
        }
        
        # 尝试分割键值对
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
                    
                row_html = ""
                
                if key == 'URL':
                    row_html = f'<span style="{styles["key"]}">{key}:</span> <a href="{value}" style="{styles["link"]}">{value}</a>'
                elif key in ['源路径', '目标路径']:
                    # 路径单独占一行
                    row_html = f'<div style="margin-bottom: 4px;"><span style="{styles["key"]}">{key}:</span> <br><span style="{styles["path"]}">{value}</span></div>'
                elif key in ['产品标题', '关键词']:
                    # 核心信息高亮
                    row_html = f'<div style="margin-bottom: 4px;"><span style="{styles["key"]}">{key}:</span> <span style="{styles["highlight"]}">{value}</span></div>'
                else:
                    row_html = f'<span style="{styles["key"]}">{key}:</span> <span style="{styles["value"]}">{value}</span>'
                
                formatted_rows.append(row_html)
            except:
                continue
                
        if not formatted_rows:
            return details # 如果解析失败，显示原始内容
            
        return "".join([f"<div style='margin-bottom: 3px;'>{row}</div>" for row in formatted_rows])

    def setup_footer(self):
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(100, 36)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        
        footer_layout.addWidget(close_btn)
        self.main_layout.addLayout(footer_layout)

    def add_field(self, layout, row, col, label_text, value_text, colspan=1):
        label = QLabel(label_text)
        label.setStyleSheet("color: #888888; font-size: 12px;") # Slightly smaller label
        
        value = str(value_text) if value_text else "--"
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #FFFFFF; font-size: 13px;") # Slightly smaller value
        value_label.setWordWrap(True)
        
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(2) # Much tighter spacing
        vbox.addWidget(label)
        vbox.addWidget(value_label)
        
        layout.addWidget(container, row, col, 1, colspan)

    def get_status_color(self, status):
        colors = {
            "拍摄中": "#ff9800",
            "拍摄完成": "#2196f3",
            "视频审核中": "#f59e0b",
            "视频后期审核中": "#f59e0b",
            "审核通过": "#4caf50",
            "后期审核通过": "#4caf50",
            "重新拍摄": "#f44336",
            "后期重新剪辑": "#f44336",
            "美工设计": "#2196f3",
            "视频剪辑": "#9c27b0",
            "已完成": "#4caf50",
            "已取消": "#f44336"
        }
        return colors.get(status, "#757575")

    def calculate_finished_steps(self):
        finished_steps = set()
        # 复用原有的逻辑，但稍作封装
        for log in self.logs:
            role = log.get('role', '')
            action = log.get('action_type', '')
            details = log.get('details', '')
            content = action + details
            
            if "摄影" in role and action == "上传素材":
                finished_steps.add("拍摄完成")
            if "美工" in role and "分发" in content and ("运营" in content or "销售" in content):
                finished_steps.add("美工分发")
            if ("剪辑" in role or "视频后期审核" in role) and ("分发" in content or "审核通过" in content) and ("运营" in content or "销售" in content or "视频" in content or "后期" in content):
                finished_steps.add("剪辑分发")
            if "销售" in role and "领取" in content:
                finished_steps.add("销售领取")
            if "运营" in role and "领取" in content:
                finished_steps.add("运营领取")
            if "运营" in role and action == "添加产品信息":
                finished_steps.add("运营上架")
        return finished_steps

    def format_time(self, time_str):
        if not time_str:
            return "--"
        # 简单处理，如果已经是格式化的字符串则直接返回
        return str(time_str)

    def mask_phone(self, phone):
        if not phone or len(phone) < 7:
            return phone
        return phone[:3] + "****" + phone[-4:]

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #23272e;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #444444;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                color: #cccccc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2E2E2E;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
