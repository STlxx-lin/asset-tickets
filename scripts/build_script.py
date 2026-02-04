#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工单管理系统打包脚本
支持 Windows 和 macOS 平台的单文件可执行程序打包
python build_script.py --release
"""

import os
import sys
import platform
import subprocess
import argparse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 导入版本号
from src.core.config import APP_VERSION

# 解决 Windows 环境下可能的编码问题
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

def install_dependencies():
    """安装依赖包"""
    print("正在安装依赖包...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    print("依赖包安装完成")

def build_windows(onefile=False):
    """构建 Windows 版本"""
    print(f"正在构建 Windows 版本 (单文件: {onefile})...")
    spec_file = "specs/工单管理系统.spec"
    if onefile:
        # 确保 spec 文件中设置了 onefile=True
        pass  # 已在 spec 文件中设置
    subprocess.run([sys.executable, "-m", "PyInstaller", spec_file], check=True)
    # 生成带版本号的文件名
    exe_name = f"素材工单系统{APP_VERSION}.exe"
    print(f"Windows 版本构建完成: dist/{exe_name}")

def build_mac(onefile=False):
    """构建 macOS 版本，同时生成DMG安装包"""
    print(f"正在构建 macOS 版本 (单文件: {onefile})...")
    spec_file = "specs/工单管理系统_mac.spec"
    # 确保在spec文件中设置了正确的onefile参数
    # 这里我们已经在spec文件中直接设置了one_file=True
    # 执行打包命令
    subprocess.run([sys.executable, "-m", "PyInstaller", spec_file], check=True)
    
    # 生成带版本号的文件名
    if onefile:
        exe_name = f"素材工单系统{APP_VERSION}_mac"
        print(f"macOS 单文件版本构建完成: dist/{exe_name}")
    else:
        app_name = f"素材工单系统{APP_VERSION}_mac.app"
        print(f"macOS App版本构建完成: dist/{app_name}")
    
    # 生成DMG安装包
    if platform.system() == "Darwin":  # 确保在macOS系统上运行
        print("正在生成DMG安装包...")
        dmg_name = f"素材工单系统{APP_VERSION}_mac.dmg"
        app_path = os.path.join("dist", f"素材工单系统{APP_VERSION}_mac.app")
        dmg_path = os.path.join("dist", dmg_name)
        
        # 使用hdiutil（macOS系统自带工具）创建DMG文件
        # 步骤1: 创建临时目录
        temp_dir = os.path.join("dist", "temp_dmg")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # 步骤2: 将App复制到临时目录
            import shutil
            shutil.copytree(app_path, os.path.join(temp_dir, f"素材工单系统{APP_VERSION}_mac.app"))
            
            # 步骤3: 添加Applications链接（macOS安装惯例）
            applications_link = os.path.join(temp_dir, "Applications")
            subprocess.run(["ln", "-s", "/Applications", applications_link], check=True)
            
            # 步骤4: 创建DMG文件
            subprocess.run([
                "hdiutil", "create", "-volname", f"素材工单系统{APP_VERSION}", 
                "-srcfolder", temp_dir, "-ov", "-format", "UDZO", dmg_path
            ], check=True)
            
            print(f"macOS DMG安装包构建完成: {dmg_path}")
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

import shutil
import re

def increment_version():
    """读取 config.py，增加版本号，并保存"""
    config_path = 'src/core/config.py'
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
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
    
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print(f"版本号已更新: v{major}.{minor}.{patch} -> {new_version}")
    return new_version

def release_version():
    """发布新版本：自动增加版本号、打标签并推送到远程仓库"""
    print(f"正在准备发布新版本...")
    
    try:
        # 检查是否安装了 git
        subprocess.run(["git", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: 未找到 git 命令，请确保已安装 Git。")
        sys.exit(1)
        
    try:
        # 1. 自动增加版本号
        new_version = increment_version()
        
        # 2. 提交版本号变更
        print(f"正在提交版本号变更...")
        subprocess.run(["git", "add", "config.py"], check=True)
        subprocess.run(["git", "commit", "-m", f"chore: bump version to {new_version}"], check=True)
        
        # 3. 推送代码变更 (包含 config.py 的修改)
        print(f"正在推送代码变更...")
        subprocess.run(["git", "push", "origin", "main"], check=True)

        # 4. 打标签
        print(f"正在创建标签: {new_version} ...")
        subprocess.run(["git", "tag", new_version], check=True)
        
        # 5. 推送标签
        print(f"正在推送标签...")
        subprocess.run(["git", "push", "origin", new_version], check=True)
        
        print(f"\n成功发布版本 {new_version}！")
        print("GitHub Actions 将自动开始构建并发布 Release。")
        print(f"查看进度: https://github.com/STlxx-lin/20250914/actions")
        
    except subprocess.CalledProcessError as e:
        print(f"\n发布流程出错: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="工单管理系统打包脚本")
    parser.add_argument("--onefile", action="store_true", help="打包成单个可执行文件")
    parser.add_argument("--release", action="store_true", help="发布新版本(打标签并推送)")
    args = parser.parse_args()
    
    # 如果指定了 --release，则执行发布流程并退出
    if args.release:
        release_version()
        return
    
    current_platform = platform.system()
    print(f"当前平台: {current_platform}")
    print(f"单文件模式: {args.onefile}")
    
    # 安装依赖
    install_dependencies()
    
    if current_platform == "Windows":
        build_windows(args.onefile)
        print("\n=== 构建完成 ===")
        if args.onefile:
            print(f"Windows 可执行文件: dist/工单管理系统{APP_VERSION}.exe")
        else:
            print(f"Windows 可执行文件目录: dist/工单管理系统{APP_VERSION}/")
        print("\n如需构建 macOS 版本，请在 macOS 系统上运行:")
        print("python build_script.py")
        
    elif current_platform == "Darwin":  # macOS
        build_mac(args.onefile)
        print("\n=== 构建完成 ===")
        if args.onefile:
            print(f"macOS 可执行文件: dist/工单管理系统{APP_VERSION}_mac")
        else:
            print(f"macOS 可执行文件目录: dist/工单管理系统{APP_VERSION}_mac.app")
        print(f"macOS DMG安装包: dist/工单管理系统{APP_VERSION}_mac.dmg")
        print("\n如需构建 Windows 版本，请在 Windows 系统上运行:")
        print("python build_script.py")
        
    else:
        print(f"不支持的平台: {current_platform}")
        print("支持的平台: Windows, macOS")
        sys.exit(1)

if __name__ == "__main__":
    main()