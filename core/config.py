"""
Config Manager - 配置管理模块
负责加载、保存和管理 YAML 配置文件
"""

import os
import yaml
from core.logger import get_logger

logger = get_logger(__name__)


class SettingManager:
    """项目配置管理器（setting.yaml）"""
    
    def __init__(self, setting_file='config/setting.yaml'):
        """
        初始化配置管理器
        
        Args:
            setting_file: 配置文件路径
        """
        self.setting_file = setting_file
    
    def load(self):
        """加载项目配置文件"""
        try:
            if not os.path.exists(self.setting_file):
                logger.warning(f"项目配置文件不存在: {self.setting_file}，将创建默认配置")
                return self._create_default_setting()
            
            with open(self.setting_file, 'r', encoding='utf-8') as f:
                setting = yaml.safe_load(f) or {}
                return setting
        except Exception as e:
            logger.error(f"加载项目配置文件失败: {str(e)}", exc_info=True)
            return {}
    
    def save(self, setting):
        """保存项目配置文件"""
        try:
            os.makedirs(os.path.dirname(self.setting_file), exist_ok=True)
            with open(self.setting_file, 'w', encoding='utf-8') as f:
                yaml.dump(setting, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            logger.info("项目配置文件保存成功")
            return True
        except Exception as e:
            logger.error(f"保存项目配置文件失败: {str(e)}", exc_info=True)
            raise Exception(f"保存项目配置文件失败: {str(e)}")
    
    def _create_default_setting(self):
        """创建默认配置"""
        os.makedirs(os.path.dirname(self.setting_file), exist_ok=True)
        default_setting = {
            'logging': {
                'enabled': True,
                'log_file': 'logs/proxy_manager.log',
                'log_level': 'INFO',
                'max_bytes': 10485760,
                'backup_count': 7,
                'log_format': '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
                'date_format': '%Y-%m-%d %H:%M:%S'
            },
            'regions': [
                {'code': 'GB', 'name': '英国'},
                {'code': 'SG', 'name': '新加坡'},
                {'code': 'HK', 'name': '香港'},
                {'code': 'MY', 'name': '马来西亚'},
                {'code': 'PH', 'name': '菲律宾'}
            ],
            'vm_account_counters': {},
            'proxy_name_counters': {},
            'devices': [],
            'config_file_path': 'config.yaml',
            'vm_script_path': 'vm.sh',
            'adb_path': 'adb',
            'vm_accounts_file_path': 'config/vm_accounts.yaml',
            'vm_model_config_path': '/data/local/tmp/vm_model_config.yaml'
        }
        with open(self.setting_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_setting, f, allow_unicode=True, default_flow_style=False)
        return default_setting


class ConfigManager:
    """网络配置管理器（config.yaml）"""
    
    def __init__(self, path_manager):
        """
        初始化配置管理器
        
        Args:
            path_manager: PathManager 实例
        """
        self.path_manager = path_manager
    
    def get_config_file(self):
        """获取配置文件路径"""
        return self.path_manager.get_config_file_path()
    
    def load(self):
        """加载网络配置文件"""
        from utils.yaml_helper import YAMLHelper
        
        config_file = self.get_config_file()
        logger.info(f"开始加载配置文件: {config_file}")
        
        if not os.path.exists(config_file):
            logger.warning(f"配置文件不存在: {config_file}，将创建空配置")
            return {}
        
        # 使用 YAMLHelper 加载配置
        yaml_helper = YAMLHelper()
        config = yaml_helper.load_yaml_file(config_file)
        
        # 确保 proxies 是列表，处理 None 的情况
        if config.get('proxies') is None:
            config['proxies'] = []
            logger.warning("配置文件中 proxies 为空，已初始化为空列表")
        
        # 迁移 proxies_dialer 到 proxies
        if 'proxies_dialer' in config and config.get('proxies_dialer'):
            config = self._migrate_proxies_dialer(config)
            self.save(config)
        
        logger.info(f"配置文件加载成功，包含 {len(config.get('proxies', []))} 个代理")
        return config
    
    def save(self, config):
        """保存网络配置文件"""
        from utils.yaml_helper import YAMLHelper
        
        config_file = self.get_config_file()
        logger.info("开始保存配置文件...")
        
        # 确保 proxies 是列表，处理 None 的情况
        if config.get('proxies') is None:
            config['proxies'] = []
            logger.warning("保存时发现 proxies 为空，已初始化为空列表")
        
        yaml_helper = YAMLHelper()
        yaml_helper.save_yaml_file(config_file, config)
        
        # 统计中转线路和普通代理数量
        from utils.yaml_helper import is_transit_proxy, format_proxy_for_display
        all_proxies = config.get('proxies', [])
        transit_count = sum(1 for p in all_proxies if is_transit_proxy(format_proxy_for_display(p)))
        proxy_count = len(all_proxies) - transit_count
        logger.info(f"配置文件保存成功，包含 {transit_count} 个中转线路，{proxy_count} 个普通代理")
        return True
    
    def _migrate_proxies_dialer(self, config):
        """迁移 proxies_dialer 到 proxies"""
        logger.info("检测到 proxies_dialer，开始迁移到 proxies...")
        
        if 'proxies' not in config:
            config['proxies'] = []
        
        migrated_count = 0
        for proxy in config['proxies_dialer']:
            if isinstance(proxy, dict):
                proxy['IsBase'] = True
                config['proxies'].insert(0, proxy)
                migrated_count += 1
        
        del config['proxies_dialer']
        logger.info(f"成功迁移 {migrated_count} 个中转线路到 proxies，已删除 proxies_dialer")
        
        return config

