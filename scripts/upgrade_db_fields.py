import sys
import os

# 将项目路径加入 PYTHONPATH 搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import db_manager

def upgrade_database():
    """手动执行数据库字段增量升级"""
    print("开始连接数据库以执行升级检查...")
    if not db_manager.connect():
        print("错误: 无法连接数据库，请检查 src/core/config.py 中的数据库连接配置。")
        return
    
    try:
        with db_manager.connection.cursor() as cursor:
            # 检查 mcs_by_takuya_work_orders 包含 edit_product_path 字段
            cursor.execute("SHOW COLUMNS FROM mcs_by_takuya_work_orders LIKE 'edit_product_path'")
            result = cursor.fetchone()
            
            if not result:
                print("未检测到 edit_product_path 字段，正在执行 ALTER TABLE 语句进行添加...")
                cursor.execute("ALTER TABLE mcs_by_takuya_work_orders ADD COLUMN edit_product_path VARCHAR(500) DEFAULT NULL")
                db_manager.connection.commit()
                print("成功：成功为 mcs_by_takuya_work_orders 表添加 edit_product_path 字段！")
            else:
                print("提示：edit_product_path 字段已存在，无需重复添加。")
                
    except Exception as e:
        print(f"异常: 升级数据库失败。错误原因: {e}")
    finally:
        db_manager.disconnect()
        print("数据库连接已关闭。")

if __name__ == "__main__":
    upgrade_database()
