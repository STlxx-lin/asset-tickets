-- 数据库升级脚本
-- 为 mcs_by_takuya_work_orders 表添加 edit_product_path（成品路径）字段

-- 检查字段是否存在，若不存在则添加
SET @dbname = DATABASE();
SET @tablename = 'mcs_by_takuya_work_orders';
SET @columnname = 'edit_product_path';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = @tablename AND COLUMN_NAME = @columnname) > 0,
  'SELECT "Column edit_product_path already exists";',
  'ALTER TABLE mcs_by_takuya_work_orders ADD COLUMN edit_product_path VARCHAR(500) DEFAULT NULL;'
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
