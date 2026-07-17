"""
修复脚本：将各角色对话框文件中的 self.xxx 引用替换为正确的形式：
- self.update_work_order_status_and_ui  -> callbacks['update_status']  (或内部定义的 _update_status)
- self.add_file_task                    -> callbacks['add_file_task']   (或内部定义的 _add_file_task)
- self.log_action                       -> callbacks['log_action']      (或内部定义的 _log_action)
- self.role                             -> parent.role
- self.refresh_work_orders              -> parent.refresh_work_orders
- self.create_path_status_label         -> parent.create_path_status_label
- self.check_path_collected_status      -> parent.check_path_collected_status
- self.show_error_dialog                -> parent.show_error_dialog
- self.styleSheet()                     -> parent.styleSheet()
- self.product_dir                      -> parent.product_dir
- self.store_dir                        -> parent.store_dir
"""
import sys
import io
import os
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DIALOG_DIR = r'e:\2025\pyproj\src\ui\process_dialogs'

# 替换规则：(pattern, replacement)  — 按顺序应用
REPLACEMENTS = [
    # callbacks 回调（使用已解包的局部变量名）
    (r'\bself\.update_work_order_status_and_ui\b', '_update_status'),
    (r'\bself\.add_file_task\b',                   '_add_file_task'),
    (r'\bself\.log_action\b',                      '_log_action'),
    # parent 透传
    (r'\bself\.role\b',                            'parent.role'),
    (r'\bself\.refresh_work_orders\b',             'parent.refresh_work_orders'),
    (r'\bself\.create_path_status_label\b',        'parent.create_path_status_label'),
    (r'\bself\.check_path_collected_status\b',     'parent.check_path_collected_status'),
    (r'\bself\.show_error_dialog\b',               'parent.show_error_dialog'),
    (r'\bself\.styleSheet\b',                      'parent.styleSheet'),
    (r'\bself\.product_dir\b',                     'parent.product_dir'),
    (r'\bself\.store_dir\b',                       'parent.store_dir'),
]

files = [
    'photography.py',
    'video_review.py',
    'video_post_review.py',
    'art.py',
    'editing.py',
    'ops.py',
    'sales.py',
]

for fname in files:
    fpath = os.path.join(DIALOG_DIR, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    total_replacements = 0
    for pattern, replacement in REPLACEMENTS:
        new_content, n = re.subn(pattern, replacement, content)
        if n:
            print(f'  [{fname}] {pattern} -> {replacement}  ({n} 处)')
            total_replacements += n
        content = new_content

    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[OK] {fname}  共替换 {total_replacements} 处')
    else:
        print(f'[--] {fname}  无需修改')
    print()

print('修复完成。')
