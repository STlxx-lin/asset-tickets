"""
notification.py — 消息推送模块。

集中管理钉钉、企业微信的机器人配置、通知类型路由，
以及从数据库加载/保存通知配置的所有逻辑。
从 main_window.py 顶部迁移而来，不改变任何业务逻辑。

对外公开接口：
    send_notification(title, text, department=None)
    load_notification_settings()           → 从 DB 加载并应用
    apply_notification_settings(settings_map)
    save_notification_settings(line_name, settings) → 保存单条并返回 bool
    get_department_line_names()            → 从 DB 取产线列表
    LINE_NOTIFICATION_SETTINGS             → 运行时缓存（dict）
    NOTIFICATION_TYPE                      → 当前全局通知类型（str）
"""
import base64
import hashlib
import hmac
import logging
import time
import urllib.parse

import requests

from src.core.config import DEFAULT_NOTIFICATION_TYPE
from src.core.database import db_manager

logger = logging.getLogger(__name__)

# ── 全局通知类型（default 行的值，供无产线场景回退） ──────────────────────
NOTIFICATION_TYPE = DEFAULT_NOTIFICATION_TYPE

# ── 全局产线通知配置缓存（按产线名存储） ─────────────────────────────────
LINE_NOTIFICATION_SETTINGS: dict = {}

# ── 钉钉机器人配置 - 按产线分拆 ──────────────────────────────────────────
# 安全说明：webhook/secret 仅存于数据库（app_notification_line_settings 表），
# 模块加载时由 load_notification_settings() 从数据库读取并覆盖本常量。
# 此处仅保留空默认值，避免密钥提交进代码仓库。
DINGTALK_BOTS = {
    # 默认机器人（当产线未配置时使用）
    "default": {
        "webhook": "",
        "secret": ""
    },
    # 01标签机械
    "01标签机械": {
        "webhook": "",
        "secret": ""
    },
    # 02标签材料
    "02标签材料": {
        "webhook": "",
        "secret": ""
    },
    # 03软包机械
    "03软包机械": {
        "webhook": "",
        "secret": ""
    },
    # 04塑料机械
    "04塑料机械": {
        "webhook": "",
        "secret": ""
    },
    # 05纸容器机械
    "05纸容器机械": {
        "webhook": "",
        "secret": ""
    },
    # 06硬包机械
    "06硬包机械": {
        "webhook": "",
        "secret": ""
    },
    # 07农用机械
    "07农用机械": {
        "webhook": "",
        "secret": ""
    },
    # 08包装机械
    "08包装机械": {
        "webhook": "",
        "secret": ""
    },
}

# ── 企业微信机器人配置 - 按产线分拆 ──────────────────────────────────────
WECHAT_WORK_BOTS = {
    # 默认机器人（当产线未配置时使用）
    "default": {
        "webhook": ""
    },
    # 01标签机械
    "01标签机械": {
        "webhook": ""
    },
    # 02标签材料
    "02标签材料": {
        "webhook": ""
    },
    # 03软包机械
    "03软包机械": {
        "webhook": ""
    },
    # 04塑料机械
    "04塑料机械": {
        "webhook": ""
    },
    # 05纸容器机械
    "05纸容器机械": {
        "webhook": ""
    },
    # 06硬包机械
    "06硬包机械": {
        "webhook": ""
    },
    # 07农用机械
    "07农用机械": {
        "webhook": ""
    },
    # 08包装机械
    "08包装机械": {
        "webhook": ""
    },
}


# ── 内部工具函数 ──────────────────────────────────────────────────────────

def get_department_line_names() -> list:
    """从部门表获取产线列表。"""
    try:
        departments = db_manager.get_departments()
        return [name.strip() for name in departments if isinstance(name, str) and name.strip()]
    except Exception as error:
        logger.warning(f"读取部门列表失败: {error}")
        return []


def _build_seed_notification_settings() -> dict:
    """基于当前代码中的通知常量构建初始入库数据。"""
    line_names = set(get_department_line_names())
    if not line_names:
        line_names = set(DINGTALK_BOTS.keys()) | set(WECHAT_WORK_BOTS.keys())
    line_names.add("default")
    seed_data = {}
    for line_name in line_names:
        dingtalk_source = DINGTALK_BOTS.get(line_name, DINGTALK_BOTS.get("default", {}))
        wechat_source = WECHAT_WORK_BOTS.get(line_name, WECHAT_WORK_BOTS.get("default", {}))
        seed_data[line_name] = {
            "notification_type": NOTIFICATION_TYPE,
            "dingtalk_webhook": dingtalk_source.get("webhook", ""),
            "dingtalk_secret": dingtalk_source.get("secret", ""),
            "wechat_work_webhook": wechat_source.get("webhook", "")
        }
    return seed_data


def load_notification_settings() -> dict:
    """从数据库加载所有产线通知配置，必要时自动写入初始数据。"""
    try:
        db_manager.seed_notification_settings_if_empty(_build_seed_notification_settings())
        loaded_settings = db_manager.get_all_notification_settings()
        return loaded_settings or _build_seed_notification_settings()
    except Exception as error:
        logger.warning(f"从数据库读取通知配置失败，已使用代码内默认配置: {error}")
        return _build_seed_notification_settings()


def apply_notification_settings(settings_map: dict) -> None:
    """将所有产线通知配置应用到运行时变量，使配置修改后即时生效。"""
    global NOTIFICATION_TYPE
    global LINE_NOTIFICATION_SETTINGS

    LINE_NOTIFICATION_SETTINGS = settings_map

    for line_name, settings in settings_map.items():
        dingtalk_config = DINGTALK_BOTS.setdefault(line_name, {})
        dingtalk_config["webhook"] = settings.get("dingtalk_webhook", "").strip()
        dingtalk_config["secret"] = settings.get("dingtalk_secret", "").strip()
        wechat_config = WECHAT_WORK_BOTS.setdefault(line_name, {})
        wechat_config["webhook"] = settings.get("wechat_work_webhook", "").strip()

    default_settings = settings_map.get("default", {})
    NOTIFICATION_TYPE = default_settings.get("notification_type", NOTIFICATION_TYPE)


def save_notification_settings(line_name: str, settings: dict) -> bool:
    """将单个产线通知配置保存到数据库。"""
    return db_manager.upsert_notification_setting(line_name, settings)


# ── 发送函数 ──────────────────────────────────────────────────────────────

def send_dingtalk_markdown(title: str, text: str, department: str = None) -> None:
    """发送钉钉 Markdown 消息，支持按产线选择不同的机器人。"""
    if department and department in DINGTALK_BOTS:
        bot_config = DINGTALK_BOTS[department]
    else:
        bot_config = DINGTALK_BOTS["default"]

    webhook = bot_config.get("webhook", "")
    secret = bot_config.get("secret", "")
    if not webhook:
        logger.info(f"钉钉推送已跳过 - 产线: {department or 'default'}, 原因: 未配置Webhook")
        return

    webhook_url = webhook
    if secret:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        webhook_url = f"{webhook}&timestamp={timestamp}&sign={sign}"

    data = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": text}
    }
    try:
        requests.post(webhook_url, json=data, headers={"Content-Type": "application/json"}, timeout=3)
        logger.info(f"钉钉推送成功 - 产线: {department or 'default'}")
    except Exception as e:
        logger.error(f"钉钉推送失败 - 产线: {department or 'default'}, 错误: {e}")


def send_wechat_work_markdown(title: str, text: str, department: str = None) -> None:
    """发送企业微信 Markdown 消息，支持按产线选择不同的机器人。"""
    if department and department in WECHAT_WORK_BOTS:
        bot_config = WECHAT_WORK_BOTS[department]
    else:
        bot_config = WECHAT_WORK_BOTS["default"]

    webhook = bot_config.get("webhook", "")
    if not webhook:
        logger.info(f"企业微信推送已跳过 - 产线: {department or 'default'}, 原因: 未配置Webhook")
        return

    data = {
        "msgtype": "markdown",
        "markdown": {"content": f"{title}\n\n{text}"}
    }
    try:
        requests.post(webhook, json=data, headers={"Content-Type": "application/json"}, timeout=3)
        logger.info(f"企业微信推送成功 - 产线: {department or 'default'}")
    except Exception as e:
        logger.error(f"企业微信推送失败 - 产线: {department or 'default'}, 错误: {e}")


def send_notification(title: str, text: str, department: str = None) -> None:
    """统一通知发送入口，根据产线配置路由到钉钉/企业微信/两者。"""
    effective_settings = LINE_NOTIFICATION_SETTINGS.get(
        department, LINE_NOTIFICATION_SETTINGS.get("default", {})
    )
    effective_type = effective_settings.get("notification_type", NOTIFICATION_TYPE)

    if effective_type in ('dingtalk', 'both'):
        send_dingtalk_markdown(title, text, department)
    if effective_type in ('wechat_work', 'both'):
        send_wechat_work_markdown(title, text, department)


# ── 模块加载时立即初始化（保持与原 main_window.py 相同行为） ─────────────
apply_notification_settings(load_notification_settings())
