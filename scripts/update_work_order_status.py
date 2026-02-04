import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from src.core.api_manager import api_manager
import logging
import requests

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('工单状态更新脚本')

"""
工单状态更新脚本

此脚本用于更新工单状态，并同步更新相关时间字段
使用方法:
python update_work_order_status.py <工单ID> <状态> <文件分发时间> <美工素材领取时间> <美工选择成品目录时间> <剪辑素材领取时间> <剪辑选择成品目录时间>
时间格式: YYYY-MM-DD HH:MM:SS，若不更新某时间字段可传入空字符串
"""

def update_work_order_status_and_times(order_id, status, file_distribution_time, art_material_receive_time, 
                                     art_finish_time, edit_material_receive_time, edit_finish_time):
    """更新工单状态和相关时间字段

    Args:
        order_id: 工单ID
        status: 工单状态
        file_distribution_time: 文件分发时间(摄影师结束时间)
        art_material_receive_time: 美工素材领取时间(美工开始时间)
        art_finish_time: 美工选择成品目录时间(美工结束时间)
        edit_material_receive_time: 剪辑素材领取时间(剪辑开始时间)
        edit_finish_time: 剪辑选择成品目录时间(剪辑结束时间)
    """
    try:
        # 更新工单状态
        if status:
            # 构造更新状态的请求
            params = {
                "filterByTk": str(order_id)
            }
            payload = {
                "f_utqw1679w43": status
            }
            
            # 发送请求更新状态
            logger.info(f"更新工单{order_id}状态为: {status}")
            response = requests.post(api_manager._update_url, params=params, json=payload, 
                                     headers=api_manager._headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"更新工单{order_id}状态失败: {response.status_code}, {response.text}")
                return False
            else:
                logger.info(f"成功更新工单{order_id}状态为: {status}")

        # 更新摄影师结束时间(文件分发时间)
        if file_distribution_time:
            result = api_manager.update_work_order_time(order_id, 'photographer_end_time', file_distribution_time)
            if not result['success']:
                logger.error(f"更新工单{order_id}的摄影师结束时间失败: {result['error']}")
                return False
            else:
                logger.info(f"成功更新工单{order_id}的摄影师结束时间为: {file_distribution_time}")

        # 更新美工开始时间(美工素材领取时间)
        if art_material_receive_time:
            result = api_manager.update_work_order_time(order_id, 'art_start_time', art_material_receive_time)
            if not result['success']:
                logger.error(f"更新工单{order_id}的美工开始时间失败: {result['error']}")
                return False
            else:
                logger.info(f"成功更新工单{order_id}的美工开始时间为: {art_material_receive_time}")

        # 更新美工结束时间(美工选择成品目录时间)
        if art_finish_time:
            result = api_manager.update_work_order_time(order_id, 'art_end_time', art_finish_time)
            if not result['success']:
                logger.error(f"更新工单{order_id}的美工结束时间失败: {result['error']}")
                return False
            else:
                logger.info(f"成功更新工单{order_id}的美工结束时间为: {art_finish_time}")

        # 更新剪辑开始时间(剪辑素材领取时间)
        if edit_material_receive_time:
            result = api_manager.update_work_order_time(order_id, 'edit_start_time', edit_material_receive_time)
            if not result['success']:
                logger.error(f"更新工单{order_id}的剪辑开始时间失败: {result['error']}")
                return False
            else:
                logger.info(f"成功更新工单{order_id}的剪辑开始时间为: {edit_material_receive_time}")

        # 更新剪辑结束时间(剪辑选择成品目录时间)
        if edit_finish_time:
            result = api_manager.update_work_order_time(order_id, 'edit_end_time', edit_finish_time)
            if not result['success']:
                logger.error(f"更新工单{order_id}的剪辑结束时间失败: {result['error']}")
                return False
            else:
                logger.info(f"成功更新工单{order_id}的剪辑结束时间为: {edit_finish_time}")

        return True
    except Exception as e:
        logger.error(f"更新工单{order_id}信息发生异常: {str(e)}")
        return False

def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("python update_work_order_status.py <工单ID> [状态] [文件分发时间] [美工素材领取时间] [美工选择成品目录时间] [剪辑素材领取时间] [剪辑选择成品目录时间]")
        print("时间格式: YYYY-MM-DD HH:MM:SS，若不更新某字段可传入空字符串")
        return

    order_id = sys.argv[1]
    status = sys.argv[2] if len(sys.argv) > 2 else ''
    file_distribution_time = sys.argv[3] if len(sys.argv) > 3 else ''
    art_material_receive_time = sys.argv[4] if len(sys.argv) > 4 else ''
    art_finish_time = sys.argv[5] if len(sys.argv) > 5 else ''
    edit_material_receive_time = sys.argv[6] if len(sys.argv) > 6 else ''
    edit_finish_time = sys.argv[7] if len(sys.argv) > 7 else ''

    logger.info(f"开始更新工单{order_id}信息...")
    result = update_work_order_status_and_times(
        order_id, status, file_distribution_time, art_material_receive_time, 
        art_finish_time, edit_material_receive_time, edit_finish_time
    )

    if result:
        logger.info(f"工单{order_id}信息更新成功")
        print(f"工单{order_id}信息更新成功")
    else:
        logger.error(f"工单{order_id}信息更新失败")
        print(f"工单{order_id}信息更新失败")

if __name__ == "__main__":
    main()