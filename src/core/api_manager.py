from datetime import date, datetime
import ipaddress
import logging
import os
import socket
import time
import urllib.parse

import requests

from .database import db_manager

logger = logging.getLogger('API Manager')

# 外部工单系统 API 仅允许访问此固定内网主机（白名单比对即解析后 IP 校验，杜绝 DNS rebinding）
_API_ALLOWED_HOSTS = {'192.168.0.54'}
_API_ALLOWED_SCHEMES = ('http', 'https')


def _safe_api_url(url: str) -> str | None:
    """校验并规范化外部 API 地址，不合法返回 None。

    校验项：协议白名单、主机白名单、解析后 IP 子集校验（防 DNS rebinding）、去除 fragment。
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in _API_ALLOWED_SCHEMES:
            return None
        host = parsed.hostname
        if not host or host not in _API_ALLOWED_HOSTS:
            return None
        allowed_ips = {ipaddress.ip_address(ip) for ip in _API_ALLOWED_HOSTS}
        resolved_ips = {ipaddress.ip_address(addr[4][0]) for addr in socket.getaddrinfo(host, None)}
        if not resolved_ips or not resolved_ips.issubset(allowed_ips):
            return None
        # 去除 fragment 后返回规范化 URL（urlparse 6 字段与 urlunsplit 5 元组不匹配，用 geturl 规范化）
        return parsed._replace(fragment='').geturl()
    except Exception:
        return None


def _post_api(url: str, *, json=None, params=None, timeout=10):
    """发送外部工单系统 API 请求：地址经 _safe_api_url 强校验且禁止重定向，防止 SSRF。不合法返回 None。"""
    safe = _safe_api_url(url)
    if safe is None:
        logger.error(f"拒绝发送API请求 - 地址不在允许列表: {url}")
        return None
    return requests.post(safe, params=params, json=json, headers=_build_headers(), allow_redirects=False, timeout=timeout)

# 时间字段 → 外部系统字段码 的统一映射（create 与 update 共用，避免两处映射分叉）
# 语义：摄影师开始/结束、美工开始/结束、剪辑开始/结束、工单开始/结束
TIME_FIELD_MAP = {
    'start_time': 'f_iis2qlzmmko',
    'end_time': 'f_4civ803ubaz',
    'photographer_start_time': 'f_8ufkn1d1z3v',
    'photographer_end_time': 'f_augkx557xwf',
    'art_start_time': 'f_n9vu52g0c4f',
    'art_end_time': 'f_pkcr94xo1py',
    'edit_start_time': 'f_vyp0iizeom5',
    'edit_end_time': 'f_6aocwxxqcfj',
}


# Token 缓存：优先数据库 app_system_settings.api_token（管理员设置页可在线更新），
# 其次环境变量 API_TOKEN（.env 由 config 模块加载）；设置保存后调用 refresh_api_token_cache() 刷新。
_token_cache: str | None = None


def _get_token() -> str:
    global _token_cache
    if _token_cache is None:
        # 数据库优先（管理员设置页可在线更新，无需重启）
        try:
            _token_cache = db_manager.get_system_setting('api_token', default='') or ''
        except Exception:
            _token_cache = ''
        if not _token_cache:
            _token_cache = os.environ.get('API_TOKEN', '')
    return _token_cache


def refresh_api_token_cache() -> None:
    """清空 token 缓存（管理员在设置页保存新 token 后调用，立即生效）。"""
    global _token_cache
    _token_cache = None


def _build_headers() -> dict:
    """构建请求头；token 从数据库设置或环境变量读取。"""
    token = _get_token()
    if not token:
        logger.warning("API Token 未配置（数据库 api_token 或环境变量 API_TOKEN），外部工单系统 API 将无法访问")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


class APIManager:
    """API管理器，封装创建工单和更新工单系统信息的API调用"""
    _instance = None
    _create_url = "http://192.168.0.54:13000/api/t_d5n8vtsnrwv:create"
    _update_url = "http://192.168.0.54:13000/api/t_d5n8vtsnrwv:update"

    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _convert_time_to_timestamp(self, time_val):
        """将时间对象或字符串转换为时间戳

        Args:
            time_val: 时间值，支持 datetime, date, 时间戳, 或时间字符串 'YYYY-MM-DD HH:MM:SS'

        Returns:
            int: 时间戳
        """
        if not time_val:
            return 0
        if isinstance(time_val, (int, float)):
            return int(time_val)
        if isinstance(time_val, datetime):
            return int(time_val.timestamp())
        if isinstance(time_val, date):
            return int(datetime.combine(time_val, datetime.min.time()).timestamp())
        try:
            timestamp = int(time.mktime(time.strptime(str(time_val), '%Y-%m-%d %H:%M:%S')))
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
            
            # 尝试从数据库获取项目类型和项目内容的名称（复用 db_manager，避免重复直连）
            try:
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
                project_type_name = db_manager.get_project_type_name(project_type_id)
                if project_type_id and not project_type_name:
                    project_type_name = str(project_type_id)
                    logger.warning(f"未找到项目类型ID {project_type_id} 对应的记录，使用ID作为名称")
                
                # 查询项目内容名称
                project_content_name = db_manager.get_project_content_name(project_content_id)
                if project_content_id and not project_content_name:
                    project_content_name = str(project_content_id)
                    logger.warning(f"未找到项目内容ID {project_content_id} 对应的记录，使用ID作为名称")
                
            except Exception as db_error:
                logger.error(f"数据库操作异常: {db_error}")
                # 数据库操作失败时，尝试使用备用方案
                project_type_name = api_order_data.get('project_type_name', api_order_data.get('project_type', ''))
                project_content_name = api_order_data.get('project_content_name', api_order_data.get('project_content', ''))
            
            # 如果仍然没有获取到值，尝试从工单表中查询
            if not project_type_name or not project_content_name:
                try:
                    order_info = db_manager.get_work_order_project_names(api_order_data['id'])
                    
                    if order_info:
                        if not project_type_name and order_info.get('project_type'):
                            project_type_name = str(order_info['project_type'])
                            logger.info(f"从工单表获取项目类型: {project_type_name}")
                        if not project_content_name and order_info.get('project_content'):
                            project_content_name = str(order_info['project_content'])
                            logger.info(f"从工单表获取项目内容: {project_content_name}")
                except Exception as e:
                    logger.error(f"从工单表查询项目信息失败: {e}")
            
            logger.info(f"最终使用的项目类型: '{project_type_name}', 项目内容: '{project_content_name}'")
            
            # 构造请求体（时间字段按 TIME_FIELD_MAP 统一映射，避免与更新接口互换）
            payload = {
                "id": str(api_order_data['id']),  # id=工单id
                "f_emd69kip4gk": str(api_order_data['model']),  # 型号=编号
                "f_ifa9xxyrmft": api_order_data.get('name', ''),  # 名称=产品名称
                "f_jxzzjg7egqm": api_order_data.get('requester', ''),  # 负责人=需求人
                "f_utqw1679w43": api_order_data.get('status', ''),
                TIME_FIELD_MAP['start_time']: int(time.time()),  # 开始时间=工单创建时间-时间戳
                "f_ay6dm3j0pfz": project_type_name,  # 项目类型=从数据库获取的名称
                "f_a9q7rpf5paj": project_content_name,  # 项目内容=从数据库获取的名称
                TIME_FIELD_MAP['end_time']: self._convert_time_to_timestamp(api_order_data.get('end_time', '')),
                TIME_FIELD_MAP['photographer_start_time']: self._convert_time_to_timestamp(api_order_data.get('photographer_start_time', '')),
                TIME_FIELD_MAP['photographer_end_time']: self._convert_time_to_timestamp(api_order_data.get('photographer_end_time', '')),
                TIME_FIELD_MAP['art_start_time']: self._convert_time_to_timestamp(api_order_data.get('art_start_time', '')),
                TIME_FIELD_MAP['art_end_time']: self._convert_time_to_timestamp(api_order_data.get('art_end_time', '')),
                TIME_FIELD_MAP['edit_start_time']: self._convert_time_to_timestamp(api_order_data.get('edit_start_time', '')),
                TIME_FIELD_MAP['edit_end_time']: self._convert_time_to_timestamp(api_order_data.get('edit_end_time', ''))
            }

            # 发送请求
            logger.info(f"发送创建工单API请求: {payload}")
            response = _post_api(self._create_url, json=payload)
            if response is None:
                return {"success": False, "error": "API 地址不在允许列表，已拒绝请求"}

            # 处理响应
            if response.status_code == 200:
                logger.info(f"创建工单{order_data['id']}成功，响应内容: {response.text[:500]}")
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
                "error": f"创建工单发生异常: {e!s}"
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
            response = _post_api(self._update_url, params=params, json=payload)
            if response is None:
                return {"success": False, "error": "API 地址不在允许列表，已拒绝请求"}

            # 处理响应
            if response.status_code == 200:
                logger.info(f"更新工单{order_id}的状态成功，响应内容: {response.text[:500]}")
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
                "error": f"更新工单状态发生异常: {e!s}"
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

            # 根据时间字段确定对应的API参数名（与创建接口共用同一份映射）
            if time_field not in TIME_FIELD_MAP:
                logger.error(f"不支持的时间字段: {time_field}")
                return {
                    "success": False,
                    "error": f"不支持的时间字段: {time_field}"
                }

            api_field = TIME_FIELD_MAP[time_field]
            payload = {
                api_field: timestamp
            }

            # 发送请求
            logger.info(f"发送更新工单时间API请求: 工单ID={order_id}, 字段={time_field}, 值={time_value}")
            response = _post_api(self._update_url, params=params, json=payload)
            if response is None:
                return {"success": False, "error": "API 地址不在允许列表，已拒绝请求"}

            # 处理响应
            if response.status_code == 200:
                logger.info(f"更新工单{order_id}的{time_field}成功，响应内容: {response.text[:500]}")
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
                "error": f"更新工单时间发生异常: {e!s}"
            }

# 创建单例实例
api_manager = APIManager()