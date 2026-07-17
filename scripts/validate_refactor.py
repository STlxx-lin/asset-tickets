"""验证脚本：检查 paths.py 导入和 to_local_path 功能。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'e:\2025\pyproj')

import importlib

# 1. 导入 paths 模块
paths = importlib.import_module('src.core.paths')
print('paths.py 导入: OK')

# 2. 检查所有预期符号
expected = [
    'VOLUMES','RAW_ROOT','ART_ROOT','VIDEO_ROOT','CENTER_ROOT',
    'IMG_EXTS','VID_EXTS',
    'PHOTOGRAPHY_UPLOAD','PHOTOGRAPHY_DIST_IMG','PHOTOGRAPHY_DIST_VIDEO',
    'ART_GET_IMG_SRC','ART_GET_IMG_DEST','ART_DIST_OPS','ART_DIST_SALES',
    'EDIT_GET_VIDEO_SRC','EDIT_GET_VIDEO_DEST','EDIT_DIST_OPS','EDIT_DIST_SALES',
    'EDIT_POST_REVIEW_TRANSIT','OPS_GET_SRC','SALES_GET_SRC','to_local_path',
]
missing = [s for s in expected if not hasattr(paths, s)]
if missing:
    print('paths.py 缺少符号:', missing)
else:
    print(f'paths.py 符号检查: {len(expected)} 个全部存在 OK')

# 3. 验证 to_local_path 功能
import platform
from src.core.paths import to_local_path

if platform.system() == 'Windows':
    r1 = to_local_path('/Volumes/01原始素材/test')
    expected1 = r'\\dabadoc\01原始素材\test'
    print('to_local_path Mac->Win:', r1, '->', 'OK' if r1 == expected1 else 'FAIL expected=' + expected1)

    r2 = to_local_path('\\\\dabadoc\\test')
    print('to_local_path Win->Win (pass-through):', r2)

    r3 = to_local_path('')
    print('to_local_path empty string:', repr(r3), '->', 'OK' if r3 == '' else 'FAIL')

print()

# 4. 验证 main_window.py 中 show_process_order_dialog 代理
with open(r'e:\2025\pyproj\src\ui\main_window.py', 'r', encoding='utf-8') as f:
    mw_lines = f.readlines()
print('main_window.py 行数:', len(mw_lines))

# 找到代理方法
proxy_lines = []
in_proxy = False
for i, line in enumerate(mw_lines):
    if 'def show_process_order_dialog' in line:
        in_proxy = True
    if in_proxy:
        proxy_lines.append((i+1, line.rstrip()))
        if len(proxy_lines) > 10:
            break

print()
print('show_process_order_dialog 代理方法:')
for ln, content in proxy_lines:
    print(f'  L{ln}: {content}')

# 5. 验证 BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK 在 video_post_review.py 中
with open(r'e:\2025\pyproj\src\ui\process_dialogs\video_post_review.py', 'r', encoding='utf-8') as f:
    vpr = f.read()
has_bypass = 'BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK' in vpr
print()
print('video_post_review.py 含 BYPASS 开关:', 'OK' if has_bypass else 'MISSING - 需要检查')

# 6. 验证 VideoPreviewWidget 在 video_review 和 video_post_review 中
for fname in ['video_review.py', 'video_post_review.py']:
    fpath = r'e:\2025\pyproj\src\ui\process_dialogs\\' + fname
    with open(fpath, 'r', encoding='utf-8') as f:
        c = f.read()
    has_vp = 'VideoPreviewWidget' in c
    print(f'{fname} 含 VideoPreviewWidget:', 'OK' if has_vp else 'MISSING')
