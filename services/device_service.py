"""
Device Service - 设备管理业务逻辑
"""

import os
import shutil
from core.logger import get_logger

logger = get_logger(__name__)


class DeviceService:
    """设备服务类"""
    
    BASE_CONFIG_DIR = 'network_config'
    CONFIG_TEMPLATE = 'config_temp.yaml'
    
    def __init__(self, adb_helper, setting_manager):
        self.adb_helper = adb_helper
        self.setting_manager = setting_manager
    
    def get_devices(self):
        """获取已连接的设备列表，并自动创建设备配置文件夹"""
        try:
            devices = self.adb_helper.get_devices()
            logger.info(f"找到 {len(devices)} 个设备")
            
            # 为每个设备自动创建配置文件夹
            for device in devices:
                device_id = device.get('device_id') or device.get('id')
                if device_id:
                    self._ensure_device_config_dir(device_id)
            
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
            
            # 确保设备配置目录存在
            self._ensure_device_config_dir(device_id)
            
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

    def get_current_device_id(self):
        try:
            setting = self.setting_manager.load()
            return True, (setting.get('current_device_id') or None)
        except Exception as e:
            logger.error(f"获取当前设备ID失败: {str(e)}", exc_info=True)
            return False, str(e)

    def set_current_device_id(self, device_id):
        try:
            if not device_id:
                return False, '设备ID不能为空'
            setting = self.setting_manager.load()
            setting['current_device_id'] = device_id
            self.setting_manager.save(setting)
            return True, {'device_id': device_id}
        except Exception as e:
            logger.error(f"设置当前设备ID失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def _ensure_device_config_dir(self, device_id):
        """确保设备配置目录和文件存在
        
        Args:
            device_id: 设备ID
        """
        try:
            config_dir = os.path.join(self.BASE_CONFIG_DIR, device_id)
            config_file = os.path.join(config_dir, 'config.yaml')
            
            # 如果目录不存在，创建目录
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
                logger.info(f"✅ 创建设备配置目录: {config_dir}")
            
            # 如果配置文件不存在，从模板复制
            if not os.path.exists(config_file):
                if os.path.exists(self.CONFIG_TEMPLATE):
                    shutil.copy(self.CONFIG_TEMPLATE, config_file)
                    logger.info(f"✅ 从模板创建配置文件: {config_file}")
                else:
                    logger.warning(f"⚠️  配置模板不存在: {self.CONFIG_TEMPLATE}，创建空配置")
                    # 创建基本的空配置文件
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write("# 设备网络配置文件\nproxies:\n\nproxy-groups:\n")
                    logger.info(f"✅ 创建空配置文件: {config_file}")
        except Exception as e:
            logger.error(f"❌ 确保设备配置目录失败: {str(e)}", exc_info=True)

