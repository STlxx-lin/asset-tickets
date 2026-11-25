# 待执行工作与遗留问题清单 (Outstanding Work)

> 本清单是对 `PROJECT_AUDIT_REPORT.md`、`docs/audit_report.md`、`docs/code_review_2026-08-14.md`、
> `docs/PROJECT_DEEP_ANALYSIS.md`、`implementation_plan.md` 的**逐条源码复核结果**，
> 用来说明「哪些已经修完」「哪些仍然存在」「按什么顺序做」。
>
> - 核验基准：`db458e4`（分支 `minnow`）
> - 核验日期：2026-11-25
> - 核验方式：逐条比对源码与报告行号 + 运行 `python -m pytest tests -q`（24 passed）
> - 用途：作为后续迭代的唯一待办来源；完成一项就在「状态」列改为 ✅ 并补充对应 commit

---

## 一、速览

| 优先级 | 含义 | 条数 |
|---|---|---|
| **P0** | 数据丢失 / 安全 / 业务结果错误，尽快处理 | 5 |
| **P1** | 一致性与安全加固，1–2 周内 | 10 |
| **P2** | 架构、性能、可维护性，1 个月内 | 10 |
| **P3** | 工程化、脚本、文档，持续 | 9 |
| 合计 | | **34** |

已完成项（审计报告/代码审查报告中列为未修复或已修复的条目）见 [第二节](#二已完成项核验证据)，共 **26 项**已确认落地。

```text
当前状态一句话总结：
核心业务链路（状态同步回滚、文件移动幂等、任务失败阻断、乐观锁、DB 访问加锁、SSRF 防护）
已基本加固完成；剩余风险集中在「删除回收」「产品信息未落库」「主线程网络 I/O」
「路径未净化」「监控与测试门禁缺失」五处。
```

---

## 二、已完成项（核验证据）

下列条目在原报告中标记为未修复或"待办"，本轮复核确认**代码中已实现**，无需重复开发。

| 原编号 | 内容 | 证据位置 |
|---|---|---|
| C1 | 管理员空密码绕过 | `character_selection.py:336-352` 空密码/未配置直接拒绝 + `hmac.compare_digest` |
| C2 | move 模式删源无完整性校验 | `task_manager.py:75-82` `_is_valid_copy()` 校验类型与大小 |
| H1–H8 | 任务失败仍推进状态 | `task_manager.py:42` `update_status = Signal(bool, list)`；7 个角色文件均含 `task_ok` 守卫 |
| H9 | 本地写库失败仍调 API | `status_sync.py:29-47` `_apply_local()` 返回 rowcount/error，`<=0` 即中止 |
| H10 | `save_product_info` 非事务 | `database.py:661-686` `connection.begin()` + 整体 rollback |
| H11 | DB 单例并发无锁 | `database.py:24-43` `_db_locked` 可重入锁，49 个公开方法中 48 个已装饰 |
| H12 | 编辑工单文件移动后 DB 失败无回滚 | `main_window.py:3025-3108` `moved_pairs` 反向回滚 |
| H15/H16 | 暂停状态取消失效 / 退出崩溃 | `task_manager.py:105-112`（暂停循环内响应取消）、`669-684`（closeEvent 取消+wait） |
| H17/H18 | 扫描 worker 未中断 | `path_check.py:235,746`、`path_permission_check.py:244,454` |
| H21 | `refresh_work_orders` 级联 3~4 次 | `main_window.py:3543-3567` `blockSignals` 包裹 + `all_orders_data` 复用 |
| H26 | 校验脚本失败仍 exit 0 | `full_audit.py:166`、`validate_notification.py:75`、`validate_refactor.py:87-88` |
| H28 | 脚本引用不存在的 `_headers` | `update_work_order_status.py:35-45` 改走 `api_manager.update_work_order_status` |
| H29 | `upgrade_db_fields.py` 无备份直接 ALTER | `upgrade_db_fields.py:31-57` SHOW CREATE TABLE 备份 + 输入 `YES` 确认 |
| R1-01 | `build_script.py` 缺 `import shutil` | `build_script.py:13` |
| R1-02 | 循环闭包晚绑定 (B023) | `clean_video_source_dialog.py:575,581`、`path_check.py:238`、`path_permission_check.py:247` 全部默认参数绑定 |
| D-01 | `has_pending_edit_review` 倒推日志死锁 | `status_sync.py:167-181` 按时间倒序取最新相关事件，只有「提交视频后期审核」才返回 True |
| D-02(SEC-01) | 打包捆绑明文 `.env` | `specs/*.spec:16-18 / 76-78`、`build_nuitka.py:285,336-338` 只打 `.env.example` |
| SEC-02 | 8MB 生产 SQL Dump | `sql/mcs_by_takuya.sql` 现为 11KB 纯结构，`INSERT` 数 = 0 |
| SEC-04 | `autocommit=True` 致 rollback 失效 | `config.py:99,109` `'autocommit': False` |
| SEC-05 | 回滚反向布尔求值 | `status_sync.py:48` `if res <= 0` |
| SEC-07 | 空部门列表全量越权 | `database.py:131-134` 显式空列表直接返回 `[]` |
| 安全 | API / Webhook SSRF | `api_manager.py:20-40`（协议+主机+解析 IP 子集校验）、`notification.py:50-85` |
| 安全 | 日志详情 HTML 注入 | `work_order_detail.py:568-589` `html.escape` |
| 安全 | 视频预览 duration=-1 异常区间 | `video_preview.py:182-188` |
| 安全 | 运营产品列表按下标误删 | `ops.py:480-495` 倒序 pop + `selected_products.clear()` |
| 安全 | 日志写入被 `isVisible()` 吞掉 | `ops.py:532-560`、`sales.py:251-266` 日志/状态更新移到 isVisible 判断之外 |
| 安全 | 非 Windows 访问 `e.winerror` | `photography.py:519,652,737` 改为 `getattr(e, 'winerror', None)` |
| 重构 | `main_window.py` 拆出 7 个角色对话框 + `paths.py` + `notification.py` | `src/ui/process_dialogs/*`、`src/core/paths.py`、`src/core/notification.py` |
| 重构 | 重复的 `to_local_path` 合并 | 全仓库仅 `src/core/paths.py:100` 一处定义 |

---

## 三、待执行清单

> 字段说明：**状态** ⬜ 未开始 / 🟨 进行中 / ✅ 已完成；**影响** 为不修的后果。

### P0 — 数据丢失 / 业务结果错误（建议首个迭代完成）

#### TODO-01 工单删除无回收站，DB 删除失败即文件永久丢失

- 状态：⬜
- 位置：`src/ui/main_window.py:3754-3820`（`handle_delete_order`）、`:3798` `shutil.rmtree(path)`
- 现状：当前顺序是「先物理删文件 → 再删 DB」，`delete_failures > 0` 时保留 DB 记录并 return；
  但 **若 `db_manager.delete_work_order()` 失败，文件已经不可恢复**（仅弹"联系管理员"）。
- 影响：误删 / DB 抖动即造成不可逆资产损失，审计报告 SEC-06 的核心诉求（回收隔离）未落地。
- 建议：
  1. 改为移动到回收目录（如 `.../_回收站/{order_id}_{timestamp}/`）而不是 `rmtree`；
  2. 先删 DB（事务内写 `deleted_at` 软删标记）→ 成功后再移动到回收站；
  3. 回收目录保留 N 天，由管理员手动清理。
- 验收：模拟 DB 删除失败 → 文件完好且可从回收目录恢复；模拟文件移动失败 → DB 记录保留。

#### TODO-02 运营「添加产品信息」从不落库

- 状态：⬜
- 位置：`src/ui/process_dialogs/ops.py:323-497`；`src/core/database.py:661`（`save_product_info` 无任何调用方）
- 现状：`products_list` 只存在于内存，仅写日志 + 推进状态到「已上架」；对话框关闭后产品信息全部丢失。
  `save_product_info` / `get_product_info` 两个方法在整个 `src/` 内零引用。
- 影响：运营上架的核心数据（标题/关键词/URL）不持久化，属于**功能性缺陷**。
- 建议：对话框打开时 `get_product_info()` 回填；添加/删除后调用 `save_product_info()`（已有事务保护）；
  失败时提示且不回退状态。
- 验收：添加 3 条产品 → 关闭重开工单，3 条仍在；删除 1 条 → 重开后仍为 2 条。

#### TODO-03 视频后期审核可对空目录「审核通过」

- 状态：⬜
- 位置：`src/ui/process_dialogs/video_post_review.py:257-268`（`files_found`）、`:410`（`pass_btn`）、`:427`（`on_approve`）
- 现状：`files_found` 为空时没有 `if not files_found: return` 之类守卫，「审核通过」按钮始终可点，
  `on_approve()` 直接 `update_status_with_api('后期审核通过')`。
- 影响：成品目录为空/网络盘未挂载时也会把工单推进到「后期审核通过」，随后剪辑无法分发。
- 建议：`files_found` 为空时禁用 `pass_btn` 并显示"未找到可审核视频"。
- 验收：断开网络盘打开对话框 → 通过按钮置灰并给出原因。

#### TODO-04 主线程同步 HTTP 请求（白屏假死）

- 状态：⬜
- 位置：`src/ui/main_window.py:1083`（`create_work_order`）、`src/ui/process_dialogs/photography.py:560`、
  `src/ui/process_dialogs/video_review.py:441`、`video_post_review.py:429`、`src/core/notification.py:87`
- 现状：`api_manager._post_api` 默认 `timeout=10`，`update_status_with_api` / `update_time_with_api`
  在按钮槽函数里同步执行；`send_notification` 的 `requests.post(timeout=3)` 也在主线程。
- 影响：外部系统不可达时 UI 冻结 10–20 秒（叠加两次同步）；通知多产线时逐条串行阻塞。
- 建议：统一封装 `NetworkWorker(QRunnable)` + `QThreadPool`，回调通过信号回主线程更新 UI；
  至少先让通知发送走后台线程（无返回值，最安全）。
- 验收：拔掉外网/停掉外部 API 后点击「创建工单」「审核通过」，窗口仍可拖动，10 秒内给出失败提示。

#### TODO-05 路径未净化 + 管理员"路径检查"在主线程 rmtree

- 状态：⬜
- 位置：`src/core/paths.py:48-96`（13 个路径 lambda 直接 `os.path.join` 拼接）、
  `src/ui/path_check.py:534`（`run_check` 内同步查库）、`:597-601`（主线程 `shutil.rmtree`）
- 现状：`dept / id / model / name` 来自 DB 或用户输入，未过滤 `..`、`/`、`\`、盘符；
  `path_check` 对话框提供"删除路径"，路径由工单字段拼出后直接 `rmtree`。
- 影响：构造恶意工单字段可删除任意目录（路径穿越）；大目录删除时 UI 卡死。
- 建议：
  1. `paths.py` 增加 `_safe_segment()`，过滤 `..`, `/`, `\`, `:`, NUL，并做 `os.path.commonpath` 归属校验；
  2. `path_check` 的删除逻辑改到 worker 线程，并校验目标必须位于 `VOLUMES` 根之下。
- 验收：型号填 `../../Windows` → 生成路径被拒绝或落回受控子目录；删除大目录时界面不阻塞。

---

### P1 — 安全与一致性（1–2 周）

#### TODO-06 外部 API 明文 HTTP + 硬编码主机白名单

- 状态：⬜
- 位置：`src/core/api_manager.py:16`（`_API_ALLOWED_HOSTS = {'192.168.0.54'}`）、`:102-103`（`http://192.168.0.54:13000/...`）
- 建议：主机/端口/协议全部迁到 `.env`（`API_BASE_URL`），白名单由 URL 推导；支持 https；
  保留"解析 IP 必须落在允许网段"的防 DNS rebinding 逻辑。
- 验收：改 `.env` 即可切换环境，无需改代码；非白名单地址仍被拒绝。

#### TODO-07 DB 主机硬编码 + DB2 死配置

- 状态：⬜
- 位置：`src/core/config.py:90`（`DB_SWITCH`）、`:94,104`（`host` 写死）、`:103-110`（`DB_CONFIG_2` 全仓库零引用）、`.env.example`（`DB2_PASSWORD` 未被任何代码读取）
- 建议：`host/port/user` 全部走 `_env()`；删除 `DB_SWITCH`/`DB_CONFIG_2`/`DB2_PASSWORD` 或补齐使用方。
- 验收：`grep DB_CONFIG_2` 无残留；`.env.example` 与实际读取的变量一一对应。

#### TODO-08 子对话框反向修改 `parent.product_dir` / `parent.store_dir`

- 状态：⬜
- 位置：`art.py:364,445,456,476-482`、`editing.py:238`、`ops.py:513`、`sales.py:227`
- 现状：对话框把状态挂到 `MainWindow` 实例上（Monkey-patching），同角色并发打开两个工单时互相覆盖。
- 建议：状态私有化到 `show_xxx_dialog` 内的闭包变量（如 `state = {'product_dir': None}`），
  需要主窗口协同时显式通过 `callbacks` 传参。
- 验收：同时打开两个「剪辑」对话框，分别选不同成品路径，互不影响。

#### TODO-09 摄影师结束时间同步失败仍推进状态

- 状态：⬜
- 位置：`src/ui/process_dialogs/photography.py:558-575`
- 现状：`api_manager.update_work_order_time(... 'photographer_end_time')` 失败只弹提示并记录日志，
  随后照常执行 `if is_video_review_enabled(): new_status = '视频审核中'`，状态照旧推进。
- 建议：与 `status_sync` 保持同一语义——外部时间同步失败即中止状态推进（本地无该列，无法回滚，只能不推进）。
- 验收：外部 API 断网时上传素材，工单状态停留在原状态并给出可重试提示。

#### TODO-10 通知发送不校验响应码

- 状态：⬜
- 位置：`src/core/notification.py:86-90`
- 现状：`requests.post(...)` 只要不抛异常就记 `"推送成功"`，钉钉/企微返回 `errcode != 0` 或 4xx/5xx 仍算成功。
- 建议：解析 `status_code` 与响应体 `errcode`/`errmsg`，非成功记 error 日志（含前 200 字符）。
- 验收：故意配置失效 webhook → 日志出现明确的失败原因。

#### TODO-11 `get_feature_enabled` 缓存 DB 故障结果（失败开放）

- 状态：⬜
- 位置：`src/core/config.py:150-158`
- 现状：`db_manager.get_system_setting()` 异常时返回 `default`（`'1'`），该值被写入 `_FEATURE_CACHE` 永久缓存，
  且语义是"开启"——DB 故障时功能开关**失败开放**，且直到重启都不再重试。
- 建议：只在返回值为非 `None` 的**真实值**时缓存；异常/回退值不缓存；入口处显式传 `default='0'` 或增加「未知态」。
- 验收：模拟 DB 断开 → 开关读取每 30 秒重试一次，不会永久锁死。

#### TODO-12 日志详情为 NULL 时 `in` 判空抛 TypeError

- 状态：⬜
- 位置：`src/ui/main_window.py:3952-3954`
- 现状：`log.get('details', '')` 在键存在且值为 `None` 时返回 `None`，`"工单ID=..." in None` 抛 `TypeError`；
  `details` 列允许 NULL（`sql/mcs_by_takuya.sql:58`）。同文件 `3605`、`3648` 已正确写成 `or ''`。
- 建议：统一改为 `log.get('details') or ''`。
- 验收：手工插一条 `details=NULL` 的日志 → 右键「路径领取状态」不再崩溃。

#### TODO-13 日期筛选 `strptime` 无容错

- 状态：⬜
- 位置：`src/ui/main_window.py:3464-3468`
- 现状：`created_at` 为字符串时用固定格式 `"%Y-%m-%d %H:%M:%S"` 解析，任何偏差（含毫秒、`T` 分隔）抛 `ValueError`，
  整个 `apply_filters` 中断，列表空白。
- 建议：用 `datetime.fromisoformat` + 多格式兜底；解析失败按"不参与日期过滤"处理并记 warning。
- 验收：手工造一条 `2026-01-01T10:00:00` 记录，筛选不报错。

#### TODO-14 网络盘 `os.walk` / `listdir` 在 UI 线程且缺异常保护

- 状态：⬜
- 位置：`video_post_review.py:260`、`art.py:415,555`、`editing.py:395,451,580,657`、`video_review.py:242`、
  `ops.py:527`（`sales.py:243` 已有 try/except，`ops.py` 没有）、`work_order_detail.py:159`（构造时查库）
- 建议：扫描/统计类操作统一走 worker（可复用 `path_check` 的 worker 模式）；`listdir` 包 `OSError`。
- 验收：网络盘断连时打开任一对话框，200ms 内出窗口 + 可关闭，不崩溃。

#### TODO-15 摄影上传多目录多选时 `src_dir` 取 `files[0]` 所在目录

- 状态：⬜
- 位置：`src/ui/process_dialogs/photography.py:611`
- 现状：`src_dir=os.path.dirname(files[0])`，用户跨目录多选时，其余目录的文件会被拼成错误路径而全部失败，
  且任务判定为"部分失败"。
- 建议：禁止跨目录多选（选择后校验父目录一致），或按目录分组拆成多个 Task。
- 验收：跨两个目录各选 1 个文件 → 明确提示"请在同一目录内选择"。

---

### P2 — 架构 / 性能 / 可维护性（1 个月）

#### TODO-16 `MainWindow` 仍是上帝类（4141 行 / 64 个方法）

- 状态：⬜
- 位置：`src/ui/main_window.py`（重构前 7283 → 现 4141，`implementation_plan.md` 目标 ~3700）
- 建议：按页面拆控制器（`WorkOrderPage` / `LogsPage` / `SettingsPage` / `UserAdminPage`），
  主窗口只负责导航与依赖注入；用户管理对话框（约 800 行重复）单独抽 `user_dialog.py`。
- 验收：单文件 ≤ 1200 行，单类公开方法 ≤ 25。

#### TODO-17 任务列表无上限、卡片不回收

- 状态：⬜
- 位置：`src/ui/task_manager.py:649`（`self.tasks.append(task)` 无移除）、`:620-650`（`task_cards` 只增不减）
- 现状：`check_tasks` 每秒遍历全部历史任务，长时运行后 O(n) 上升、QThread 对象泄漏。
- 建议：任务完成后从 `self.tasks` 移除并 `deleteLater()`；`task_cards` 同步 pop。
- 验收：连续添加 200 个任务后，`len(self.tasks)` 有界，内存不增长。

#### TODO-18 `on_finished` 内 `msg_box.exec()` 阻塞主线程与其他任务

- 状态：⬜
- 位置：`src/ui/task_manager.py:638`
- 建议：改为非模态提示（`msg_box.open()`）或汇总到任务面板的"错误详情"。
- 验收：同时完成 3 个带错任务 → 不出现 3 层模态堆叠。

#### TODO-19 `notification` 模块导入即查库

- 状态：⬜
- 位置：`src/core/notification.py:312-313`（模块底部 `apply_notification_settings(load_notification_settings())`）
- 影响：任何 `import src.core.notification` 都触发建连 + 查询 + 可能的 seed 写入，拖慢启动、离线时卡住。
- 建议：改为显式 `init_notification()`，由 `main.py` 在闪屏阶段的后台线程调用。
- 验收：`import src.core.notification` 耗时 < 5ms，无网络活动。

#### TODO-20 状态常量 / 进度推导多处重复且已分叉

- 状态：⬜
- 位置：`main_window.py`（`calculate_art_status` / `calculate_edit_status`）、`work_order_detail.py:581-680`、
  `status_sync.py:167-181`、`art.py:235-246`、`path_check.py:111-131`
- 建议：新建 `src/core/workflow.py`（状态枚举 + 进度推导单一实现）与 `src/core/constants.py`（状态字符串/颜色/顺序）。
- 验收：全仓库状态字符串字面量只出现在 `constants.py`。

#### TODO-21 全局串行锁替代连接池

- 状态：⬜
- 位置：`src/core/database.py:24-43`
- 现状：`_db_locked` 把 48 个方法串行化，GUI 与后台任务互相等待，网络抖动时整体卡住。
- 建议：`threading.local()` 连接或轻量连接池（`DBUtils.PooledDB`），读操作可并发。
- 验收：一个长查询进行时，另一线程的短查询仍能在 200ms 内返回。

#### TODO-22 API 200 但响应非 JSON 被误判失败；时间解析失败返回 0

- 状态：⬜
- 位置：`src/core/api_manager.py:227-235`（`response.json()` 在外层 try 内）、`_convert_time_to_timestamp`（失败 `return 0`）
- 建议：JSON 解析独立 try，解析失败但状态码 200 视为成功并记录原始文本；时间解析失败返回 `None` 并跳过写入，
  避免把外部字段写成 0 时间戳。
- 验收：外部返回纯文本 `ok` → 判成功；非法时间串 → 不发送该字段。

#### TODO-23 `get_roles()` 读路径带写副作用

- 状态：⬜
- 位置：`src/core/database.py:94-101`（`INSERT IGNORE` + `commit`）
- 建议：seed 挪到显式初始化（`ensure_default_roles()`），读接口只读。
- 验收：只读账号调用 `get_roles()` 不报权限错误。

#### TODO-24 `sql/mcs_by_takuya.sql` DDL 漂移 + 1NF 违规 + 字符集混用

- 状态：⬜
- 位置：`sql/mcs_by_takuya.sql`
- 现状（已核验）：
  1. `mcs_by_takuya_work_orders` 缺 `version`（乐观锁）与 `edit_product_path` 两列，新库初始化即无法运行；
  2. 缺 `work_order_status_history`、`app_system_settings`、`app_notification_line_settings`、`mcs_by_takuya_review_feedback` 四张表；
  3. 表名错误：第 24 行为 `mcs1_by_takuya_users`（应为 `mcs_by_takuya_users`），与第 134 行重复定义；
  4. 1NF：`users.role` / `users.department` 存逗号分隔多值；
  5. 字符集混用：`utf8mb4_general_ci` 与 `utf8mb4_unicode_ci` 并存。
- 建议：以 `database.py` 中的 `CREATE TABLE IF NOT EXISTS` 为准重建一份基线 DDL；拆分多值字段为关联表（分阶段）。
- 验收：空库执行该 SQL 后 `python main.py` 可正常登录与创建工单。

#### TODO-25 缺少 UI / 核心逻辑自动化测试

- 状态：⬜
- 位置：`tests/`（仅 `test_adversarial_challenger.py`，24 用例，覆盖 `has_pending_edit_review` / `get_work_orders` / `_rollback`）
- 缺口：`status_sync` 全流程、`task_manager` 移动幂等、`paths` 路径生成、7 个角色对话框的
  `update_status` 回调、`config` 功能开关。
- 建议：先补 `paths`、`status_sync`、`task_manager` 三个纯逻辑模块（可用 `tmp_path` + mock DB），目标覆盖率 ≥ 60%。
- 验收：CI 中 `pytest --cov` 输出报告且低于阈值即失败。

#### TODO-26 `status_sync._rollback` 无版本保护（并发 ABA）

- 状态：⬜
- 位置：`src/core/status_sync.py:41-47`
- 现状：回滚不带 `expected_version`（注释已说明"窗口极小"），但两次 API 超时（各 10s）后窗口可达 20 秒，
  期间他端可能已推进状态，回滚会把新状态覆盖回旧值。
- 建议：回滚也带版本号（写入时记录 `rowcount` 前后的 version），冲突时只记 error 不再覆盖。
- 验收：并发脚本模拟"回滚期间他端修改"→ 日志报冲突，不覆盖。

---

### P3 — 工程化 / 脚本 / 文档（持续）

#### TODO-27 CI 无 lint / 测试门禁，构建仅在版本号变化时触发

- 状态：⬜
- 位置：`.github/workflows/build.yml`（仅 `check_version` / `auto_tag` / `build` / `release` 四个 job）
- 现状：`pyproject.toml` 已配 `[tool.ruff]`，但 `ruff` 不在 `requirements.txt`，CI 也从不运行 `ruff` 与 `pytest`；
  `build` job 条件为 `needs.check_version.outputs.version_changed == 'true'`，PR 与普通 push **不会构建**。
- 建议：新增 `lint` / `test` job（`pip install ruff pytest pytest-cov`），作为 `build` 的 `needs`；
  PR 上至少跑 lint + test。
- 验收：故意提交一条 lint 违规 → PR 检查变红。

#### TODO-28 `scripts/full_audit.py` 仍硬编码本机绝对路径与 `.bak` 依赖

- 状态：⬜
- 位置：`scripts/full_audit.py:11-12`（`sys.path.insert(0, r'e:\2025\pyproj')`、`MW = r'e:\2025\pyproj\...'`）、`:127`（`.bak` 路径）
- 现状：代码审查 R4-01 标记未修；在非作者机器上第 1 步即 `FileNotFoundError`。
- 建议：路径全部改为 `Path(__file__).resolve().parent.parent`；`.bak` 对比段落删除（重构已完成，无对比价值）。
- 验收：在任意机器 `python scripts/full_audit.py` 正常输出且退出码反映真实结果。

#### TODO-29 一次性重构脚本残留

- 状态：⬜
- 位置：`scripts/patch_main_window.py`（按 `A_START=43 / C_START=3275` 硬编码行号删改源码，无内容断言）、
  `scripts/extract_dialogs.py`、`scripts/fix_dialog_refs.py`（会直接 `write_text` 改写 `process_dialogs/*`）
- 现状：重构已落地（`main_window.py` 4141 行），这些脚本再运行一次会破坏文件。
- 建议：整体删除，或移入 `scripts/archive/` 并在文件头加 "仅历史参考，请勿执行"。
- 验收：`scripts/` 下不存在可直接破坏工作区的脚本。

#### TODO-30 macOS PyInstaller 产物名与 spec 不一致

- 状态：⬜
- 位置：`scripts/build_script.py:57-70`（期望 `素材工单系统{ver}_mac.app`）vs `specs/工单管理系统_mac.spec:61-62`（实际 `工单管理系统{ver}_mac`）
- 影响：`build_mac()` 里 `app_path = dist/素材工单系统...app` 路径不存在，后续 DMG 步骤必失败。
- 建议：统一产物名（建议 spec 名为唯一来源，脚本从 spec 推导）。
- 验收：macOS 上 `python scripts/build_script.py` 能跑完并生成 `.dmg`。

#### TODO-31 spec 中 `one_file` / `onefile` 参数无效（静默忽略）

- 状态：⬜
- 位置：`specs/工单管理系统.spec:70`、`specs/工单管理系统_mac.spec:132`
- 现状：`PyInstaller.building.api.EXE.__init__(*args, **kwargs)` 接受任意 kwargs 但**不识别** `one_file`；
  单文件与否由是否使用 `COLLECT` 决定。当前写法给人"已开启单文件"的错觉。
- 建议：删除该参数，并在注释中说明"无 COLLECT 即为 onefile"。
- 验收：`pyinstaller specs/*.spec` 无 `Unknown option` 警告。

#### TODO-32 README 引用的截图不存在

- 状态：⬜
- 位置：`README.md:41,45,49`（`docs/images/desktop-main.png`、`ticket-detail.png`、`dashboard-overview.png`），`docs/images/` 目录不存在
- 建议：补图或改为纯文本说明；同时删除"Web 看板"截图（仓库中 0 个 `.php` 文件，属规划中组件）。
- 验收：README 渲染无裂图。

#### TODO-33 文档与代码漂移

- 状态：⬜
- 位置：
  - `project_files.md:30`（"约 3950 行"）、`:114`（对比表"~3687 行"）→ 实际 4141 行；
  - `CHANGELOG.md:5`（最新 `v1.18.0`）vs `src/core/config.py:3`（`APP_VERSION = "v1.18.37"`）；
  - `docs/audit_report.md` 与根目录 `PROJECT_AUDIT_REPORT.md` 仅 3 行差异，双份维护易再次分叉。
- 建议：行数改为"约值"并注明统计方式；CHANGELOG 补齐至当前版本；审计报告保留根目录一份，`docs/` 下改为链接。
- 验收：`grep` 文档中的行数/版本号与代码一致。

#### TODO-34 SQL 结构文件仍含内网地址与 `DROP TABLE`

- 状态：⬜
- 位置：`sql/mcs_by_takuya.sql:7`（`Source Host : 192.168.0.54:3306`）、各表 `DROP TABLE IF EXISTS`
- 现状：数据行已清空（`INSERT` 数 = 0），但仍暴露内网拓扑，且脚本误执行会清空生产表。
- 建议：注释头里的主机地址改为占位符；`DROP TABLE` 改为可选段落（默认注释）。
- 验收：`grep -i '192.168' sql/` 无结果。

---

## 四、建议执行顺序

```text
里程碑 M1（P0，1 周）      TODO-01 ~ TODO-05
    目标：杜绝数据永久丢失、产品信息可追溯、主线程不再冻结

里程碑 M2（P1，2 周）      TODO-06 ~ TODO-15
    目标：外部系统与 DB 配置化、对话框状态私有化、状态推进与外部同步严格一致

里程碑 M3（P2，1 个月）    TODO-16 ~ TODO-26
    目标：MainWindow 拆分、连接池、workflow 单一来源、基线 DDL、核心模块测试

里程碑 M4（P3，持续）      TODO-27 ~ TODO-34
    目标：CI 门禁（lint + test）、脚本清理、文档与代码一致
```

依赖关系提示：

- TODO-24（基线 DDL）应在 TODO-25（测试）之前完成，测试需要可重复建库。
- TODO-16（拆 MainWindow）会与 TODO-08 / TODO-12 / TODO-14 改动同文件，建议合并到同一迭代，
  先完成行为修复再拆文件，避免双重 diff。
- TODO-27（CI 门禁）建议尽早做，否则后续 P0/P1 修复缺少回归保护。

---

## 五、复现与验证命令

```bash
# 现有测试基线
python -m pytest tests -q          # 当前：24 passed

# 静态检查（需先安装：pip install ruff）
ruff check src scripts tests main.py

# 全量审计脚本（TODO-28 未完成前，仅作者机器可跑）
python scripts/full_audit.py
```

---

## 六、维护约定

1. 每完成一项：把「状态」改为 ✅，在条目末尾追加 `- 完成：<commit> <一句话>`。
2. 新增问题请沿用 `TODO-xx` 编号并标注优先级，不要直接改历史条目的描述。
3. 本文件是唯一待办来源；审计报告与代码审查报告仅作为历史证据保留，不再逐条维护状态。
