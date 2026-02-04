import sys
import os
import subprocess
import shutil
import time
import platform
from config import APP_VERSION

def remove_build_artifacts(base_name):
    """
    尝试清理 Nuitka 生成的构建目录，带有重试机制以解决文件锁定问题
    """
    dirs_to_remove = [f"{base_name}.build", f"{base_name}.onefile-build"]
    
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

def build():
    """
    使用 Nuitka 进行打包，生成更小、更快的可执行文件。
    支持 Windows 和 macOS。
    """
    main_script = "main.py"
    
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
    
    # 基础构建命令
    cmd = [
        python_exe, "-m", "nuitka",
        # 编译模式
        "--standalone",      # 独立运行模式
        
        # 自动下载依赖 (如 MinGW64/ccache)
        "--assume-yes-for-downloads",
        
        # 插件支持
        "--enable-plugin=pyside6", # 自动检测并包含 PySide6 依赖
        
        # 显式包含模块
        "--include-package=packaging",
        "--include-package=api_manager",
        "--include-package=database",
        "--include-package=config",
        "--include-package=ui",
        "--include-module=pymysql",
        "--include-module=requests",
        "--include-module=netifaces",
        
        # 优化选项
        "--lto=yes",          # 链接时间优化 (yes=更小但慢, no=快)
    ]

    # 平台特定选项
    if system == "Windows":
        cmd.append("--onefile")         # 打包成单文件
        cmd.append(f"--output-filename={output_name}") # 输出文件名
        cmd.append("--windows-disable-console") # 运行时不显示控制台窗口
    elif system == "Darwin":
        cmd.append("--macos-create-app-bundle") # 生成 .app 包
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
        subprocess.check_call(cmd)
        
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
        else:
            output_display = output_name

        print(f"\n打包成功！文件位于: {output_display}")
        if system == "Windows":
            print("提示: Nuitka 首次运行可能需要下载 C 编译器 (MinGW64)，请耐心等待。")
    except subprocess.CalledProcessError as e:
        print(f"\n打包失败，错误代码: {e.returncode}")
        sys.exit(1)
    finally:
        # 手动清理构建目录
        remove_build_artifacts("main")

if __name__ == "__main__":
    build()
