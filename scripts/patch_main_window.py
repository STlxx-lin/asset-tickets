"""
patch_main_window.py — 一次性完成 main_window.py 的三处修改：
  1. 删除 L43-L77   路径常量定义 → 替换为 from src.core.paths import ...
  2. 删除 L79-L135  两份 to_local_path 函数定义
  3. 替换 L3275-L6532 show_process_order_dialog 方法体 → 3 行调度代理
"""
import sys
import io
import shutil
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SRC = r'e:\2025\pyproj\src\ui\main_window.py'
BAK = r'e:\2025\pyproj\src\ui\main_window.py.bak'

# 先备份
shutil.copy2(SRC, BAK)
print(f'已备份至 {BAK}')

with open(SRC, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f'原始行数: {len(lines)}')

# ── 定义所有区块（1-indexed，含两端）──────────────────────────────────────
# 区块 A: 路径常量 L43-L77 → 替换为 paths 导入
# 区块 B: 两份 to_local_path L79-L135 → 删除（保留 L78 空行以免注释粘连）
# 区块 C: show_process_order_dialog 方法体 L3275-L6532 → 替换为代理

A_START, A_END = 43, 77   # 路径常量（含 #注释行 L43）
B_START, B_END = 79, 135  # 两份 to_local_path
C_START, C_END = 3275, 6532  # 整个 show_process_order_dialog

PATHS_IMPORT = (
    "# 路径常量与工具函数 — 统一由 src.core.paths 提供\n"
    "from src.core.paths import (\n"
    "    VOLUMES, RAW_ROOT, ART_ROOT, VIDEO_ROOT, CENTER_ROOT,\n"
    "    IMG_EXTS, VID_EXTS,\n"
    "    PHOTOGRAPHY_UPLOAD, PHOTOGRAPHY_DIST_IMG, PHOTOGRAPHY_DIST_VIDEO,\n"
    "    ART_GET_IMG_SRC, ART_GET_IMG_DEST, ART_DIST_OPS, ART_DIST_SALES,\n"
    "    EDIT_GET_VIDEO_SRC, EDIT_GET_VIDEO_DEST, EDIT_DIST_OPS, EDIT_DIST_SALES,\n"
    "    EDIT_POST_REVIEW_TRANSIT, OPS_GET_SRC, SALES_GET_SRC, to_local_path,\n"
    ")\n"
)

PROXY_METHOD = (
    "    def show_process_order_dialog(self, order_data):\n"
    "        \"\"\"将工单处理对话框路由到 process_dialogs 包中对应的角色模块。\"\"\"\n"
    "        from src.ui.process_dialogs import show_process_order_dialog as _dispatch\n"
    "        callbacks = {\n"
    "            'update_status': self.update_work_order_status_and_ui,\n"
    "            'add_file_task': self.add_file_task,\n"
    "            'log_action':    self.log_action,\n"
    "        }\n"
    "        _dispatch(self, order_data, callbacks)\n"
)

# ── 逐行重建文件 ────────────────────────────────────────────────────────────
result = []
i = 0  # 0-indexed
n = len(lines)

while i < n:
    lineno = i + 1  # 1-indexed

    if lineno == A_START:
        # 替换 A 区块（L43-L77）→ paths import
        result.append(PATHS_IMPORT)
        i = A_END  # 跳到 A_END 的下一行（i++ at end of loop）

    elif lineno == B_START:
        # 删除 B 区块（L79-L135）
        i = B_END  # 跳过，B_END 下一行继续

    elif lineno == C_START:
        # 替换 C 区块（L3275-L6532）→ 代理方法
        result.append(PROXY_METHOD)
        i = C_END  # 跳过整个原方法体，从 L6533 继续

    else:
        result.append(lines[i])

    i += 1

print(f'修改后行数: {len(result)}')

with open(SRC, 'w', encoding='utf-8') as f:
    f.writelines(result)

print('写入完成。')
