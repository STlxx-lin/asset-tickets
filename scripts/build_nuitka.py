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


def run_single_build(python_exe, is_onefile: bool, debug_console: bool):
    system = platform.system()
    main_script = "main.py"
    icon_png = "logo-ykohqv-s3wb4i-pck6c0.png"
    icon_ico = "app_icon.ico"
    icon_icns = "app_icon.icns"

    os.makedirs("dist", exist_ok=True)

    if system == "Windows":
        if is_onefile:
            target_name = f"WorkOrder_System_{APP_VERSION}_Portable.exe"
        else:
            target_name = f"WorkOrder_System_{APP_VERSION}.exe"
    elif system == "Darwin":
        target_name = f"WorkOrder_System_{APP_VERSION}"
    else:
        target_name = f"WorkOrder_System_{APP_VERSION}.bin"

    print(f"\n==========================================")
    print(f"开始构建: {'单文件版' if is_onefile else '绿色免安装目录版'} ({system})")
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
                final_folder = os.path.join("dist", f"WorkOrder_System_{APP_VERSION}_Standalone")
                if os.path.exists(raw_dist):
                    if os.path.exists(final_folder):
                        shutil.rmtree(final_folder)
                    shutil.move(raw_dist, final_folder)
                    # 将 .env 拷贝一份进绿色文件夹
                    if os.path.exists(".env"):
                        shutil.copy(".env", os.path.join(final_folder, ".env"))
                    # 压缩成 zip
                    zip_path = os.path.join("dist", f"WorkOrder_System_{APP_VERSION}_Standalone.zip")
                    zip_directory(final_folder, zip_path)
            else:
                final_exe = os.path.join("dist", target_name)
                print(f"\n单文件版构建完成: {final_exe}")

        elif system == "Darwin":
            target_app_name = f"{target_name}.app"
            candidate_paths = [
                "main.app",
                os.path.join("main.dist", "main.app"),
                os.path.join("dist", "main.app"),
                os.path.join("dist", "main.dist", "main.app"),
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
                        if d.endswith('.app') and d != target_app_name:
                            source_app = os.path.join(root, d)
                            break
                    if source_app:
                        break

            if source_app:
                if os.path.abspath(source_app) != os.path.abspath(target_app_name):
                    if os.path.exists(target_app_name):
                        shutil.rmtree(target_app_name)
                    shutil.move(source_app, target_app_name)

                macos_bin_dir = os.path.join(target_app_name, "Contents", "MacOS")
                if os.path.exists(macos_bin_dir):
                    for fname in os.listdir(macos_bin_dir):
                        fpath = os.path.join(macos_bin_dir, fname)
                        try:
                            st = os.stat(fpath)
                            os.chmod(fpath, st.st_mode | 0o111)
                        except Exception:
                            pass
                print(f"\nmacOS 应用包构建完成: {target_app_name}")

    finally:
        remove_build_artifacts()


def build():
    parser = argparse.ArgumentParser(description="工单系统 Nuitka 高性能打包脚本")
    parser.add_argument(
        "--mode",
        choices=["both", "standalone", "onefile"],
        default=os.environ.get("BUILD_MODE", "both"),
        help="打包模式：standalone(绿色免安装秒开版), onefile(单文件版), both(同时构建两者)"
    )
    parser.add_argument("--debug", action="store_true", help="开启调试控制台")
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
        if args.mode == "both":
            run_single_build(python_exe, is_onefile=False, debug_console=debug_console)
            run_single_build(python_exe, is_onefile=True, debug_console=debug_console)
        elif args.mode == "standalone":
            run_single_build(python_exe, is_onefile=False, debug_console=debug_console)
        else:
            run_single_build(python_exe, is_onefile=True, debug_console=debug_console)
    else:
        run_single_build(python_exe, is_onefile=False, debug_console=debug_console)

    print("\n==========================================")
    print(f"🎉 全部打包完成！产物已存放在 dist/ 目录中。")
    print("==========================================")


if __name__ == "__main__":
    build()
