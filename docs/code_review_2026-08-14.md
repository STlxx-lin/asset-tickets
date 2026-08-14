# 代码审查报告(全量)

- 审查日期:2026-08-14
- 审查范围:`src/` 全部 25 个 Python 文件 + `scripts/` 11 个脚本 + `main.py`、`.env.example`、`requirements.txt`、`sql/mcs_by_takuya.sql`
- 审查方式:12 个并行审查单元(10 个逐文件单元 + 2 个交叉单元:危险模式扫描、跨文件重复代码),每个单元逐行阅读并交叉核验依赖模块,行号与 read 工具输出一致
- 完整分单元明细见 `.review/04~12_*.md` 与工作流输出(01~03 单元)

## 修复进展(2026-08-14 更新)

以下条目已在本轮修复完成并通过离线验证(`.review/verify_fixes.py`,全部通过):

| 条目 | 内容 | 文件 |
|---|---|---|
| C1 | 管理员空密码绕过:拒绝空密码、`hmac.compare_digest` 比较、未配置时 error 日志 | config.py、character_selection.py |
| C2 | move 删源前校验目标等价(类型+大小),不等价则不删源并记错误;copy 模式覆盖语义 | task_manager.py |
| H1-H8 | Task 信号携带 `(ok, errors)`,13 处 `update_status` 回调在任务失败时中止状态推进/通知/成功提示;photography 破坏性清理(删"不通过"目录+清反馈)移到复制成功之后;editing 提交审核 file_filter 修复(排除 源文件/不通过) | task_manager.py、art.py、art_post_review.py、editing.py、photography.py、ops.py、sales.py |
| H9 | status_sync 检查本地写库返回值,失败即跳过 API 同步;回滚逐一检查并如实上报;时间字段白名单统一到 database.TIME_FIELDS(补上缺失的 end_time) | status_sync.py、database.py |
| H10 | save_product_info DELETE+INSERT 显式事务化,中途失败整体回滚 | database.py |
| H11 | DatabaseManager 全部 46 个公开方法加 `@_db_locked` 可重入锁,串行化连接访问 | database.py |
| H15/H16 | 暂停循环响应取消;closeEvent 取消并 wait 运行中任务(5s 上限) | task_manager.py |
| H17/H18 | path_check/path_permission_check worker 支持 requestInterruption,对话框关闭时中断+wait | path_check.py、path_permission_check.py |
| H12 | 编辑工单 DB 更新失败时反向回滚已移动文件 | main_window.py |
| H13 | 删除工单改为先删文件后删 DB,删除失败保留 DB 记录;去掉 rmtree ignore_errors=True | main_window.py |
| H14 | `QLabel(order_data['id'])` int 崩溃 → str() | main_window.py |

待办(未在本轮修复):H19-H24(主线程同步 HTTP/网络盘操作异步化)、H23/H24(API 明文 HTTP/DB 主机配置化)、H25-H29(构建脚本)、大量 medium/low(常量单一来源、对话框基类抽取、死代码清理等,见架构性建议)。

## 严重程度统计

| 严重程度 | 数量(去重前约) | 说明 |
|---|---|---|
| critical | 2 | 空密码绕过管理员认证;move 任务删除源文件无完整性校验(数据丢失) |
| high | 约 30 | 状态与磁盘不一致、线程生命周期、主线程阻塞、构建链路失效、认证/传输安全 |
| medium | 约 90 | 边界缺陷、静默吞异常、性能瓶颈、可维护性 |
| low | 约 120 | 死代码、重复代码、魔法字符串、注释残留 |

合计约 240 条(含交叉单元与逐文件单元的重叠,实际去重后约 200 条)。

---

# Critical(2)

## C1. 管理员密码未配置时为空串,空密码可直接通过管理员认证

- **file**: `src/ui/character_selection.py:266-277`(核心 269)、`src/core/config.py:97`
- **category**: security
- **detail**: `ADMIN_PASSWORD = _env('ADMIN_PASSWORD')`,`_env` 缺失时返回 `''`;`verify_admin_password` 直接 `if password == ADMIN_PASSWORD:`。未配置环境变量时,任何人点「管理员登录」不输密码即可通过,获得全部管理员能力(编辑/删除工单、系统设置、日志中心)。
- **suggestion**: 空密码视为未配置:未配置时禁用管理员入口或启动即报错;比较用 `hmac.compare_digest`;密码建议加盐哈希存储。

## C2. task_manager move 模式:目标存在即跳过并删除源文件,无完整性校验,存在数据永久丢失风险

- **file**: `src/ui/task_manager.py:84-87`(跳过)、`125-132`(删除源)
- **category**: bug
- **detail**: 第 85 行仅凭 `os.path.exists(dest_file)` 判定"目标有完整副本"便跳过移动,清理阶段(125-132)直接删除这些源文件(目录用 `shutil.rmtree`)。若目标端是上次中断残留的残缺副本、同名不同内容、或源为目录而目标为同名文件,源数据被删除且不可恢复。调用方 art.py:427-434、editing.py:354-361 均为真实 move 路径。
- **suggestion**: 跳过前校验目录/文件类型一致与大小(或 mtime/哈希);删除源前再次确认目标等价;copy 模式的跳过应计入提示而非静默。

---

# High(约 30 条,按主题归并)

## A. 状态推进不感知任务失败(状态与磁盘不一致)—— 项目最集中的系统性缺陷

| # | file:line | 问题 |
|---|---|---|
| H1 | `src/ui/task_manager.py:153-154` | Task.run 出错时仍无条件 emit `update_status`,错误只进 errors 列表 |
| H2 | `src/ui/process_dialogs/photography.py:455-463` | 重新上传时先 `rmtree(fail_dir, ignore_errors=True)` + 清反馈记录,复制任务随后才异步执行;复制失败则退回素材与反馈永久丢失 |
| H3 | `photography.py:467-534, 577-600, 630-653` | 上传/分发回调不感知复制失败,失败仍推进状态、发"成功"通知、提示"成功上传 N 个文件" |
| H4 | `src/ui/process_dialogs/art.py:393-417, 427-434, 472-510` | 领取/分发任务失败仍推进 art_status、写日志、发通知、弹成功框 |
| H5 | `src/ui/process_dialogs/art_post_review.py:491-540` | 审批通过:文件移动失败仍判"审批通过"、状态置"美工已完成"、发通过通知、自动关窗 |
| H6 | `src/ui/process_dialogs/editing.py:440-448` | 提交审核的 file_filter 恒为真(`os.path.isdir` 对文件条目恒 False),「源文件」子目录与退回的「不通过」旧视频被重复上传到中转目录 |
| H7 | `editing.py:321-344, 404-448, 458-481, 509-532` | 四个 update_status 回调均不检查任务错误,全部失败仍推进状态/时间/通知 |
| H8 | `src/ui/process_dialogs/video_review.py:396-410, 426-456` | on_approve API 同步失败仍提示"审核通过"并关闭;on_reject 先移文件后同步状态,失败重试覆盖旧退回文件并重复写反馈 |

**统一建议**: 让 Task 完成时通过信号携带 `errors`/成功计数;所有 `update_status_func` 先判断任务结果,失败则中止状态推进、不弹成功提示、保留对话框可重试。

## B. 本地写库/回滚失败被静默忽略

| # | file:line | 问题 |
|---|---|---|
| H9 | `src/core/status_sync.py:33-34, 41-45` | update_status_with_api/update_time_with_api 不检查本地写库返回值;本地失败仍调 API 并返回成功;回滚失败被静默吞掉 |
| H10 | `src/core/database.py:485-505` | save_product_info 非事务性 DELETE+INSERT,中途失败丢产品信息(autocommit 模式下 rollback 无效) |
| H11 | `src/core/database.py:14-43` | 全局单例连接被主线程与 QThread 并发使用,无锁,存在协议状态污染与连接泄漏 |
| H12 | `src/ui/main_window.py:2967-3026` | 编辑工单先移动文件、后写 DB;DB 失败时文件已移动无回滚,路径与数据不一致 |
| H13 | `src/ui/main_window.py:1061-1076` | 删除工单先删 DB 记录再 `rmtree(ignore_errors=True)`,删除失败静默、界面仍报"已删除",残留孤儿文件 |
| H14 | `src/ui/main_window.py:2637` | `QLabel(order_data['id'])` 传入 int,打开编辑工单对话框即 TypeError 崩溃 |

## C. 线程生命周期 / 资源泄漏

| # | file:line | 问题 |
|---|---|---|
| H15 | `src/ui/task_manager.py:75-76, 168-171` | 暂停状态下 cancel() 失效,线程永久卡在暂停循环,任务永不结束、QThread 泄漏 |
| H16 | `task_manager.py:411-417` | closeEvent 不等待/终止运行中任务,退出时 "QThread: Destroyed while thread is still running" 崩溃;关闭后 on_finished 仍弹模态框 |
| H17 | `src/ui/path_check.py:475-478, 526` | 对话框关闭不停止/等待 `_PathScanWorker`,`dialog.exec()` 返回后线程被 GC,崩溃或访问已删除控件 |
| H18 | `src/ui/path_permission_check.py:339-342, 348` | 与 H17 同型的 worker 未清理 |

## D. 主线程同步阻塞(性能)

| # | file:line | 问题 |
|---|---|---|
| H19 | `src/core/api_manager.py:154` + `main_window.py:1125` | create_work_order 同步 requests.post(timeout=10) 在 GUI 主线程,外部系统不可达时 UI 冻结最长 10 秒 |
| H20 | `photography.py:475/494/581/634`、`video_review.py:398/444` 等 | 任务完成回调/审核按钮在主线程执行 update_status_with_api + update_time_with_api,UI 卡死可达 20 秒 |
| H21 | `src/ui/main_window.py:3514-3544` | refresh_work_orders 触发 currentIndexChanged 级联,apply_filters 被连带执行 3~4 次,每次全量重建表格并重复查询日志 |
| H22 | `src/ui/video_review.py:193-205`、`editing.py:347-352`、`art_post_review.py:295` 等 | 打开对话框/点击按钮时主线程同步 os.walk 网络共享目录,大目录下 UI 卡顿 |

## E. 认证与传输安全

| # | file:line | 问题 |
|---|---|---|
| H23 | `src/core/api_manager.py:39-40, 27-33` | API 地址硬编码 `http://192.168.0.54:13000`,Bearer token 明文 HTTP 传输,可被内网抓包截获 |
| H24 | `src/core/config.py:57-74` + `.env` | DB 主机 IP 硬编码;DB 密码缺失时默认空串,可能以空密码直连生产库 |

## F. 构建/运维脚本(独立于运行时)

| # | file:line | 问题 |
|---|---|---|
| H25 | `scripts/build_script.py:43-78` | 产物名与 spec 实际输出名不一致(`素材工单系统_{APP_VERSION}_pyinstaller`),macOS DMG 步骤必失败 |
| H26 | `scripts/full_audit.py:160`、`validate_notification.py:72`、`validate_refactor.py:80` | 校验失败仍退出码 0,CI 门禁形同虚设 |
| H27 | `scripts/patch_main_window.py:30-83` | 按硬编码行号删改源码,无内容断言,行号漂移即静默破坏文件 |
| H28 | `scripts/update_work_order_status.py:50-51` | 引用不存在的 `api_manager._headers`(实际是 `_build_headers()`),状态更新功能必失败 |
| H29 | `scripts/upgrade_db_fields.py:25-26` | 直接 ALTER 生产表,无备份,MySQL DDL 隐式提交不可回滚 |

---

# Medium(约 90 条,按主题归并)

## 状态/数据一致性

- `status_sync.py:100-101` — has_pending_edit_review 静默吞异常,DB 故障被当"无待审核"放行
- `main_window.py:2886-2901` — 未选择项目类型时占位文本"请选择项目类型"被写入 DB
- `main_window.py:3583/3626`、`work_order_detail.py:623/629/641/423` — 日志 details/role 为 NULL 时 `in` 判断抛 TypeError,详情/列表崩溃
- `main_window.py:3059-3070` — 摄影师兜底识别误取型号/名称,素材上传到错误目录
- `main_window.py:310` — 工单 ID 分钟级精度,并发创建必然冲突
- `main_window.py:2035/2445/2467/3497` — 多个 DB 写操作返回值被忽略,失败静默当成功
- `api_manager.py:157-163` — HTTP 200 但响应非 JSON 被误判为创建失败
- `api_manager.py:48-65` — 空/非法时间串转 0 时间戳提交,可能清零外部字段
- `config.py:110-115` — get_feature_enabled 把 DB 查询失败(None)永久缓存,开关一直关闭
- `database.py:404` — 时间字段白名单在 database/status_sync/api_manager 三处重复维护,`end_time` 缺失易漂移
- `database.py:297-316` — add_work_order 显式插 id,已存在时报"创建失败"
- `art.py:397-401/441-445/478-480/545-547`、`art_post_review.py:501-503` — art_status_before 快照过期/为 None,API 失败回滚失效
- `art_post_review.py:525-531` — makedirs 失败提前 return,已排队任务计数永不达标,状态卡死
- `art_post_review.py:555-599` — 退回部分失败仍整体判"退回重做"并发通知
- `editing.py:232-234/366/409` — parent.product_dir 共享状态,异步回调覆盖其他工单对话框路径
- `editing.py:324/418/461/512` — old_status 用对话框打开时快照,回滚覆盖中间变更
- `video_post_review.py:424-438/467-481` — API 失败仍按成功收尾(通知/日志/accept)
- `video_post_review.py:451-465` — 退回同名文件冲突(FileExistsError)、失败弹窗风暴、反馈写失败静默
- `video_post_review.py:222-235` — 成品目录无视频文件仍可"审核通过"(空列表直接通过)
- `ops.py:481-535` — 产品列表固定下标删除,先单删再批量删会误删/漏删
- `ops.py:565-577`、`sales.py:241-250` — 任务完成回调被 `if not dialog.isVisible(): return` 整体跳过,关闭对话框后状态/日志丢失、状态卡住
- `notification.py:222-224` — 推送不校验状态码与 errcode,服务端拒绝也记"推送成功"
- `work_order_detail.py:501-509` — 日志详情富文本未 html.escape,存在 HTML 注入(配合 setOpenExternalLinks)
- `task_manager.py:109` — 进度基于枚举索引,过滤文件占用进度份额
- `task_manager.py:115-147` — 子目录重复项用顶层 os.listdir 匹配,清理不一致且误报"未移动"
- `task_manager.py:85-87` — copy 模式对已存在目标静默跳过,用户以为复制成功
- `video_preview.py:168-184` — duration()=-1 时显示 "-1:59" 并设置非法滑块范围;未连接 errorOccurred

## 线程/对话框

- `path_check.py:50-98/183-188`、`path_permission_check.py:127-145` — 网络盘操作无超时无取消,线程可能永久挂起
- `path_check.py:480-509` — 删除路径在主线程同步 rmtree,UI 卡死
- `path_check.py:455-465` — run_check 在主线程执行 get_logs_by_order_id 网络查询
- `work_order_detail.py:148` — 对话框构造时主线程同步 MySQL 查询
- `notification.py:266` — 模块导入即执行 DB 读写,拖慢启动
- `task_manager.py:240-244/293-408` — 已完成任务不清理,列表无界增长,check_tasks 每秒 O(n)
- `task_manager.py:354-382` — on_finished 模态 exec 阻塞主线程与所有并发任务

## 路径/文件安全

- `path_check.py:136-158/502` — 工单字段直接拼路径 + 本对话框提供 rmtree,存在路径穿越 + 任意目录删除风险
- `ops.py:49-50/203/558`、`sales.py:233`、`editing.py:61-71/383` — department/id/model/name 未净化即拼入文件系统路径
- `task_manager.py:81-82/91` — fname 未做路径归一化校验(当前调用方安全,但 Task 是公开类)

## 其它

- `main_window.py:1497-1510` — 功能开关 and 短路串联,部分写入不一致
- `main_window.py:3457` — strptime 固定格式,格式不符抛 ValueError 中断筛选
- `main_window.py:3754/3777` — check_path_collected_status 每次单独查库(N 次查询),时间戳比较未判空
- `main_window.py:3013` — send_notification 主线程同步 HTTP,最多阻塞约 6 秒
- `database.py:58-64` — get_roles 每次调用 10 次 INSERT + commit,读路径带写副作用
- `database.py:784-811` — seed 事务被 CREATE TABLE 隐式提交破坏
- `database.py:1068-1086` — get_local_ip UDP socket 异常路径未关闭
- `paths.py:109-110` — to_local_path 共享名前缀大小写判断与正则不一致
- `character_selection.py:86-108` — role/department/name 为 NULL 时崩溃
- `character_selection.py:26-27/79-84/395-400` — 启动时同步远程查询 + 用户表重复全量查询
- `ops.py:516-519` — 每加一条产品信息同步 DB 更新 + 全量刷新,失败静默
- `ops.py:558-585`、`sales.py:228-258` — os.listdir/os.makedirs 无异常处理,网络盘异常崩溃
- `video_review.py:193-205` — 打开弹窗主线程递归扫描 8 个摄影师网络目录
- `photography.py:543-556/618` — 视频分发误用图片扩展名校验
- `photography.py:571/624` — 直接访问 e.winerror,非 Windows 平台 AttributeError
- `photography.py:451/535-542` — 多选跨目录文件,任务只取 files[0] 目录,复制错乱

---

# Low(约 120 条,摘录)

- **死代码**: `main_window.py:709-710`(version_label 重复创建)、`3006-3009`(rename_tips)、`3712`(expanded_row)、`62`(注释掉的 sys.path);`work_order_detail.py:689-692`(mask_phone);各流程文件尾部残留迁移注释(photography.py:672、video_review.py:463、art.py:607、editing.py:564、ops.py:593);`_update_status` 解包未使用(photography.py:59、video_review.py:53、ops.py:45、sales.py:40、editing.py:53、video_post_review.py:106、art.py:52、art_post_review.py:110)
- **重复代码**: 三个审批对话框 70% 逐块重复(video_review/video_post_review/art_post_review);「办理工单」骨架+QSS 在 5 文件重复;create_clickable_path_label 定义 5 处;os.walk 收集片段重复 7 次;摄影师列表硬编码 3 份(photography.py:277、video_review.py:192 vs paths.py:44);新增/编辑用户对话框 400 行重复(main_window.py:1656-2454);三处大段暗色 QSS 重复(main_window.py:107-139/204-282/1663-1739)
- **状态常量无单一来源**: 工单状态字符串/映射散落 main_window.py:865、3835-3867、3869-3901、work_order_detail.py:562-579 及 8 个流程文件
- **废弃/不推荐用法**: `dialog.exec_()`(main_window.py:2044/2454);QThread 子类反模式(task_manager.py:27-33);信号 disconnect/connect 绕弯(video_review.py:363-368、video_post_review.py:391-396)
- **边界**: 日志分页满页多出空页(main_window.py:1293-1295);部门必填校验形同虚设(464-466);int 转换无保护(2057/2464);`order.get('status') or '未知'` 兜底不生效(2508);折叠动画起始值跳变(work_order_detail.py:73-75);permission_check 写测试文件名同秒碰撞(.perm_test)
- **脚本**: 硬编码本机绝对路径(extract_dialogs/fix_dialog_refs/patch_main_window/validate_notification/validate_refactor);`except Exception` 吞异常无 traceback;`--onefile` 参数静默忽略;requirements 未锁版本;sql 导出文件含 DROP TABLE 与内网 IP
- **其它**: `sys.exit` 直接连接 clicked 信号(main_window.py:664);`from packaging import version` 位于类定义之间(590);`title_label` 变量名重复定义(ops.py:142/218);`clear()` 未复位时间标签与滑块(video_preview.py:251-265)

---

# 架构性建议(来自交叉审查单元)

1. **任务结果回传**(最重要): Task 完成信号携带 `(ok, errors)`,所有 `update_status_func` 按结果决定是否推进状态——这是修复 H1~H8 的系统性方案。
2. **状态常量单一来源**: 新建 `src/core/constants.py`(WORK_ORDER_STATUSES / STATUS_PROGRESS / STATUS_COLOR / 白名单),main_window、work_order_detail、8 个流程文件统一引用。
3. **进度推导单一来源**: 新建 `src/core/workflow.py`,把日志证据扫描逻辑(main_window.py:3545-3664、work_order_detail.py:581-680、status_sync.py:89-101、art.py:235-246、path_check.py:111-131 共 5 处,规则已分叉)收敛为一个模块。
4. **对话框公共基类**: `_approval_base.py`(审批三连)、`_dialog_common.py`(骨架/QSS/路径标签/os.walk 收集),预计删减 40~50% 重复代码。
5. **status_sync 封装使用一致化**: ops.py:518/574、main_window.py:3497 绕过 `update_status_with_api` 直接写库,外部系统永远不知道状态变更。
6. **DB 层加锁**: DatabaseManager 增加 threading.Lock(或 thread-local 连接),修复 H11 与 C2 之外的全部并发隐患。
7. **主线程网络操作统一迁移**: HTTP(api_manager/notification)与网络盘 os.walk/stat/rmtree 全部移入后台线程,UI 只做信号回填。

---

# 修复优先级建议

| 优先级 | 内容 | 对应条目 |
|---|---|---|
| P0(立即) | 管理员空密码;move 删源无校验;上传/审批状态推进不感知任务失败 | C1, C2, H1~H8 |
| P0(立即) | status_sync 本地写库失败静默;save_product_info 事务化;DB 连接加锁 | H9, H10, H11 |
| P1(本周) | QThread 生命周期(暂停取消、closeEvent wait、path_check worker);主线程同步 HTTP/网络盘操作异步化 | H15~H22 |
| P1(本周) | 编辑工单/删除工单的"先文件后 DB"顺序与回滚;QLabel int 崩溃 | H12~H14 |
| P2(两周内) | API 明文 HTTP→配置化+HTTPS;DB 主机/密码配置化;脚本层(构建产物名、退出码、行号补丁、_headers、ALTER 备份) | H23~H29 |
| P3(持续) | 常量/进度推导单一来源、对话框基类抽取、死代码清理 | 架构性建议 + Low |

---

*注:完整逐单元报告(含每条问题的 detail 与 suggestion)位于 `.review/04_task_manager.md`、`05_path_check.md`、`06_photography_video_review.md`、`07_art_chain.md`、`08_editing_video_post.md`、`09_ops_sales_char_preview.md`、`10_scripts.md`、`11_danger_patterns.md`、`12_duplication.md`;01~03 单元(core/main_window 上下半)见会话工作流输出。*
