import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
import zipfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.config import APP_VERSION


def remove_build_artifacts():
    """尝试清理 Nuitka 生成的临时构建中间目录"""
    dirs_to_remove = [
        "main.build",
        "main.onefile-build",
        os.path.join("dist", "main.build"),
        os.path.join("dist", "main.onefile-build"),
    ]
    for d in dirs_to_remove:
        if os.path.exists(d):
            for _ in range(3):
                try:
                    shutil.rmtree(d)
                    break
                except Exception:
                    time.sleep(1)


def clean_path_for_rebuild(path):
    if not os.path.exists(path):
        return
    print(f"正在清理路径: {path} ...")
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    except Exception as e:
        print(f"清理警告: {path}, 错误: {e}")


def build_windows_icon_ico(source_png, target_ico):
    """确保生成并返回标准的 Windows 多尺寸 ICO 图标路径"""
    if os.path.exists(target_ico) and os.path.getsize(target_ico) > 1000:
        return os.path.abspath(target_ico)

    if not os.path.exists(source_png):
        return ""

    try:
        from scripts.generate_icons import png_to_ico
        generated = png_to_ico(source_png, target_ico)
        if generated and os.path.exists(generated):
            return os.path.abspath(generated)
    except Exception:
        pass

    try:
        from PySide6.QtGui import QImage
        image = QImage(source_png)
        if not image.isNull():
            if os.path.exists(target_ico):
                os.remove(target_ico)
            if image.save(target_ico):
                return os.path.abspath(target_ico)
    except Exception:
        pass

    return ""


def build_macos_icon_icns(source_png, target_icns):
    if platform.system() != "Darwin":
        return ""
    if os.path.exists(target_icns):
        return target_icns
    if not os.path.exists(source_png):
        return ""
    iconset_dir = "app_icon.iconset"
    try:
        if os.path.exists(iconset_dir):
            shutil.rmtree(iconset_dir)
        os.makedirs(iconset_dir, exist_ok=True)
        sizes = [16, 32, 128, 256, 512]
        for size in sizes:
            subprocess.run(
                ["sips", "-z", str(size), str(size), source_png, "--out", os.path.join(iconset_dir, f"icon_{size}x{size}.png")],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            retina_size = size * 2
            subprocess.run(
                ["sips", "-z", str(retina_size), str(retina_size), source_png, "--out", os.path.join(iconset_dir, f"icon_{size}x{size}@2x.png")],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        subprocess.run(
            ["iconutil", "-c", "icns", iconset_dir, "-o", target_icns],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return target_icns if os.path.exists(target_icns) else ""
    except Exception:
        return ""
    finally:
        if os.path.exists(iconset_dir):
            shutil.rmtree(iconset_dir, ignore_errors=True)


def zip_directory(dir_path, zip_path):
    """将目录打包为 zip 文件"""
    print(f"正在压缩生成绿色免安装包: {zip_path} ...")
    base_dir_name = os.path.basename(dir_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dir_path):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, os.path.dirname(dir_path))
                zf.write(full_path, rel_path)
    print(f"绿色免安装包生成完成: {zip_path}")


def generate_macos_console_launcher(target_dir, app_name):
    """为 macOS App 生成配套的双击启动控制台 .command 脚本（精确通过 Info.plist 定位主程序，排除 .so / .dylib）"""
    launcher_path = os.path.join(target_dir, "启动调试控制台.command")
    script_content = f'''#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=========================================="
echo "正在启动工单管理系统 (控制台调试模式)..."
echo "=========================================="

APP_PATH="$DIR/{app_name}"
if [ ! -d "$APP_PATH" ]; then
    APP_PATH=$(find "$DIR" -name "*.app" -type d -maxdepth 2 | head -n 1)
fi

if [ -z "$APP_PATH" ] || [ ! -d "$APP_PATH" ]; then
    echo "错误: 未在当前目录下找到应用程序包 (.app)！"
    echo "=========================================="
    echo "按任意键关闭此终端窗口..."
    read -n 1 -s
    exit 1
fi

EXEC_BIN=""

# 1. 首选方案：从 Info.plist 读取 CFBundleExecutable 主程序名称（最权威精确）
if [ -f "$APP_PATH/Contents/Info.plist" ]; then
    EXEC_NAME=$(defaults read "$APP_PATH/Contents/Info.plist" CFBundleExecutable 2>/dev/null)
    if [ -z "$EXEC_NAME" ]; then
        EXEC_NAME=$(/usr/libexec/PlistBuddy -c "Print :CFBundleExecutable" "$APP_PATH/Contents/Info.plist" 2>/dev/null)
    fi
    if [ -z "$EXEC_NAME" ]; then
        EXEC_NAME=$(grep -A 1 "CFBundleExecutable" "$APP_PATH/Contents/Info.plist" | tail -n 1 | sed -e 's/.*<string>//' -e 's/<\\/string>.*//' | tr -d ' \\t\\r\\n')
    fi
    if [ -n "$EXEC_NAME" ] && [ -f "$APP_PATH/Contents/MacOS/$EXEC_NAME" ]; then
        EXEC_BIN="$APP_PATH/Contents/MacOS/$EXEC_NAME"
    fi
fi

# 2. 备选方案：匹配 App 同名二进制文件或 main
if [ -z "$EXEC_BIN" ] || [ ! -f "$EXEC_BIN" ]; then
    APP_BASENAME=$(basename "$APP_PATH" .app)
    if [ -f "$APP_PATH/Contents/MacOS/$APP_BASENAME" ]; then
        EXEC_BIN="$APP_PATH/Contents/MacOS/$APP_BASENAME"
    elif [ -f "$APP_PATH/Contents/MacOS/main" ]; then
        EXEC_BIN="$APP_PATH/Contents/MacOS/main"
    fi
fi

# 3. 兜底方案：在 MacOS 目录下查找第一个非 .so/.dylib/.plist/.command 的独立二进制文件
if [ -z "$EXEC_BIN" ] || [ ! -f "$EXEC_BIN" ]; then
    EXEC_BIN=$(find "$APP_PATH/Contents/MacOS" -maxdepth 1 -type f ! -name "*.so" ! -name "*.dylib" ! -name "*.plist" ! -name "*.command" ! -name "*.sh" 2>/dev/null | head -n 1)
fi

if [ -n "$EXEC_BIN" ] && [ -f "$EXEC_BIN" ]; then
    chmod +x "$EXEC_BIN" 2>/dev/null
    echo "正在运行: $EXEC_BIN"
    echo "------------------------------------------"
    "$EXEC_BIN" "$@"
else
    echo "错误: 未能在 $APP_PATH/Contents/MacOS/ 下找到可执行二进制文件！"
fi

echo ""
echo "=========================================="
echo "程序已退出。按任意键关闭此终端窗口..."
read -n 1 -s
'''
    try:
        with open(launcher_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(script_content)
        st = os.stat(launcher_path)
        os.chmod(launcher_path, st.st_mode | 0o755)
    except Exception as e:
        print(f"生成控制台启动脚本警告: {e}")
    return launcher_path


def create_macos_dmg(app_path, dmg_path, volume_name, extra_files=None):
    """在 macOS 环境下使用 hdiutil 生成 DMG 镜像包"""
    if platform.system() != "Darwin":
        return
    print(f"正在生成 DMG 安装包: {dmg_path} ...")
    temp_dir = os.path.join("dist", "temp_dmg_" + str(int(time.time())))
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)
    try:
        app_basename = os.path.basename(app_path)
        shutil.copytree(app_path, os.path.join(temp_dir, app_basename), symlinks=True)
        if extra_files:
            for ef in extra_files:
                if os.path.exists(ef):
                    shutil.copy(ef, os.path.join(temp_dir, os.path.basename(ef)))
        # 创建 Applications 软链接
        app_link = os.path.join(temp_dir, "Applications")
        try:
            os.symlink("/Applications", app_link)
        except Exception:
            pass

        if os.path.exists(dmg_path):
            os.remove(dmg_path)

        for attempt in range(1, 6):
            res = subprocess.run([
                "hdiutil", "create", "-volname", volume_name,
                "-srcfolder", temp_dir, "-ov", "-format", "UDZO", dmg_path
            ], capture_output=True, text=True)
            if res.returncode == 0:
                print(f"DMG 创建成功: {dmg_path}")
                break
            print(f"hdiutil 创建 DMG 重试第 {attempt} 次: {res.stderr}")
            time.sleep(3)
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_single_build(python_exe, is_onefile: bool, debug_console: bool):
    system = platform.system()
    main_script = "main.py"
    icon_png = "logo-ykohqv-s3wb4i-pck6c0.png"
    icon_ico = "app_icon.ico"
    icon_icns = "app_icon.icns"

    os.makedirs("dist", exist_ok=True)

    if system == "Windows":
        if is_onefile:
            target_name = f"WorkOrder_System_{APP_VERSION}_Debug.exe" if debug_console else f"WorkOrder_System_{APP_VERSION}_Portable.exe"
        else:
            target_name = f"WorkOrder_System_{APP_VERSION}_Debug.exe" if debug_console else f"WorkOrder_System_{APP_VERSION}.exe"
    elif system == "Darwin":
        target_name = f"WorkOrder_System_{APP_VERSION}_Debug" if debug_console else f"WorkOrder_System_{APP_VERSION}"
    else:
        target_name = f"WorkOrder_System_{APP_VERSION}_Debug.bin" if debug_console else f"WorkOrder_System_{APP_VERSION}.bin"

    version_label = "【控制台调试版】" if debug_console else "【标准版】"
    print(f"\n==========================================")
    print(f"开始构建 {version_label}: {'单文件版' if is_onefile else '免安装应用包'} ({system})")
    print(f"==========================================")

    cmd = [
        python_exe, "-m", "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--python-flag=isolated",
        "--enable-plugin=pyside6",
        "--include-qt-plugins=platforms,styles,imageformats",
        "--include-package=packaging",
        "--include-package=qfluentwidgets",
        "--include-package-data=qfluentwidgets",
        "--include-package=src.core",
        "--include-package=src.ui",
        "--include-module=pymysql",
        "--include-module=requests",
        "--include-module=netifaces",
        "--include-module=encodings",
        "--include-package=encodings",
        "--include-module=codecs",
        f"--include-data-files={icon_png}={icon_png}",
        f"--include-data-files={icon_ico}={icon_ico}" if os.path.exists(icon_ico) else "",
        "--include-data-files=.env=.env" if os.path.exists(".env") else "",
        "--lto=no",
    ]
    cmd = [c for c in cmd if c]

    if system == "Windows":
        cmd.append(f"--output-filename={target_name}")
        cmd.append("--output-dir=dist")
        if is_onefile:
            cmd.append("--onefile")
            cmd.append(f"--onefile-tempdir-spec={{TEMP}}/MCSWorkOrder/cache/{APP_VERSION}")
        if not debug_console:
            cmd.append("--windows-console-mode=disable")
        built_ico = build_windows_icon_ico(icon_png, icon_ico)
        if built_ico:
            cmd.append(f"--windows-icon-from-ico={built_ico}")
    elif system == "Darwin":
        built_icns = build_macos_icon_icns(icon_png, icon_icns)
        cmd.append("--macos-create-app-bundle")
        if built_icns:
            cmd.append(f"--macos-app-icon={built_icns}")
    else:
        cmd.append("--onefile")
        cmd.append(f"--output-filename={target_name}")

    cmd.append(main_script)

    build_env = os.environ.copy()
    build_env.pop("PYTHONHOME", None)
    build_env.pop("PYTHONPATH", None)

    try:
        subprocess.check_call(cmd, env=build_env)

        if system == "Windows":
            if not is_onefile:
                raw_dist = os.path.join("dist", "main.dist")
                folder_suffix = "_Standalone_Debug" if debug_console else "_Standalone"
                final_folder = os.path.join("dist", f"WorkOrder_System_{APP_VERSION}{folder_suffix}")
                if os.path.exists(raw_dist):
                    if os.path.exists(final_folder):
                        shutil.rmtree(final_folder)
                    shutil.move(raw_dist, final_folder)
                    # 将 .env 拷贝一份进绿色文件夹
                    if os.path.exists(".env"):
                        shutil.copy(".env", os.path.join(final_folder, ".env"))
                    # 压缩成 zip
                    zip_path = os.path.join("dist", f"WorkOrder_System_{APP_VERSION}{folder_suffix}.zip")
                    zip_directory(final_folder, zip_path)
            else:
                final_exe = os.path.join("dist", target_name)
                print(f"\n单文件版构建完成: {final_exe}")

        elif system == "Darwin":
            target_app_name = f"{target_name}.app"
            final_app_path = os.path.join("dist", target_app_name)
            candidate_paths = [
                "main.app",
                os.path.join("main.dist", "main.app"),
                os.path.join("dist", "main.app"),
                os.path.join("dist", "main.dist", "main.app"),
                target_app_name,
            ]
            source_app = None
            for p in candidate_paths:
                if os.path.exists(p):
                    source_app = p
                    break

            if not source_app:
                for root, dirs, _ in os.walk('.'):
                    if '/.' in root or '\\.' in root:
                        continue
                    for d in dirs:
                        if d.endswith('.app') and d not in (target_app_name, "dist"):
                            source_app = os.path.join(root, d)
                            break
                    if source_app:
                        break

            if source_app:
                if os.path.abspath(source_app) != os.path.abspath(final_app_path):
                    if os.path.exists(final_app_path):
                        shutil.rmtree(final_app_path)
                    shutil.move(source_app, final_app_path)

                macos_bin_dir = os.path.join(final_app_path, "Contents", "MacOS")
                if os.path.exists(macos_bin_dir):
                    for fname in os.listdir(macos_bin_dir):
                        fpath = os.path.join(macos_bin_dir, fname)
                        try:
                            st = os.stat(fpath)
                            os.chmod(fpath, st.st_mode | 0o755)
                        except Exception:
                            pass
                print(f"\nmacOS 应用包构建完成: {final_app_path}")

                # 生成配套的调试控制台启动脚本
                extra_files = []
                if debug_console:
                    launcher_script = generate_macos_console_launcher("dist", target_app_name)
                    if os.path.exists(launcher_script):
                        extra_files.append(launcher_script)
                        # 也放一份在 .app 内部备用
                        try:
                            shutil.copy(launcher_script, os.path.join(final_app_path, "Contents", "MacOS", "launch_console.command"))
                        except Exception:
                            pass

                # 生成 DMG 与 ZIP 包
                if platform.system() == "Darwin":
                    dmg_name = f"{target_name}.dmg"
                    dmg_path = os.path.join("dist", dmg_name)
                    vol_name = f"工单管理系统{APP_VERSION}" + ("(调试版)" if debug_console else "")
                    create_macos_dmg(final_app_path, dmg_path, vol_name, extra_files=extra_files)

                    # 生成 ZIP 包
                    zip_name = f"{target_name}.zip"
                    zip_path = os.path.join("dist", zip_name)
                    print(f"正在打包 macOS ZIP: {zip_path} ...")
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for root, _, files in os.walk(final_app_path):
                            for f in files:
                                full_p = os.path.join(root, f)
                                rel_p = os.path.relpath(full_p, "dist")
                                zf.write(full_p, rel_p)
                        for ef in extra_files:
                            if os.path.exists(ef):
                                zf.write(ef, os.path.basename(ef))
                    print(f"macOS ZIP 生成完成: {zip_path}")

    finally:
        remove_build_artifacts()


def build():
    parser = argparse.ArgumentParser(description="工单系统 Nuitka 高性能打包脚本")
    parser.add_argument(
        "--mode",
        choices=["both", "standalone", "onefile"],
        default=os.environ.get("BUILD_MODE", "both"),
        help="打包模式：standalone(绿色免安装版/单版本), onefile(单文件版), both(构建所有推荐版本)"
    )
    parser.add_argument("--debug", action="store_true", help="仅构建控制台调试版本")
    parser.add_argument("--standard", action="store_true", help="仅构建标准无控制台版本")
    args = parser.parse_args()

    system = platform.system()
    python_exe = sys.executable

    if system == "Windows":
        if "WindowsApps" in python_exe:
            local_app_data = os.environ.get('LOCALAPPDATA', '')
            possible_paths = [
                os.path.join(local_app_data, r"Programs\Python\Python312\python.exe"),
                os.path.join(local_app_data, r"Programs\Python\Python311\python.exe"),
                r"C:\Program Files\Python312\python.exe",
                r"C:\Program Files\Python311\python.exe",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    python_exe = path
                    break

    debug_console = args.debug or os.environ.get("NUITKA_DEBUG_CONSOLE", "0") == "1"

    if system == "Windows":
        if debug_console:
            run_single_build(python_exe, is_onefile=True, debug_console=True)
        elif args.mode == "both":
            run_single_build(python_exe, is_onefile=False, debug_console=False)
            run_single_build(python_exe, is_onefile=True, debug_console=False)
        elif args.mode == "standalone":
            run_single_build(python_exe, is_onefile=False, debug_console=False)
        else:
            run_single_build(python_exe, is_onefile=True, debug_console=False)
    elif system == "Darwin":
        # macOS 平台：若未单独指定 --debug 或 --standard，默认构建两个版本（标准版 + 控制台调试版）
        if args.debug:
            run_single_build(python_exe, is_onefile=False, debug_console=True)
        elif args.standard:
            run_single_build(python_exe, is_onefile=False, debug_console=False)
        else:
            print("\n🍏 检测到 macOS 平台，将自动打包两个版本：【标准版】与【控制台调试版】")
            run_single_build(python_exe, is_onefile=False, debug_console=False)
            run_single_build(python_exe, is_onefile=False, debug_console=True)
    else:
        run_single_build(python_exe, is_onefile=False, debug_console=debug_console)

    print("\n==========================================")
    print(f"🎉 全部打包完成！产物已存放在 dist/ 目录中。")
    print("==========================================")


if __name__ == "__main__":
    build()
