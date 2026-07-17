# main_window.py 功能模块化重构

## 背景

`main_window.py` 当前 **7283 行**，一个文件中混杂了路径常量、通知系统、对话框、UI 页面、用户管理、工单处理等多个不相关职责，维护成本极高。

本次重构目标：**减少 main_window.py 约 3500 行**，拆分出职责单一的独立模块，不改变任何现有业务逻辑。

---

## 决策汇总（Grill-me 确认）

| 决策点 | 结论 |
|---|---|
| 重心 | 优先拆分 `show_process_order_dialog`（约 3300 行，7 个角色分支） |
| 附带抽离 | 全局路径常量 + `to_local_path` → `src/core/paths.py` |
| 对话框结构 | 每个角色文件导出一个**顶层函数** `show_xxx_dialog(parent, order_data, callbacks)` |
| 共享回调 | 封装为 `callbacks` 字典传入（含 `update_status`、`add_file_task`、`log_action`） |
| 执行顺序 | **一次性完成**所有文件创建与主窗口改动 |

---

## 新建文件清单

### ① [NEW] `src/core/paths.py`

迁移内容（全部从 main_window.py 顶部提取）：

- 平台判断常量：`RAW_ROOT`, `ART_ROOT`, `VIDEO_ROOT`, `CENTER_ROOT`, `VOLUMES`
- 扩展名集合：`IMG_EXTS`, `VID_EXTS`
- 路径 lambda（13 个）：`PHOTOGRAPHY_UPLOAD`, `PHOTOGRAPHY_DIST_IMG`, `PHOTOGRAPHY_DIST_VIDEO`, `ART_GET_IMG_SRC`, `ART_GET_IMG_DEST`, `ART_DIST_OPS`, `ART_DIST_SALES`, `EDIT_GET_VIDEO_SRC`, `EDIT_GET_VIDEO_DEST`, `EDIT_DIST_OPS`, `EDIT_DIST_SALES`, `EDIT_POST_REVIEW_TRANSIT`, `OPS_GET_SRC`, `SALES_GET_SRC`
- 工具函数：`to_local_path(path_str)`（同时清除 main_window.py 中重复定义的第二份 `to_local_path`，共两份 → 保留一份）

### ② [NEW] `src/ui/process_dialogs/__init__.py`

只导出一个调度入口：

```python
from .dispatcher import show_process_order_dialog
__all__ = ['show_process_order_dialog']
```

### ③ [NEW] `src/ui/process_dialogs/dispatcher.py`

替代原 `show_process_order_dialog` 方法，根据 `role` 路由到各角色函数：

```python
def show_process_order_dialog(parent, order_data, callbacks):
    role = parent.role
    if role in ["采购", "摄影"]:
        from .photography import show_photography_dialog
        show_photography_dialog(parent, order_data, callbacks)
    elif role == "视频审核":
        from .video_review import show_video_review_dialog
        show_video_review_dialog(parent, order_data, callbacks)
    elif role == "视频后期审核":
        from .video_post_review import show_video_post_review_dialog
        show_video_post_review_dialog(parent, order_data, callbacks)
    elif role == "美工":
        from .art import show_art_dialog
        show_art_dialog(parent, order_data, callbacks)
    elif role == "剪辑":
        from .editing import show_editing_dialog
        show_editing_dialog(parent, order_data, callbacks)
    elif role == "运营":
        from .ops import show_ops_dialog
        show_ops_dialog(parent, order_data, callbacks)
    elif role == "销售":
        from .sales import show_sales_dialog
        show_sales_dialog(parent, order_data, callbacks)
```

### ④–⑩ 各角色对话框文件

| 文件 | 对应原代码行 | 角色 |
|---|---|---|
| `photography.py` | 3311–3894 | 采购/摄影 |
| `video_review.py` | 3895–4292 | 视频审核 |
| `video_post_review.py` | 4293–4696 | 视频后期审核 |
| `art.py` | 4697–5227 | 美工 |
| `editing.py` | 5228–5744 | 剪辑 |
| `ops.py` | 5745–6298 | 运营 |
| `sales.py` | 6299–6532 | 销售 |

每个文件结构：

```python
# e.g. photography.py
from PySide6.QtWidgets import ...
from src.core.paths import PHOTOGRAPHY_UPLOAD, PHOTOGRAPHY_DIST_IMG, ...
from src.core.database import db_manager

def show_photography_dialog(parent, order_data, callbacks):
    # 完整的对话框构建与 exec() 逻辑
    ...
```

---

## 修改文件

### [MODIFY] `src/ui/main_window.py`

1. **删除**顶部路径常量与工具函数（约 80 行），改为：
   ```python
   from src.core.paths import (VOLUMES, IMG_EXTS, VID_EXTS,
       PHOTOGRAPHY_UPLOAD, PHOTOGRAPHY_DIST_IMG, ..., to_local_path)
   ```
2. **删除**重复的 `to_local_path` 定义（108–135 行，第二份副本）
3. **删除** `show_process_order_dialog` 方法体（3275–6532 行），改为：
   ```python
   def show_process_order_dialog(self, order_data):
       from src.ui.process_dialogs import show_process_order_dialog as _dispatch
       callbacks = {
           'update_status': self.update_work_order_status_and_ui,
           'add_file_task': self.add_file_task,
           'log_action': self.log_action,
       }
       _dispatch(self, order_data, callbacks)
   ```

### [MODIFY] `src/core/paths.py` ← 新建后无需再修改

---

## callbacks 字典约定

```python
callbacks = {
    'update_status': Callable[[str, str], None],  # (order_id, new_status)
    'add_file_task': Callable[..., None],          # 同原 self.add_file_task 签名
    'log_action':    Callable[[str, str], None],   # (action_type, details)
}
```

对话框内调用示例：

```python
callbacks['update_status'](order_data['id'], '后期处理中')
callbacks['add_file_task'](name=task_name, files=..., src_dir=..., dest_dir=..., op_type='move')
callbacks['log_action']('剪辑领取素材', f"工单ID={order_data['id']}")
```

---

## 预期效果

| 指标 | 重构前 | 重构后 |
|---|---|---|
| main_window.py 行数 | 7283 | ~3700 |
| 路径相关重复 | 2 份 `to_local_path` | 1 份（在 paths.py） |
| 单角色对话框文件 | 0 | 7 个（平均 ~450 行） |
| 可测试性 | 极低 | 每个角色可单独测试 |

---

## 验证计划

1. 运行启动测试：`python -m pytest scratch/test_main_window_init.py`
2. 运行预览控件测试：`python -m pytest scratch/test_preview_widget_init.py`
3. 手动启动主程序，逐一点击 7 个角色的「办理工单」按钮，确认对话框正常弹出
4. 验证「视频后期审核」的 `BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK` 开关仍然有效

> [!IMPORTANT]
> `video_review.py` 和 `video_post_review.py` 中需要保留对 `VideoPreviewWidget` 的引用（已在上一轮重构中引入），以及 `BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK` 开关的导入。
