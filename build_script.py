#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工单管理系统打包脚本
支持 Windows 和 macOS 平台的单文件可执行程序打包
"""

import os
import sys
import platform
import subprocess
import argparse
# 导入版本号
from config import APP_VERSION

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
    spec_file = "工单管理系统.spec"
    if onefile:
        # 确保 spec 文件中设置了 onefile=True
        pass  # 已在 spec 文件中设置
    subprocess.run([sys.executable, "-m", "PyInstaller", spec_file], check=True)
    # 生成带版本号的文件名
    exe_name = f"工单管理系统{APP_VERSION}.exe"
    print(f"Windows 版本构建完成: dist/{exe_name}")

def build_mac(onefile=False):
    """构建 macOS 版本，同时生成DMG安装包"""
    print(f"正在构建 macOS 版本 (单文件: {onefile})...")
    spec_file = "工单管理系统_mac.spec"
    # 确保在spec文件中设置了正确的onefile参数
    # 这里我们已经在spec文件中直接设置了one_file=True
    # 执行打包命令
    subprocess.run([sys.executable, "-m", "PyInstaller", spec_file], check=True)
    
    # 生成带版本号的文件名
    if onefile:
        exe_name = f"工单管理系统{APP_VERSION}_mac"
        print(f"macOS 单文件版本构建完成: dist/{exe_name}")
    else:
        app_name = f"工单管理系统{APP_VERSION}_mac.app"
        print(f"macOS App版本构建完成: dist/{app_name}")
    
    # 生成DMG安装包
    if platform.system() == "Darwin":  # 确保在macOS系统上运行
        print("正在生成DMG安装包...")
        dmg_name = f"工单管理系统{APP_VERSION}_mac.dmg"
        app_path = os.path.join("dist", f"工单管理系统{APP_VERSION}_mac.app")
        dmg_path = os.path.join("dist", dmg_name)
        
        # 使用hdiutil（macOS系统自带工具）创建DMG文件
        # 步骤1: 创建临时目录
        temp_dir = os.path.join("dist", "temp_dmg")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # 步骤2: 将App复制到临时目录
            import shutil
            shutil.copytree(app_path, os.path.join(temp_dir, f"工单管理系统{APP_VERSION}_mac.app"))
            
            # 步骤3: 添加Applications链接（macOS安装惯例）
            applications_link = os.path.join(temp_dir, "Applications")
            subprocess.run(["ln", "-s", "/Applications", applications_link], check=True)
            
            # 步骤4: 创建DMG文件
            subprocess.run([
                "hdiutil", "create", "-volname", f"工单管理系统{APP_VERSION}", 
                "-srcfolder", temp_dir, "-ov", "-format", "UDZO", dmg_path
            ], check=True)
            
            print(f"macOS DMG安装包构建完成: {dmg_path}")
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description="工单管理系统打包脚本")
    parser.add_argument("--onefile", action="store_true", help="打包成单个可执行文件")
    args = parser.parse_args()
    
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