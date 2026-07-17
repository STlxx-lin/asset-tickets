"""验证 notification 拆分结果。"""
import sys, io, ast, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'e:\2025\pyproj')

# 1. 语法检查
files = [
    r'e:\2025\pyproj\src\core\notification.py',
    r'e:\2025\pyproj\src\ui\main_window.py',
]
ok = True
for fpath in files:
    try:
        src = open(fpath, encoding='utf-8').read()
        ast.parse(src)
        lines = src.count('\n')
        print(f'[OK] {os.path.basename(fpath)}  ({lines} 行)')
    except SyntaxError as e:
        print(f'[ERR] {os.path.basename(fpath)}: {e}')
        ok = False

# 2. main_window 符号检查
with open(r'e:\2025\pyproj\src\ui\main_window.py', encoding='utf-8') as f:
    mw = f.read()

print()
print('main_window.py — 必须存在的符号:')
must_exist = [
    'from src.core.notification import',
    'send_notification',
    'LINE_NOTIFICATION_SETTINGS',
    'load_notification_settings',
    'apply_notification_settings',
    'save_notification_settings',
    'get_department_line_names',
]
for sym in must_exist:
    status = 'OK' if sym in mw else 'MISSING'
    print(f'  [{status}] {sym}')

print()
print('main_window.py — 旧定义应已删除:')
must_gone = [
    'def send_dingtalk_markdown',
    'def send_wechat_work_markdown',
    'DINGTALK_BOTS = {',
    'WECHAT_WORK_BOTS = {',
    'import requests',
    'import hmac',
]
for sym in must_gone:
    status = 'FOUND (未删净!)' if sym in mw else 'GONE OK'
    print(f'  [{status}] {sym}')

# 3. notification.py 实际导入
print()
try:
    import src.core.notification as notif
    print('notification.py 导入: OK')
    print(f'  NOTIFICATION_TYPE = {notif.NOTIFICATION_TYPE!r}')
    print(f'  send_notification callable: {callable(notif.send_notification)}')
    print(f'  LINE_NOTIFICATION_SETTINGS type: {type(notif.LINE_NOTIFICATION_SETTINGS).__name__}')
except Exception as e:
    print(f'notification.py 导入失败: {e}')
    ok = False

print()
print('全部通过' if ok else '存在错误，请检查')
