"""
clean_video_source_dialog.py — 02视频部工单源文件扫描与清理工具

功能：
1. 扫描 \\dabadoc\\02图像部\\02视频部 下各产线各工单的「源文件」目录；
2. 精准过滤：跳过并保护所有 .drp 达芬奇项目工程文件，仅清理大视频素材等非 .drp 文件；
3. 支持单项清理与一键批量清理，带安全确认和空间释放统计；
4. 自动清理因删除变空的子文件夹并记录管理员操作日志。
"""
import csv
import datetime
import logging
import os
import shutil
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.database import db_manager
from src.core.paths import PHOTOGRAPHERS, RAW_ROOT, VIDEO_ROOT, to_local_path

logger = logging.getLogger(__name__)

# 垃圾文件集合（核对原始素材时排除）
GARBAGE_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini', '.thumbnails', '.localized', '.fseventsd', '.Spotlight-V100'}


def _count_valid_files(dir_path: str) -> tuple[int, int]:
    """统计目录下的有效文件数（排除系统垃圾文件）和总字节大小"""
    cnt = 0
    total_sz = 0
    try:
        for r, _d, files in os.walk(dir_path):
            for f in files:
                if f not in GARBAGE_FILES and not f.startswith('._') and not f.endswith('.tmp'):
                    cnt += 1
                    try:
                        total_sz += os.path.getsize(os.path.join(r, f))
                    except OSError:
                        pass
    except OSError:
        pass
    return cnt, total_sz


def _format_size(size_bytes: int) -> str:
    """格式化字节大小为易读字符串"""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 ** 3):.2f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes > 0:
        return f"{size_bytes} B"
    return "0 B"


def find_matching_raw_dir(
    raw_base_dir: str | None, photographers: list, dept: str, folder_name: str
) -> tuple[bool, str, str, int, str]:
    """
    在 01原始素材 中多级匹配对应工单的有效素材文件夹。
    判定标准：必须匹配文件夹名称/工单ID，且目录下确实存在有效素材文件（排除系统垃圾文件）。
    返回: (has_backup, matched_photographer, matched_raw_path, raw_file_count, status_desc)
    """
    if not raw_base_dir or not os.path.exists(raw_base_dir):
        return False, "", "", 0, "01原始素材盘不可达"

    target_name_clean = folder_name.strip().lower()
    # 提取工单ID（开头纯数字部分，如 "2608171428"）
    order_id = folder_name.strip().split()[0] if folder_name.strip() else ""

    empty_candidate = None  # 记录找到的空文件夹候选

    for pg in photographers:
        pg_dir = os.path.join(raw_base_dir, pg)
        if not os.path.exists(pg_dir) or not os.path.isdir(pg_dir):
            continue

        # 优先检查对应部门，其次检查该摄影师下的其他部门
        dept_dirs_to_check = []
        target_dept_dir = os.path.join(pg_dir, dept)
        if os.path.exists(target_dept_dir):
            dept_dirs_to_check.append((dept, target_dept_dir))

        # 追加其他部门目录作为备选
        try:
            for other_d in os.listdir(pg_dir):
                if other_d != dept:
                    p = os.path.join(pg_dir, other_d)
                    if os.path.isdir(p):
                        dept_dirs_to_check.append((other_d, p))
        except OSError:
            pass

        for d_name, d_path in dept_dirs_to_check:
            try:
                sub_folders = os.listdir(d_path)
            except OSError:
                continue

            for sub_f in sub_folders:
                cand_path = os.path.join(d_path, sub_f)
                if not os.path.isdir(cand_path):
                    continue

                sub_f_clean = sub_f.strip().lower()
                # 匹配条件：文件夹名称完全相同、去除空格后相同、或工单ID相同
                is_match = False
                if sub_f_clean == target_name_clean:
                    is_match = True
                elif order_id and len(order_id) >= 6 and sub_f.startswith(order_id):
                    is_match = True

                if is_match:
                    cnt, sz = _count_valid_files(cand_path)
                    if cnt > 0:
                        dept_note = f" · {d_name}" if d_name != dept else ""
                        return True, pg, cand_path, cnt, f"存在 ({pg}{dept_note} · {cnt}个文件)"
                    elif empty_candidate is None:
                        empty_candidate = (pg, cand_path, 0, f"原始目录为空 ({pg} · 0个文件)")

    if empty_candidate:
        return False, empty_candidate[0], empty_candidate[1], empty_candidate[2], empty_candidate[3]

    return False, "", "", 0, "01原始素材无对应文件夹"


class _ScanVideoSourcesWorker(QThread):
    """后台扫描 02视频部 下所有「源文件」文件夹并与 01原始素材 核对"""

    found_item = Signal(dict)
    finished_scan = Signal(list)

    def __init__(self, target_dept: str = ""):
        super().__init__()
        self.target_dept = target_dept

    def run(self):
        results = []
        root_local = to_local_path(VIDEO_ROOT)
        raw_root_local = to_local_path(RAW_ROOT)

        if not root_local or not os.path.exists(root_local):
            self.finished_scan.emit(results)
            return

        # 01原始素材根路径: \\dabadoc\01原始素材\01原始素材
        raw_base_dir = os.path.join(raw_root_local, '01原始素材') if raw_root_local else None

        # 获取所有摄影师目录列表
        photographers = list(PHOTOGRAPHERS)
        if raw_base_dir and os.path.exists(raw_base_dir):
            try:
                for d in os.listdir(raw_base_dir):
                    if os.path.isdir(os.path.join(raw_base_dir, d)) and d not in photographers:
                        photographers.append(d)
            except OSError:
                pass

        try:
            # 第一层：产线目录
            try:
                dept_dirs = [d for d in os.listdir(root_local) if os.path.isdir(os.path.join(root_local, d))]
            except OSError:
                dept_dirs = []

            for dept in sorted(dept_dirs):
                if self.isInterruptionRequested():
                    return
                if self.target_dept and dept != self.target_dept:
                    continue

                dept_path = os.path.join(root_local, dept)

                # 搜索产线目录下的所有「源文件」文件夹
                # 可能在: dept/工单/源文件 或 dept/00待处理/工单/源文件 等
                for root, dirs, _files in os.walk(dept_path):
                    if self.isInterruptionRequested():
                        return
                    if '源文件' in dirs:
                        src_dir = os.path.join(root, '源文件')
                        # 工单主文件夹名称（例如 "2608171428 DBTT-J24x40-150 DBTT-J24x40-150"）
                        folder_name = os.path.basename(root)
                        rel = os.path.relpath(root, dept_path)
                        order_folder = rel.replace('\\', '/')

                        # 1. 分析该源文件目录中的非.drp文件和.drp文件
                        drp_cnt = 0
                        non_drp_files = []
                        total_bytes = 0

                        for s_root, _s_dirs, s_files in os.walk(src_dir):
                            for sf in s_files:
                                full_p = os.path.join(s_root, sf)
                                if sf.lower().endswith('.drp'):
                                    drp_cnt += 1
                                else:
                                    non_drp_files.append(full_p)
                                    try:
                                        total_bytes += os.path.getsize(full_p)
                                    except OSError:
                                        pass

                        # 2. 与 01原始素材 核对文件夹名称及有效文件数
                        (
                            has_raw_backup,
                            matched_photographer,
                            matched_raw_path,
                            raw_file_count,
                            raw_status_desc,
                        ) = find_matching_raw_dir(raw_base_dir, photographers, dept, folder_name)

                        item_data = {
                            'dept': dept,
                            'folder_name': folder_name,
                            'order_folder': order_folder,
                            'path': src_dir,
                            'non_drp_count': len(non_drp_files),
                            'drp_count': drp_cnt,
                            'size_bytes': total_bytes,
                            'size_str': _format_size(total_bytes),
                            'non_drp_files': non_drp_files,
                            'has_raw_backup': has_raw_backup,
                            'raw_photographer': matched_photographer,
                            'raw_path': matched_raw_path,
                            'raw_file_count': raw_file_count,
                            'raw_status_desc': raw_status_desc,
                        }
                        results.append(item_data)
                        self.found_item.emit(item_data)

        except Exception as e:
            logger.error(f"扫描视频源文件出错: {e}")

        self.finished_scan.emit(results)


def show_clean_video_source_dialog(parent, preselect_order_id: str = ""):
    """显示 02视频部 源文件扫描清理管理对话框。"""
    dialog = QDialog(parent)
    dialog.setWindowTitle("02视频部 - 源文件扫描与一键清理")
    dialog.setMinimumSize(1200, 700)
    dialog.resize(1280, 740)
    dialog.setStyleSheet("""
        QDialog {
            background-color: #23272e;
            color: #ffffff;
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            font-size: 13px;
        }
        QLabel {
            color: #e8eaed;
        }
        QTableWidget {
            background-color: #2a2e37;
            border: 1px solid #3a3f4b;
            border-radius: 6px;
            color: #e8eaed;
            gridline-color: #3a3f4b;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QHeaderView::section {
            background-color: #323742;
            color: #9ba3b0;
            border: none;
            border-right: 1px solid #3a3f4b;
            padding: 6px;
            font-weight: bold;
        }
        QComboBox {
            background-color: #2a2e37;
            border: 1px solid #3a3f4b;
            border-radius: 4px;
            color: #e8eaed;
            padding: 4px 10px;
            min-height: 24px;
        }
        QLineEdit {
            background-color: #2a2e37;
            border: 1px solid #3a3f4b;
            border-radius: 4px;
            color: #e8eaed;
            padding: 4px 10px;
            min-height: 24px;
            font-size: 13px;
        }
        QLineEdit:focus {
            border: 1px solid #4f8ef7;
            background-color: #323742;
        }
        QPushButton {
            background-color: #4f8ef7;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 8px 18px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #6ba3ff;
        }
        QPushButton[type="cancel"] {
            background-color: #3a3f4b;
        }
        QPushButton[type="cancel"]:hover {
            background-color: #4a5060;
        }
    """)

    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(12)

    # 顶部标题与说明
    top_layout = QHBoxLayout()
    top_layout.setSpacing(15)
    title_box = QVBoxLayout()
    title_label = QLabel("02视频部 — 源文件扫描与一键清理")
    title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
    desc_label = QLabel(
        "安全策略：自动核对「01原始素材」对应摄影师目录；跳过并保留全部 .drp 达芬奇工程文件；无原始备份的目录自动高亮标记并防误删。"
    )
    desc_label.setStyleSheet("color: #9ba3b0; font-size: 12px;")
    title_box.addWidget(title_label)
    title_box.addWidget(desc_label)
    top_layout.addLayout(title_box)
    top_layout.addStretch()

    # 搜索框
    search_input = QLineEdit()
    search_input.setPlaceholderText("🔍 输入工单名称 / ID 搜索...")
    search_input.setClearButtonEnabled(True)
    search_input.setMinimumWidth(260)
    top_layout.addWidget(search_input)

    # 产线筛选
    dept_label = QLabel("产线：")
    dept_combo = QComboBox()
    dept_combo.addItem("全部产线")
    dept_combo.setMinimumWidth(110)
    top_layout.addWidget(dept_label)
    top_layout.addWidget(dept_combo)

    main_layout.addLayout(top_layout)

    # 表格 (9列)
    table = QTableWidget()
    table.setColumnCount(9)
    table.setHorizontalHeaderLabels([
        "选择", "产线", "工单目录", "01原始素材备份核对", "待清理文件(非.drp)", "待释放空间", "保留.drp", "源文件完整路径", "操作"
    ])
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)

    table.setColumnWidth(0, 50)
    table.setColumnWidth(8, 160)
    table.verticalHeader().setDefaultSectionSize(44)
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    main_layout.addWidget(table, 1)

    # 进度条
    progress_bar = QProgressBar()
    progress_bar.setStyleSheet("""
        QProgressBar {
            background-color: #2a2e37;
            border: 1px solid #3a3f4b;
            border-radius: 4px;
            text-align: center;
            color: #ffffff;
            height: 16px;
        }
        QProgressBar::chunk {
            background-color: #4f8ef7;
            border-radius: 3px;
        }
    """)
    progress_bar.setVisible(False)
    main_layout.addWidget(progress_bar)

    # 底部控制栏
    bottom_layout = QHBoxLayout()

    select_all_cb = QCheckBox("全选(仅已备份)")
    select_all_cb.setStyleSheet("color: #e8eaed; font-size: 13px;")
    bottom_layout.addWidget(select_all_cb)

    only_dirty_cb = QCheckBox("仅显示有待清理文件的目录")
    only_dirty_cb.setStyleSheet("color: #9ba3b0; font-size: 13px;")
    only_dirty_cb.setChecked(True)
    bottom_layout.addWidget(only_dirty_cb)

    only_no_backup_cb = QCheckBox("仅显示无原始备份")
    only_no_backup_cb.setStyleSheet("color: #ff9800; font-size: 13px;")
    only_no_backup_cb.setChecked(False)
    bottom_layout.addWidget(only_no_backup_cb)

    summary_label = QLabel("正在准备扫描…")
    summary_label.setStyleSheet("color: #9ba3b0; font-size: 13px;")
    bottom_layout.addWidget(summary_label)

    bottom_layout.addStretch()

    export_no_backup_btn = QPushButton("📄 导出无备份列表")
    export_no_backup_btn.setStyleSheet("background-color: #e67e22; color: white; border: none; border-radius: 6px; padding: 9px 18px; font-weight: bold;")
    export_no_backup_btn.setToolTip("将所有在 01原始素材 中缺少备份文件夹的工单信息导出为 CSV/Excel 表格")

    rescan_btn = QPushButton("🔄 重新扫描")
    rescan_btn.setStyleSheet("background-color: #3a3f4b; color: white; border: none; border-radius: 6px; padding: 9px 20px; font-weight: bold;")
    
    clean_batch_btn = QPushButton("🧹 一键清理选中项目 (保留.drp)")
    clean_batch_btn.setStyleSheet("background-color: #d9534f; color: white; border: none; border-radius: 6px; padding: 9px 22px; font-size: 14px; font-weight: bold;")

    close_btn = QPushButton("关闭")
    close_btn.setProperty("type", "cancel")
    close_btn.setStyleSheet("background-color: #3a3f4b; color: white; border: none; border-radius: 6px; padding: 9px 20px; font-weight: bold;")

    bottom_layout.addWidget(export_no_backup_btn)
    bottom_layout.addWidget(rescan_btn)
    bottom_layout.addWidget(clean_batch_btn)
    bottom_layout.addWidget(close_btn)
    main_layout.addLayout(bottom_layout)

    # 数据管理
    all_scan_items = []
    worker = None

    def update_summary():
        total_items = len(all_scan_items)
        need_clean = sum(1 for it in all_scan_items if it['non_drp_count'] > 0)
        total_bytes = sum(it['size_bytes'] for it in all_scan_items)
        total_drp = sum(it['drp_count'] for it in all_scan_items)
        no_backup = sum(1 for it in all_scan_items if not it['has_raw_backup'])
        
        warn_part = f" · <span style='color: #ff5252; font-weight: bold;'>⚠️ 无原始备份 {no_backup} 处</span>" if no_backup > 0 else " · <span style='color: #4caf50;'>已全部核对归档</span>"
        summary_label.setText(
            f"共扫描 {total_items} 处源文件 · 待清理 {need_clean} 处 · "
            f"预计释放 {_format_size(total_bytes)} · 保留 {total_drp} 个 .drp"
            f"{warn_part}"
        )

    def refresh_table_view():
        table.setRowCount(0)
        only_dirty = only_dirty_cb.isChecked()
        only_no_backup = only_no_backup_cb.isChecked()
        sel_dept = dept_combo.currentText()
        search_kw = search_input.text().strip().lower()

        filtered = []
        for it in all_scan_items:
            if sel_dept != "全部产线" and it['dept'] != sel_dept:
                continue
            if only_dirty and it['non_drp_count'] == 0:
                continue
            if only_no_backup and it['has_raw_backup']:
                continue
            if search_kw:
                # 仅匹配工单名称/文件夹（不匹配产线、完整路径等）
                target_order_name = f"{it.get('order_folder', '')} {it.get('folder_name', '')}".lower()
                if search_kw not in target_order_name:
                    continue
            filtered.append(it)

        table.setRowCount(len(filtered))
        for row, it in enumerate(filtered):
            # 复选框
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb = QCheckBox()
            # 只有在有待清理文件且有原始备份时才默认勾选，防止误删无备份项
            cb.setChecked(it['non_drp_count'] > 0 and it['has_raw_backup'])
            cb.setEnabled(it['non_drp_count'] > 0)
            cb.setProperty("item_data", it)
            chk_layout.addWidget(cb)
            table.setCellWidget(row, 0, chk_widget)

            # 文本单元格
            dept_item = QTableWidgetItem(it['dept'])
            order_item = QTableWidgetItem(it['order_folder'])

            # 01原始素材核对结果
            if it['has_raw_backup']:
                raw_item = QTableWidgetItem(f"✅ 存在 ({it['raw_photographer']} · {it['raw_file_count']}个文件)")
                raw_item.setForeground(QColor(0, 200, 180))
                raw_item.setToolTip(f"原始素材路径：\n{it['raw_path']}\n有效文件数：{it['raw_file_count']} 个\n\n（双击该单元格可在资源管理器中打开）")
            elif it.get('raw_status_desc', '').startswith('原始目录为空'):
                raw_item = QTableWidgetItem(f"⚠️ 原始文件夹为空 (0文件)")
                raw_item.setForeground(QColor(255, 140, 0))
                raw_item.setToolTip(f"⚠️ 警告：目录存在但没有任何有效素材文件！\n路径：{it['raw_path']}\n\n（双击该单元格可在资源管理器中打开）")
            else:
                raw_item = QTableWidgetItem("⚠️ 01原始无对应文件夹")
                raw_item.setForeground(QColor(255, 85, 85))
                raw_item.setToolTip("⚠️ 警告：在 \\\\dabadoc\\01原始素材\\01原始素材 下任何摄影师目录均未找到对应工单文件夹！清理将导致源文件彻底丢失！")

            count_item = QTableWidgetItem(str(it['non_drp_count']))
            size_item = QTableWidgetItem(it['size_str'])
            drp_item = QTableWidgetItem(str(it['drp_count']))
            path_item = QTableWidgetItem(it['path'])

            # 颜色标记
            if it['non_drp_count'] > 0:
                count_item.setForeground(QColor(255, 140, 0))
                size_item.setForeground(QColor(255, 140, 0))
            else:
                count_item.setForeground(QColor(40, 167, 69))
                size_item.setForeground(QColor(150, 155, 165))

            if it['drp_count'] > 0:
                drp_item.setForeground(QColor(0, 200, 180))

            items_to_put = [dept_item, order_item, raw_item, count_item, size_item, drp_item, path_item]
            for col, item in enumerate(items_to_put, start=1):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if not it['has_raw_backup']:
                    item.setBackground(QColor(55, 30, 30))
                table.setItem(row, col, item)

            # 操作按钮（打开 / 清理）
            op_widget = QWidget()
            op_layout = QHBoxLayout(op_widget)
            op_layout.setContentsMargins(4, 2, 4, 2)
            op_layout.setSpacing(6)
            op_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            open_btn = QPushButton("打开")
            open_btn.setStyleSheet("background-color: #4f8ef7; color: white; border: none; border-radius: 4px; padding: 5px 12px; font-size: 12px; font-weight: bold;")
            open_btn.clicked.connect(lambda _, p=it['path']: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
            op_layout.addWidget(open_btn)

            clean_btn = QPushButton("清理")
            clean_btn.setStyleSheet("background-color: #dc3545; color: white; border: none; border-radius: 4px; padding: 5px 12px; font-size: 12px; font-weight: bold;")
            clean_btn.setEnabled(it['non_drp_count'] > 0)
            clean_btn.clicked.connect(lambda _, item_info=it: clean_single_item(item_info))
            op_layout.addWidget(clean_btn)

            table.setCellWidget(row, 8, op_widget)

        update_summary()

    def on_item_found(item_data):
        all_scan_items.append(item_data)
        # 更新产线下拉
        if dept_combo.findText(item_data['dept']) == -1:
            dept_combo.addItem(item_data['dept'])
        update_summary()

    def on_scan_done(results):
        dialog.unsetCursor()
        rescan_btn.setEnabled(True)
        clean_batch_btn.setEnabled(True)
        refresh_table_view()

    def start_scan():
        nonlocal worker
        if worker is not None and worker.isRunning():
            return
        dialog.setCursor(Qt.CursorShape.WaitCursor)
        rescan_btn.setEnabled(False)
        clean_batch_btn.setEnabled(False)
        all_scan_items.clear()
        table.setRowCount(0)
        summary_label.setText("正在全盘扫描 02视频部 源文件目录并核对 01原始素材…")

        worker = _ScanVideoSourcesWorker()
        worker.found_item.connect(on_item_found)
        worker.finished_scan.connect(on_scan_done)
        worker.start()

    def clean_target_files(files_to_del, base_dir: str) -> tuple[int, list]:
        """删除指定文件列表，并向上清理变空的子目录"""
        deleted_count = 0
        errors = []
        for fp in files_to_del:
            try:
                if os.path.exists(fp):
                    os.remove(fp)
                    deleted_count += 1
            except Exception as e:
                errors.append(f"{os.path.basename(fp)}: {e}")

        # 自底向上清理空子文件夹
        if os.path.exists(base_dir):
            for root, _dirs, _files in os.walk(base_dir, topdown=False):
                if root != base_dir:
                    try:
                        if not os.listdir(root):
                            os.rmdir(root)
                    except OSError:
                        pass

        return deleted_count, errors

    def clean_single_item(it: dict):
        """单项清理"""
        if not it['non_drp_files']:
            QMessageBox.information(dialog, "提示", "当前目录没有需要清理的非 .drp 文件。")
            return

        warn_extra = ""
        if not it['has_raw_backup']:
            warn_extra = "\n\n⚠️⚠️【高风险警告】在「01原始素材」未找到对应的备份文件夹！\n本次删除后该工单的源视频素材将永久丢失，无法恢复！"

        ret = QMessageBox.warning(
            dialog,
            "确认清理",
            f"确定要清理该工单的源文件吗？\n\n"
            f"产线：{it['dept']}\n"
            f"工单：{it['order_folder']}\n"
            f"路径：{it['path']}\n"
            f"原始素材归档：{'已归档 (' + it['raw_photographer'] + ')' if it['has_raw_backup'] else '❌ 无备份'}\n\n"
            f"• 将删除：{it['non_drp_count']} 个素材文件（共 {it['size_str']}）\n"
            f"• 将保留：{it['drp_count']} 个 .drp 工程文件（跳过不删除）"
            f"{warn_extra}\n\n"
            f"删除后不可恢复，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        del_cnt, errs = clean_target_files(it['non_drp_files'], it['path'])

        # 记录日志
        try:
            db_manager.add_log(
                user='管理员',
                action_type="清理视频源文件",
                details=f"产线={it['dept']}, 目录={it['order_folder']}, 清理了 {del_cnt} 个文件({it['size_str']}), 保留 {it['drp_count']} 个.drp文件, 原始素材归档={it['has_raw_backup']}"
            )
        except Exception:
            pass

        if errs:
            QMessageBox.warning(dialog, "清理提示", f"已清理 {del_cnt} 个文件，以下文件失败：\n" + "\n".join(errs[:5]))
        else:
            QMessageBox.information(dialog, "清理成功", f"清理完成！\n已删除 {del_cnt} 个素材文件，完整保留 {it['drp_count']} 个 .drp 工程文件。")

        # 重新扫描
        start_scan()

    def on_batch_clean():
        """批量清理选中项目"""
        selected_items = []
        for r in range(table.rowCount()):
            chk_widget = table.cellWidget(r, 0)
            if chk_widget:
                cb = chk_widget.findChild(QCheckBox)
                if cb and cb.isChecked() and cb.isEnabled():
                    item_data = cb.property("item_data")
                    if item_data and item_data['non_drp_count'] > 0:
                        selected_items.append(item_data)

        if not selected_items:
            QMessageBox.information(dialog, "提示", "请先勾选需要清理的目录。")
            return

        total_files = sum(it['non_drp_count'] for it in selected_items)
        total_bytes = sum(it['size_bytes'] for it in selected_items)
        total_drps = sum(it['drp_count'] for it in selected_items)
        no_backup_selected = [it for it in selected_items if not it['has_raw_backup']]

        warn_extra = ""
        if no_backup_selected:
            warn_extra = (
                f"\n\n⚠️⚠️【高风险警告】选中的项目中包含 {len(no_backup_selected)} 个在「01原始素材」无备份的工单：\n"
                + "\n".join(f"• [{it['dept']}] {it['order_folder']}" for it in no_backup_selected[:5])
            )
            if len(no_backup_selected) > 5:
                warn_extra += f"\n... 等共 {len(no_backup_selected)} 个"
            warn_extra += "\n\n这些工单的素材删除后将永久丢失！"

        ret = QMessageBox.warning(
            dialog,
            "批量清理确认",
            f"确定要批量清理勾选的 {len(selected_items)} 个工单源文件目录吗？\n\n"
            f"• 将删除：{total_files} 个文件（预计释放 {_format_size(total_bytes)}）\n"
            f"• 将跳过并保留：{total_drps} 个 .drp 工程文件"
            f"{warn_extra}\n\n"
            f"⚠️ 删除后不可恢复，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        progress_bar.setVisible(True)
        progress_bar.setRange(0, len(selected_items))
        progress_bar.setValue(0)

        total_deleted = 0
        all_errs = []

        for idx, it in enumerate(selected_items):
            del_cnt, errs = clean_target_files(it['non_drp_files'], it['path'])
            total_deleted += del_cnt
            if errs:
                all_errs.extend(errs)
            progress_bar.setValue(idx + 1)

        progress_bar.setVisible(False)

        # 记录日志
        try:
            db_manager.add_log(
                user='管理员',
                action_type="批量清理视频源文件",
                details=f"批量清理了 {len(selected_items)} 个目录，删除 {total_deleted} 个文件({_format_size(total_bytes)})，保留 {total_drps} 个.drp, 其中无原始备份={len(no_backup_selected)}个"
            )
        except Exception:
            pass

        if all_errs:
            QMessageBox.warning(
                dialog,
                "批量清理完成",
                f"已删除 {total_deleted} 个文件，保留 {total_drps} 个 .drp 文件。\n"
                f"部分文件删除失败({len(all_errs)}个)：\n" + "\n".join(all_errs[:5])
            )
        else:
            QMessageBox.information(
                dialog,
                "批量清理完成",
                f"批量清理成功！\n\n• 已成功删除：{total_deleted} 个文件（释放约 {_format_size(total_bytes)}）\n• 已完整保留：{total_drps} 个 .drp 工程文件"
            )

        start_scan()

    def on_select_all_toggled(checked):
        for r in range(table.rowCount()):
            chk_widget = table.cellWidget(r, 0)
            if chk_widget:
                cb = chk_widget.findChild(QCheckBox)
                if cb and cb.isEnabled():
                    item_data = cb.property("item_data")
                    # 勾选时默认仅勾选有原始备份的，除非是取消勾选
                    if checked:
                        cb.setChecked(item_data and item_data.get('has_raw_backup', False))
                    else:
                        cb.setChecked(False)

    # 双击单元格打开路径
    def on_cell_double_clicked(row, column):
        if row < table.rowCount():
            chk_widget = table.cellWidget(row, 0)
            if chk_widget:
                cb = chk_widget.findChild(QCheckBox)
                if cb:
                    it = cb.property("item_data")
                    if it:
                        # 双击第3列（原始素材备份列）：打开 01原始素材 路径
                        if column == 3 and it['has_raw_backup'] and it['raw_path']:
                            if os.path.exists(it['raw_path']):
                                QDesktopServices.openUrl(QUrl.fromLocalFile(it['raw_path']))
                        # 双击第7列（源文件路径）：打开视频部源文件路径
                        elif column == 7 and it['path']:
                            if os.path.exists(it['path']):
                                QDesktopServices.openUrl(QUrl.fromLocalFile(it['path']))

    def on_export_no_backup():
        """导出在 01原始素材 中无对应文件夹的工单信息列表为 CSV/TXT"""
        no_backup_items = [it for it in all_scan_items if not it['has_raw_backup']]
        if not no_backup_items:
            QMessageBox.information(dialog, "提示", "当前扫描结果中没有无原始备份的工单，无需导出。")
            return

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"02视频部_无原始素材备份列表_{now_str}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            dialog,
            "导出无原始备份工单列表",
            default_filename,
            "CSV 表格文件 (*.csv);;文本文件 (*.txt)"
        )
        if not file_path:
            return

        try:
            # 导出文件：保存对话框返回的用户选定路径，规范化后写入（resolve 解析相对/.. 成分）
            out_path = Path(file_path).resolve()
            is_csv = out_path.name.lower().endswith('.csv')
            if is_csv:
                with out_path.open('w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    # 写入表头
                    writer.writerow([
                        "产线", "工单目录", "01原始素材核对结果", "待清理文件数(非.drp)", "占用空间", "保留.drp数", "源文件完整路径"
                    ])
                    for it in no_backup_items:
                        writer.writerow([
                            it['dept'],
                            it['order_folder'],
                            it.get('raw_status_desc', '01原始素材无对应文件夹'),
                            it['non_drp_count'],
                            it['size_str'],
                            it['drp_count'],
                            it['path'],
                        ])
            else:
                lines = [f"# 02视频部 无原始素材备份工单列表\n"]
                lines.append(f"# 导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                lines.append(f"# 共计: {len(no_backup_items)} 条记录\n\n")
                for idx, it in enumerate(no_backup_items, 1):
                    lines.append(f"{idx}. [{it['dept']}] {it['order_folder']}\n")
                    lines.append(f"   路径: {it['path']}\n")
                    lines.append(f"   待清理文件: {it['non_drp_count']} 个 ({it['size_str']}), 保留.drp: {it['drp_count']} 个\n\n")
                out_path.write_text(''.join(lines), encoding='utf-8')

            ret = QMessageBox.information(
                dialog,
                "导出成功",
                f"已成功导出 {len(no_backup_items)} 条无原始备份记录至：\n{file_path}\n\n是否立即打开所在文件夹？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if ret == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(file_path)))
        except Exception as e:
            logger.error(f"导出无备份列表失败: {e}")
            QMessageBox.critical(dialog, "导出失败", f"导出文件时发生错误：\n{e}")

    table.cellDoubleClicked.connect(on_cell_double_clicked)
    select_all_cb.toggled.connect(on_select_all_toggled)
    only_dirty_cb.toggled.connect(lambda _: refresh_table_view())
    only_no_backup_cb.toggled.connect(lambda _: refresh_table_view())
    dept_combo.currentIndexChanged.connect(lambda _: refresh_table_view())
    search_input.textChanged.connect(lambda _: refresh_table_view())
    export_no_backup_btn.clicked.connect(on_export_no_backup)
    rescan_btn.clicked.connect(start_scan)
    clean_batch_btn.clicked.connect(on_batch_clean)
    close_btn.clicked.connect(dialog.reject)

    def stop_worker():
        nonlocal worker
        if worker is not None and worker.isRunning():
            worker.requestInterruption()
            worker.wait(2000)

    dialog.finished.connect(lambda _: stop_worker())

    # 开始扫描
    start_scan()
    dialog.exec()

