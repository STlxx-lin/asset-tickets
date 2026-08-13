# 项目文件总览

> 版本：v1.17.10 · Python 3.x · PySide6 · PyMySQL · MySQL

---

## 目录结构

```
pyproj/
├── main.py                          # 程序入口，启动 QApplication
├── requirements.txt                 # Python 依赖清单
├── .env.example                     # 环境配置示例（复制为 .env 使用，.env 不入库）
├── app_icon.ico                     # 应用图标
├── README.md
├── CHANGELOG.md
│
├── src/                             # 源代码根包
│   ├── main.py                      # 应用初始化（登录→主窗口）
│   │
│   ├── core/                        # 业务逻辑与基础设施层
│   │   ├── config.py                # 全局配置（版本号、DB、通知类型、调试开关、.env 加载、功能开关缓存）
│   │   ├── database.py              # 数据库封装（db_manager 单例，常驻连接，所有 SQL 操作）
│   │   ├── api_manager.py           # 外部 API 封装（api_manager 单例，统一时间字段映射）
│   │   ├── status_sync.py           # ★ 状态/时间同步与回滚封装（update_status_with_api 等）
│   │   ├── paths.py                 # 路径常量与 to_local_path 工具函数
│   │   └── notification.py          # 消息推送（钉钉/企业微信配置、发送、DB 读写）
│   │
│   └── ui/                          # 界面层
│       ├── main_window.py           # 主窗口（约 3950 行）
│       ├── video_preview.py         # 通用音视频/图片混合预览控件 VideoPreviewWidget
│       ├── task_manager.py          # 后台文件任务队列 UI + Task 线程（原 tasks.py 已合并于此）
│       ├── work_order_detail.py     # 工单详情只读弹窗（WorkOrderDetailDialog）
│       ├── character_selection.py   # 登录后角色/产线选择对话框
│       ├── path_check.py            # 路径文件检查对话框（管理员：存在性/文件数/无用内容/打开/删除）
│       ├── path_permission_check.py # 路径权限检查对话框（按角色检查读/写权限，异步扫描）
│       │
│       └── process_dialogs/         # 工单处理对话框子包
│           ├── __init__.py          # 导出 show_process_order_dialog 调度入口
│           ├── dispatcher.py        # 按 role 路由，调用对应角色函数
│           ├── photography.py       # 采购/摄影
│           ├── video_review.py      # 视频审核
│           ├── video_post_review.py # 视频后期审核
│           ├── post_review_combined.py # ★ 后期审批合并对话框（双审批角色，切换按钮）
│           ├── art.py               # 美工
│           ├── art_post_review.py   # ★ 美工后期审批
│           ├── editing.py           # 剪辑
│           ├── ops.py               # 运营
│           └── sales.py             # 销售
│
├── scripts/                         # 运维与构建脚本
├── sql/mcs_by_takuya.sql            # 数据库初始化 DDL（已清理死表）
└── docs/                            # NOTIFICATION_MIGRATION.md / REORGANIZATION.md
```

---

## 各模块职责

### `src/core/`

| 文件 | 职责 |
|---|---|
| [config.py](file:///e:/2025/pyproj/src/core/config.py) | 版本号、DB 切换开关、默认通知类型、`BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK` 调试开关 |
| [database.py](file:///e:/2025/pyproj/src/core/database.py) | `db_manager` 单例，封装所有 MySQL CRUD（工单、用户、通知配置、系统设置） |
| [api_manager.py](file:///e:/2025/pyproj/src/core/api_manager.py) | `api_manager` 单例，对接外部 HTTP 接口 |
| [paths.py](file:///e:/2025/pyproj/src/core/paths.py) | 平台路径常量（`VOLUMES`、`RAW_ROOT`…）、扩展名集合（`IMG_EXTS`、`VID_EXTS`）、13 个路径 lambda、`to_local_path()` |
| [notification.py](file:///e:/2025/pyproj/src/core/notification.py) | 钉钉/企业微信配置、全部发送函数、DB 读写、`LINE_NOTIFICATION_SETTINGS` 运行时缓存 |

### `src/ui/`

| 文件 | 职责 |
|---|---|
| [main_window.py](file:///e:/2025/pyproj/src/ui/main_window.py) | 主窗口框架：导航、Dashboard、Logs、Reports、Settings、用户管理、工单列表 |
| [video_preview.py](file:///e:/2025/pyproj/src/ui/video_preview.py) | 通用混合预览控件，`show_file(path)` 自适应图片/视频，内置播放器控制栏 |
| [task_manager.py](file:///e:/2025/pyproj/src/ui/task_manager.py) | 后台文件任务队列 UI，支持复制/移动进度展示 |
| [path_check.py](file:///e:/2025/pyproj/src/ui/path_check.py) | 路径文件检查（管理员）：存在性/文件数/无用内容/打开/删除/折叠 |
| [path_permission_check.py](file:///e:/2025/pyproj/src/ui/path_permission_check.py) | 路径权限检查（按角色读/写权限，异步扫描） |
| [work_order_detail.py](file:///e:/2025/pyproj/src/ui/work_order_detail.py) | 工单详情只读弹窗 |
| [character_selection.py](file:///e:/2025/pyproj/src/ui/character_selection.py) | 登录后角色/产线选择 |

### `src/ui/process_dialogs/`

| 文件 | 职责 | 对外接口 |
|---|---|---|
| `__init__.py` | 包入口，导出调度函数 | `show_process_order_dialog` |
| `dispatcher.py` | 按 `role` 路由到对应角色函数 | — |
| `photography.py` | 采购/摄影：上传素材、分发图片/视频 | `show_photography_dialog(parent, order_data, callbacks)` |
| `video_review.py` | 视频审核：文件列表 + 预览 + 审核通过/退回 | `show_video_review_dialog(...)` |
| `video_post_review.py` | 视频后期审核：同上 + 状态校验开关 | `show_video_post_review_dialog(...)` |
| `art.py` | 美工：领取图片素材、分发成品 | `show_art_dialog(...)` |
| `editing.py` | 剪辑：领取视频素材、提交审核、分发 | `show_editing_dialog(...)` |
| `ops.py` | 运营：领取素材、选品上架 | `show_ops_dialog(...)` |
| `sales.py` | 销售：领取素材 | `show_sales_dialog(...)` |

#### callbacks 字典约定

所有角色函数通过统一的 `callbacks` 字典与主窗口通信：

```python
callbacks = {
    'update_status': Callable[[str, str], None],  # (order_id, new_status)
    'add_file_task': Callable[..., None],          # 同 MainWindow.add_file_task 签名
    'log_action':    Callable[[str, str], None],   # (action_type, details)
}
```

---

## 重构前后对比

| 指标 | 重构前 | 重构后 |
|---|---|---|
| `main_window.py` 行数 | **7283 行** | ~3687 行（↓ 49%） |
| `to_local_path` 定义份数 | 2（重复） | 1（在 `paths.py`） |
| 通知相关代码 | 内联在 main_window.py | `src/core/notification.py` |
| 工单处理对话框文件数 | 0（全内联） | **8**（dispatcher + 7 角色） |
| 单角色文件平均行数 | — | ~450 行 |
| 可独立测试的角色对话框 | 否 | 是 |

---

## 模块依赖关系

```
main.py
  └── src/main.py
        └── src/ui/main_window.py
              ├── src/core/config.py
              ├── src/core/database.py
              ├── src/core/api_manager.py
              ├── src/core/paths.py
              ├── src/core/notification.py
              ├── src/ui/video_preview.py
              ├── src/ui/task_manager.py
              ├── src/ui/tasks.py
              ├── src/ui/work_order_detail.py
              ├── src/ui/character_selection.py
              └── src/ui/process_dialogs/
                    ├── dispatcher.py
                    │     ├── photography.py
                    │     ├── video_review.py
                    │     ├── video_post_review.py
                    │     ├── art.py
                    │     ├── editing.py
                    │     ├── ops.py
                    │     └── sales.py
                    └── (各文件均依赖 src/core/paths.py + src/core/database.py + src/core/notification.py)
```

> [!NOTE]
> `★NEW` 为本次重构新建文件；`★精简` 为重构后行数大幅减少的现有文件。
