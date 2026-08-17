"""
提取脚本：将 main_window.py 中各角色代码块写入 process_dialogs/ 子包。
"""
import io
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 路径基于脚本自身位置解析（不依赖硬编码的绝对路径），保证在任何机器上运行都指向本项目
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
SRC_FILE = os.path.join(PROJECT_ROOT, 'src', 'ui', 'main_window.py')
OUT_DIR = os.path.join(PROJECT_ROOT, 'src', 'ui', 'process_dialogs')

with open(SRC_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

os.makedirs(OUT_DIR, exist_ok=True)


def extract_block(start_1idx: int, end_1idx: int, extra_dedent: int = 12) -> str:
    """
    取 [start_1idx, end_1idx] 行（1-indexed，含两端），去除前 extra_dedent 个空格缩进。
    前两行为 if/elif 条件行，跳过。
    """
    block = lines[start_1idx - 1: end_1idx]          # 角色分支全部行（含 if/elif 行）
    body  = block[1:]                                  # 去掉 if/elif 首行
    result = []
    for line in body:
        if line.startswith(' ' * extra_dedent):
            result.append(line[extra_dedent:])
        elif line.strip() == '':
            result.append('\n')
        else:
            result.append(line)
    return ''.join(result)


HEADER = '''\
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QMessageBox, QHeaderView, QSplitter, QGroupBox, QListWidget,
    QTabWidget, QLineEdit, QComboBox, QFormLayout, QDialogButtonBox,
    QListWidgetItem, QTableWidget, QTableWidgetItem, QFileDialog,
    QProgressBar, QTextBrowser, QTextEdit, QDateEdit, QScrollArea,
    QFrame, QProgressDialog, QCheckBox, QGridLayout, QApplication,
)
from PySide6.QtGui import (
    QStandardItemModel, QStandardItem, QFont, QDesktopServices,
    QPainter, QColor, QPixmap,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QUrl, QDate
from src.core.paths import (
    VOLUMES, IMG_EXTS, VID_EXTS,
    PHOTOGRAPHY_UPLOAD, PHOTOGRAPHY_DIST_IMG, PHOTOGRAPHY_DIST_VIDEO,
    ART_GET_IMG_SRC, ART_GET_IMG_DEST, ART_DIST_OPS, ART_DIST_SALES,
    EDIT_GET_VIDEO_SRC, EDIT_GET_VIDEO_DEST, EDIT_DIST_OPS, EDIT_DIST_SALES,
    EDIT_POST_REVIEW_TRANSIT, OPS_GET_SRC, SALES_GET_SRC, to_local_path,
)
from src.core.database import db_manager
from src.core.config import BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK
from src.ui.video_preview import VideoPreviewWidget
import os
import shutil
import re
'''

# (start_1idx, end_1idx, module_name, func_name, role_label)
SEGMENTS = [
    (3311, 3894, 'photography',       'show_photography_dialog',       '采购/摄影'),
    (3895, 4292, 'video_review',      'show_video_review_dialog',      '视频审核'),
    (4293, 4696, 'video_post_review', 'show_video_post_review_dialog', '视频后期审核'),
    (4697, 5227, 'art',               'show_art_dialog',               '美工'),
    (5228, 5744, 'editing',           'show_editing_dialog',           '剪辑'),
    (5745, 6298, 'ops',               'show_ops_dialog',               '运营'),
    (6299, 6532, 'sales',             'show_sales_dialog',             '销售'),
]

for start, end, module, func, label in SEGMENTS:
    body = extract_block(start, end, extra_dedent=12)

    content_parts = [
        f'"""\n{func} — {label} 工单处理对话框\n',
        '从 main_window.py 重构迁移而来，不改变任何业务逻辑。\n"""\n',
        HEADER,
        '\n\n',
        f'def {func}(parent, order_data, callbacks):\n',
        '    """\n',
        '    处理工单对话框入口。\n\n',
        '    Args:\n',
        '        parent: 父窗口（MainWindow 实例）\n',
        '        order_data: 工单数据字典\n',
        '        callbacks: 回调字典，含 update_status / add_file_task / log_action\n',
        '    """\n',
        "    # ---- 解包 callbacks ----\n",
        "    _update_status = callbacks['update_status']\n",
        "    _add_file_task = callbacks['add_file_task']\n",
        "    _log_action    = callbacks['log_action']\n",
        '\n',
        body,
    ]
    content = ''.join(content_parts)

    # 仅允许写入 OUT_DIR 目录内：resolve 规范化路径并用 commonpath 校验（禁止 ../ 越界访问）
    out_path = (Path(OUT_DIR) / f'{module}.py').resolve()
    if os.path.commonpath([str(out_path), os.path.abspath(OUT_DIR)]) != os.path.abspath(OUT_DIR):
        print(f'[跳过] 模块名越界: {module!r}')
        continue
    out_path.write_text(content, encoding='utf-8')
    print(f'[OK] {module}.py  lines {start}-{end}  ({len(content)} bytes)')

print('\n全部完成。')
