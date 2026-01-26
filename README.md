# 工单管理系统 (Work Order Management System)

本项目是一个专为多角色、多部门协作设计的工单管理系统。它由一个基于 **PySide6** 的桌面应用程序和一个 **PHP** 开发的现代化数据看板网站组成，后端共享同一个 **MySQL** 数据库。

系统旨在简化和自动化工单处理流程，涵盖从工单创建、分配、处理到完成的全过程，并提供强大的数据可视化和分析功能。

## 🚀 功能特点

### 桌面端应用 (Python/PySide6)
- **多角色权限**: 支持采购、摄影、美工、剪辑、运营、销售等多种角色，提供定制化操作界面。
- **工单全生命周期管理**: 实时更新状态，支持按部门筛选，查看完整操作日志。
- **自动化协作**: 
  - 任务自动流转
  - 关键操作自动记录日志
  - 钉钉/企业微信消息通知
- **便捷操作**: 
  - 文件/文件夹路径双击打开
  - 运营产品信息管理（标题、关键词、URL）
- **管理员功能**: 专属管理面板，查看系统所有操作日志。

### Web 数据看板 (PHP)
- **现代化仪表盘**: Apple/Nike 风格设计，实时展示总工单数、日志数等核心指标。
- **图表分析**: 使用 Chart.js 动态展示工单趋势、角色活动分布等。
- **高级查询**: 卡片式工单列表，支持多维度筛选和异步详情加载。
- **深度分析**: 提供部门效率评级、多维度数据报表。

## 🛠️ 环境要求

- **Python**: 3.8+
- **Database**: MySQL 5.7+ / MariaDB 10.2+
- **Web Server**: Nginx/Apache (PHP 7.4+) - *用于部署Web看板*

## 📦 安装与配置

### 1. 克隆项目

```bash
git clone <repository_url>
cd pyproj
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 数据库配置

1. 导入数据库结构文件 `mcs_by_takuya.sql` 到您的 MySQL 数据库中。
2. 复制并修改配置文件：
   
   打开 `config.py` 文件，根据您的环境配置数据库连接信息：

   ```python
   # config.py
   
   # 数据库配置
   DB_CONFIG_1 = {
       'host': 'your_host',
       'database': 'your_db_name',
       'user': 'your_username',
       'password': 'your_password',
       # ...
   }
   
   # 选择使用的配置
   DB_SWITCH = 'db1'
   ```

### 4. 其他配置

在 `config.py` 中还可以配置：
- **通知类型**: `dingtalk` (钉钉), `wechat_work` (企业微信), 或 `both`。
- **管理员密码**: 修改 `ADMIN_PASSWORD`。

## ▶️ 运行应用

```bash
python main.py
```

## � 打包部署

项目包含自动化打包脚本，支持构建 Windows Exe 和 macOS App/DMG。

```bash
# Windows / macOS 通用
python build_script.py

# 打包成单文件 (One-file mode)
python build_script.py --onefile
```

构建产物将输出到 `dist/` 目录。

## �📂 项目结构

```
e:\2025\pyproj/
├── main.py                 # 程序入口
├── config.py               # 配置文件
├── database.py             # 数据库操作层
├── api_manager.py          # API 交互层
├── requirements.txt        # 依赖列表
├── ui/                     # 界面模块
│   ├── character_selection.py  # 角色选择界面
│   ├── main_window.py          # 主窗口逻辑
│   └── ...
├── build_script.py         # 打包脚本
├── mcs_by_takuya.sql       # 数据库初始化脚本
├── MANUAL.md               # 详细维护手册
└── ...
```

## 📖 详细文档

更多详细功能说明和维护指南，请参阅 [MANUAL.md](MANUAL.md)。
