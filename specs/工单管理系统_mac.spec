# -*- mode: python ; coding: utf-8 -*-

# 从配置文件导入版本号
import os
import sys
import shutil
import subprocess
# 添加当前目录到Python路径，使用os.getcwd()代替__file__
sys.path.append(os.getcwd())
from src.core.config import APP_VERSION

ICON_PNG = os.path.join(os.getcwd(), "logo-ykohqv-s3wb4i-pck6c0.png")
ICON_ICNS = os.path.join(os.getcwd(), "app_icon.icns")

def resolve_bundle_icon():
    if os.path.exists(ICON_ICNS):
        return ICON_ICNS
    if sys.platform != "darwin":
        return None
    if not os.path.exists(ICON_PNG):
        return None
    iconset_dir = os.path.join(os.getcwd(), "app_icon.iconset")
    try:
        if os.path.exists(iconset_dir):
            shutil.rmtree(iconset_dir)
        os.makedirs(iconset_dir, exist_ok=True)
        sizes = [16, 32, 128, 256, 512]
        for size in sizes:
            subprocess.run(
                ["sips", "-z", str(size), str(size), ICON_PNG, "--out", os.path.join(iconset_dir, f"icon_{size}x{size}.png")],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            retina_size = size * 2
            subprocess.run(
                ["sips", "-z", str(retina_size), str(retina_size), ICON_PNG, "--out", os.path.join(iconset_dir, f"icon_{size}x{size}@2x.png")],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        subprocess.run(
            ["iconutil", "-c", "icns", iconset_dir, "-o", ICON_ICNS],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if os.path.exists(ICON_ICNS):
            return ICON_ICNS
        return None
    except Exception:
        return None
    finally:
        if os.path.exists(iconset_dir):
            shutil.rmtree(iconset_dir, ignore_errors=True)

bundle_icon = resolve_bundle_icon()
bundle_info_plist = {
    'CFBundleName': '工单管理系统',
    'CFBundleDisplayName': '工单管理系统',
    'CFBundleVersion': APP_VERSION,
    'CFBundleShortVersionString': APP_VERSION,
    'NSHighResolutionCapable': True,
}
if bundle_icon:
    bundle_info_plist['CFBundleIconFile'] = os.path.basename(bundle_icon)

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
    icon=bundle_icon,
    bundle_identifier='com.workorder.management',
    version=APP_VERSION,
    info_plist=bundle_info_plist,
)
