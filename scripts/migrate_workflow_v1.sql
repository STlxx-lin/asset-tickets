-- ============================================================================
-- 工作流数据库优化迁移 v1（2026-08-14）
-- ----------------------------------------------------------------------------
-- 内容：
--   1. work_order_status_history 状态历史表（status / art_status 双字段留痕）
--   2. AFTER UPDATE 触发器自动写入历史（应用层零改动）
--   3. 查询索引（logs 筛选排序 / work_orders 列表排序）
--   4. work_orders.version 乐观锁列（配合 status_sync 并发保护）
--
-- 执行前请备份：mysqldump -u<user> -p mcs_by_takuya > backup_20260814.sql
-- 目标环境：MySQL 5.7+（已在本 dump 同版本 5.7.44 验证语法）
-- ============================================================================

USE mcs_by_takuya;

-- ---------------------------------------------------------------------------
-- 1. 状态历史表
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS work_order_status_history (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  order_id    VARCHAR(20) NOT NULL COMMENT '工单ID',
  field_name  VARCHAR(20) NOT NULL COMMENT '字段名: status / art_status',
  from_status VARCHAR(20) NULL COMMENT '变更前状态（NULL=首次写入）',
  to_status   VARCHAR(20) NOT NULL COMMENT '变更后状态',
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间',
  KEY idx_wosh_order (order_id, created_at DESC),
  KEY idx_wosh_time  (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单状态变更历史';

-- ---------------------------------------------------------------------------
-- 2. 状态历史触发器（status / art_status 任一变化即留痕；回滚也是历史的一部分）
-- ---------------------------------------------------------------------------
DELIMITER $$
DROP TRIGGER IF EXISTS trg_wo_status_history$$
CREATE TRIGGER trg_wo_status_history
AFTER UPDATE ON mcs_by_takuya_work_orders
FOR EACH ROW
BEGIN
  IF NOT (OLD.status <=> NEW.status) THEN
    INSERT INTO work_order_status_history (order_id, field_name, from_status, to_status)
    VALUES (NEW.id, 'status', OLD.status, NEW.status);
  END IF;
  IF NOT (OLD.art_status <=> NEW.art_status) THEN
    INSERT INTO work_order_status_history (order_id, field_name, from_status, to_status)
    VALUES (NEW.id, 'art_status', OLD.art_status, NEW.art_status);
  END IF;
END$$
DELIMITER ;

-- ---------------------------------------------------------------------------
-- 3. 查询索引（日志中心按时间/操作类型筛选排序；工单列表按创建时间倒序）
-- ---------------------------------------------------------------------------
ALTER TABLE mcs_by_takuya_logs
  ADD INDEX idx_logs_timestamp (timestamp DESC),
  ADD INDEX idx_logs_action_time (action_type, timestamp DESC),
  ADD INDEX idx_logs_order_time (order_id, timestamp DESC);

ALTER TABLE mcs_by_takuya_work_orders
  ADD INDEX idx_wo_created (created_at DESC);

-- ---------------------------------------------------------------------------
-- 4. 乐观锁版本列（status_sync 写入时 WHERE id=? AND version=?，冲突即提示刷新）
-- ---------------------------------------------------------------------------
ALTER TABLE mcs_by_takuya_work_orders
  ADD COLUMN version INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号';

-- ============================================================================
-- 回滚脚本（如需要）：
--   DROP TRIGGER trg_wo_status_history;
--   DROP TABLE work_order_status_history;
--   ALTER TABLE mcs_by_takuya_logs
--     DROP INDEX idx_logs_timestamp, DROP INDEX idx_logs_action_time, DROP INDEX idx_logs_order_time;
--   ALTER TABLE mcs_by_takuya_work_orders
--     DROP INDEX idx_wo_created, DROP COLUMN version;
-- ============================================================================
