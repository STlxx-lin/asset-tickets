import pymysql
from typing import List, Dict, Any, Optional
import logging
import pymysql
from api_manager import api_manager
from datetime import datetime
from config import DB_CONFIG

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.config = DB_CONFIG  # 从配置文件导入数据库连接配置
        self.setup_logging()
        # self.init_database()  # 已关闭数据库初始化

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def connect(self):
        try:
            self.connection = pymysql.connect(**self.config)
            self.logger.info("数据库连接成功")
            return True
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            return False

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.logger.info("数据库连接已关闭")

    def init_database(self):
        if not self.connect():
            return
        try:
            with self.connection.cursor() as cursor:
                # 角色表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mcs_by_takuya_roles (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # 部门表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mcs_by_takuya_departments (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # 工单表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mcs_by_takuya_work_orders (
                        id VARCHAR(20) PRIMARY KEY,
                        department_id INT,
                        model VARCHAR(100),
                        name VARCHAR(200),
                        creator VARCHAR(100),
                        type VARCHAR(50),
                        status VARCHAR(20) DEFAULT 'pending',
                        project_type VARCHAR(100),
                        project_content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (department_id) REFERENCES mcs_by_takuya_departments(id)
                    )
                """)
                # 用户表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mcs_by_takuya_users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(100) UNIQUE NOT NULL,
                        role_id INT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (role_id) REFERENCES mcs_by_takuya_roles(id)
                    )
                """)
                # 用户部门关联表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mcs_by_takuya_user_departments (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        department_id INT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES mcs_by_takuya_users(id),
                        FOREIGN KEY (department_id) REFERENCES mcs_by_takuya_departments(id),
                        UNIQUE KEY unique_user_dept (user_id, department_id)
                    )
                """)
                # 日志表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mcs_by_takuya_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        role VARCHAR(50),
                        action_type VARCHAR(255),
                        details VARCHAR(255),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ip_address VARCHAR(45),
                        user_name VARCHAR(100)
                    )
                """)
                # 产品信息表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mcs_by_takuya_product_info (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        work_order_id VARCHAR(20),
                        title VARCHAR(255) NOT NULL,
                        keywords VARCHAR(500) NOT NULL,
                        url VARCHAR(500) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (work_order_id) REFERENCES mcs_by_takuya_work_orders(id) ON DELETE CASCADE
                    )
                """)
                # 新增版本表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mcs_by_takuya_versions (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        version VARCHAR(20) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                ''')
                # 如果表为空，插入初始版本
                cursor.execute("SELECT COUNT(*) FROM mcs_by_takuya_versions")
                if cursor.fetchone()[0] == 0:
                    cursor.execute("INSERT INTO mcs_by_takuya_versions (version) VALUES ('v1.09')")
                # 默认角色
                default_roles = ["采购", "摄影", "美工", "剪辑", "运营", "销售"]
                for role in default_roles:
                    cursor.execute("INSERT IGNORE INTO mcs_by_takuya_roles (name) VALUES (%s)", (role,))
                # 默认部门
                default_departments = [
                    "01标签机械", "02标签材料", "03软包机械", "04塑料机械",
                    "05纸容器机械", "06硬包机械", "07农用机械"
                ]
                for dept in default_departments:
                    cursor.execute("INSERT IGNORE INTO mcs_by_takuya_departments (name) VALUES (%s)", (dept,))
                # 示例工单（移除，不再插入默认工单）
                # sample_orders = [
                #     ("202506011120", "01标签机械", "DBGFQ-370", "高速分切机", "Peter", "拍摄中"),
                # ]
                # for order in sample_orders:
                #     cursor.execute("SELECT id FROM mcs_by_takuya_departments WHERE name = %s", (order[1],))
                #     dept_result = cursor.fetchone()
                #     if dept_result:
                #         dept_id = dept_result[0]
                #         cursor.execute("""
                #             INSERT IGNORE INTO mcs_by_takuya_work_orders 
                #             (id, department_id, model, name, creator, type) 
                #             VALUES (%s, %s, %s, %s, %s, %s)
                #         """, (order[0], dept_id, order[2], order[3], order[4], order[5]))
                self.connection.commit()
                self.logger.info("数据库初始化完成")
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
        finally:
            self.disconnect()

    def get_roles(self) -> List[str]:
        if not self.connect():
            return []
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT name FROM mcs_by_takuya_roles")
                all_roles = [row[0] for row in cursor.fetchall()]
                
                # 按照指定顺序排序
                desired_order = ["采购", "摄影", "美工", "剪辑", "运营", "销售"]
                ordered_roles = []
                
                # 先添加指定顺序的角色
                for role in desired_order:
                    if role in all_roles:
                        ordered_roles.append(role)
                
                # 再添加其他可能存在的角色（按字母顺序）
                other_roles = [role for role in all_roles if role not in desired_order]
                other_roles.sort()
                ordered_roles.extend(other_roles)
                
                return ordered_roles
        except Exception as e:
            self.logger.error(f"获取角色失败: {e}")
            return []
        finally:
            self.disconnect()

    def get_departments(self) -> List[str]:
        if not self.connect():
            return []
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT name FROM mcs_by_takuya_departments ORDER BY name")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"获取部门失败: {e}")
            return []
        finally:
            self.disconnect()

    def get_work_orders(self, user_departments: List[str] = None) -> List[Dict[str, Any]]:
        if not self.connect():
            return []
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                if user_departments:
                    placeholders = ','.join(['%s'] * len(user_departments))
                    query = f"""
                        SELECT wo.id, d.name as department, wo.model, wo.name, 
                               wo.creator, wo.requester, wo.type, wo.status, wo.created_at, 
                               pt.name as project_type, pc.name as project_content,
                               wo.project_type_id, wo.project_content_id, wo.remarks
                        FROM mcs_by_takuya_work_orders wo
                        JOIN mcs_by_takuya_departments d ON wo.department_id = d.id
                        LEFT JOIN mcs_by_takuya_project_types pt ON wo.project_type_id = pt.id
                        LEFT JOIN mcs_by_takuya_project_contents pc ON wo.project_content_id = pc.id
                        WHERE d.name IN ({placeholders})
                        ORDER BY wo.created_at DESC
                    """
                    cursor.execute(query, user_departments)
                else:
                    cursor.execute("""
                        SELECT wo.id, d.name as department, wo.model, wo.name, 
                               wo.creator, wo.requester, wo.type, wo.status, wo.created_at, 
                               pt.name as project_type, pc.name as project_content,
                               wo.project_type_id, wo.project_content_id, wo.remarks
                        FROM mcs_by_takuya_work_orders wo
                        JOIN mcs_by_takuya_departments d ON wo.department_id = d.id
                        LEFT JOIN mcs_by_takuya_project_types pt ON wo.project_type_id = pt.id
                        LEFT JOIN mcs_by_takuya_project_contents pc ON wo.project_content_id = pc.id
                        ORDER BY wo.created_at DESC
                    """)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"获取工单失败: {e}")
            return []
        finally:
            self.disconnect()

    def add_role(self, role_name: str) -> bool:
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("INSERT INTO mcs_by_takuya_roles (name) VALUES (%s)", (role_name,))
                self.connection.commit()
                    # 可以根据API需求添加更多字段
                
                api_response = api_manager.create_work_order(api_data)
                if api_response['success']:
                    self.logger.info(f"API创建工单成功: {order_data['id']}")
                else:
                    self.logger.error(f"API创建工单失败: {order_data['id']}, 错误: {api_response.get('error', '未知错误')}")
                
                return True
        except Exception as e:
            self.logger.error(f"添加角色失败: {e}")
            return False
        finally:
            self.disconnect()

    def remove_role(self, role_name: str) -> bool:
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("DELETE FROM mcs_by_takuya_roles WHERE name = %s", (role_name,))
                self.connection.commit()

                # 调用API创建工单系统信息
                try:
                    from api_manager import api_manager
                    # 构造API所需的工单数据
                    api_order_data = {
                        'id': order_data['id'],
                        'project_name': order_data['name'],
                        'applicant': order_data['creator'],
                        'status': '拍摄中',
                        'start_time': order_data.get('start_time', '')
                    }
                    # 调用API
                    response = api_manager.create_work_order(api_order_data)
                    if response['success']:
                        self.logger.info(f"通过API创建工单系统信息成功: {order_data['id']}")
                    else:
                        self.logger.error(f"通过API创建工单系统信息失败: {order_data['id']}, 错误: {response.get('error', '未知错误')}")
                except Exception as e:
                    self.logger.error(f"调用API创建工单系统信息发生异常: {e}")

                return True
        except Exception as e:
            self.logger.error(f"删除角色失败: {e}")
            return False
        finally:
            self.disconnect()

    def add_department(self, dept_name: str) -> bool:
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("INSERT INTO mcs_by_takuya_departments (name) VALUES (%s)", (dept_name,))
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"添加部门失败: {e}")
            return False
        finally:
            self.disconnect()

    def remove_department(self, dept_name: str) -> bool:
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("DELETE FROM mcs_by_takuya_departments WHERE name = %s", (dept_name,))
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"删除部门失败: {e}")
            return False
        finally:
            self.disconnect()

    def add_log(self, role: str, action_type: str, details: str, ip_address: str = "N/A", user_name: str = "") -> bool:
        if not self.connect(): return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO mcs_by_takuya_logs (role, action_type, details, ip_address, user_name) VALUES (%s, %s, %s, %s, %s)",
                    (role, action_type, details, ip_address, user_name)
                )
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"记录日志失败: {e}")
            return False
        finally:
            self.disconnect()

    def get_logs(self, limit: int = 200, role: str = None, user_name: str = None, action_type: str = None, ip_address: str = None, start_time: str = None, end_time: str = None, offset: int = 0) -> List[Dict[str, Any]]:
        if not self.connect(): return []
        try:
            sql = "SELECT role, user_name, action_type, details, timestamp, ip_address FROM mcs_by_takuya_logs"
            conditions = []
            params = []
            if role:
                conditions.append("role = %s")
                params.append(role)
            if user_name:
                conditions.append("user_name LIKE %s")
                params.append(f"%{user_name}%")
            if action_type:
                conditions.append("action_type = %s")
                params.append(action_type)
            if ip_address:
                conditions.append("ip_address LIKE %s")
                params.append(f"%{ip_address}%")
            if start_time:
                conditions.append("timestamp >= %s")
                params.append(start_time)
            if end_time:
                conditions.append("timestamp <= %s")
                params.append(end_time)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.append(limit)
            params.append(offset)
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"获取日志失败: {e}")
            return []
        finally:
            self.disconnect()

    def add_work_order(self, order_data: Dict[str, Any]) -> bool:
        if not self.connect(): return False
        try:
            with self.connection.cursor() as cursor:
                # 获取部门ID
                cursor.execute("SELECT id FROM mcs_by_takuya_departments WHERE name = %s", (order_data['department'],))
                dept_result = cursor.fetchone()
                if not dept_result:
                    self.logger.error(f"找不到部门: {order_data['department']}")
                    return False
                dept_id = dept_result[0]

                # 获取项目类型ID
                # 支持两种字段名：project_type_id（直接传递ID）和projecttype_id（用户提到的字段名）
                project_type_id = order_data.get('project_type_id')
                if project_type_id is None:
                    project_type_id = order_data.get('projecttype_id')
                
                # 如果没有直接提供ID，尝试通过名称获取
                if project_type_id is None:
                    # 尝试从多个可能的名称字段获取
                    project_type = order_data.get('project_type', '')
                    if not project_type:
                        project_type = order_data.get('project_type_name', '')
                    if project_type:
                        cursor.execute("SELECT id FROM mcs_by_takuya_project_types WHERE name = %s", (project_type,))
                        type_result = cursor.fetchone()
                        if type_result:
                            project_type_id = type_result[0]

                # 获取项目内容ID
                # 支持两种字段名：project_content_id（直接传递ID）和project_contentid（用户提到的字段名）
                project_content_id = order_data.get('project_content_id')
                if project_content_id is None:
                    project_content_id = order_data.get('project_contentid')
                
                # 如果没有直接提供ID，尝试通过名称获取
                if project_content_id is None:
                    # 尝试从多个可能的名称字段获取
                    project_content = order_data.get('project_content', '')
                    if not project_content:
                        project_content = order_data.get('project_content_name', '')
                    if project_content:
                        cursor.execute("SELECT id FROM mcs_by_takuya_project_contents WHERE name = %s", (project_content,))
                        content_result = cursor.fetchone()
                        if content_result:
                            project_content_id = content_result[0]

                # 获取备注信息
                remarks = order_data.get('remarks', '')

                # 插入工单数据
                query = """
                    INSERT INTO mcs_by_takuya_work_orders 
                    (id, department_id, model, name, creator, requester, type, status, project_type_id, project_content_id, remarks) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                order_type = order_data.get('type', '常规')
                requester = order_data.get('requester', '')
                cursor.execute(query, (
                    order_data['id'],
                    dept_id,
                    order_data['model'],
                    order_data['name'],
                    order_data['creator'],
                    requester,
                    order_type,
                    '拍摄中',
                    project_type_id,
                    project_content_id,
                    remarks
                ))
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"添加工单失败: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def update_work_orders_status_bulk(self, ids: List[str], new_status: str) -> int:
        """
        批量更新工单状态。
        :param ids: 工单ID列表
        :param new_status: 新状态
        :return: 成功更新的工单数量
        """
        if not self.connect() or not ids:
            return 0
        try:
            with self.connection.cursor() as cursor:
                placeholders = ','.join(['%s'] * len(ids))
                query = f"UPDATE mcs_by_takuya_work_orders SET status=%s WHERE id IN ({placeholders})"
                cursor.execute(query, [new_status] + ids)
                self.connection.commit()
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"批量更新工单状态失败: {e}")
            self.connection.rollback()
            return 0
        finally:
            self.disconnect()

    def update_work_order_status(self, order_id: str, new_status: str) -> bool:
        """
        更新单个工单的状态。
        :param order_id: 工单ID
        :param new_status: 新状态
        :return: 是否成功
        """
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE mcs_by_takuya_work_orders SET status=%s WHERE id=%s",
                    (new_status, order_id)
                )
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新工单状态失败: {e}")
            self.connection.rollback()
            return False

    def update_work_order_time_field(self, order_id: str, field_name: str, time_value: datetime) -> bool:
        """
        更新工单的时间字段。
        :param order_id: 工单ID
        :param field_name: 时间字段名称
        :param time_value: 时间值
        :return: 是否成功
        """
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                # 检查字段是否存在
                valid_fields = ['art_start_time', 'art_end_time', 'edit_start_time', 'edit_end_time', 'start_time', 'photographer_start_time', 'photographer_end_time']
                if field_name not in valid_fields:
                    self.logger.error(f"无效的时间字段: {field_name}")
                    return False
                
                cursor.execute(
                    f"UPDATE mcs_by_takuya_work_orders SET {field_name}=%s WHERE id=%s",
                    (time_value, order_id)
                )
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新工单时间字段失败: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def get_logs_by_order_id(self, order_id: str):
        if not self.connect():
            return []
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT role, user_name, action_type, details, timestamp
                    FROM mcs_by_takuya_logs
                    WHERE details LIKE %s
                    ORDER BY timestamp DESC
                """, (f"%工单ID={order_id}%",))
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"获取工单日志失败: {e}")
            return []
        finally:
            self.disconnect()

    def save_product_info(self, work_order_id: str, products: List[Dict[str, str]]) -> bool:
        """保存产品信息到数据库"""
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                # 先删除该工单的旧产品信息
                cursor.execute("DELETE FROM mcs_by_takuya_product_info WHERE work_order_id = %s", (work_order_id,))
                
                # 插入新的产品信息
                for product in products:
                    cursor.execute("""
                        INSERT INTO mcs_by_takuya_product_info (work_order_id, title, keywords, url)
                        VALUES (%s, %s, %s, %s)
                    """, (work_order_id, product['title'], product['keywords'], product['url']))
                
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"保存产品信息失败: {e}")
            return False
        finally:
            self.disconnect()

    def get_product_info(self, work_order_id: str) -> List[Dict[str, str]]:
        """获取工单的产品信息"""
        if not self.connect():
            return []
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT title, keywords, url
                    FROM mcs_by_takuya_product_info
                    WHERE work_order_id = %s
                    ORDER BY created_at ASC
                """, (work_order_id,))
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"获取产品信息失败: {e}")
            return []
        finally:
            self.disconnect()

    def clear_all_data(self) -> bool:
        """
        清空所有数据，重新初始化数据库。
        """
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                # 按外键依赖顺序删除数据
                cursor.execute("DELETE FROM mcs_by_takuya_logs")
                cursor.execute("DELETE FROM mcs_by_takuya_work_orders")
                cursor.execute("DELETE FROM mcs_by_takuya_user_departments")
                cursor.execute("DELETE FROM mcs_by_takuya_users")
                cursor.execute("DELETE FROM mcs_by_takuya_roles")
                cursor.execute("DELETE FROM mcs_by_takuya_departments")
                
                # 重新插入默认数据
                # 默认角色
                default_roles = ["采购", "摄影", "美工", "剪辑", "运营", "销售"]
                for role in default_roles:
                    cursor.execute("INSERT INTO mcs_by_takuya_roles (name) VALUES (%s)", (role,))
                
                # 默认部门
                default_departments = [
                    "01标签机械", "02标签材料", "03软包机械", "04塑料机械",
                    "05纸容器机械", "06硬包机械", "07农用机械"
                ]
                for dept in default_departments:
                    cursor.execute("INSERT IGNORE INTO mcs_by_takuya_departments (name) VALUES (%s)", (dept,))
                
                # 示例工单（移除，不再插入默认工单）
                # sample_orders = [
                #     ("202506011120", "01标签机械", "DBGFQ-370", "高速分切机", "Peter", "拍摄中"),
                # ]
                # for order in sample_orders:
                #     cursor.execute("SELECT id FROM mcs_by_takuya_departments WHERE name = %s", (order[1],))
                #     dept_result = cursor.fetchone()
                #     if dept_result:
                #         dept_id = dept_result[0]
                #         cursor.execute("""
                #             INSERT INTO mcs_by_takuya_work_orders 
                #             (id, department_id, model, name, creator, type) 
                #             VALUES (%s, %s, %s, %s, %s, %s)
                #         """, (order[0], dept_id, order[2], order[3], order[4], order[5]))
                
                self.connection.commit()
                self.logger.info("数据库数据已清空并重新初始化")
                return True
        except Exception as e:
            self.logger.error(f"清空数据失败: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def delete_work_order(self, order_id: str) -> bool:
        """根据工单ID删除工单及其相关数据（产品信息、日志等通过外键自动删除）"""
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("DELETE FROM mcs_by_takuya_work_orders WHERE id = %s", (order_id,))
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"删除工单失败: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def update_work_order_full(self, order_id: str, department: str, model: str, name: str, creator: str, project_type: str = "", project_content: str = "", projecttype_id: int = None, project_contentid: int = None, remarks: str = "") -> bool:
        if not self.connect(): return False
        try:
            with self.connection.cursor() as cursor:
                # 先获取部门ID
                cursor.execute("SELECT id FROM mcs_by_takuya_departments WHERE name = %s", (department,))
                dept_result = cursor.fetchone()
                if not dept_result:
                    self.logger.error(f"找不到部门: {department}")
                    return False
                dept_id = dept_result[0]

                # 获取项目类型ID
                # 优先使用直接提供的ID (projecttype_id)
                project_type_id = projecttype_id
                if project_type_id is None:
                    # 其次尝试通过名称获取
                    if project_type:
                        cursor.execute("SELECT id FROM mcs_by_takuya_project_types WHERE name = %s", (project_type,))
                        type_result = cursor.fetchone()
                        if type_result:
                            project_type_id = type_result[0]

                # 获取项目内容ID
                # 优先使用直接提供的ID (project_contentid)
                project_content_id = project_contentid
                if project_content_id is None:
                    # 其次尝试通过名称获取
                    if project_content:
                        cursor.execute("SELECT id FROM mcs_by_takuya_project_contents WHERE name = %s", (project_content,))
                        content_result = cursor.fetchone()
                        if content_result:
                            project_content_id = content_result[0]

                # 更新工单信息
                cursor.execute("""
                    UPDATE mcs_by_takuya_work_orders 
                    SET department_id = %s, model = %s, name = %s, creator = %s, 
                        project_type_id = %s, project_content_id = %s, remarks = %s 
                    WHERE id = %s
                """, (dept_id, model, name, creator, project_type_id, project_content_id, remarks, order_id))
                
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新工单失败: {e}")
            return False
        finally:
            self.disconnect()

    def get_users(self, name: str = None, ip: str = None, role: str = None, department: str = None) -> List[Dict[str, Any]]:
        if not self.connect():
            return []
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                sql = "SELECT id, ip, name, role, department FROM mcs_by_takuya_users"
                conditions = []
                params = []
                
                if name:
                    conditions.append("name LIKE %s")
                    params.append(f"%{name}%")
                
                if ip:
                    conditions.append("ip LIKE %s")
                    params.append(f"%{ip}%")
                
                if role:
                    conditions.append("role LIKE %s")
                    params.append(f"%{role}%")
                
                if department:
                    conditions.append("department LIKE %s")
                    params.append(f"%{department}%")
                
                if conditions:
                    sql += " WHERE " + " AND ".join(conditions)
                
                sql += " ORDER BY id DESC"
                
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"获取用户失败: {e}")
            return []
        finally:
            self.disconnect()

    def add_user(self, ip: str, name: str, role: str, department: str) -> bool:
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO mcs_by_takuya_users (ip, name, role, department) VALUES (%s, %s, %s, %s)",
                    (ip, name, role, department)
                )
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"添加用户失败: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def update_user(self, user_id: int, ip: str, name: str, role: str, department: str) -> bool:
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE mcs_by_takuya_users SET ip=%s, name=%s, role=%s, department=%s WHERE id=%s",
                    (ip, name, role, department, user_id)
                )
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新用户失败: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def delete_user(self, user_id: int) -> bool:
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("DELETE FROM mcs_by_takuya_users WHERE id=%s", (user_id,))
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"删除用户失败: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def get_action_types(self) -> list:
        if not self.connect(): return []
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT action_type FROM mcs_by_takuya_logs ORDER BY action_type")
                return [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            self.logger.error(f"获取操作类型失败: {e}")
            return []
        finally:
            self.disconnect()

    def get_user_names(self) -> list:
        if not self.connect(): return []
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT user_name FROM mcs_by_takuya_logs ORDER BY user_name")
                return [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            self.logger.error(f"获取用户姓名失败: {e}")
            return []
        finally:
            self.disconnect()

    def get_latest_version(self) -> dict:
        """获取最新版本信息，包括版本号和下载链接"""
        if not self.connect():
            return {}
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT version, win_update_url, mac_update_url FROM mcs_by_takuya_versions ORDER BY created_at DESC LIMIT 1")
                row = cursor.fetchone()
                return row if row else {}
        except Exception as e:
            self.logger.error(f"获取最新版本失败: {e}")
            return {}
        finally:
            self.disconnect()

    def get_project_types(self) -> List[Dict[str, Any]]:
        """获取所有项目类型"""
        if not self.connect():
            return []
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT id, name FROM mcs_by_takuya_project_types ORDER BY name")
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"获取项目类型失败: {e}")
            return []
        finally:
            self.disconnect()

    def get_project_contents_by_type(self, type_id: int) -> List[Dict[str, Any]]:
        """根据项目类型ID获取关联的项目内容"""
        if not self.connect():
            return []
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT pc.id, pc.name
                    FROM mcs_by_takuya_project_contents pc
                    JOIN mcs_by_takuya_type_contents tc ON pc.id = tc.content_id
                    WHERE tc.type_id = %s
                    ORDER BY pc.name
                """, (type_id,))
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"获取项目内容失败: {e}")
            return []
        finally:
            self.disconnect()

    def update_work_order_project_info(self, order_id: str, project_type_id: int, project_content_id: int, remarks: str = None) -> bool:
        """更新工单的项目类型、项目内容和备注信息"""
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE mcs_by_takuya_work_orders
                    SET project_type_id = %s, project_content_id = %s, remarks = %s
                    WHERE id = %s
                """, (project_type_id, project_content_id, remarks, order_id))
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新工单项目信息失败: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def add_work_order_with_project_info(self, order_data: Dict[str, Any]) -> bool:
        """添加工单并设置项目类型、项目内容和备注信息"""
        if not self.connect(): return False
        try:
            with self.connection.cursor() as cursor:
                # 获取部门ID
                cursor.execute("SELECT id FROM mcs_by_takuya_departments WHERE name = %s", (order_data['department'],))
                dept_result = cursor.fetchone()
                if not dept_result:
                    self.logger.error(f"找不到部门: {order_data['department']}")
                    return False
                dept_id = dept_result[0]

                # 添加工单
                query = """
                    INSERT INTO mcs_by_takuya_work_orders 
                    (id, department_id, model, name, creator, requester, type, status, project_type_id, project_content_id, remarks) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                order_type = order_data.get('type', '常规')
                requester = order_data.get('requester', '')
                # 支持两种字段名：project_type_id和projecttype_id
                project_type_id = order_data.get('project_type_id')
                if project_type_id is None:
                    project_type_id = order_data.get('projecttype_id')
                
                # 支持两种字段名：project_content_id和project_contentid
                project_content_id = order_data.get('project_content_id')
                if project_content_id is None:
                    project_content_id = order_data.get('project_contentid')
                
                remarks = order_data.get('remarks', '')

                cursor.execute(query, (
                    order_data['id'],
                    dept_id,
                    order_data['model'],
                    order_data['name'],
                    order_data['creator'],
                    requester,
                    order_type,
                    '拍摄中',
                    project_type_id,
                    project_content_id,
                    remarks
                ))
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"添加工单失败: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

# 全局数据库管理器实例
db_manager = DatabaseManager()