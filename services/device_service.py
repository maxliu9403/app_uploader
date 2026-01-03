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
    
    # 已建立反向端口转发的设备集合（内存缓存，服务重启后会重新建立）
    _reverse_port_established: set = set()
    
    def get_devices(self):
        """获取已连接的设备列表，并自动创建设备配置文件夹 + 反向端口转发"""
        try:
            devices = self.adb_helper.get_devices()
            logger.info(f"📱 找到 {len(devices)} 个设备")
            
            # 为每个设备自动创建配置文件夹 + 设置反向端口转发
            for device in devices:
                device_id = device.get('device_id') or device.get('id')
                status = device.get('status', '')
                
                if not device_id:
                    continue
                
                # 只处理状态正常的设备
                if status != 'device':
                    logger.warning(f"⚠️ 设备 {device_id} 状态异常: {status}，跳过端口转发设置")
                    continue
                
                # 1. 确保设备配置目录存在
                self._ensure_device_config_dir(device_id)
                
                # 2. 检查是否需要设置反向端口转发（新设备）
                if device_id not in DeviceService._reverse_port_established:
                    logger.info(f"🆕 [新设备] 检测到新连接的设备: {device_id}")
                    self._setup_device_reverse_port(device_id)
            
            return True, devices
        except Exception as e:
            logger.error(f"获取设备列表失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def _setup_device_reverse_port(self, device_id, port=5000):
        """
        为设备设置 ADB 反向端口转发
        
        Args:
            device_id: 设备ID
            port: 端口号（默认5000，用于后端API通信）
        """
        try:
            logger.info(f"🔗 [ADB Reverse] 开始为设备 {device_id} 设置反向端口转发...")
            
            # 先检查是否已有端口转发
            success, existing_ports = self.adb_helper.list_reverse_ports(device_id)
            if success and existing_ports:
                logger.info(f"📋 [ADB Reverse] 设备 {device_id} 现有端口转发: {existing_ports}")
                
                # 检查是否已存在 5000 端口转发
                target_rule = f"tcp:{port}"
                for rule in existing_ports:
                    if target_rule in rule:
                        logger.info(f"✅ [ADB Reverse] 端口 {port} 已存在转发规则，无需重复设置")
                        DeviceService._reverse_port_established.add(device_id)
                        return True
            
            # 设置反向端口转发
            success, message = self.adb_helper.setup_reverse_port(device_id, port, port)
            
            if success:
                DeviceService._reverse_port_established.add(device_id)
                logger.info(f"✅ [ADB Reverse] 设备 {device_id} 端口转发设置完成")
                logger.info(f"   📡 手机可通过 http://127.0.0.1:{port} 访问电脑后端服务")
                return True
            else:
                logger.error(f"❌ [ADB Reverse] 设备 {device_id} 端口转发设置失败: {message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [ADB Reverse] 设备 {device_id} 端口转发异常: {str(e)}", exc_info=True)
            return False
    
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

