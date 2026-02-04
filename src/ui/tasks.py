from PySide6.QtCore import QObject, Signal, QThread
import os
import shutil
import time

class FileOperationTask(QThread):
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
        self.update_status_func = update_status_func

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
                time.sleep(0.2)

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
                print(f"处理文件 {fname} 时出错: {e}")
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
                print(f"删除源文件夹时出错: {e}")

        if self.update_status_func:
            self.update_status_func()

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