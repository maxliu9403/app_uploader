"""
Device Service - 设备管理业务逻辑
"""

from core.logger import get_logger

logger = get_logger(__name__)


class DeviceService:
    """设备服务类"""
    
    def __init__(self, adb_helper, setting_manager):
        self.adb_helper = adb_helper
        self.setting_manager = setting_manager
    
    def get_devices(self):
        """获取已连接的设备列表"""
        try:
            devices = self.adb_helper.get_devices()
            logger.info(f"找到 {len(devices)} 个设备")
            return True, devices
        except Exception as e:
            logger.error(f"获取设备列表失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def get_device_configs(self):
        """获取已保存的设备配置"""
        try:
            setting = self.setting_manager.load()
            devices = setting.get('devices') or []
            if devices is None:
                devices = []
            return True, devices
        except Exception as e:
            logger.error(f"获取设备配置失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def save_device_config(self, device_id, remark):
        """保存设备配置"""
        try:
            if not device_id:
                return False, '设备ID不能为空'
            
            setting = self.setting_manager.load()
            devices = setting.get('devices') or []
            if devices is None or not isinstance(devices, list):
                devices = []
            
            # 检查是否已存在
            existing_index = None
            for idx, device in enumerate(devices):
                if device.get('device_id') == device_id:
                    existing_index = idx
                    break
            
            device_config = {'device_id': device_id, 'remark': remark}
            
            if existing_index is not None:
                devices[existing_index] = device_config
            else:
                devices.append(device_config)
            
            setting['devices'] = devices
            self.setting_manager.save(setting)
            
            logger.info(f"设备配置已保存: {device_id}")
            return True, device_config
        except Exception as e:
            logger.error(f"保存设备配置失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def delete_device_config(self, device_id):
        """删除设备配置"""
        try:
            setting = self.setting_manager.load()
            devices = setting.get('devices') or []
            if devices is None:
                devices = []
            
            original_count = len(devices)
            devices = [d for d in devices if d.get('device_id') != device_id]
            
            if len(devices) == original_count:
                return False, f'设备配置不存在: {device_id}'
            
            setting['devices'] = devices
            self.setting_manager.save(setting)
            
            logger.info(f"设备配置 '{device_id}' 删除成功")
            return True, None
        except Exception as e:
            logger.error(f"删除设备配置失败: {str(e)}", exc_info=True)
            return False, str(e)

