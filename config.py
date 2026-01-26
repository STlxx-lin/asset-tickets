# 配置文件
# 版本号统一管理
APP_VERSION = "v1.15.5"

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
    'password': 'asd669076',
    'charset': 'utf8mb4',
    'autocommit': True
}

# 数据库配置2 - cs1
DB_CONFIG_2 = {
    'host': '192.168.0.54',
    'database': 'cs1',
    'user': 'cs1',
    'password': 'HZGYFdNfdBf57L2r',
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

# 通知类型配置
# 可选值：
# - 'dingtalk': 仅使用钉钉通知
# - 'wechat_work': 仅使用企业微信通知
# - 'both': 同时使用钉钉和企业微信通知
NOTIFICATION_TYPE = 'wechat_work'

# 管理员登录密码配置
ADMIN_PASSWORD = 'DBJX.8888' 