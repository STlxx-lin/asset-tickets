from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget,
                             QPushButton, QListWidget, QListWidgetItem, QProgressBar, QLabel, QMessageBox)
from PySide6.QtCore import QThread, Signal, Qt, QObject, QSize, QTimer
import os
import shutil

class TaskStatusUpdater(QObject):
    """任务状态更新器，用于在主线程中更新状态"""
    update_status = Signal()

class Task(QThread):
    """文件操作任务类"""
    progress_changed = Signal(int)  # 进度变化信号
    finished = Signal()  # 完成信号
    canceled = Signal()  # 取消信号
    paused = Signal(bool)  # 暂停/继续信号

    def __init__(self, name, files, src_dir, dest_dir, file_filter=None, op_type="copy", update_status_func=None):
        """初始化文件操作任务
        
        Args:
            name: 任务名称
            files: 文件列表
            src_dir: 源目录
            dest_dir: 目标目录
            file_filter: 文件过滤函数
            op_type: 操作类型，"copy"或"move"
            update_status_func: 更新状态的回调函数
        """
        super().__init__()
        self.name = name
        self.files = files
        self.src_dir = src_dir
        self.dest_dir = dest_dir
        self.file_filter = file_filter
        self.op_type = op_type
        self._is_paused = False
        self._is_canceled = False
        self.errors = []  # 记录错误信息
        
        # 创建状态更新器
        if update_status_func:
            self.status_updater = TaskStatusUpdater()
            self.status_updater.update_status.connect(update_status_func)
        else:
            self.status_updater = None

    def run(self):
        """运行任务"""
        total = len(self.files)
        processed = 0
        move_successful = True  # 标记移动操作是否成功

        for i, fname in enumerate(self.files):
            if self._is_canceled:
                self.canceled.emit()
                return

            while self._is_paused:
                self.msleep(200)  # 使用QThread的msleep而不是time.sleep

            if self.file_filter and not self.file_filter(fname):
                continue

            src_file = os.path.join(self.src_dir, fname)
            dest_file = os.path.join(self.dest_dir, fname)

            # 如果目标文件已存在，跳过
            if os.path.exists(dest_file):
                continue

            try:
                # 新增：确保目标文件的父目录存在
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                if os.path.isdir(src_file):
                    if self.op_type == "copy":
                        shutil.copytree(src_file, dest_file, dirs_exist_ok=True)
                    else:  # move
                        shutil.move(src_file, dest_file)
                else:
                    if self.op_type == "copy":
                        shutil.copy2(src_file, dest_file)
                    else:  # move
                        shutil.move(src_file, dest_file)
                processed += 1
            except Exception as e:
                msg = f"处理文件 {fname} 时出错: {e}"
                print(msg)
                self.errors.append(msg)
                move_successful = False
                continue

            self.progress_changed.emit(int((i + 1) / total * 100))

        # 只有在移动操作成功且源文件夹存在时才删除
        if self.op_type == "move" and move_successful and os.path.exists(self.src_dir):
            try:
                # 检查源文件夹是否为空
                remaining_files = os.listdir(self.src_dir)
                if not remaining_files:
                    # 如果为空，直接删除
                    os.rmdir(self.src_dir)
                    print(f"已删除空文件夹: {self.src_dir}")
                else:
                    # 如果不为空，说明有重复文件被跳过，强制删除整个文件夹
                    shutil.rmtree(self.src_dir)
                    print(f"已删除源文件夹（包含重复文件）: {self.src_dir}")
            except Exception as e:
                msg = f"删除源文件夹时出错: {e}"
                print(msg)
                self.errors.append(msg)

        if self.status_updater:
            self.status_updater.update_status.emit()

        self.finished.emit()

    def pause(self):
        """暂停任务"""
        self._is_paused = True
        self.paused.emit(True)

    def resume(self):
        """继续任务"""
        self._is_paused = False
        self.paused.emit(False)

    def cancel(self):
        """取消任务"""
        self._is_canceled = True
        self.canceled.emit()

class TaskManagerDialog(QDialog):
    def __init__(self, parent=None, auto_show=False):
        super().__init__(parent)
        self.setWindowTitle("任务列表")
        self.resize(600, 400)
        # 移除窗口置顶标志，避免遮挡其他弹窗
        # self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.layout = QVBoxLayout(self)
        self.auto_show = auto_show  # 控制是否自动显示窗口
        # 恢复主标题为"任务列表"
        self.title_label = QLabel("任务列表")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #FFFFFF;
                padding: 10px;
                background: #2E2E2E;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(8)
        self.list_widget.setStyleSheet("""
            QListWidget {
                font-size: 16px;
                padding: 8px;
                background: #2E2E2E;
                border: 1px solid #555555;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 8px;
                margin: 3px;
                background: #3c3c3c;
                border-radius: 5px;
            }
        """)
        self.layout.addWidget(self.list_widget)

        # 添加关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("关闭窗口")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        self.layout.addLayout(btn_layout)

        self.tasks = []
        self.auto_close_timer = QTimer(self)
        self.auto_close_timer.setInterval(1000)
        self.auto_close_timer.timeout.connect(self.check_tasks)
        self.auto_close_timer.start()

        # 设置为非模态窗口
        self.setModal(False)
        
        # 延迟关闭定时器，让用户看到完成状态
        self.delay_close_timer = QTimer(self)
        self.delay_close_timer.setInterval(3000)  # 3秒后关闭
        self.delay_close_timer.timeout.connect(self.delayed_close)
        self.delay_close_timer.setSingleShot(True)

    def check_tasks(self):
        if not self.tasks:
            # 如果任务列表为空，隐藏窗口
            if not self.delay_close_timer.isActive():
                self.delay_close_timer.start()
            # 确保窗口不再置顶
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            if self.isVisible():
                self.hide()  # 隐藏窗口
            return
        
        # 检查所有任务是否都已完成
        all_finished = True
        for task in self.tasks:
            if not hasattr(task, '_finished'):
                task._finished = False
            # 如果任务线程仍在运行，则标记为未完成
            if task.isRunning():
                task._finished = False
                all_finished = False
            elif not task._finished:
                # 线程已结束但未标记为完成
                task._finished = True
            
            # 如果有任何一个任务未完成，整体标记为未完成
            if not task._finished:
                all_finished = False
        
        # 如果所有任务都完成了，启动延迟关闭
        if all_finished:
            self.auto_close_timer.stop()
            if not self.delay_close_timer.isActive():
                self.delay_close_timer.start()
    
    def delayed_close(self):
        """延迟关闭窗口，让用户看到完成状态"""
        self.close()

    def add_task(self, task):
        # 如果有新任务添加，停止延迟关闭定时器
        if self.delay_close_timer.isActive():
            self.delay_close_timer.stop()
        
        # 提取工单ID
        work_order_id = "未知工单"
        if "工单" in task.name:
            try:
                start_idx = task.name.find("工单") + 2
                end_idx = task.name.find(" ", start_idx)
                if end_idx == -1:
                    end_idx = len(task.name)
                work_order_id = task.name[start_idx:end_idx]
            except:
                pass
        item = QListWidgetItem(task.name)
        item.setSizeHint(QSize(0, 80))
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(5)
        # 工单ID标签
        id_label = QLabel(f"工单号：{work_order_id}")
        id_label.setStyleSheet("font-size: 15px; color: #00e0ff; font-weight: bold; padding-bottom: 2px;")
        vbox.addWidget(id_label)
        # 进度条
        progress = QProgressBar()
        progress.setFixedHeight(35)
        progress.setMinimumWidth(400)
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 5px;
                text-align: center;
                background: #3c3c3c;
                font-size: 14px;
                padding: 2px;
                color: #FFFFFF;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #00e0ff);
                border-radius: 3px;
            }
        """)
        vbox.addWidget(progress)
        vbox.addStretch()
        widget.setLayout(vbox)
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        def on_progress(val):
            progress.setValue(val)
        def on_finished():
            # 暂时停止自动关闭检测，防止在弹窗时窗口被关闭
            self.auto_close_timer.stop()
            if self.delay_close_timer.isActive():
                self.delay_close_timer.stop()

            progress.setValue(100)
            task._finished = True
            
            if task.errors:
                item.setText(f"{task.name}（完成有错误）")
                id_label.setText(f"工单号：{work_order_id}（完成有错误）")
                id_label.setStyleSheet("font-size: 15px; color: #ff9900; font-weight: bold; padding-bottom: 2px;")
                
                # 构造错误信息
                error_msg = "\n".join(task.errors[:10])
                if len(task.errors) > 10:
                    error_msg += f"\n... (还有 {len(task.errors)-10} 个错误)"
                
                # 显示错误提示
                QMessageBox.warning(self, "任务执行出错", f"任务 {task.name} 执行过程中出现错误：\n{error_msg}")
            else:
                item.setText(f"{task.name}（已完成）")
                # 更新工单ID标签显示为已完成状态
                id_label.setText(f"工单号：{work_order_id}（已完成）")
                id_label.setStyleSheet("font-size: 15px; color: #00ff00; font-weight: bold; padding-bottom: 2px;")
            
            # 恢复自动关闭检测
            self.auto_close_timer.start()
        def on_canceled():
            item.setText(f"{task.name}（已取消）")
            task._finished = True
            # 更新工单ID标签显示为已取消状态
            id_label.setText(f"工单号：{work_order_id}（已取消）")
            id_label.setStyleSheet("font-size: 15px; color: #ff0000; font-weight: bold; padding-bottom: 2px;")
        task.progress_changed.connect(on_progress)
        task.finished.connect(on_finished)
        task.canceled.connect(on_canceled)
        self.tasks.append(task)
        task._finished = False
        task.start()
        
        # 只有在auto_show为True时才自动显示窗口
        if self.auto_show:
            self.show()
            self.raise_()
            self.activateWindow()
            
    
    def closeEvent(self, event):
        """窗口关闭时清理定时器"""
        if self.auto_close_timer.isActive():
            self.auto_close_timer.stop()
        if self.delay_close_timer.isActive():
            self.delay_close_timer.stop()
        super().closeEvent(event)