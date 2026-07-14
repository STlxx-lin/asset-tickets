# -*- mode: python ; coding: utf-8 -*-

# 从配置文件导入版本号
import os
import sys
SPEC_FILE = globals().get('__file__')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC_FILE))) if SPEC_FILE else os.getcwd()
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, 'main.py')
ICON_ICO = os.path.join(PROJECT_ROOT, 'app_icon.ico')
sys.path.append(PROJECT_ROOT)
from src.core.config import APP_VERSION

a = Analysis(
    [MAIN_SCRIPT],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pymysql',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'src.core.api_manager',  # 添加项目中的关键模块
        'src.core.database',     # 添加项目中的关键模块
        'src.core.config',       # 添加配置模块
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
    name=f'素材工单系统_{APP_VERSION}_pyinstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    icon=ICON_ICO if os.path.exists(ICON_ICO) else None,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    one_file=True,  # 添加此参数以生成单个可执行文件
)
app = BUNDLE(
    exe,
    name=f'素材工单系统_{APP_VERSION}_pyinstaller.app',
    icon=None,
    bundle_identifier=None,
)
