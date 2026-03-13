import sys
import os
import subprocess
import shutil
import time
import platform
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.config import APP_VERSION

def remove_build_artifacts():
    """
    尝试清理 Nuitka 生成的构建目录，带有重试机制以解决文件锁定问题
    """
    dirs_to_remove = [
        "main.build",
        "main.onefile-build",
        os.path.join("dist", "main.build"),
        os.path.join("dist", "main.onefile-build"),
    ]
    
    for d in dirs_to_remove:
        if os.path.exists(d):
            print(f"正在清理目录: {d} ...")
            # 简单的重试机制
            max_retries = 5
            for i in range(max_retries):
                try:
                    shutil.rmtree(d)
                    print(f"清理成功: {d}")
                    break
                except Exception as e:
                    if i < max_retries - 1:
                        print(f"清理失败 ({e})，等待 2 秒后重试 ({i+1}/{max_retries})...")
                        time.sleep(2)
                    else:
                        print(f"警告: 无法清理目录 {d}: {e}")
                        print("您可以稍后手动删除这些目录。")

def clean_path_for_rebuild(path):
    if not os.path.exists(path):
        return
    print(f"正在清理路径: {path} ...")
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        print(f"清理成功: {path}")
    except Exception as e:
        raise RuntimeError(f"清理失败: {path}, 错误: {e}") from e

def build_windows_icon_ico(source_png, target_ico):
    if not os.path.exists(source_png):
        return ""
    try:
        from PySide6.QtGui import QImage
        image = QImage(source_png)
        if image.isNull():
            return ""
        if os.path.exists(target_ico):
            os.remove(target_ico)
        if image.save(target_ico, "ICO"):
            return target_ico
        return ""
    except Exception:
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
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            retina_size = size * 2
            subprocess.run(
                ["sips", "-z", str(retina_size), str(retina_size), source_png, "--out", os.path.join(iconset_dir, f"icon_{size}x{size}@2x.png")],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        subprocess.run(
            ["iconutil", "-c", "icns", iconset_dir, "-o", target_icns],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return target_icns if os.path.exists(target_icns) else ""
    except Exception:
        return ""
    finally:
        if os.path.exists(iconset_dir):
            shutil.rmtree(iconset_dir, ignore_errors=True)

def build():
    """
    使用 Nuitka 进行打包，生成更小、更快的可执行文件。
    支持 Windows 和 macOS。
    """
    main_script = "main.py"
    icon_png = "logo-ykohqv-s3wb4i-pck6c0.png"
    icon_ico = "app_icon.ico"
    icon_icns = "app_icon.icns"
    clean_path_for_rebuild("dist")
    clean_path_for_rebuild("main.build")
    clean_path_for_rebuild("main.onefile-build")
    
    # 检测操作系统
    system = platform.system()
    print(f"检测到操作系统: {system}")
    
    if system == "Windows":
        output_name = f"素材工单系统{APP_VERSION}.exe"
    elif system == "Darwin": # macOS
        output_name = f"素材工单系统{APP_VERSION}"
    else:
        output_name = f"素材工单系统{APP_VERSION}.bin"

    python_exe = sys.executable
    onefile_mode = os.environ.get("NUITKA_ONEFILE", "1") == "1"# 生成单文件可执行文件
    debug_console = os.environ.get("NUITKA_DEBUG_CONSOLE", "0") == "1" # 调试模式下保持控制台可见
    pythonhome_env = os.environ.get("PYTHONHOME")
    pythonpath_env = os.environ.get("PYTHONPATH")

    # Windows 特定环境检测
    if system == "Windows":
        if "WindowsApps" in python_exe:
            print("警告: 检测到正在使用 Windows Store 版 Python，Nuitka 不支持该版本。")
            # 尝试寻找官方 Python 安装
            local_app_data = os.environ.get('LOCALAPPDATA', '')
            possible_paths = [
                os.path.join(local_app_data, r"Programs\Python\Python312\python.exe"),
                os.path.join(local_app_data, r"Programs\Python\Python311\python.exe"),
                r"C:\Program Files\Python312\python.exe",
                r"C:\Program Files\Python311\python.exe",
            ]
            
            found_good_python = False
            for path in possible_paths:
                if os.path.exists(path):
                    print(f"自动切换到官方 Python: {path}")
                    python_exe = path
                    found_good_python = True
                    break
            
            if not found_good_python:
                print("错误: 未找到官方 Python 安装 (非 Windows Store 版)。请安装官方 Python 并确保已安装 Nuitka。")
                sys.exit(1)
    
    print(f"开始使用 Nuitka 打包 {main_script}...")
    if pythonhome_env:
        print(f"警告: 当前环境变量 PYTHONHOME={pythonhome_env}，已启用隔离模式避免影响运行。")
    if pythonpath_env:
        print(f"警告: 当前环境变量 PYTHONPATH={pythonpath_env}，已启用隔离模式避免影响运行。")
    # 基础构建命令
    cmd = [
        python_exe, "-m", "nuitka",
        # 编译模式
        "--standalone",      # 独立运行模式
        
        # 自动下载依赖 (如 MinGW64/ccache)
        "--assume-yes-for-downloads",
        "--python-flag=isolated",
        
        # 插件支持
        "--enable-plugin=pyside6", # 自动检测并包含 PySide6 依赖
        "--include-qt-plugins=platforms,styles,imageformats",
        
        # 显式包含模块
        "--include-package=packaging",
        "--include-package=src.core",
        "--include-package=src.ui",
        "--include-module=pymysql",
        "--include-module=requests",
        "--include-module=netifaces",
        "--include-module=encodings",
        "--include-package=encodings",
        "--include-module=codecs",
        f"--include-data-files={icon_png}={icon_png}",
        
        # 优化选项
        "--lto=no",          # 链接时间优化 (yes=更小但慢, no=快)
    ]

    # 平台特定选项
    if system == "Windows":
        cmd.append(f"--output-filename={output_name}") # 输出文件名
        
        # 强制指定输出目录为 dist
        dist_dir = "dist"
        if not os.path.exists(dist_dir):
            os.makedirs(dist_dir)
        cmd.append(f"--output-dir={dist_dir}")
        
        if onefile_mode:
            cmd.append("--onefile")
            cmd.append("--onefile-tempdir-spec={TEMP}/MCSWorkOrder/onefile/{PID}")
        if not debug_console:
            cmd.append("--windows-console-mode=disable")
        built_ico = build_windows_icon_ico(icon_png, icon_ico)
        if built_ico:
            cmd.append(f"--windows-icon-from-ico={built_ico}")
    elif system == "Darwin":
        built_icns = build_macos_icon_icns(icon_png, icon_icns)
        cmd.append("--macos-create-app-bundle") # 生成 .app 包
        if built_icns:
            cmd.append(f"--macos-app-icon={built_icns}")
        # 不指定 app-name，让其默认为 main.app，然后手动重命名
        # 避免 Nuitka 对非 ASCII 字符名称的潜在处理问题
        # cmd.append(f"--macos-app-name={output_name}") 
        # macOS 下不使用 --onefile，因为 app bundle 本身就是个文件夹结构
    else:
        cmd.append("--onefile")
        cmd.append(f"--output-filename={output_name}")

    # 添加入口脚本
    cmd.append(main_script)
    
    print("执行命令:", " ".join(cmd))
    
    try:
        build_env = os.environ.copy()
        build_env.pop("PYTHONHOME", None)
        build_env.pop("PYTHONPATH", None)
        subprocess.check_call(cmd, env=build_env)
        
        # macOS 额外处理：重命名生成的 .app
        if system == "Darwin":
            default_app_name = "main.app"
            target_app_name = f"{output_name}.app"
            
            # 查找生成的 .app (可能是 main.app 或者其他)
            source_app = None
            if os.path.exists(default_app_name):
                source_app = default_app_name
            else:
                # 尝试查找当前目录下其他的 .app
                apps = [f for f in os.listdir('.') if f.endswith('.app') and f != target_app_name]
                if apps:
                    source_app = apps[0]
            
            if source_app and source_app != target_app_name:
                print(f"检测到应用包 {source_app}，正在重命名为 {target_app_name}...")
                if os.path.exists(target_app_name):
                    shutil.rmtree(target_app_name)
                os.rename(source_app, target_app_name)
            elif not os.path.exists(target_app_name):
                print(f"警告: 未找到生成的 .app 包 (预期: {default_app_name} 或其他)")
                
            output_display = target_app_name
        elif system == "Windows":
            output_display = os.path.join("dist", output_name) if onefile_mode else os.path.join("dist", "main.dist", output_name)
        else:
            output_display = output_name

        print(f"\n打包成功！文件位于: {output_display}")
        if system == "Windows":
            print(f"打包模式: {'onefile' if onefile_mode else 'standalone'}")
            print(f"控制台模式: {'开启' if debug_console else '关闭'}")
            if not onefile_mode:
                print("提示: 若需单文件，请先设置环境变量 NUITKA_ONEFILE=1 后再执行打包。")
            if not debug_console:
                print("提示: 若需查看启动报错，请先设置环境变量 NUITKA_DEBUG_CONSOLE=1 后再执行打包。")
            print("提示: Nuitka 首次运行可能需要下载 C 编译器 (MinGW64)，请耐心等待。")
    except subprocess.CalledProcessError as e:
        print(f"\n打包失败，错误代码: {e.returncode}")
        sys.exit(1)
    finally:
        # 手动清理构建目录
        remove_build_artifacts()

if __name__ == "__main__":
    build()
