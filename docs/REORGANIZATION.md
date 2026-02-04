# 项目重构与分类整理说明

本项目已进行系统化的目录结构重构，以提高代码的可维护性和扩展性。以下是新的目录结构说明及使用指南。

## 1. 目录结构

```
e:\2025\pyproj\
├── main.py                 # 项目启动入口
├── src/                    # 源代码根目录
│   ├── main.py             # 应用程序主逻辑
│   ├── core/               # 核心模块 (配置, 数据库, API)
│   │   ├── config.py
│   │   ├── database.py
│   │   └── api_manager.py
│   └── ui/                 # 界面模块
│       ├── main_window.py
│       ├── character_selection.py
│       └── ...
├── scripts/                # 脚本与工具
│   ├── build_nuitka.py     # Nuitka 打包脚本
│   ├── build_script.py     # PyInstaller 打包脚本
│   ├── update_work_order_status.py # 工单状态更新脚本
│   └── 一键打包.bat        # Windows 一键打包工具
├── specs/                  # 打包配置文件 (*.spec)
├── sql/                    # 数据库脚本
│   └── mcs_by_takuya.sql
├── docs/                   # 文档
│   └── REORGANIZATION.md   # 本文档
└── README.md               # 项目说明
```

## 2. 如何运行

### 开发环境运行
在项目根目录下运行：
```bash
python main.py
```
或者：
```bash
python src/main.py
```

### 脚本运行
运行工单状态更新脚本：
```bash
python scripts/update_work_order_status.py [参数...]
```

## 3. 如何打包

### Windows 一键打包
直接运行 `scripts/一键打包.bat`。

### 手动打包
使用 Nuitka:
```bash
python scripts/build_nuitka.py
```
使用 PyInstaller:
```bash
python scripts/build_script.py
```

## 4. 关键变更说明
- **引用路径更新**: 所有模块引用已更新为绝对路径导入 (如 `from src.core.database import ...`)。
- **构建脚本适配**: 打包脚本已更新以适配新的目录结构。
- **入口文件**: 根目录保留 `main.py` 作为入口，方便使用。

如有任何问题，请参考 `src/` 下的具体代码实现。
