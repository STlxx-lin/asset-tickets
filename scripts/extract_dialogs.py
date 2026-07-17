"""
提取脚本：将 main_window.py 中各角色代码块写入 process_dialogs/ 子包。
"""
import sys
import io
import os
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC_FILE = r'e:\2025\pyproj\src\ui\main_window.py'
OUT_DIR  = r'e:\2025\pyproj\src\ui\process_dialogs'

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
        f'从 main_window.py 重构迁移而来，不改变任何业务逻辑。\n"""\n',
        HEADER,
        '\n\n',
        f'def {func}(parent, order_data, callbacks):\n',
        f'    """\n',
        f'    处理工单对话框入口。\n\n',
        f'    Args:\n',
        f'        parent: 父窗口（MainWindow 实例）\n',
        f'        order_data: 工单数据字典\n',
        f'        callbacks: 回调字典，含 update_status / add_file_task / log_action\n',
        f'    """\n',
        f"    # ---- 解包 callbacks ----\n",
        f"    _update_status = callbacks['update_status']\n",
        f"    _add_file_task = callbacks['add_file_task']\n",
        f"    _log_action    = callbacks['log_action']\n",
        f'\n',
        body,
    ]
    content = ''.join(content_parts)

    out_path = os.path.join(OUT_DIR, f'{module}.py')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[OK] {module}.py  lines {start}-{end}  ({len(content)} bytes)')

print('\n全部完成。')
