import requests
import logging
import time
import requests

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
            # 构造请求体
            payload = {
                "id": str(order_data['id']),  # id=工单id
                "f_emd69kip4gk": str(order_data['model']),  # 型号=编号
                "f_ifa9xxyrmft": order_data.get('name', ''),  # 名称=产品名称
                "f_jxzzjg7egqm": order_data.get('requester', ''),  # 负责人=需求人
                "f_utqw1679w43": order_data.get('status', ''),
                "f_iis2qlzmmko": int(time.time()),  # 开始时间=工单创建时间-时间戳
                "f_ay6dm3j0pfz": order_data.get('project_type_name', ''),  # 项目类型=项目类型名称
                "f_a9q7rpf5paj": order_data.get('project_content_name', ''),  # 项目内容=项目内容名称
                "f_4civ803ubaz": self._convert_time_to_timestamp(order_data.get('end_time', '')),
                "f_8ufkn1d1z3v": self._convert_time_to_timestamp(order_data.get('photographer_start_time', '')),
                "f_augkx557xwf": self._convert_time_to_timestamp(order_data.get('photographer_end_time', '')),
                "f_vyp0iizeom5": self._convert_time_to_timestamp(order_data.get('art_start_time', '')),
                "f_pkcr94xo1py": self._convert_time_to_timestamp(order_data.get('art_end_time', '')),
                "f_n9vu52g0c4f": self._convert_time_to_timestamp(order_data.get('edit_start_time', '')),
                "f_6aocwxxqcfj": self._convert_time_to_timestamp(order_data.get('edit_end_time', ''))
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