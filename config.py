# 配置文件
# 版本号统一管理
APP_VERSION = "v1.15"

# 数据库连接配置
# DB_CONFIG = {
#     'host': '192.168.0.54',
#     'database': 'mcs_by_takuya',
#     'user': 'mcs_by_takuya',
#     'password': 'asd669076',
#     'charset': 'utf8mb4',
#     'autocommit': True
# }

DB_CONFIG = {
    'host': '192.168.0.54',
    'database': 'cs1',
    'user': 'cs1',
    'password': 'HZGYFdNfdBf57L2r',
    'charset': 'utf8mb4',
    'autocommit': True
}

# 通知类型配置
# 可选值：
# - 'dingtalk': 仅使用钉钉通知
# - 'wechat_work': 仅使用企业微信通知
# - 'both': 同时使用钉钉和企业微信通知
NOTIFICATION_TYPE = 'wechat_work' 