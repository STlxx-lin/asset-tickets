import logging
import os
import shutil

from PySide6.QtCore import QObject, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CardWidget,
    FluentIcon as FIF,
    ProgressBar as FluentProgressBar,
    PushButton as FluentPushButton,
)

logger = logging.getLogger(__name__)

# 系统垃圾文件（Mac/Windows 自动生成，与业务无关）：
# 移动任务源目录残留时不计入失败，避免"成品已移动成功但任务整体报失败、状态无法推进"
SYSTEM_JUNK_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini', '.localized', '.fseventsd', '.Spotlight-V100'}


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
        self._started_by_manager = False
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

            # 跳过系统垃圾文件（.DS_Store 等）：不移动、不计失败，避免污染目标目录或导致任务误判失败
            if os.path.basename(fname) in SYSTEM_JUNK_FILES:
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
                # 其余文件（新增/隐藏/未在任务列表中的）一律保留，不删除；
                # 系统垃圾文件与残留目录不计入失败：垃圾文件（如 .DS_Store）Mac 会随时
                # 重新生成且不影响业务，此前计入失败会导致成品已移动但任务整体报失败，
                # 状态/日志无法推进（典型：美工后期审批通过后卡在"美工后期审核中"）。
                # 子目录中的业务文件若移动失败，已在前面逐文件循环中记录 errors。
                still_remaining = [
                    f for f in os.listdir(self.src_dir)
                    if f not in removable
                    and f not in SYSTEM_JUNK_FILES
                    and not os.path.isdir(os.path.join(self.src_dir, f))
                ]
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


class TaskCardWidget(CardWidget):
    """单个文件操作任务卡片控件（基于 Fluent CardWidget）"""
    def __init__(self, task_name, parent=None):
        super().__init__(parent)
        self.task_name = task_name
        self.is_finished = False
        self.has_errors = False
        self.setBorderRadius(8)
        self.setStyleSheet("""
            CardWidget#TaskCard {
                background-color: #232732;
                border: 1px solid #303646;
                border-radius: 8px;
            }
        """)
        
        # 提取工单ID
        self.work_order_id = "未知工单"
        if "工单" in task_name:
            try:
                start_idx = task_name.find("工单") + 2
                end_idx = task_name.find(" ", start_idx)
                if end_idx == -1:
                    end_idx = len(task_name)
                self.work_order_id = task_name[start_idx:end_idx]
            except (IndexError, ValueError):
                pass

        self._init_ui()

    def _init_ui(self):
        self.setObjectName("TaskCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 头部：工单号与状态胶囊
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.id_label = QLabel(f"工单: {self.work_order_id}")
        self.id_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #4f8ef7; background: transparent;")
        header_layout.addWidget(self.id_label)
        
        header_layout.addStretch()
        
        self.status_badge = QLabel("传输中")
        self.status_badge.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #38bdf8; "
            "background-color: #0c4a6e; border-radius: 4px; padding: 2px 8px;"
        )
        header_layout.addWidget(self.status_badge)
        layout.addLayout(header_layout)

        # 任务描述标签
        self.desc_label = QLabel(self.task_name)
        self.desc_label.setStyleSheet("font-size: 12px; color: #9ba3b0; background: transparent;")
        self.desc_label.setWordWrap(True)
        self.desc_label.setToolTip(self.task_name)
        layout.addWidget(self.desc_label)

        # Fluent 进度条（带动画）
        self.progress_bar = FluentProgressBar()
        self.progress_bar.setUseAni(True)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

    def set_progress(self, val):
        self.progress_bar.setValue(val)

    def set_finished(self, errors=None):
        self.is_finished = True
        self.progress_bar.setValue(100)
        if errors:
            self.has_errors = True
            self.status_badge.setText("异常")
            self.status_badge.setStyleSheet(
                "font-size: 11px; font-weight: bold; color: #f87171; "
                "background-color: #450a0a; border-radius: 4px; padding: 2px 8px;"
            )
            if hasattr(self.progress_bar, 'setError'):
                self.progress_bar.setError(True)
        else:
            self.status_badge.setText("已完成")
            self.status_badge.setStyleSheet(
                "font-size: 11px; font-weight: bold; color: #4ade80; "
                "background-color: #052e16; border-radius: 4px; padding: 2px 8px;"
            )

    def set_canceled(self):
        self.is_finished = True
        self.status_badge.setText("已取消")
        self.status_badge.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #facc15; "
            "background-color: #422006; border-radius: 4px; padding: 2px 8px;"
        )


class EmbeddedTaskManagerWidget(QGroupBox):
    """嵌入主窗口右侧栏的任务进度监控面板（Fluent 风格）"""
    def __init__(self, parent=None):
        super().__init__("任务进度", parent)
        self.cards = []
        self.tasks = []
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("EmbeddedTaskManager")
        self.setStyleSheet("""
            QGroupBox#EmbeddedTaskManager {
                background-color: #1d2128;
                border: 1px solid #2e3340;
                border-radius: 8px;
                margin-top: 14px;
                font-size: 12px;
                font-weight: bold;
                color: #9ba3b0;
            }
            QGroupBox#EmbeddedTaskManager::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 12px;
            }
        """)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 14, 10, 10)
        main_layout.setSpacing(6)

        # 顶部工具栏：清空按钮
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        self.clear_btn = FluentPushButton(FIF.DELETE, "清空完成项")
        self.clear_btn.setFixedHeight(28)
        self.clear_btn.setEnabled(False)
        self.clear_btn.clicked.connect(self.clear_finished)
        top_bar.addWidget(self.clear_btn)
        main_layout.addLayout(top_bar)

        # 滚动区域
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        if self.scroll_area.viewport():
            self.scroll_area.viewport().setStyleSheet("background: transparent;")
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(8)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 空状态占位标签
        self.placeholder_label = QLabel("暂无进行中的传输任务")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #6b7280; font-size: 12px; padding: 25px 0; background: transparent;")
        self.container_layout.addWidget(self.placeholder_label)

        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area)

    def add_task(self, task: Task):
        self.tasks.append(task)
        self.placeholder_label.hide()

        card = TaskCardWidget(task.name, self.container_widget)
        self.cards.insert(0, card)  # 最新任务排在最上方
        self.container_layout.insertWidget(0, card)

        def on_progress(val):
            card.set_progress(val)

        def on_finished():
            card.set_finished(task.errors)
            self._update_clear_button_state()

        def on_canceled():
            card.set_canceled()
            self._update_clear_button_state()

        task.progress_changed.connect(on_progress)
        task.task_finished.connect(on_finished)
        task.canceled.connect(on_canceled)

        self._update_clear_button_state()

        # 启动任务（若尚未启动）
        if not task.isRunning() and not getattr(task, '_started_by_manager', False):
            task._started_by_manager = True
            task.start()

    def clear_finished(self):
        to_remove = []
        for card in self.cards:
            if card.is_finished:
                to_remove.append(card)

        for card in to_remove:
            self.cards.remove(card)
            self.container_layout.removeWidget(card)
            card.deleteLater()

        if not self.cards:
            self.placeholder_label.show()

        self._update_clear_button_state()

    def _update_clear_button_state(self):
        has_finished = any(card.is_finished for card in self.cards)
        self.clear_btn.setEnabled(has_finished)


class TaskManagerDialog(QDialog):
    def __init__(self, parent=None, auto_show=False):
        super().__init__(parent)
        self.setWindowTitle("任务列表")
        self.resize(620, 460)
        # 任务进度窗口置顶显示（文件移动进度需随时可见，不被主窗口/其他弹窗遮挡）
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #121418;
                color: #e8eaed;
            }
            QLabel {
                background: transparent;
                color: #e8eaed;
            }
        """)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(18, 18, 18, 18)
        self.main_layout.setSpacing(12)
        self.auto_show = auto_show

        # 头部概览卡片
        header_card = CardWidget(self)
        header_card.setStyleSheet("""
            CardWidget {
                background-color: #1a1d24;
                border: 1px solid #282c37;
                border-radius: 10px;
            }
        """)
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        self.title_label = QLabel("后台任务监控中心")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; background: transparent;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.count_badge = QLabel("0 项进行中")
        self.count_badge.setStyleSheet("color: #4f8ef7; font-size: 12px; font-weight: bold; background: #232732; padding: 4px 10px; border-radius: 6px;")
        header_layout.addWidget(self.count_badge)
        self.main_layout.addWidget(header_card)

        # 任务卡片滚动列表
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        if self.scroll_area.viewport():
            self.scroll_area.viewport().setStyleSheet("background: transparent;")
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(8)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.placeholder_label = QLabel("暂无执行中的文件任务")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #6b7280; font-size: 13px; padding: 40px 0; background: transparent;")
        self.container_layout.addWidget(self.placeholder_label)

        self.scroll_area.setWidget(self.container_widget)
        self.main_layout.addWidget(self.scroll_area)

        # 底部按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = FluentPushButton(FIF.CLOSE, "关闭窗口")
        self.close_btn.setFixedHeight(34)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        self.main_layout.addLayout(btn_layout)

        self.tasks = []
        self.task_cards = {}
        self.auto_close_timer = QTimer(self)
        self.auto_close_timer.setInterval(1000)
        self.auto_close_timer.timeout.connect(self.check_tasks)
        self.auto_close_timer.start()

        # 设置为非模态窗口
        self.setModal(False)
        
        # 延迟关闭定时器，让用户看到完成状态
        self.delay_close_timer = QTimer(self)
        self.delay_close_timer.setInterval(3000)
        self.delay_close_timer.timeout.connect(self.delayed_close)
        self.delay_close_timer.setSingleShot(True)

    def check_tasks(self):
        if not self.tasks:
            if not self.delay_close_timer.isActive():
                self.delay_close_timer.start()
            if self.isVisible():
                self.hide()
            return
        
        running_count = 0
        all_finished = True
        for task in self.tasks:
            if not hasattr(task, '_finished'):
                task._finished = False
            if task.isRunning():
                task._finished = False
                all_finished = False
                running_count += 1
            elif not task._finished:
                task._finished = True
            
            if not task._finished:
                all_finished = False

        self.count_badge.setText(f"{running_count} 项进行中" if running_count > 0 else "全部完成")
        
        if all_finished:
            self.auto_close_timer.stop()
            if not self.delay_close_timer.isActive():
                self.delay_close_timer.start()
    
    def delayed_close(self):
        """延迟关闭窗口，让用户看到完成状态"""
        self.close()

    def add_task(self, task):
        if self.delay_close_timer.isActive():
            self.delay_close_timer.stop()
        
        self.placeholder_label.hide()
        card = TaskCardWidget(task.name, self.container_widget)
        self.task_cards[task] = card
        self.container_layout.insertWidget(0, card)

        def on_progress(val):
            card.set_progress(val)

        def on_finished():
            self.auto_close_timer.stop()
            if self.delay_close_timer.isActive():
                self.delay_close_timer.stop()

            card.set_finished(task.errors)
            task._finished = True
            
            if task.errors:
                error_msg = "\n".join(task.errors[:10])
                if len(task.errors) > 10:
                    error_msg += f"\n... (还有 {len(task.errors)-10} 个错误)"
                
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("任务执行出错")
                msg_box.setText(f"任务 {task.name} 执行过程中出现错误：\n{error_msg}")
                
                copy_button = msg_box.addButton("复制完整错误", QMessageBox.ButtonRole.ActionRole)
                msg_box.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
                
                full_error = f"任务 {task.name} 执行过程中出现错误：\n" + "\n".join(task.errors)
                
                def on_copy_clicked():
                    QApplication.clipboard().setText(full_error)
                    copy_button.setText("已复制 ✓")
                    copy_button.setEnabled(False)
                    QTimer.singleShot(800, msg_box.accept)
                
                copy_button.clicked.connect(on_copy_clicked)
                msg_box.exec()
            
            self.auto_close_timer.start()

        def on_canceled():
            card.set_canceled()
            task._finished = True

        task.progress_changed.connect(on_progress)
        task.task_finished.connect(on_finished)
        task.canceled.connect(on_canceled)
        self.tasks.append(task)
        task._finished = False
        if not task.isRunning() and not getattr(task, '_started_by_manager', False):
            task._started_by_manager = True
            task.start()
        
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