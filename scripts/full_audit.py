"""
全面审计脚本：检查重构后项目的完整性。
"""
import sys, io, re, ast, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'e:\2025\pyproj')

MW = r'e:\2025\pyproj\src\ui\main_window.py'
DIALOG_DIR = r'e:\2025\pyproj\src\ui\process_dialogs'
DIALOG_FILES = ['photography.py','video_review.py','video_post_review.py','art.py','editing.py','ops.py','sales.py']

print('='*60)
print('1. 所有新文件 AST 语法检查')
print('='*60)
all_files = [
    r'e:\2025\pyproj\src\core\paths.py',
    r'e:\2025\pyproj\src\core\notification.py',
    MW,
    os.path.join(DIALOG_DIR, '__init__.py'),
    os.path.join(DIALOG_DIR, 'dispatcher.py'),
] + [os.path.join(DIALOG_DIR, f) for f in DIALOG_FILES]

ok = True
for fp in all_files:
    try:
        src = open(fp, encoding='utf-8').read()
        ast.parse(src)
        print(f'  [OK] {os.path.basename(fp)}')
    except SyntaxError as e:
        print(f'  [ERR] {os.path.basename(fp)}: {e}')
        ok = False

print()
print('='*60)
print('2. main_window.py — callbacks 三个目标方法')
print('='*60)
with open(MW, encoding='utf-8') as f:
    mw_lines = f.readlines()
    mw = ''.join(mw_lines)

REQUIRED_METHODS = [
    'update_work_order_status_and_ui',
    'add_file_task',
    'log_action',
    'refresh_work_orders',
    'show_process_order_dialog',
    'handle_process_selected_order',
    'create_path_status_label',
    'check_path_collected_status',
    'show_error_dialog',
]
for m in REQUIRED_METHODS:
    hits = [i+1 for i, l in enumerate(mw_lines) if f'def {m}' in l]
    if hits:
        print(f'  [OK] def {m}  L{hits[0]}')
    else:
        print(f'  [MISSING] def {m}')
        ok = False

print()
print('='*60)
print('3. main_window.py — 不该存在的旧定义')
print('='*60)
MUST_BE_GONE = [
    'def send_dingtalk_markdown',
    'def send_wechat_work_markdown',
    'DINGTALK_BOTS = {',
    'WECHAT_WORK_BOTS = {',
    'def to_local_path',          # 已迁移到 paths.py
]
for s in MUST_BE_GONE:
    found = s in mw
    status = 'FOUND (未删净!)' if found else 'GONE OK'
    mark = '[!!]' if found else '[OK]'
    print(f'  {mark} {s!r}: {status}')
    if found:
        ok = False

print()
print('='*60)
print('4. 关键 import 检查')
print('='*60)
REQUIRED_IMPORTS = [
    'from src.core.paths import',
    'from src.core.notification import',
    'from src.ui.process_dialogs import',
]
for imp in REQUIRED_IMPORTS:
    found = imp in mw
    print(f'  [{"OK" if found else "MISSING"}] {imp}')
    if not found:
        ok = False

print()
print('='*60)
print('5. process_dialogs — 残余 self. 引用检查')
print('='*60)
for fname in DIALOG_FILES:
    fp = os.path.join(DIALOG_DIR, fname)
    with open(fp, encoding='utf-8') as f:
        dlines = f.readlines()
    issues = []
    for i, line in enumerate(dlines):
        if line.strip().startswith('#'):
            continue
        if re.search(r'\bself\.', line):
            issues.append((i+1, line.rstrip()))
    if issues:
        print(f'  [!!] {fname}:')
        for ln, content in issues:
            print(f'       L{ln}: {content}')
        ok = False
    else:
        print(f'  [OK] {fname}')

print()
print('='*60)
print('6. 检查 patch off-by-one 是否导致其他方法丢失')
print('='*60)
# 对比 .bak (原始) 与当前文件的所有 indent=4 def 方法列表
with open(r'e:\2025\pyproj\src\ui\main_window.py.bak', encoding='utf-8') as f:
    bak_lines = f.readlines()

bak_methods = set()
for line in bak_lines:
    if re.match(r'    def (\w+)\(self', line):
        m = re.search(r'def (\w+)', line)
        if m:
            bak_methods.add(m.group(1))

cur_methods = set()
for line in mw_lines:
    if re.match(r'    def (\w+)\(self', line):
        m = re.search(r'def (\w+)', line)
        if m:
            cur_methods.add(m.group(1))

missing_methods = bak_methods - cur_methods
# 排除预期被移除的（这些现在在 process_dialogs 里，不再是方法了）
# 原来 show_process_order_dialog 内部 helper 函数也会被误算，过滤掉一些
# 真正属于 MainWindow 类方法的才算
known_relocated = set()  # 没有方法整体搬移到别处，只是把内联代码抽走了

if missing_methods:
    print(f'  [!!] 以下方法在 .bak 中存在但当前缺失:')
    for m in sorted(missing_methods):
        print(f'       def {m}')
    ok = False
else:
    print(f'  [OK] 所有 MainWindow 方法均完整')

print()
print('='*60)
print(f'总体结果: {"全部通过 ✅" if ok else "存在问题 ❌ 见上方标注"}')
print('='*60)
