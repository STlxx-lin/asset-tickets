#!/usr/bin/env python3
"""
工单管理系统打包脚本
支持 Windows 和 macOS 平台的单文件可执行程序打包
python scripts/build_script.py --release
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 导入版本号
from src.core.config import APP_VERSION

# 解决 Windows 环境下可能的编码问题
if sys.platform.startswith('win'):
    for stream in (sys.stdout, sys.stderr):
        reconf = getattr(stream, 'reconfigure', None)
        if callable(reconf):
            try:
                reconf(encoding='utf-8')
            except Exception:
                pass

def install_dependencies():
    """安装依赖包"""
    print("正在安装依赖包...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", os.path.join(PROJECT_ROOT, "requirements.txt")], check=True, cwd=PROJECT_ROOT)
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True, cwd=PROJECT_ROOT)
    print("依赖包安装完成")

def build_windows(onefile=False):
    """构建 Windows 版本"""
    print(f"正在构建 Windows 版本 (单文件: {onefile})...")
    ico_path = os.path.join(PROJECT_ROOT, "app_icon.ico")
    png_path = os.path.join(PROJECT_ROOT, "logo-ykohqv-s3wb4i-pck6c0.png")
    if not os.path.exists(ico_path) and os.path.exists(png_path):
        try:
            from scripts.generate_icons import png_to_ico
            png_to_ico(png_path, ico_path)
        except Exception as e:
            print(f"警告: 生成 ICO 图标失败: {e}")
    spec_file = os.path.join(PROJECT_ROOT, "specs", "工单管理系统.spec")
    if onefile:
        # 确保 spec 文件中设置了 onefile=True
        pass  # 已在 spec 文件中设置
    subprocess.run([sys.executable, "-m", "PyInstaller", spec_file], check=True, cwd=PROJECT_ROOT)
    # 生成带版本号的文件名（须与 specs/工单管理系统.spec 中 name 一致，否则提示的路径与实际产物不符）
    exe_name = f"WorkOrder_System_{APP_VERSION}_PyInstaller.exe"
    print(f"Windows 版本构建完成: dist/{exe_name}")

def build_mac(onefile=False, debug=None):
    """构建 macOS 版本（默认自动构建标准版与控制台调试版两种产物，并分别生成 DMG 安装包）"""
    spec_file = os.path.join(PROJECT_ROOT, "specs", "工单管理系统_mac.spec")
    
    # 根据参数决定构建单版本还是双版本
    if debug is True:
        build_targets = [("控制台调试版", "1", f"工单管理系统{APP_VERSION}_mac_debug", f"素材工单系统{APP_VERSION}_Debug_mac")]
    elif debug is False:
        build_targets = [("标准版", "0", f"工单管理系统{APP_VERSION}_mac", f"素材工单系统{APP_VERSION}_mac")]
    else:
        build_targets = [
            ("标准版", "0", f"工单管理系统{APP_VERSION}_mac", f"素材工单系统{APP_VERSION}_mac"),
            ("控制台调试版", "1", f"工单管理系统{APP_VERSION}_mac_debug", f"素材工单系统{APP_VERSION}_Debug_mac"),
        ]

    for label, console_flag, base_name, dmg_prefix in build_targets:
        print(f"\n==========================================")
        print(f"正在构建 macOS {label} (单文件: {onefile})...")
        print(f"==========================================")
        
        build_env = os.environ.copy()
        build_env["BUILD_CONSOLE"] = console_flag
        subprocess.run([sys.executable, "-m", "PyInstaller", spec_file], check=True, cwd=PROJECT_ROOT, env=build_env)
        
        app_name = f"{base_name}.app"
        app_path = os.path.join("dist", app_name)
        print(f"macOS {label} 应用包构建完成: {app_path}")
        
        # 生成 DMG 安装包
        if platform.system() == "Darwin":
            print(f"正在生成 {label} 的 DMG 安装包...")
            dmg_name = f"{dmg_prefix}.dmg"
            dmg_path = os.path.join("dist", dmg_name)
            
            temp_dir = os.path.join("dist", f"temp_dmg_{console_flag}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # 复制 App 到临时目录
                shutil.copytree(app_path, os.path.join(temp_dir, app_name), symlinks=True)
                
                # 添加 Applications 软链接
                applications_link = os.path.join(temp_dir, "Applications")
                try:
                    subprocess.run(["ln", "-s", "/Applications", applications_link], check=True)
                except Exception:
                    pass
                
                # 创建 DMG 文件
                vol_name = f"素材工单系统{APP_VERSION}" + ("(调试版)" if console_flag == "1" else "")
                subprocess.run([
                    "hdiutil", "create", "-volname", vol_name, 
                    "-srcfolder", temp_dir, "-ov", "-format", "UDZO", dmg_path
                ], check=True)
                
                print(f"macOS {label} DMG 安装包构建完成: {dmg_path}")
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)

def increment_version():
    """读取 config.py，增加版本号，并保存"""
    # 基于脚本位置解析固定路径（不依赖当前工作目录），避免误写其他位置的 config.py
    config_path = (Path(PROJECT_ROOT) / 'src' / 'core' / 'config.py').resolve()
    content = config_path.read_text(encoding='utf-8')
    
    # 匹配 APP_VERSION = "v1.2.3" 或 'v1.2.3'
    pattern = r'APP_VERSION\s*=\s*["\']v?(\d+)\.(\d+)\.(\d+)["\']'
    match = re.search(pattern, content)
    
    if not match:
        print("错误: 在 config.py 中未找到符合格式的 APP_VERSION (例如 v1.0.0)")
        sys.exit(1)
        
    major, minor, patch = map(int, match.groups())
    new_patch = patch + 1
    new_version = f"v{major}.{minor}.{new_patch}"
    
    # 替换内容
    new_content = re.sub(pattern, f'APP_VERSION = "{new_version}"', content)
    
    config_path.write_text(new_content, encoding='utf-8')
        
    print(f"版本号已更新: v{major}.{minor}.{patch} -> {new_version}")
    return new_version

def release_version(skip_push=False):
    """发布新版本：自动增加版本号、打标签并推送到远程仓库"""
    print("正在准备发布新版本...")
    
    try:
        # 检查是否安装了 git
        subprocess.run(["git", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: 未找到 git 命令，请确保已安装 Git。")
        sys.exit(1)
        
    try:
        # 1. 自动增加版本号
        new_version = increment_version()
        
        # 2. 提交版本号变更
        print("正在提交版本号变更...")
        subprocess.run(["git", "add", "src/core/config.py"], check=True)
        subprocess.run(["git", "commit", "-m", f"chore: bump version to {new_version}"], check=True)
        
        # 3. 打标签
        print(f"正在创建标签: {new_version} ...")
        subprocess.run(["git", "tag", new_version], check=True)

        if skip_push:
            print(f"\n已完成本地发布准备: {new_version}")
            print("已跳过推送。您可以稍后手动执行以下命令：")
            print("git push origin main")
            print(f"git push origin {new_version}")
            return

        # 4. 推送代码与标签
        try:
            print("正在推送代码变更...")
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("正在推送标签...")
            subprocess.run(["git", "push", "origin", new_version], check=True)
            print(f"\n成功发布版本 {new_version}！")
            print("GitHub Actions 将自动开始构建并发布 Release。")
            print("查看进度: https://github.com/STlxx-lin/20250914/actions")
        except subprocess.CalledProcessError:
            print("\n警告: 网络异常导致推送失败，但本地版本提交与标签已创建。")
            print("请网络恢复后手动执行：")
            print("git push origin main")
            print(f"git push origin {new_version}")
        
    except subprocess.CalledProcessError as e:
        print(f"\n发布流程出错: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="工单管理系统打包脚本")
    parser.add_argument("--onefile", action="store_true", help="打包成单个可执行文件")
    parser.add_argument("--debug", action="store_true", help="仅构建带控制台的调试版本")
    parser.add_argument("--standard", action="store_true", help="仅构建不带控制台的标准版本")
    parser.add_argument("--release", action="store_true", help="发布新版本(打标签并推送)")
    parser.add_argument("--release-local", action="store_true", help="仅本地发布(提交+打标签，不推送)")
    args = parser.parse_args()
    
    # 如果指定了 --release，则执行发布流程并退出
    if args.release:
        release_version(skip_push=False)
        return
    if args.release_local:
        release_version(skip_push=True)
        return
    
    current_platform = platform.system()
    print(f"当前平台: {current_platform}")
    print(f"单文件模式: {args.onefile}")
    
    # 调试选项：True 为仅调试版，False 为仅标准版，None 为默认双版本
    debug_mode = True if args.debug else (False if args.standard else None)
    
    # 安装依赖
    install_dependencies()
    
    if current_platform == "Windows":
        build_windows(args.onefile)
        print("\n=== 构建完成 ===")
        if args.onefile:
            print(f"Windows 可执行文件: dist/WorkOrder_System_{APP_VERSION}_PyInstaller.exe")
        else:
            print(f"Windows 可执行文件目录: dist/WorkOrder_System_{APP_VERSION}_PyInstaller/")
        print("\n如需构建 macOS 版本，请在 macOS 系统上运行:")
        print("python scripts/build_script.py")
        
    elif current_platform == "Darwin":  # macOS
        build_mac(args.onefile, debug=debug_mode)
        print("\n=== macOS 打包全部完成 ===")
        print(f"产物已存放于 dist/ 目录中。")
        print("\n如需构建 Windows 版本，请在 Windows 系统上运行:")
        print("python scripts/build_script.py")
        
    else:
        print(f"不支持的平台: {current_platform}")
        print("支持的平台: Windows, macOS")
        sys.exit(1)

if __name__ == "__main__":
    main()
