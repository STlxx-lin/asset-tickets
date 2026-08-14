import logging
import os
import shutil

from PySide6.QtCore import QObject, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class TaskStatusUpdater(QObject):
    """任务状态更新器，用于在主线程中更新状态。

    update_status 携带任务执行结果 (ok, errors)：
    - ok: 任务是否全部成功（无错误）
    - errors: 任务执行中的错误列表（失败时非空，供回调决定是否推进状态/发通知）
    """
    update_status = Signal(bool, list)

class Task(QThread):
    """文件操作任务类"""
    progress_changed = Signal(int)  # 进度变化信号
    # 自定义完成信号：改名避免遮蔽 QThread 内置 finished（run() 异常时内置信号触发、
    # 本信号不触发，遮蔽会导致任务完成回调静默丢失）
    task_finished = Signal()  # 完成信号
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

    def _is_valid_copy(self, src_path, dest_path):
        """判断目标是否为源文件的完整等价副本（类型一致且文件大小一致）。

        仅凭存在性判断不可靠：目标可能是中断残留的残缺副本、同名不同内容，
        此时若删除源文件会造成数据永久丢失，因此必须校验等价性。
        """
        try:
            if os.path.isdir(src_path):
                return os.path.isdir(dest_path)
            return os.path.isfile(dest_path) and os.path.getsize(dest_path) == os.path.getsize(src_path)
        except OSError:
            return False

    def run(self):
        """运行任务"""
        total = len(self.files)
        move_successful = True  # 标记移动操作是否成功
        skipped_existing = []  # 目标已存在且为等价副本而被跳过的文件（确认后可安全清理）

        for i, fname in enumerate(self.files):
            if self._is_canceled:
                self.canceled.emit()
                return

            while self._is_paused:
                # 暂停期间也要响应取消，否则任务将永久卡死在暂停循环
                if self._is_canceled:
                    self.canceled.emit()
                    return
                self.msleep(200)  # 使用QThread的msleep而不是time.sleep

            if self.file_filter and not self.file_filter(fname):
                continue

            src_file = os.path.join(self.src_dir, fname)
            dest_file = os.path.join(self.dest_dir, fname)

            # 目标已存在：仅在目标为源文件的等价副本时才跳过（源文件稍后确认后可清理）
            if os.path.exists(dest_file):
                if self.op_type == "move":
                    if self._is_valid_copy(src_file, dest_file):
                        skipped_existing.append(fname)
                        continue
                    # 目标存在但并非等价副本：禁止覆盖与删除源，报错保留，避免数据丢失
                    msg = f"目标文件已存在但与源文件不一致（类型或大小不同），已跳过并保留源文件: {fname}"
                    logger.error(msg)
                    self.errors.append(msg)
                    move_successful = False
                    continue
                # copy 模式：目标已存在视为更新覆盖（copy2 天然覆盖旧文件）
                pass

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
            except Exception as e:
                msg = f"处理文件 {fname} 时出错: {e}"
                logger.error(msg)
                self.errors.append(msg)
                move_successful = False
                continue

            self.progress_changed.emit(int((i + 1) / total * 100))

        # 清理源目录：仅在所有文件均已成功移动/确认目标有等价副本后执行
        if self.op_type == "move" and move_successful and os.path.exists(self.src_dir):
            try:
                # 先删除移动后遗留的空子目录（文件已全部移走，目录本身不在任务列表中）
                for f in list(os.listdir(self.src_dir)):
                    path = os.path.join(self.src_dir, f)
                    if os.path.isdir(path) and not os.listdir(path):
                        try:
                            os.rmdir(path)
                            logger.info(f"已删除空子目录: {f}")
                        except Exception as e:
                            logger.error(f"删除空子目录 {f} 时出错: {e}")
                # 仅删除“目标已存在且等价”被跳过的重复项；删除前再次校验目标副本等价，防止删除不可恢复数据
                removable = []
                for f in list(os.listdir(self.src_dir)):
                    if f in skipped_existing:
                        src_path = os.path.join(self.src_dir, f)
                        dest_path = os.path.join(self.dest_dir, f)
                        if self._is_valid_copy(src_path, dest_path):
                            removable.append(f)
                        else:
                            msg = f"源目录重复文件 {f} 的目标副本校验不通过，已保留源文件"
                            logger.warning(msg)
                            self.errors.append(msg)
                for f in removable:
                    path = os.path.join(self.src_dir, f)
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                        logger.info(f"已删除源目录重复文件: {f}")
                    except Exception as e:
                        msg = f"删除源目录重复文件 {f} 时出错: {e}"
                        logger.error(msg)
                        self.errors.append(msg)
                # 其余文件（新增/隐藏/未在任务列表中的）一律保留，不删除
                still_remaining = [f for f in os.listdir(self.src_dir) if f not in removable]
                if still_remaining:
                    msg = f"源目录仍有 {len(still_remaining)} 个文件未移动，已保留: {', '.join(still_remaining[:5])}"
                    logger.warning(msg)
                    self.errors.append(msg)
                # 目录已空则移除
                if not os.listdir(self.src_dir):
                    os.rmdir(self.src_dir)
                    logger.info(f"已删除空文件夹: {self.src_dir}")
            except Exception as e:
                msg = f"清理源文件夹时出错: {e}"
                logger.error(msg)
                self.errors.append(msg)

        if self.status_updater:
            # 携带任务结果：ok=False 时 errors 非空，回调可据此中止状态推进/通知，避免"文件失败仍报成功"
            self.status_updater.update_status.emit(not self.errors, list(self.errors))

        self.task_finished.emit()

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
            except (IndexError, ValueError):
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
                
                # 显示错误提示（带复制完整错误信息按钮）
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("任务执行出错")
                msg_box.setText(f"任务 {task.name} 执行过程中出现错误：\n{error_msg}")
                
                copy_button = msg_box.addButton("复制完整错误", QMessageBox.ActionRole)
                msg_box.addButton("确定", QMessageBox.AcceptRole)
                
                full_error = f"任务 {task.name} 执行过程中出现错误：\n" + "\n".join(task.errors)
                
                def on_copy_clicked():
                    QApplication.clipboard().setText(full_error)
                    copy_button.setText("已复制 ✓")
                    copy_button.setEnabled(False)
                    QTimer.singleShot(800, msg_box.accept)
                
                copy_button.clicked.connect(on_copy_clicked)
                msg_box.exec()
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
        task.task_finished.connect(on_finished)
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
        """窗口关闭时清理定时器，并取消/等待仍在运行的任务，避免 QThread 泄漏或退出崩溃"""
        if self.auto_close_timer.isActive():
            self.auto_close_timer.stop()
        if self.delay_close_timer.isActive():
            self.delay_close_timer.stop()
        # 取消并等待仍在运行的任务，防止 "QThread: Destroyed while thread is still running" 崩溃
        for task in self.tasks:
            if task.isRunning():
                task.cancel()
        pending = []
        for task in self.tasks:
            if task.isRunning() and not task.wait(5000):
                logger.warning(f"任务 {task.name} 在 5 秒内未退出（可能为网络盘阻塞），转为后台完成")
                pending.append(task)
        if pending:
            # 超时任务仍在运行：隐藏窗口而非销毁（保留线程引用防止 QThread 崩溃），
            # 恢复轮询，任务完成后自动关闭窗口
            self._detached_tasks = getattr(self, '_detached_tasks', []) + pending
            self.hide()
            self.auto_close_timer.start()
            event.ignore()
            return
        super().closeEvent(event)