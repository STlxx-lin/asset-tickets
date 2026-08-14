import functools
import logging
import threading
from datetime import datetime
from typing import Any

import pymysql

from .config import DB_CONFIG, DEFAULT_NOTIFICATION_TYPE

# 默认角色列表（唯一来源，新增角色仅在此维护）
DEFAULT_ROLES = ["采购", "摄影", "美工", "剪辑", "运营", "销售", "视频审核", "视频后期审核", "美工后期审批"]

# 本地表存在的时间字段白名单（供 update_work_order_time_field 与 status_sync 回滚共用）。
# 注意：photographer_*/start_time/end_time 仅存在于外部 API 字段映射（api_manager.TIME_FIELD_MAP），
# 本地 mcs_by_takuya_work_orders 表无对应列——摄影时间只直调外部 API 同步（photography.py），
# 禁止写入本地，避免白名单与真实 schema 漂移造成 Unknown column 误用陷阱。
TIME_FIELDS = [
    'art_start_time', 'art_end_time', 'edit_start_time', 'edit_end_time',
]

# 数据库操作全局锁：pymysql 连接对象非线程安全（主线程 UI 槽函数与 QThread 任务回调
# 可能并发访问同一个 db_manager 单例），用可重入锁将所有涉及 self.connection 的
# 操作串行化，避免协议状态污染（cursor 交错 / Packet sequence number wrong）与并发建连泄漏。
_db_lock = threading.RLock()


def _db_locked(func):
    """装饰器：对 DatabaseManager 公开方法加全局可重入锁。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _db_lock:
            return func(*args, **kwargs)
    return wrapper


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.config = DB_CONFIG  # 从配置文件导入数据库连接配置
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    @_db_locked
    def connect(self):
        """获取数据库连接；若已有存活连接则复用，否则重新连接。"""
        # 复用存活连接，避免每次查询都新建连接
        if self.connection is not None:
            try:
                self.connection.ping(reconnect=True)
                return True
            except Exception:
                # 连接已失效（如数据库重启），关闭后重新建立
                try:
                    self.connection.close()
                except Exception:
                    pass
                self.connection = None
        try:
            self.connection = pymysql.connect(**self.config)
            self.logger.info("数据库连接成功")
            return True
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            return False

    @_db_locked
    def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
            self.logger.info("数据库连接已关闭")

    @_db_locked
    def get_roles(self) -> list[str]:
        if not self.connect():
            return []
        try:
            with self.connection.cursor() as cursor:
                # 确保默认角色存在（如数据库已建但缺少角色时）
                for role in DEFAULT_ROLES:
                    cursor.execute("INSERT IGNORE INTO mcs_by_takuya_roles (name) VALUES (%s)", (role,))
                self.connection.commit()

                cursor.execute("SELECT name FROM mcs_by_takuya_roles")
                all_roles = [row[0] for row in cursor.fetchall()]
                
                # 按照指定顺序排序
                desired_order = DEFAULT_ROLES
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

    @_db_locked
    def get_departments(self) -> list[str]:
        if not self.connect():
            return []
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT name FROM mcs_by_takuya_departments ORDER BY name")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"获取部门失败: {e}")
            return []

    @_db_locked
    def get_work_orders(self, user_departments: list[str] = None) -> list[dict[str, Any]]:
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
                               wo.project_type_id, wo.project_content_id, wo.remarks,
                               wo.edit_product_path, wo.art_status,
                               wo.art_start_time, wo.art_end_time,
                               wo.edit_start_time, wo.edit_end_time
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
                               wo.project_type_id, wo.project_content_id, wo.remarks,
                               wo.edit_product_path, wo.art_status,
                               wo.art_start_time, wo.art_end_time,
                               wo.edit_start_time, wo.edit_end_time
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

    @_db_locked
    def add_role(self, role_name: str) -> bool:
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("INSERT INTO mcs_by_takuya_roles (name) VALUES (%s)", (role_name,))
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"添加角色失败: {e}")
            return False

    @_db_locked
    def remove_role(self, role_name: str) -> bool:
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("DELETE FROM mcs_by_takuya_roles WHERE name = %s", (role_name,))
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"删除角色失败: {e}")
            return False

    @_db_locked
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

    @_db_locked
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

    @_db_locked
    def add_log(self, role: str, action_type: str, details: str, ip_address: str = "N/A", user_name: str = "") -> bool:
        if not self.connect(): return False
        try:
            # 从 details 中提取工单ID（工单ID=xxx 格式），写入 order_id 列加速按工单查询
            order_id = None
            if '工单ID=' in details:
                try:
                    order_id = details.split('工单ID=', 1)[1].split(',', 1)[0].strip() or None
                except Exception:
                    order_id = None
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO mcs_by_takuya_logs (role, action_type, details, ip_address, user_name, order_id) VALUES (%s, %s, %s, %s, %s, %s)",
                    (role, action_type, details, ip_address, user_name, order_id)
                )
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"记录日志失败: {e}")
            return False

    @_db_locked
    def get_logs(self, limit: int = 200, role: str | None = None, user_name: str | None = None, action_type: str | None = None, ip_address: str | None = None, start_time: str | None = None, end_time: str | None = None, offset: int = 0) -> list[dict[str, Any]]:
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

    @_db_locked
    def add_work_order(self, order_data: dict[str, Any]) -> bool:
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

    @_db_locked
    def update_work_orders_status_bulk(self, ids: list[str], new_status: str) -> int:
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

    @_db_locked
    def update_work_order_status(self, order_id: str, new_status: str, expected_version: int | None = None) -> bool:
        """
        更新单个工单的状态。
        :param order_id: 工单ID
        :param new_status: 新状态
        :param expected_version: 乐观锁期望版本号；非 None 时仅当版本匹配才更新（并发保护）
        :return: 是否成功
        """
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                if expected_version is not None:
                    cursor.execute(
                        "UPDATE mcs_by_takuya_work_orders SET status=%s, version=version+1 WHERE id=%s AND version=%s",
                        (new_status, order_id, expected_version)
                    )
                else:
                    cursor.execute(
                        "UPDATE mcs_by_takuya_work_orders SET status=%s, version=version+1 WHERE id=%s",
                        (new_status, order_id)
                    )
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新工单状态失败: {e}")
            self.connection.rollback()
            return False

    @_db_locked
    def update_work_order_art_status(self, order_id: str, new_status: str, expected_version: int | None = None) -> bool:
        """
        更新单个工单的美工专属状态（art_status 字段，与全局 status 解耦）。

        美工链状态独立记录，避免与剪辑链的全局状态互相覆盖。
        :param order_id: 工单ID
        :param new_status: 美工新状态
        :param expected_version: 乐观锁期望版本号；非 None 时仅当版本匹配才更新
        :return: 是否成功
        """
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                if expected_version is not None:
                    cursor.execute(
                        "UPDATE mcs_by_takuya_work_orders SET art_status=%s, version=version+1 WHERE id=%s AND version=%s",
                        (new_status, order_id, expected_version)
                    )
                else:
                    cursor.execute(
                        "UPDATE mcs_by_takuya_work_orders SET art_status=%s, version=version+1 WHERE id=%s",
                        (new_status, order_id)
                    )
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新工单美工状态失败: {e}")
            self.connection.rollback()
            return False

    @_db_locked
    def update_work_order_time_field(self, order_id: str, field_name: str, time_value: datetime, expected_version: int | None = None) -> bool:
        """
        更新工单的时间字段。
        :param order_id: 工单ID
        :param field_name: 时间字段名称
        :param time_value: 时间值
        :param expected_version: 乐观锁期望版本号；非 None 时仅当版本匹配才更新
        :return: 是否成功
        """
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                # 检查字段是否存在（引用模块级白名单 TIME_FIELDS，避免与 status_sync 回滚白名单漂移）
                if field_name not in TIME_FIELDS:
                    self.logger.error(f"无效的时间字段: {field_name}")
                    return False

                if expected_version is not None:
                    cursor.execute(
                        f"UPDATE mcs_by_takuya_work_orders SET {field_name}=%s, version=version+1 WHERE id=%s AND version=%s",
                        (time_value, order_id, expected_version)
                    )
                else:
                    cursor.execute(
                        f"UPDATE mcs_by_takuya_work_orders SET {field_name}=%s, version=version+1 WHERE id=%s",
                        (time_value, order_id)
                    )
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新工单时间字段失败: {e}")
            self.connection.rollback()
            return False

    @_db_locked
    def update_work_order_product_path(self, order_id: str, product_path: str, expected_version: int | None = None) -> bool:
        """
        更新工单的成品路径字段值。
        :param order_id: 工单ID
        :param product_path: 成品路径
        :param expected_version: 乐观锁期望版本号；非 None 时仅当版本匹配才更新
        :return: 是否成功
        """
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                if expected_version is not None:
                    cursor.execute(
                        "UPDATE mcs_by_takuya_work_orders SET edit_product_path=%s, version=version+1 WHERE id=%s AND version=%s",
                        (product_path, order_id, expected_version)
                    )
                else:
                    cursor.execute(
                        "UPDATE mcs_by_takuya_work_orders SET edit_product_path=%s, version=version+1 WHERE id=%s",
                        (product_path, order_id)
                    )
                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新工单成品路径失败: {e}")
            self.connection.rollback()
            return False

    # 供 status_sync 多字段原子写入使用的字段白名单（status/art_status/成品路径 + 时间字段）
    _WORK_ORDER_UPDATE_FIELDS = {'status', 'art_status', 'edit_product_path'} | set(TIME_FIELDS)

    @_db_locked
    def update_work_order_fields(self, order_id: str, updates: dict, expected_version: int | None = None) -> int:
        """
        单条 UPDATE 原子更新多个字段（带可选乐观锁版本检查）。

        供 status_sync 使用：把"状态 + art_status + 时间"收敛进同一条 UPDATE，
        消除"先写后调封装、本地失败不回滚"的窗口期。

        :param order_id: 工单ID
        :param updates: 字段名 → 值 字典（键必须位于 _WORK_ORDER_UPDATE_FIELDS 白名单）
        :param expected_version: 期望版本号；非 None 时仅当版本匹配才更新
        :return: 受影响行数；-1 表示异常（区别于"版本冲突/工单不存在"的 0）
        """
        if not updates:
            return 0
        invalid = set(updates) - self._WORK_ORDER_UPDATE_FIELDS
        if invalid:
            self.logger.error(f"更新工单字段包含白名单外字段: {invalid}")
            return -1
        if not self.connect():
            return -1
        try:
            sets = ", ".join(f"{k}=%s" for k in updates)
            params = list(updates.values())
            with self.connection.cursor() as cursor:
                if expected_version is not None:
                    cursor.execute(
                        f"UPDATE mcs_by_takuya_work_orders SET {sets}, version=version+1 WHERE id=%s AND version=%s",
                        params + [order_id, expected_version]
                    )
                else:
                    cursor.execute(
                        f"UPDATE mcs_by_takuya_work_orders SET {sets}, version=version+1 WHERE id=%s",
                        params + [order_id]
                    )
                self.connection.commit()
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"更新工单字段失败: {e}")
            self.connection.rollback()
            return -1

    @_db_locked
    def get_work_order_version(self, order_id: str) -> int | None:
        """读取工单乐观锁版本号；工单不存在或查询失败返回 None。"""
        if not self.connect():
            return None
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT version FROM mcs_by_takuya_work_orders WHERE id=%s", (order_id,))
                row = cursor.fetchone()
                return int(row[0]) if row else None
        except Exception as e:
            self.logger.error(f"读取工单版本失败: {e}")
            return None

    @_db_locked
    def get_work_order_by_id(self, order_id: str) -> dict[str, Any] | None:
        """按工单ID查询最新数据（办理对话框打开前刷新，避免使用列表快照）。

        字段集与 get_work_orders 保持一致；工单不存在或查询失败返回 None。
        """
        if not self.connect():
            return None
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT wo.id, d.name as department, wo.model, wo.name,
                           wo.creator, wo.requester, wo.type, wo.status,
                           wo.created_at, wo.updated_at,
                           pt.name as project_type, pc.name as project_content,
                           wo.project_type_id, wo.project_content_id, wo.remarks,
                           wo.edit_product_path, wo.art_status,
                           wo.art_start_time, wo.art_end_time,
                           wo.edit_start_time, wo.edit_end_time
                    FROM mcs_by_takuya_work_orders wo
                    JOIN mcs_by_takuya_departments d ON wo.department_id = d.id
                    LEFT JOIN mcs_by_takuya_project_types pt ON wo.project_type_id = pt.id
                    LEFT JOIN mcs_by_takuya_project_contents pc ON wo.project_content_id = pc.id
                    WHERE wo.id = %s
                """, (order_id,))
                return cursor.fetchone()
        except Exception as e:
            self.logger.error(f"获取工单{order_id}失败: {e}")
            return None

    @_db_locked
    def get_logs_by_order_id(self, order_id: str):
        if not self.connect():
            return []
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT role, user_name, action_type, details, timestamp
                    FROM mcs_by_takuya_logs
                    WHERE order_id = %s
                    ORDER BY timestamp DESC
                """, (order_id,))
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"获取工单日志失败: {e}")
            return []

    @_db_locked
    def get_logs_by_order_ids(self, order_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not order_ids:
            return {}
        if not self.connect():
            return {}
        try:
            conditions = " OR ".join(["order_id = %s"] * len(order_ids))
            params = list(order_ids)
            query = f"""
                SELECT order_id, role, user_name, action_type, details, timestamp
                FROM mcs_by_takuya_logs
                WHERE {conditions}
                ORDER BY timestamp DESC
            """
            result = {oid: [] for oid in order_ids}
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    oid = row.get('order_id')
                    if oid in result:
                        result[oid].append(row)
            return result
        except Exception as e:
            self.logger.error(f"批量获取工单日志失败: {e}")
            return {}


    @_db_locked
    def save_product_info(self, work_order_id: str, products: list[dict[str, str]]) -> bool:
        """保存产品信息到数据库（DELETE + 全部 INSERT 在同一事务内，中途失败整体回滚）"""
        if not self.connect():
            return False
        try:
            # autocommit 模式下 begin() 会挂起自动提交，直到 COMMIT/ROLLBACK 后恢复，
            # 保证 DELETE 与全部 INSERT 原子化：任一条插入失败都不会留下"旧数据已删、新数据残缺"的半写状态
            self.connection.begin()
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
            try:
                self.connection.rollback()
            except Exception:
                pass
            return False

    @_db_locked
    def get_product_info(self, work_order_id: str) -> list[dict[str, str]]:
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

    @_db_locked
    def delete_work_order(self, order_id: str) -> bool:
        """根据工单ID删除工单（产品信息通过外键 ON DELETE CASCADE 自动删除；日志表无外键，历史日志保留）"""
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

    @_db_locked
    def update_work_order_full(self, order_id: str, department: str, model: str, name: str, creator: str, requester: str = "", project_type: str = "", project_content: str = "", projecttype_id: int = None, project_contentid: int = None, remarks: str = "") -> bool:
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
                    SET department_id = %s, model = %s, name = %s, creator = %s, requester = %s,
                        project_type_id = %s, project_content_id = %s, remarks = %s 
                    WHERE id = %s
                """, (dept_id, model, name, creator, requester, project_type_id, project_content_id, remarks, order_id))

                self.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新工单失败: {e}")
            try:
                self.connection.rollback()
            except Exception:
                pass
            return False

    @_db_locked
    def get_users(self, name: str | None = None, ip: str | None = None, role: str | None = None, department: str | None = None) -> list[dict[str, Any]]:
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

    @_db_locked
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

    @_db_locked
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

    @_db_locked
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

    @_db_locked
    def get_action_types(self) -> list:
        if not self.connect(): return []
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT action_type FROM mcs_by_takuya_logs ORDER BY action_type")
                return [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            self.logger.error(f"获取操作类型失败: {e}")
            return []

    @_db_locked
    def get_user_names(self) -> list:
        if not self.connect(): return []
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT user_name FROM mcs_by_takuya_logs ORDER BY user_name")
                return [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            self.logger.error(f"获取用户姓名失败: {e}")
            return []

    @_db_locked
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

    def _ensure_notification_settings_table(self, cursor) -> None:
        """确保按产线通知配置表存在。"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_notification_line_settings (
                line_name VARCHAR(100) PRIMARY KEY,
                notification_type VARCHAR(20) NOT NULL DEFAULT 'wechat_work',
                dingtalk_webhook TEXT,
                dingtalk_secret VARCHAR(255),
                wechat_work_webhook TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    @_db_locked
    def get_all_notification_settings(self) -> dict[str, dict[str, str]]:
        """获取所有产线的通知配置。"""
        if not self.connect():
            return {}

        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                self._ensure_notification_settings_table(cursor)
                cursor.execute("""
                    SELECT line_name, notification_type, dingtalk_webhook, dingtalk_secret, wechat_work_webhook
                    FROM app_notification_line_settings
                """)
                rows = cursor.fetchall()
                settings_map = {}
                for row in rows:
                    line_name = row.get("line_name")
                    if not line_name:
                        continue
                    settings_map[line_name] = {
                        "notification_type": row.get("notification_type") or DEFAULT_NOTIFICATION_TYPE,
                        "dingtalk_webhook": row.get("dingtalk_webhook") or "",
                        "dingtalk_secret": row.get("dingtalk_secret") or "",
                        "wechat_work_webhook": row.get("wechat_work_webhook") or ""
                    }
                return settings_map
        except Exception as e:
            self.logger.error(f"获取通知配置失败: {e}")
            return {}

    @_db_locked
    def upsert_notification_setting(self, line_name: str, settings: dict[str, str]) -> bool:
        """保存单个产线的通知配置。"""
        if not self.connect():
            return False

        try:
            with self.connection.cursor() as cursor:
                self._ensure_notification_settings_table(cursor)
                cursor.execute("""
                    INSERT INTO app_notification_line_settings
                    (line_name, notification_type, dingtalk_webhook, dingtalk_secret, wechat_work_webhook)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        notification_type = VALUES(notification_type),
                        dingtalk_webhook = VALUES(dingtalk_webhook),
                        dingtalk_secret = VALUES(dingtalk_secret),
                        wechat_work_webhook = VALUES(wechat_work_webhook)
                """, (
                    line_name,
                    settings.get("notification_type", DEFAULT_NOTIFICATION_TYPE),
                    settings.get("dingtalk_webhook", ""),
                    settings.get("dingtalk_secret", ""),
                    settings.get("wechat_work_webhook", "")
                ))
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"保存产线通知配置失败: {e}")
            self.connection.rollback()
            return False

    @_db_locked
    def seed_notification_settings_if_empty(self, seed_data: dict[str, dict[str, str]]) -> bool:
        """当通知配置表为空时，写入当前代码内的通知配置作为初始数据。"""
        if not self.connect():
            return False

        try:
            with self.connection.cursor() as cursor:
                # 显式开启事务，避免 autocommit=True 导致部分数据提前提交
                self.connection.begin()
                self._ensure_notification_settings_table(cursor)
                cursor.execute("SELECT COUNT(*) FROM app_notification_line_settings")
                row_count = cursor.fetchone()[0]
                if row_count > 0:
                    # 已有数据时提交并直接返回，保持事务边界完整
                    self.connection.commit()
                    return True

                # 批量构造插入参数（注意：此前 CREATE TABLE 的 DDL 在 MySQL 中会隐式提交，
                # 故此处事务无法覆盖建表，仅保证 INSERT 批量写入的一致性）
                insert_values = []
                for line_name, settings in seed_data.items():
                    insert_values.append((
                        line_name,
                        settings.get("notification_type", DEFAULT_NOTIFICATION_TYPE),
                        settings.get("dingtalk_webhook", ""),
                        settings.get("dingtalk_secret", ""),
                        settings.get("wechat_work_webhook", "")
                    ))
                if insert_values:
                    cursor.executemany("""
                        INSERT INTO app_notification_line_settings
                        (line_name, notification_type, dingtalk_webhook, dingtalk_secret, wechat_work_webhook)
                        VALUES (%s, %s, %s, %s, %s)
                    """, insert_values)
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"初始化通知配置失败: {e}")
            self.connection.rollback()
            return False

    @_db_locked
    def get_project_types(self) -> list[dict[str, Any]]:
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

    @_db_locked
    def get_project_contents_by_type(self, type_id: int) -> list[dict[str, Any]]:
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

    @_db_locked
    def get_project_type_name(self, type_id) -> str | None:
        """根据项目类型ID获取名称，未找到时返回 None"""
        if type_id is None:
            return None
        if not self.connect():
            return None
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT name FROM mcs_by_takuya_project_types WHERE id = %s LIMIT 1", (type_id,))
                result = cursor.fetchone()
                return str(result[0]) if result else None
        except Exception as e:
            self.logger.error(f"获取项目类型名称失败: {e}")
            return None

    @_db_locked
    def get_project_content_name(self, content_id) -> str | None:
        """根据项目内容ID获取名称，未找到时返回 None"""
        if content_id is None:
            return None
        if not self.connect():
            return None
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT name FROM mcs_by_takuya_project_contents WHERE id = %s LIMIT 1", (content_id,))
                result = cursor.fetchone()
                return str(result[0]) if result else None
        except Exception as e:
            self.logger.error(f"获取项目内容名称失败: {e}")
            return None

    @_db_locked
    def get_work_order_project_names(self, order_id: str) -> dict[str, Any]:
        """根据工单ID获取项目类型和项目内容名称"""
        if not self.connect():
            return {}
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT pt.name as project_type, pc.name as project_content
                    FROM mcs_by_takuya_work_orders wo
                    LEFT JOIN mcs_by_takuya_project_types pt ON wo.project_type_id = pt.id
                    LEFT JOIN mcs_by_takuya_project_contents pc ON wo.project_content_id = pc.id
                    WHERE wo.id = %s
                """, (order_id,))
                return cursor.fetchone() or {}
        except Exception as e:
            self.logger.error(f"获取工单项目信息失败: {e}")
            return {}

    @_db_locked
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

    def _ensure_review_feedback_table(self, cursor) -> None:
        """确保审核反馈表存在。"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mcs_by_takuya_review_feedback (
                id INT AUTO_INCREMENT PRIMARY KEY,
                work_order_id VARCHAR(20) NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                directory VARCHAR(500) NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_order_id) REFERENCES mcs_by_takuya_work_orders(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    @_db_locked
    def add_review_feedback(self, work_order_id: str, file_name: str, directory: str, reason: str) -> bool:
        """添加一条审核不通过反馈。"""
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                self._ensure_review_feedback_table(cursor)
                cursor.execute("""
                    INSERT INTO mcs_by_takuya_review_feedback (work_order_id, file_name, directory, reason)
                    VALUES (%s, %s, %s, %s)
                """, (work_order_id, file_name, directory, reason))
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"添加审核反馈失败: {e}")
            self.connection.rollback()
            return False

    @_db_locked
    def get_review_feedback(self, work_order_id: str) -> list[dict[str, Any]]:
        """获取某个工单的所有审核反馈记录。"""
        if not self.connect():
            return []
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                self._ensure_review_feedback_table(cursor)
                cursor.execute("""
                    SELECT file_name, directory, reason, created_at
                    FROM mcs_by_takuya_review_feedback
                    WHERE work_order_id = %s
                    ORDER BY created_at DESC
                """, (work_order_id,))
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"获取审核反馈失败: {e}")
            return []

    @_db_locked
    def delete_review_feedback(self, work_order_id: str) -> bool:
        """删除某个工单的所有审核反馈记录。"""
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                self._ensure_review_feedback_table(cursor)
                cursor.execute("""
                    DELETE FROM mcs_by_takuya_review_feedback
                    WHERE work_order_id = %s
                """, (work_order_id,))
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"删除审核反馈失败: {e}")
            self.connection.rollback()
            return False

    def _ensure_system_settings_table(self, cursor) -> None:
        """确保系统功能设置表存在（key-value 结构）。"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_system_settings (
                setting_key VARCHAR(100) PRIMARY KEY,
                setting_value VARCHAR(1000) NOT NULL DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    @_db_locked
    def get_system_setting(self, key: str, default: str = None) -> str | None:
        """读取系统设置项。表不存在或键不存在时返回 default。"""
        if not self.connect():
            return default
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                self._ensure_system_settings_table(cursor)
                cursor.execute(
                    "SELECT setting_value FROM app_system_settings WHERE setting_key = %s",
                    (key,)
                )
                row = cursor.fetchone()
                return row['setting_value'] if row else default
        except Exception as e:
            self.logger.error(f"读取系统设置 [{key}] 失败: {e}")
            return default

    @_db_locked
    def set_system_setting(self, key: str, value: str) -> bool:
        """写入或更新系统设置项。"""
        if not self.connect():
            return False
        try:
            with self.connection.cursor() as cursor:
                self._ensure_system_settings_table(cursor)
                cursor.execute("""
                    INSERT INTO app_system_settings (setting_key, setting_value)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
                """, (key, value))
                self.connection.commit()
                return True
        except Exception as e:
            self.logger.error(f"保存系统设置 [{key}] 失败: {e}")
            self.connection.rollback()
            return False

    @_db_locked
    def get_local_ip(self) -> str:
        """获取本机最适合系统的本地 IP 地址，支持在开启 VPN 时智能识别物理局域网 IP。"""
        import socket

        import netifaces

        local_ips = []
        try:
            for iface in netifaces.interfaces():
                iface_lower = iface.lower()
                # 标记是否为常见的虚拟网卡/VPN适配器
                is_virtual = any(x in iface_lower for x in ['tun', 'tap', 'vpn', 'ppp', 'virtual', 'vbox', 'vmnet', 'virtualbox', 'docker', 'tailscale', 'zerotier'])
                ifaddrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in ifaddrs:
                    for addr_info in ifaddrs[netifaces.AF_INET]:
                        ip = addr_info['addr']
                        if not ip.startswith('127.') and not ip.startswith('169.254.'):
                            local_ips.append((ip, is_virtual))
        except Exception as e:
            self.logger.warning(f"获取本机网卡 IP 列表失败: {e}")

        # 1. 优先比对数据库中已注册的用户 IP。若本机 IP 存在于注册列表中，且为物理网卡，优先使用
        try:
            users = self.get_users()
            registered_ips = {u['ip'].strip() for u in users if u.get('ip')}
            
            matched_physical_ips = [ip for ip, is_virt in local_ips if ip in registered_ips and not is_virt]
            if matched_physical_ips:
                return matched_physical_ips[0]
                
            matched_any_ips = [ip for ip, is_virt in local_ips if ip in registered_ips]
            if matched_any_ips:
                return matched_any_ips[0]
        except Exception as e:
            self.logger.warning(f"获取已注册用户 IP 列表匹配失败: {e}")

        # 2. 尝试通过 UDP 连接数据库主机，获取通信网卡 IP
        try:
            db_host = self.config.get('host')
            if db_host and db_host not in ('localhost', '127.0.0.1'):
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(1.0)
                s.connect((db_host, 3306))
                ip = s.getsockname()[0]
                s.close()
                if not ip.startswith('127.') and not ip.startswith('169.254.'):
                    return ip
        except Exception:
            pass

        # 3. 尝试通过 UDP 连接公网 DNS (8.8.8.8) 获取默认出口 IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1.0)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            if not ip.startswith('127.') and not ip.startswith('169.254.'):
                return ip
        except Exception:
            pass

        # 4. 兜底逻辑：返回网卡列表中第一个物理网卡 IP；若无，返回第一个虚拟网卡 IP
        physical_ips = [ip for ip, is_virt in local_ips if not is_virt]
        if physical_ips:
            return physical_ips[0]
        if local_ips:
            return local_ips[0][0]

        return '无法获取IP'

# 全局数据库管理器实例
db_manager = DatabaseManager()
