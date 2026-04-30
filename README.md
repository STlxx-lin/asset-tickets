# 工单管理系统 (Work Order Management System)

多角色协作工单管理系统，包含一个基于 **PySide6** 的桌面端和一个基于 **PHP** 的数据看板，后端共享 **MySQL** 数据库。

系统目标是把工单从创建、分配、执行、回传到归档的全过程标准化，同时为管理者提供可视化统计与运营决策支持。

## 目录

- [项目亮点](#项目亮点)
- [功能概览](#功能概览)
- [技术架构](#技术架构)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [运行与打包](#运行与打包)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 项目亮点

- **多角色协同**：支持采购、摄影、美工、剪辑、运营、销售等角色按权限操作。
- **全流程追踪**：工单状态、操作日志、部门流转清晰可追溯。
- **自动化通知**：可对接钉钉、企业微信，减少人工同步成本。
- **可视化看板**：基于 Chart.js 的统计图表，支持趋势和分布分析。
- **设计统一**：Web 看板采用简洁、统一、响应式的页面布局与交互风格。

## 功能概览

### 桌面端 (Python / PySide6)

- **角色化操作界面**：不同角色进入不同工作流与操作入口。
- **工单生命周期管理**：覆盖创建、指派、处理、验收、归档。
- **关键动作自动记录**：重要环节自动写入日志，便于审计与排障。
- **便捷日常操作**：支持路径双击打开、产品信息维护（标题/关键词/URL）。
- **管理员视图**：集中查看系统运行情况与全量日志。

### Web 看板 (PHP)

- **核心指标总览**：总工单数、处理进度、日志规模等指标可视化呈现。
- **趋势与分布图表**：按时间、角色、部门维度展示业务变化。
- **多维筛选查询**：卡片化列表配合筛选条件快速定位目标工单。
- **管理分析报表**：支持部门效率评级与多指标分析。

## 技术架构

```text
[PySide6 Desktop] ----\
                        >---- [MySQL] ---- [PHP Dashboard]
[Automation/Notify] ---/
```

- **Desktop（PySide6）**：承担业务操作主流程。
- **Dashboard（PHP）**：承担数据统计展示与管理分析。
- **Database（MySQL）**：统一存储工单、日志、配置等核心数据。
- **Core Modules（src/core）**：封装配置、数据库访问、接口调用等基础能力。

## 环境要求

- **Python**：3.12+
- **Database**：MySQL 5.7+ / MariaDB 10.2+
- **Web Server**：Nginx/Apache + PHP 7.4+（部署 Web 看板时需要）

## 快速开始

### 1. 获取代码

```bash
git clone <repository_url>
cd pyproj
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 初始化数据库

1. 创建数据库。
2. 导入 `sql/mcs_by_takuya.sql`。
3. 确认数据库账号具备读写权限。

### 4. 配置连接

编辑 `src/core/config.py`，填入真实数据库信息。

```python
# src/core/config.py

# 数据库配置
DB_CONFIG_1 = {
    "host": "127.0.0.1",
    "database": "your_db_name",
    "user": "your_username",
    "password": "your_password",
}

# 选择使用的数据库配置
DB_SWITCH = "db1"
```

### 5. 启动应用

```bash
python main.py
```

## 配置说明

主要配置文件：`src/core/config.py`

- `DB_CONFIG_1` / `DB_CONFIG_2`：数据库连接参数。
- `DB_SWITCH`：选择当前生效的数据库配置。
- `NOTIFY_TYPE`：通知类型，可选 `dingtalk`、`wechat_work`、`both`。
- `ADMIN_PASSWORD`：管理员口令（建议上线前改为强密码）。

建议：

- 生产环境使用独立数据库账号，最小权限原则授权。
- 不要把真实密码直接提交到仓库，可改为环境变量读取。

## 运行与打包

### 本地运行

```bash
python main.py
```

### 打包发布

```bash
# 使用 Nuitka 打包（推荐）
python scripts/build_nuitka.py

# 使用 PyInstaller 打包
python scripts/build_script.py

# Windows 一键打包脚本
scripts/一键打包.bat
```

构建产物通常输出到项目根目录或 `dist/` 目录。

## 项目结构

```text
e:\2025\pyproj/
├── main.py
├── requirements.txt
├── .github/
├── docs/
├── scripts/
│   ├── build_nuitka.py
│   ├── build_script.py
│   └── ...
├── specs/
├── sql/
├── src/
│   ├── core/
│   │   ├── api_manager.py
│   │   ├── config.py
│   │   └── database.py
│   └── ui/
│       ├── main_window.py
│       └── ...
└── README.md
```

## 常见问题

### 1. 启动时报数据库连接失败

- 检查 `config.py` 中的主机、端口、库名、账号密码。
- 确认 MySQL 服务已启动且可从当前机器访问。
- 确认导入了 `sql/mcs_by_takuya.sql`。

### 2. Web 看板没有数据

- 检查看板连接的数据库是否与桌面端一致。
- 检查时区和编码设置，避免统计维度错位。

### 3. 通知没有发送

- 检查 `NOTIFY_TYPE` 配置是否正确。
- 检查钉钉/企业微信 webhook 或凭证是否有效。

## 贡献指南

- 提交前请先阅读 `CONTRIBUTING.md`。
- 行为规范请遵守 `CODE_OF_CONDUCT.md`。
- 安全问题请按 `SECURITY.md` 指引私下上报。

## 许可证

本项目使用 **MIT License**，详见 `LICENSE` 文件。
