"""
路径常量与跨平台路径工具函数。

本模块集中管理所有网络共享路径前缀、文件扩展名集合、
各角色路径模板 lambda，以及 to_local_path() 跨平台转换函数。
从 main_window.py 顶部迁移而来，请勿在 main_window.py 中重复定义。
"""
import os
import re
import platform

# ---------------------------------------------------------------------------
# 平台路径根前缀
# ---------------------------------------------------------------------------
if platform.system() == 'Windows':
    RAW_ROOT = r'\\dabadoc\01原始素材'
    ART_ROOT = r'\\dabadoc\02图像部\01美工部'
    VIDEO_ROOT = r'\\dabadoc\02图像部\01视频部'
    CENTER_ROOT = r'\\dabadoc\03素材中心'
    VOLUMES = r'\\dabadoc'
else:
    RAW_ROOT = '/Volumes/01原始素材'
    ART_ROOT = '/Volumes/02图像部/01美工部'
    VIDEO_ROOT = '/Volumes/02图像部/01视频部'
    CENTER_ROOT = '/Volumes/03素材中心'
    VOLUMES = '/Volumes'

# ---------------------------------------------------------------------------
# 文件扩展名集合
# ---------------------------------------------------------------------------
# 图片扩展名，包含常见 RAW 格式
IMG_EXTS = {
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.heic',
    '.raw', '.arw', '.cr2', '.nef', '.raf', '.dng', '.sr2', '.orf',
    '.rw2', '.pef', '.srw', '.cr3',
}
# 视频扩展名
VID_EXTS = {
    '.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv', '.webm',
    '.m4v', '.3gp', '.mpeg', '.mpg',
}

# ---------------------------------------------------------------------------
# 路径模板 lambda（共 13 个）
# ---------------------------------------------------------------------------
PHOTOGRAPHY_UPLOAD = lambda photographer, dept, id_, model, name: \
    os.path.join(VOLUMES, '01原始素材', '01原始素材', photographer, dept, f"{id_} {model} {name}")

PHOTOGRAPHY_DIST_IMG = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '01原始素材', '02美工待领取', dept, '01图片', f"{id_} {model} {name}")

PHOTOGRAPHY_DIST_VIDEO = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '01原始素材', '02美工待领取', dept, '02视频', f"{id_} {model} {name}")

ART_GET_IMG_SRC = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '01原始素材', '02美工待领取', dept, '01图片', f"{id_} {model} {name}")

ART_GET_IMG_DEST = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '02图像部', '01美工部', dept, '00待处理', f"{id_} {model} {name}")

ART_DIST_OPS = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '03素材中心', '01运营部', dept, f"{id_} {model} {name}")

ART_DIST_SALES = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '03素材中心', '02销售部', dept, f"{id_} {model} {name}")

EDIT_GET_VIDEO_SRC = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '01原始素材', '02美工待领取', dept, '02视频', f"{id_} {model} {name}")

EDIT_GET_VIDEO_DEST = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '02图像部', '02视频部', dept, '00待处理', f"{id_} {model} {name}")

EDIT_DIST_OPS = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '03素材中心', '01运营部', dept, f"{id_} {model} {name}", '02视频')

EDIT_DIST_SALES = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '03素材中心', '02销售部', dept, f"{id_} {model} {name}", '02视频')

EDIT_POST_REVIEW_TRANSIT = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '02图像部', '02视频部', dept, '01待审核', f"{id_} {model} {name}")

OPS_GET_SRC = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '03素材中心', '01运营部', dept, f"{id_} {model} {name}")

SALES_GET_SRC = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '03素材中心', '02销售部', dept, f"{id_} {model} {name}")


# ---------------------------------------------------------------------------
# 跨平台路径转换工具
# ---------------------------------------------------------------------------
def to_local_path(path_str: str) -> str:
    """跨平台路径格式翻译（适配 Windows 的 \\\\dabadoc 和 macOS 的 /Volumes）"""
    if not path_str:
        return ""

    # 规整化斜杠，便于统一替换
    norm_path = path_str.replace('\\', '/')

    # 检测是 Mac 格式前缀还是 Win 格式前缀
    is_mac_root = norm_path.startswith('/Volumes')
    is_win_root = norm_path.startswith('//dabadoc') or norm_path.startswith('//DABADOC')

    if platform.system() == 'Windows':
        if is_mac_root:
            # Mac 路径转 Win：/Volumes -> \\dabadoc
            local_path = norm_path.replace('/Volumes', r'\\dabadoc', 1)
        else:
            local_path = norm_path
        return os.path.normpath(local_path)
    else:
        # macOS 平台
        if is_win_root:
            # Win 路径转 Mac：//dabadoc -> /Volumes
            local_path = re.sub(r'^//[dD][aA][bB][aA][dD][oO][cC]', '/Volumes', norm_path)
        else:
            local_path = norm_path
        # macOS 必须是正斜杠
        return os.path.normpath(local_path).replace('\\', '/')
