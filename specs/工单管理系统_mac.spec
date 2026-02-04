# -*- mode: python ; coding: utf-8 -*-

# 从配置文件导入版本号
import os
import sys
# 添加当前目录到Python路径，使用os.getcwd()代替__file__
sys.path.append(os.getcwd())
from config import APP_VERSION

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pymysql',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'api_manager',  # 添加项目中的关键模块
        'database',     # 添加项目中的关键模块
        'config',       # 添加配置模块
        'typing_extensions',  # 修复urllib3相关警告
        'charset_normalizer'  # 修复请求相关警告
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'工单管理系统{APP_VERSION}_mac',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    one_file=True,
)

app = BUNDLE(
    exe,
    name=f'工单管理系统{APP_VERSION}_mac.app',
    icon=None,
    bundle_identifier='com.workorder.management',
    version=APP_VERSION,
    info_plist={
        'CFBundleName': '工单管理系统',
        'CFBundleDisplayName': '工单管理系统',
        'CFBundleVersion': APP_VERSION,
        'CFBundleShortVersionString': APP_VERSION,
        'NSHighResolutionCapable': True,
    },
)
