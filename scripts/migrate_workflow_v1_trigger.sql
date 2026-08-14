-- ============================================================
-- 触发器：工单状态变更自动留痕（trg_wo_status_history）
-- 使用方法：Navicat 打开本文件 → 全选（Ctrl+A）→ 运行
-- 需要具备 SUPER 权限的账号（root）执行
-- ============================================================
USE mcs_by_takuya;

DROP TRIGGER IF EXISTS trg_wo_status_history;

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
END
