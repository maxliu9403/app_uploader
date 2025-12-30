"""
VM Service - VM 管理业务逻辑
简化版本：核心功能保留，详细实现可参考原 proxy_manager.py
"""

from core.logger import get_logger

logger = get_logger(__name__)


class VMService:
    """VM 服务类"""
    
    def __init__(self, path_manager, adb_helper, setting_manager):
        self.path_manager = path_manager
        self.adb_helper = adb_helper
        self.setting_manager = setting_manager
    
    def generate_account_name(self, app_type, region):
        """生成 VM 账号名称"""
        try:
            setting = self.setting_manager.load()
            counters = setting.get('vm_account_counters') or {}
            if counters is None:
                counters = {}
            
            counter_key = f"{app_type}_{region}"
            current_count = counters.get(counter_key, 0)
            next_num = current_count + 1
            account_name = f"{app_type}_{region}_{next_num:03d}"
            
            logger.info(f"生成账号名称: {account_name}")
            return True, account_name
        except Exception as e:
            logger.error(f"生成账号名称失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def increment_account_counter(self, app_type, region):
        """增加账号计数器"""
        try:
            setting = self.setting_manager.load()
            counters = setting.get('vm_account_counters') or {}
            if counters is None:
                counters = {}
            
            counter_key = f"{app_type}_{region}"
            current_count = counters.get(counter_key, 0)
            counters[counter_key] = current_count + 1
            
            setting['vm_account_counters'] = counters
            self.setting_manager.save(setting)
            
            logger.info(f"更新 VM 账号计数器: {counter_key} = {counters[counter_key]}")
            return True, None
        except Exception as e:
            logger.error(f"更新计数器失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def get_config_value(self, field_name, device_id=None):
        """从设备读取配置值"""
        try:
            config_file_path = self.path_manager.get_vm_accounts_file_path()
            command = f"cat {config_file_path} 2>/dev/null | grep '^{field_name}=' | head -n 1 | cut -d= -f2- | tr -d '\\r\\n '"
            
            returncode, stdout, stderr = self.adb_helper.execute_shell_command(
                command=command,
                device_id=device_id,
                use_su=False,
                timeout=10
            )
            
            if returncode == 0 and stdout.strip():
                value = stdout.strip()
                logger.info(f"成功获取配置值: {field_name} = {value}")
                return True, value
            else:
                logger.warning(f"配置文件中未找到字段: {field_name}")
                return False, f'未找到字段 "{field_name}"'
        except Exception as e:
            logger.error(f"获取配置值失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def get_account_list(self, device_id=None):
        """获取 VM 账号列表"""
        try:
            config_path = self.path_manager.get_vm_model_config_path().rstrip('/') + '/'
            command = f"ls -1 {config_path}*.conf 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/\\.conf$//' || echo ''"
            
            returncode, stdout, stderr = self.adb_helper.execute_shell_command(
                command=command,
                device_id=device_id,
                use_su=False,
                timeout=10
            )
            
            if returncode == 0:
                accounts = []
                for line in stdout.strip().split('\n'):
                    account_name = line.strip()
                    if account_name:
                        accounts.append(account_name)
                
                logger.info(f"成功获取账号列表: {len(accounts)} 个账号")
                return True, accounts
            else:
                logger.warning("获取账号列表失败或目录为空")
                return True, []
        except Exception as e:
            logger.error(f"获取账号列表失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    # 注意：create_account, load_account, save_account 等涉及 SSE 流式响应的方法
    # 建议保留原 proxy_manager.py 中的实现，在路由层直接调用
    # 这里提供基础方法供其他地方调用

