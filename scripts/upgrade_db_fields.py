import os
import sys
import traceback
from pathlib import Path

# 将项目路径加入 PYTHONPATH 搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import db_manager


def upgrade_database():
    """手动执行数据库字段增量升级

    安全说明：MySQL 的 ALTER TABLE 属于 DDL，会隐式提交且无法回滚。
    执行前必须展示将要执行的 DDL 并要求确认，且先导出表结构备份。
    """
    print("开始连接数据库以执行升级检查...")
    if not db_manager.connect():
        print("错误: 无法连接数据库，请检查 src/core/config.py 中的数据库连接配置。")
        sys.exit(1)

    ddl = "ALTER TABLE mcs_by_takuya_work_orders ADD COLUMN edit_product_path VARCHAR(500) DEFAULT NULL"
    try:
        with db_manager.connection.cursor() as cursor:
            # 检查 mcs_by_takuya_work_orders 包含 edit_product_path 字段
            cursor.execute("SHOW COLUMNS FROM mcs_by_takuya_work_orders LIKE 'edit_product_path'")
            result = cursor.fetchone()

            if not result:
                # 执行前导出表结构备份（DDL 不可回滚，无备份直接执行风险不可接受）
                try:
                    with db_manager.connection.cursor() as backup_cursor:
                        backup_cursor.execute("SHOW CREATE TABLE mcs_by_takuya_work_orders")
                        row = backup_cursor.fetchone()
                        if row and len(row) >= 2:
                            backup_dir = os.path.dirname(os.path.abspath(__file__))
                            backup_path = (Path(backup_dir) / f"backup_mcs_by_takuya_work_orders_{row[0] and 'schema'}.sql").resolve()
                            # 仅允许写入脚本所在目录（commonpath 校验，禁止 ../ 越界）
                            if os.path.commonpath([str(backup_path), os.path.abspath(backup_dir)]) != os.path.abspath(backup_dir):
                                print("警告: 备份路径越界，未生成备份，中止执行。")
                                sys.exit(1)
                            backup_path.write_text(f"-- 备份时间: 执行前自动生成\n{row[1]};\n", encoding='utf-8')
                            print(f"已导出表结构备份: {backup_path}")
                        else:
                            print("警告: 无法读取 SHOW CREATE TABLE 结果，未生成备份，中止执行。")
                            sys.exit(1)
                except Exception as e:
                    print(f"错误: 导出表结构备份失败: {e}")
                    print("中止执行以避免不可回滚的 DDL 操作。")
                    sys.exit(1)

                print("未检测到 edit_product_path 字段，将执行以下 DDL（不可回滚，请确认）：")
                print(f"  {ddl}")
                confirm = input("确认执行？输入 YES 继续: ").strip()
                if confirm != "YES":
                    print("已取消，未执行任何变更。")
                    sys.exit(0)
                cursor.execute(ddl)
                print("成功：成功为 mcs_by_takuya_work_orders 表添加 edit_product_path 字段！")
            else:
                print("提示：edit_product_path 字段已存在，无需重复添加。")

    except Exception as e:
        print(f"异常: 升级数据库失败。错误原因: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        db_manager.disconnect()
        print("数据库连接已关闭。")


if __name__ == "__main__":
    upgrade_database()
