"""
路径常量与跨平台路径工具函数。

本模块集中管理所有网络共享路径前缀、文件扩展名集合、
各角色路径模板 lambda，以及 to_local_path() 跨平台转换函数。
从 main_window.py 顶部迁移而来，请勿在 main_window.py 中重复定义。
"""
import os
import platform
import re

# ---------------------------------------------------------------------------
# 平台路径根前缀
# ---------------------------------------------------------------------------
if platform.system() == 'Windows':
    RAW_ROOT = r'\\dabadoc\01原始素材'
    ART_ROOT = r'\\dabadoc\02图像部\01美工部'
    VIDEO_ROOT = r'\\dabadoc\02图像部\02视频部'
    CENTER_ROOT = r'\\dabadoc\03素材中心'
    VOLUMES = r'\\dabadoc'
else:
    RAW_ROOT = '/Volumes/01原始素材'
    ART_ROOT = '/Volumes/02图像部/01美工部'
    VIDEO_ROOT = '/Volumes/02图像部/02视频部'
    CENTER_ROOT = '/Volumes/03素材中心'
    VOLUMES = '/Volumes'

# ---------------------------------------------------------------------------
# 文件扩展名集合
# ---------------------------------------------------------------------------
# 图片扩展名，包含常见 RAW 格式
IMG_EXTS = {
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff', '.webp', '.heic',
    '.raw', '.arw', '.cr2', '.nef', '.raf', '.dng', '.sr2', '.orf',
    '.rw2', '.pef', '.srw', '.cr3',
}
# 视频扩展名
VID_EXTS = {
    '.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv', '.webm',
    '.m4v', '.3gp', '.mpeg', '.mpg', '.ts',
}

# 摄影师列表（新增摄影师时只需在此处追加，删除/迁移工单路径会自动覆盖）
PHOTOGRAPHERS = ["01阿乐", "02杨钧", "03Peter", "04玉瑞", "05Jessie", "06Candy", "07项项", "08Arin"]

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

# 美工后期审批中转目录：美工分发成品先复制到此，审批通过后再到运营/销售目录
# 目录下分「01运营」「02销售」两个子目录，对应美工分发运营/销售
ART_POST_REVIEW_TRANSIT = lambda dept, id_, model, name: \
    os.path.join(VOLUMES, '02图像部', '01美工部', dept, '01待审批', f"{id_} {model} {name}")

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
    is_win_root = norm_path.startswith(('//dabadoc', '//DABADOC'))

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


def get_order_all_paths(dept: str, id_: str | int, model: str, name: str) -> list[str]:
    """
    获取指定工单在全系统所有可能存在的网络盘路径列表（自动规整为当前操作系统本地路径格式，并严格有序去重）。
    
    涵盖节点（共 13 个模板）：
    1. 摄影师上传目录（8 位摄影师）
    2. 美工待领取图片 (01原始素材/02美工待领取/.../01图片)
    3. 剪辑待领取视频 (01原始素材/02美工待领取/.../02视频)
    4. 美工待处理目录 (02图像部/01美工部/.../00待处理)
    5. 美工待审批中转目录 (02图像部/01美工部/.../01待审批)
    6. 美工/运营分发素材中心 (03素材中心/01运营部)
    7. 美工/销售分发素材中心 (03素材中心/02销售部)
    8. 视频待处理目录 (02图像部/02视频部/.../00待处理)
    9. 视频待审核中转目录 (02图像部/02视频部/.../01待审核)
    10. 视频分发运营素材中心 (03素材中心/01运营部/.../02视频)
    11. 视频分发销售素材中心 (03素材中心/02销售部/.../02视频)
    """
    paths = []
    
    # 1. 摄影师上传目录（8位摄影师）
    for photographer in PHOTOGRAPHERS:
        p = to_local_path(PHOTOGRAPHY_UPLOAD(photographer, dept, id_, model, name))
        if p and p not in paths:
            paths.append(p)
            
    # 2. 各业务流转与中转目录模板
    flow_templates = [
        PHOTOGRAPHY_DIST_IMG,
        PHOTOGRAPHY_DIST_VIDEO,
        ART_GET_IMG_DEST,
        ART_POST_REVIEW_TRANSIT,
        ART_DIST_OPS,
        ART_DIST_SALES,
        EDIT_GET_VIDEO_DEST,
        EDIT_POST_REVIEW_TRANSIT,
        EDIT_DIST_OPS,
        EDIT_DIST_SALES,
    ]
    for tpl in flow_templates:
        p = to_local_path(tpl(dept, id_, model, name))
        if p and p not in paths:
            paths.append(p)
            
    return paths


def get_order_path_migration_pairs(old_dept: str, old_model: str, old_name: str,
                                    new_dept: str, new_model: str, new_name: str,
                                    id_: str | int) -> list[tuple[str, str]]:
    """
    生成工单信息（产线/型号/名称）变更时所有关联路径的 (old_path, new_path) 迁移映射对。
    自动按顺序对应、过滤无变动路径并严格去重。
    """
    old_paths = get_order_all_paths(old_dept, id_, old_model, old_name)
    new_paths = get_order_all_paths(new_dept, id_, new_model, new_name)
    
    pairs = []
    for old_p, new_p in zip(old_paths, new_paths):
        if old_p and new_p and old_p != new_p and (old_p, new_p) not in pairs:
            pairs.append((old_p, new_p))
    return pairs

