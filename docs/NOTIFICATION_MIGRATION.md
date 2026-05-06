# 通知配置迁移说明

## 背景

历史版本中，通知类型使用 `config.py` 中的 `NOTIFICATION_TYPE` 单值配置，无法满足“按产线独立配置”的业务需求。

## 迁移目标

- 将通知配置从静态文件迁移到数据库。
- 支持每个产线（部门）独立维护：
  - `notification_type`
  - `dingtalk_webhook`
  - `dingtalk_secret`
  - `wechat_work_webhook`

## 数据表

- 表名：`app_notification_line_settings`
- 主键：`line_name`
- 用途：按产线存储通知配置

## 迁移策略

1. 应用启动时检查通知配置表是否为空。
2. 若为空，则将代码中现有通知配置写入数据库作为初始数据。
3. 后续统一从数据库读取并通过设置界面维护。

## 默认值策略

- `config.py` 中保留 `DEFAULT_NOTIFICATION_TYPE` 作为数据库无值时的全局兜底值。
- 业务逻辑优先使用数据库产线配置，其次回退 `default` 产线配置，最后回退 `DEFAULT_NOTIFICATION_TYPE`。
