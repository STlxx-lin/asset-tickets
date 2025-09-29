import requests
import logging
import time
import pymysql
from config import DB_CONFIG
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('API Manager')

class APIManager:
    """API管理器，封装创建工单和更新工单系统信息的API调用"""
    _instance = None
    _token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEsInJvbGVOYW1lIjoiYWRtaW4iLCJpYXQiOjE3NTU4Mzk3NTcsImV4cCI6MzMzMTM0Mzk3NTd9.4xYz71zgKO2S_iluTwCY7i2h1nRpHE1cuMKa20E7grw"
    _headers = {
        "Authorization": _token,
        "Content-Type": "application/json"
    }
    _create_url = "http://192.168.0.54:13000/api/t_d5n8vtsnrwv:create"
    _update_url = "http://192.168.0.54:13000/api/t_d5n8vtsnrwv:update"

    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(APIManager, cls).__new__(cls)
        return cls._instance

    def _convert_time_to_timestamp(self, time_str):
        """将时间字符串转换为时间戳

        Args:
            time_str: 时间字符串，格式如'YYYY-MM-DD HH:MM:SS'

        Returns:
            int: 时间戳
        """
        if not time_str:
            return 0
        try:
            # 将时间字符串转换为时间戳
            timestamp = int(time.mktime(time.strptime(time_str, '%Y-%m-%d %H:%M:%S')))
            return timestamp
        except Exception as e:
            logger.error(f"时间转换失败: {e}")
            return 0

    def create_work_order(self, order_data):
        """创建工单系统信息

        Args:
            order_data: 工单数据字典，包含id、项目名称、申请人等信息

        Returns:
            dict: 响应结果，包含success和message或error
        """
        try:
            # 创建一个副本以避免修改原始数据
            api_order_data = order_data.copy()
            
            # 初始化项目类型和内容名称
            project_type_name = ""
            project_content_name = ""
            
            # 尝试从数据库获取项目类型和项目内容的名称
            try:
                # 直接连接数据库查询
                conn = pymysql.connect(**DB_CONFIG)
                cursor = conn.cursor()
                
                logger.info(f"尝试从数据库获取项目类型和内容信息")
                
                # 1. 首先检查order_data中是否有project_type_id或project_content_id
                project_type_id = api_order_data.get('project_type_id') or api_order_data.get('projecttype_id')
                project_content_id = api_order_data.get('project_content_id') or api_order_data.get('projectcontent_id')
                
                # 2. 如果没有直接的ID字段，尝试使用project_type和project_content字段作为ID
                if not project_type_id:
                    project_type_id = api_order_data.get('project_type')
                if not project_content_id:
                    project_content_id = api_order_data.get('project_content')
                
                logger.info(f"查询参数: project_type_id={project_type_id}, project_content_id={project_content_id}")
                
                # 查询项目类型名称
                if project_type_id:
                    try:
                        # 首先检查表结构
                        cursor.execute("DESCRIBE mcs_by_takuya_project_types")
                        columns = cursor.fetchall()
                        logger.info(f"项目类型表结构: {[col[0] for col in columns]}")
                        
                        # 尝试不同的字段名查询
                        # 方法1：尝试查询所有列
                        query = "SELECT * FROM mcs_by_takuya_project_types WHERE id = %s LIMIT 1"
                        cursor.execute(query, (project_type_id,))
                        result = cursor.fetchone()
                        
                        if result:
                            # 尝试不同的可能的名称字段
                            for field_idx, field_name in enumerate([col[0] for col in columns]):
                                if field_name.lower() in ['name', 'title', 'label', 'display_name']:
                                    project_type_name = str(result[field_idx])
                                    logger.info(f"通过字段 {field_name} 成功获取项目类型名称: {project_type_name}")
                                    break
                            
                            # 如果没有找到专门的名称字段，尝试使用ID作为名称
                            if not project_type_name:
                                project_type_name = str(project_type_id)
                                logger.warning(f"未找到明确的名称字段，使用ID作为项目类型名称: {project_type_name}")
                        else:
                            # 查询所有项目类型数据以便调试
                            cursor.execute("SELECT * FROM mcs_by_takuya_project_types LIMIT 5")
                            all_types = cursor.fetchall()
                            logger.info(f"查询到的项目类型数据示例: {all_types}")
                            
                            # 如果没有找到，尝试将ID作为名称使用
                            project_type_name = str(project_type_id)
                            logger.warning(f"未找到项目类型ID {project_type_id} 对应的记录，使用ID作为名称")
                    except Exception as e:
                        logger.error(f"查询项目类型失败: {e}")
                        logger.debug(traceback.format_exc())
                        # 异常时使用ID作为名称
                        project_type_name = str(project_type_id)
                
                # 查询项目内容名称
                if project_content_id:
                    try:
                        # 首先检查表结构
                        cursor.execute("DESCRIBE mcs_by_takuya_project_contents")
                        columns = cursor.fetchall()
                        logger.info(f"项目内容表结构: {[col[0] for col in columns]}")
                        
                        # 尝试不同的字段名查询
                        # 方法1：尝试查询所有列
                        query = "SELECT * FROM mcs_by_takuya_project_contents WHERE id = %s LIMIT 1"
                        cursor.execute(query, (project_content_id,))
                        result = cursor.fetchone()
                        
                        if result:
                            # 尝试不同的可能的名称字段
                            for field_idx, field_name in enumerate([col[0] for col in columns]):
                                if field_name.lower() in ['name', 'title', 'label', 'display_name']:
                                    project_content_name = str(result[field_idx])
                                    logger.info(f"通过字段 {field_name} 成功获取项目内容名称: {project_content_name}")
                                    break
                            
                            # 如果没有找到专门的名称字段，尝试使用ID作为名称
                            if not project_content_name:
                                project_content_name = str(project_content_id)
                                logger.warning(f"未找到明确的名称字段，使用ID作为项目内容名称: {project_content_name}")
                        else:
                            # 查询所有项目内容数据以便调试
                            cursor.execute("SELECT * FROM mcs_by_takuya_project_contents LIMIT 5")
                            all_contents = cursor.fetchall()
                            logger.info(f"查询到的项目内容数据示例: {all_contents}")
                            
                            # 如果没有找到，尝试将ID作为名称使用
                            project_content_name = str(project_content_id)
                            logger.warning(f"未找到项目内容ID {project_content_id} 对应的记录，使用ID作为名称")
                    except Exception as e:
                        logger.error(f"查询项目内容失败: {e}")
                        logger.debug(traceback.format_exc())
                        # 异常时使用ID作为名称
                        project_content_name = str(project_content_id)
                
                # 关闭数据库连接
                cursor.close()
                conn.close()
                
            except Exception as db_error:
                logger.error(f"数据库操作异常: {db_error}")
                # 数据库操作失败时，尝试使用备用方案
                project_type_name = api_order_data.get('project_type_name', api_order_data.get('project_type', ''))
                project_content_name = api_order_data.get('project_content_name', api_order_data.get('project_content', ''))
            
            # 如果仍然没有获取到值，尝试从工单表中查询
            if not project_type_name or not project_content_name:
                try:
                    conn = pymysql.connect(**DB_CONFIG)
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    
                    # 从工单表中查询项目类型和内容
                    query = """
                        SELECT project_type, project_content 
                        FROM mcs_by_takuya_work_orders 
                        WHERE id = %s
                    """
                    cursor.execute(query, (api_order_data['id'],))
                    order_info = cursor.fetchone()
                    
                    if order_info:
                        if not project_type_name and order_info.get('project_type'):
                            project_type_name = str(order_info['project_type'])
                            logger.info(f"从工单表获取项目类型: {project_type_name}")
                        if not project_content_name and order_info.get('project_content'):
                            project_content_name = str(order_info['project_content'])
                            logger.info(f"从工单表获取项目内容: {project_content_name}")
                    
                    cursor.close()
                    conn.close()
                except Exception as e:
                    logger.error(f"从工单表查询项目信息失败: {e}")
            
            logger.info(f"最终使用的项目类型: '{project_type_name}', 项目内容: '{project_content_name}'")
            
            # 构造请求体
            payload = {
                "id": str(api_order_data['id']),  # id=工单id
                "f_emd69kip4gk": str(api_order_data['model']),  # 型号=编号
                "f_ifa9xxyrmft": api_order_data.get('name', ''),  # 名称=产品名称
                "f_jxzzjg7egqm": api_order_data.get('requester', ''),  # 负责人=需求人
                "f_utqw1679w43": api_order_data.get('status', ''),
                "f_iis2qlzmmko": int(time.time()),  # 开始时间=工单创建时间-时间戳
                "f_ay6dm3j0pfz": project_type_name,  # 项目类型=从数据库获取的名称
                "f_a9q7rpf5paj": project_content_name,  # 项目内容=从数据库获取的名称
                "f_4civ803ubaz": self._convert_time_to_timestamp(api_order_data.get('end_time', '')),
                "f_8ufkn1d1z3v": self._convert_time_to_timestamp(api_order_data.get('photographer_start_time', '')),
                "f_augkx557xwf": self._convert_time_to_timestamp(api_order_data.get('photographer_end_time', '')),
                "f_vyp0iizeom5": self._convert_time_to_timestamp(api_order_data.get('art_start_time', '')),
                "f_pkcr94xo1py": self._convert_time_to_timestamp(api_order_data.get('art_end_time', '')),
                "f_n9vu52g0c4f": self._convert_time_to_timestamp(api_order_data.get('edit_start_time', '')),
                "f_6aocwxxqcfj": self._convert_time_to_timestamp(api_order_data.get('edit_end_time', ''))
            }

            # 发送请求
            logger.info(f"发送创建工单API请求: {payload}")
            response = requests.post(self._create_url, json=payload, headers=self._headers, timeout=10)

            # 处理响应
            if response.status_code == 200:
                logger.info(f"创建工单{order_data['id']}成功")
                return {
                    "success": True,
                    "message": f"创建工单{order_data['id']}成功",
                    "data": response.json() if response.text else {}
                }
            else:
                logger.error(f"创建工单{order_data['id']}失败: 状态码{response.status_code}, 响应内容{response.text}")
                return {
                    "success": False,
                    "error": f"创建工单失败，状态码{response.status_code}, 响应内容{response.text}"
                }
        except Exception as e:
            logger.error(f"创建工单{order_data['id']}发生异常: {e}")
            return {
                "success": False,
                "error": f"创建工单发生异常: {str(e)}"
            }

    def update_work_order_status(self, order_id, status):
        """更新工单系统中的状态字段

        Args:
            order_id: 工单ID
            status: 工单状态

        Returns:
            dict: 响应结果，包含success和message或error
        """
        try:
            # 构造请求参数和请求体
            params = {
                "filterByTk": str(order_id)
            }

            payload = {
                "f_utqw1679w43": status
            }

            # 发送请求
            logger.info(f"发送更新工单状态API请求: 工单ID={order_id}, 状态={status}")
            response = requests.post(self._update_url, params=params, json=payload, headers=self._headers, timeout=10)

            # 处理响应
            if response.status_code == 200:
                logger.info(f"更新工单{order_id}的状态成功")
                return {
                    "success": True,
                    "message": f"更新工单{order_id}的状态成功",
                    "data": response.json() if response.text else {}
                }
            else:
                logger.error(f"更新工单{order_id}的状态失败: 状态码{response.status_code}, 响应内容{response.text}")
                return {
                    "success": False,
                    "error": f"更新工单状态失败，状态码{response.status_code}, 响应内容{response.text}"
                }
        except Exception as e:
            logger.error(f"更新工单{order_id}的状态发生异常: {e}")
            return {
                "success": False,
                "error": f"更新工单状态发生异常: {str(e)}"
            }

    def update_work_order_time(self, order_id, time_field, time_value):
        """更新工单系统中的时间字段

        Args:
            order_id: 工单ID
            time_field: 时间字段名称(如'art_start_time', 'edit_end_time'等)
            time_value: 时间值，格式为'YYYY-MM-DD HH:MM:SS'

        Returns:
            dict: 响应结果，包含success和message或error
        """
        try:
            # 构造请求参数和请求体
            params = {
                "filterByTk": str(order_id)
            }

            # 转换时间格式为时间戳
            timestamp = self._convert_time_to_timestamp(time_value)

            # 根据时间字段确定对应的API参数名
            field_mapping = {
                'start_time': 'f_iis2qlzmmko',
                'end_time': 'f_4civ803ubaz',
                'photographer_start_time': 'f_8ufkn1d1z3v',
                'photographer_end_time': 'f_augkx557xwf',
                'art_start_time': 'f_n9vu52g0c4f',
                'art_end_time': 'f_pkcr94xo1py',
                'edit_start_time': 'f_vyp0iizeom5',
                'edit_end_time': 'f_6aocwxxqcfj'
            }

            if time_field not in field_mapping:
                logger.error(f"不支持的时间字段: {time_field}")
                return {
                    "success": False,
                    "error": f"不支持的时间字段: {time_field}"
                }

            api_field = field_mapping[time_field]
            payload = {
                api_field: timestamp
            }

            # 发送请求
            logger.info(f"发送更新工单时间API请求: 工单ID={order_id}, 字段={time_field}, 值={time_value}")
            response = requests.post(self._update_url, params=params, json=payload, headers=self._headers, timeout=10)

            # 处理响应
            if response.status_code == 200:
                logger.info(f"更新工单{order_id}的{time_field}成功")
                return {
                    "success": True,
                    "message": f"更新工单{order_id}的{time_field}成功",
                    "data": response.json() if response.text else {}
                }
            else:
                logger.error(f"更新工单{order_id}的{time_field}失败: 状态码{response.status_code}, 响应内容{response.text}")
                return {
                    "success": False,
                    "error": f"更新工单时间失败，状态码{response.status_code}, 响应内容{response.text}"
                }
        except Exception as e:
            logger.error(f"更新工单{order_id}的{time_field}发生异常: {e}")
            return {
                "success": False,
                "error": f"更新工单时间发生异常: {str(e)}"
            }

# 创建单例实例
api_manager = APIManager()