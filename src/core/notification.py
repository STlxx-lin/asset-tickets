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
import logging
import time
import hmac
import hashlib
import base64
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
DINGTALK_BOTS = {
    # 默认机器人（当产线未配置时使用）
    "default": {
        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=f8f3fca934e63b2771b3b5ac90362f9d40890d4b3026d776fcf7c0921752384e",
        "secret": "SEC34b86bcc26edaf4a578463bd196d05e45563891439a65392e4d506d1aa77472b"
    },
    # 01标签机械
    "01标签机械": {
        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=f78301316a57069ed3aea13dc11575dc62d7272bb2b14b55c8313837ea1f3e1d",
        "secret": "SEC7fb47f63b4063809a11b22afc79d350b025ccf2e2031f6d77aad043a97baa13e"
    },
    # 02标签材料
    "02标签材料": {
        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=b09ed28b9bfb908dcc060fcab64e4ea6b39f947440d7dd919f47e2f4adb70be0",
        "secret": "SEC993358f80b4018dc694d8e7948cbbb9b83d8259fcb8ace5e978a2cb71cc17bc0"
    },
    # 03软包机械
    "03软包机械": {
        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=6d2304f20f3b6f8a456e375aad0eaf522f26f5124f9283eacca0610c9004e8b2",
        "secret": "SEC84683c43e5f3c4a7c27d3918d4736e91eb7abd3345a0d000c412f5bd505eef5e"
    },
    # 04塑料机械
    "04塑料机械": {
        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=48644a18544f840e921707ac4b2897d1433bd69dff0020f3cfa1277fa61e3b09",
        "secret": "SEC000c57c9f13c270b61ac23f3b6a80820479ece19f0e3619478057482926f3805"
    },
    # 05纸容器机械
    "05纸容器机械": {
        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=3fbcda6baf9c32ef1853449cb2efbffee9cd25f780d43937343850224a23cf26",
        "secret": "SEC0702be6f875f311a7297f96690d28801fce6f32ec432dda52deb0dea12315de5"
    },
    # 06硬包机械
    "06硬包机械": {
        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=4673857c444041ec8bbe3d6b5bf3a31bf19202b2442df02d4d7e8258d31f0a9f",
        "secret": "SEC332ff1e73f6498100ae7ff13eb0e323771d4b6a4b90d678a94eb77400c2285c4"
    },
    # 07农用机械
    "07农用机械": {
        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=aa09ba0e539e8804fb40b9e7abdb559ad04e7f02307fd810616b7dd3d2e9cf5f",
        "secret": "SECebf2eb43238a0b88514670df81660ac52f9cec651a2e764140471546421b484a"
    },
    # 08包装机械
    "08包装机械": {
        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=3377632c97e05c29a9b063f7d1b7420c91891aa6af1c5cc4d709cefc3cb5a5e8",
        "secret": "SEC2c7e9a5bb6e0fa6fc6d1063832bc4fd3a0daad920fa6363de009463f15dde7bc"
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
        "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=791b78c2-63e2-4795-88d9-62eae5a9dfbe"
    },
    # 02标签材料
    "02标签材料": {
        "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=c675c3cd-125a-4cc2-bcb4-d24fd6ca06cc"
    },
    # 03软包机械
    "03软包机械": {
        "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=e9601e62-bcf1-4215-8a9e-034bde2d3709"
    },
    # 04塑料机械
    "04塑料机械": {
        "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=41134839-49b8-48a0-bc97-95da269c8bd4"
    },
    # 05纸容器机械
    "05纸容器机械": {
        "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=41134839-49b8-48a0-bc97-95da269c8bd4"
    },
    # 06硬包机械
    "06硬包机械": {
        "webhook": ""
    },
    # 07农用机械
    "07农用机械": {
        "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=f26afc32-1298-4335-9014-17d9d0cfbbe7"
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
        print(f"钉钉推送已跳过 - 产线: {department or 'default'}, 原因: 未配置Webhook")
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
        print(f"钉钉推送成功 - 产线: {department or 'default'}")
    except Exception as e:
        print(f"钉钉推送失败 - 产线: {department or 'default'}, 错误: {e}")


def send_wechat_work_markdown(title: str, text: str, department: str = None) -> None:
    """发送企业微信 Markdown 消息，支持按产线选择不同的机器人。"""
    if department and department in WECHAT_WORK_BOTS:
        bot_config = WECHAT_WORK_BOTS[department]
    else:
        bot_config = WECHAT_WORK_BOTS["default"]

    webhook = bot_config.get("webhook", "")
    if not webhook:
        print(f"企业微信推送已跳过 - 产线: {department or 'default'}, 原因: 未配置Webhook")
        return

    data = {
        "msgtype": "markdown",
        "markdown": {"content": f"{title}\n\n{text}"}
    }
    try:
        requests.post(webhook, json=data, headers={"Content-Type": "application/json"}, timeout=3)
        print(f"企业微信推送成功 - 产线: {department or 'default'}")
    except Exception as e:
        print(f"企业微信推送失败 - 产线: {department or 'default'}, 错误: {e}")


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
