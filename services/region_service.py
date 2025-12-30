"""
Region Service - 地区管理业务逻辑
"""

from core.logger import get_logger

logger = get_logger(__name__)


class RegionService:
    """地区服务类"""
    
    def __init__(self, setting_manager):
        self.setting_manager = setting_manager
    
    def get_all_regions(self):
        """获取所有地区"""
        try:
            setting = self.setting_manager.load()
            regions = setting.get('regions') or []
            if regions is None:
                regions = []
            if not regions:
                regions = [
                    {'code': 'GB', 'name': '英国'},
                    {'code': 'SG', 'name': '新加坡'},
                    {'code': 'HK', 'name': '香港'},
                    {'code': 'MY', 'name': '马来西亚'},
                    {'code': 'PH', 'name': '菲律宾'}
                ]
            logger.info(f"成功返回 {len(regions)} 个地区")
            return True, regions
        except Exception as e:
            logger.error(f"获取地区列表失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def add_region(self, code, name):
        """添加地区"""
        try:
            code = code.strip().upper()
            name = name.strip()
            
            if not code or not name:
                return False, '地区代码和名称不能为空'
            
            setting = self.setting_manager.load()
            regions = setting.get('regions') or []
            if regions is None:
                regions = []
            
            # 检查是否已存在
            for region in regions:
                if region.get('code') == code:
                    return False, f'地区代码 "{code}" 已存在'
            
            new_region = {'code': code, 'name': name}
            regions.append(new_region)
            setting['regions'] = regions
            self.setting_manager.save(setting)
            
            logger.info(f"地区 '{code}' ({name}) 添加成功")
            return True, new_region
        except Exception as e:
            logger.error(f"添加地区失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def delete_region(self, code):
        """删除地区"""
        try:
            code = code.upper()
            setting = self.setting_manager.load()
            regions = setting.get('regions') or []
            if regions is None:
                regions = []
            
            original_count = len(regions)
            regions = [r for r in regions if r.get('code') != code]
            
            if len(regions) == original_count:
                return False, f'地区代码 "{code}" 不存在'
            
            setting['regions'] = regions
            self.setting_manager.save(setting)
            
            logger.info(f"地区 '{code}' 删除成功")
            return True, None
        except Exception as e:
            logger.error(f"删除地区失败: {str(e)}", exc_info=True)
            return False, str(e)

