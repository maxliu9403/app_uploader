"""
Path Manager - 路径管理模块
统一管理所有配置文件路径
"""

from core.logger import get_logger

logger = get_logger(__name__)


class PathManager:
    """路径管理器，负责管理和缓存各种文件路径"""
    
    def __init__(self, setting_manager):
        """
        初始化路径管理器
        
        Args:
            setting_manager: SettingManager 实例
        """
        self.setting_manager = setting_manager
        self._cached_paths = {}
    
    def get_config_file_path(self):
        """获取网络配置文件路径"""
        if 'config_file' not in self._cached_paths:
            setting = self.setting_manager.load()
            path = setting.get('config_file_path', 'config.yaml')
            self._cached_paths['config_file'] = path if path else 'config.yaml'
        return self._cached_paths['config_file']
    
    def get_vm_script_path(self):
        """获取 VM 脚本路径"""
        if 'vm_script' not in self._cached_paths:
            setting = self.setting_manager.load()
            path = setting.get('vm_script_path', 'vm.sh')
            self._cached_paths['vm_script'] = path if path else 'vm.sh'
        return self._cached_paths['vm_script']
    
    def get_adb_path(self):
        """获取 ADB 可执行文件路径"""
        if 'adb' not in self._cached_paths:
            setting = self.setting_manager.load()
            path = setting.get('adb_path', 'adb')
            self._cached_paths['adb'] = path if path else 'adb'
        return self._cached_paths['adb']
    
    def get_vm_accounts_file_path(self):
        """获取多账号动态配置文件路径"""
        if 'vm_accounts' not in self._cached_paths:
            setting = self.setting_manager.load()
            path = setting.get('vm_accounts_file_path', 'config/vm_accounts.yaml')
            self._cached_paths['vm_accounts'] = path if path else 'config/vm_accounts.yaml'
        return self._cached_paths['vm_accounts']
    
    def get_vm_model_config_path(self):
        """获取 VM 机型配置路径"""
        if 'vm_model_config' not in self._cached_paths:
            setting = self.setting_manager.load()
            path = setting.get('vm_model_config_path', '/data/local/tmp/vm_model_config.yaml')
            self._cached_paths['vm_model_config'] = path if path else '/data/local/tmp/vm_model_config.yaml'
        return self._cached_paths['vm_model_config']
    
    def clear_cache(self):
        """清除路径缓存（在更新路径配置后调用）"""
        self._cached_paths.clear()
        logger.info("路径缓存已清除")

