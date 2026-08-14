# 配置文件
# 版本号统一管理
APP_VERSION = "v1.18.03"

# ---------------------------------------------------------------------------
# 敏感配置统一从环境变量 / .env 文件读取（不提交到代码库）
# 优先级：系统环境变量 > 项目根目录 .env 文件 > 下方默认值
# 可用键：
#   DB1_PASSWORD / DB2_PASSWORD / ADMIN_PASSWORD / API_TOKEN
# 打包部署时请在程序旁放置 .env 文件（参考 .env.example）
# ---------------------------------------------------------------------------
import logging
import os

_logger = logging.getLogger(__name__)


def _load_env_file():
    """按优先级从多个位置加载 .env 文件（KEY=VALUE 每行，# 为注释），不覆盖已有环境变量。

    候选位置：
    1. 打包后程序所在目录（exe / .app 同目录，构建产物自带 .env 时生效）
    2. PyInstaller onefile 解压目录（sys._MEIPASS，datas 打包的 .env 解压至此）
    3. 项目根目录（源码运行时，src/core/config.py 上溯三级；Nuitka onefile 解压根）
    4. 当前工作目录
    """
    import sys
    candidates = []
    try:
        if getattr(sys, 'frozen', False):
            candidates.append(os.path.dirname(sys.executable))
    except Exception:
        pass
    # PyInstaller onefile：数据文件解压到 _MEIPASS 临时目录
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.append(meipass)
    # Nuitka onefile：数据文件解压在模块上溯三级处（src/core/config.py → 解压根）
    candidates.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    candidates.append(os.getcwd())

    loaded = None
    for base in candidates:
        env_path = os.path.join(base, '.env')
        if os.path.exists(env_path):
            loaded = env_path
            break
    if not loaded:
        return
    try:
        with open(loaded, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        _logger.warning(f"加载 .env 文件失败: {e}")


_load_env_file()


def _env(key: str, default: str = '') -> str:
    """读取环境变量；未配置时警告并返回默认值。"""
    value = os.environ.get(key, '').strip()
    if not value:
        _logger.warning(f"环境变量 {key} 未配置，相关功能可能无法正常使用")
        return default
    return value


# 数据库切换开关
# 可选值：
# - 'db1': 使用第一个数据库配置（mcs_by_takuya）
# - 'db2': 使用第二个数据库配置（cs1）
DB_SWITCH = 'db1'

# 数据库配置1 - mcs_by_takuya
DB_CONFIG_1 = {
    'host': '192.168.0.54',
    'database': 'mcs_by_takuya',
    'user': 'mcs_by_takuya',
    'password': _env('DB1_PASSWORD'),
    'charset': 'utf8mb4',
    'autocommit': True
}

# 数据库配置2 - cs1
DB_CONFIG_2 = {
    'host': '192.168.0.54',
    'database': 'cs1',
    'user': 'cs1',
    'password': _env('DB2_PASSWORD'),
    'charset': 'utf8mb4',
    'autocommit': True
}

# 根据开关选择当前使用的数据库配置
if DB_SWITCH == 'db1':
    DB_CONFIG = DB_CONFIG_1
elif DB_SWITCH == 'db2':
    DB_CONFIG = DB_CONFIG_2
else:
    # 默认使用第一个数据库配置
    DB_CONFIG = DB_CONFIG_1

# 通知类型配置（已迁移到数据库按产线管理，参见 app_notification_line_settings 表）
# 迁移说明文档：docs/NOTIFICATION_MIGRATION.md
# 可选值：
# - 'dingtalk': 仅使用钉钉通知
# - 'wechat_work': 仅使用企业微信通知
# - 'both': 同时使用钉钉和企业微信通知
# NOTIFICATION_TYPE = 'wechat_work'

# 全局回退通知类型（用于数据库无值时统一兜底）
DEFAULT_NOTIFICATION_TYPE = 'wechat_work'

# 管理员登录密码配置（从环境变量 ADMIN_PASSWORD 读取）
# 安全说明：未配置时保持为空字符串，登录校验处会拒绝空密码，避免空密码绕过管理员认证。
ADMIN_PASSWORD = _env('ADMIN_PASSWORD')
if not ADMIN_PASSWORD:
    _logger.error(
        "环境变量 ADMIN_PASSWORD 未配置，管理员登录功能将被禁用（拒绝所有管理员登录）。"
        "请在生产环境 .env 中配置强密码。"
    )

# 测试开关：是否跳过视频后期审核的状态校验（默认为True方便调试测试）
# BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK = True #跳过
BYPASS_VIDEO_POST_REVIEW_STATUS_CHECK = False #不跳过

# ---------------------------------------------------------------------------
# 功能开关读取（带内存缓存，避免每次打开对话框都查询数据库）
# 设置页保存后调用 clear_feature_cache() 使其失效
# ---------------------------------------------------------------------------
_FEATURE_CACHE: dict = {}


def get_feature_enabled(key: str, default: str = '1') -> bool:
    """读取 app_system_settings 中的功能开关（'1' 为开启）。"""
    if key not in _FEATURE_CACHE:
        from src.core.database import db_manager
        _FEATURE_CACHE[key] = db_manager.get_system_setting(key, default=default)
    return _FEATURE_CACHE.get(key, default) == '1'


def clear_feature_cache() -> None:
    """清空功能开关缓存（设置保存后调用，使修改即时生效）。"""
    _FEATURE_CACHE.clear()
