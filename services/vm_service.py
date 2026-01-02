"""
VM Service - VM 管理业务逻辑
简化版本：核心功能保留，详细实现可参考原 proxy_manager.py
"""

from core.logger import get_logger

logger = get_logger(__name__)


class VMService:
    """VM 服务类"""
    
    def __init__(self, path_manager, adb_helper, setting_manager, config_manager=None):
        self.path_manager = path_manager
        self.adb_helper = adb_helper
        self.setting_manager = setting_manager
        self.config_manager = config_manager
    
    def generate_account_name(self, app_type, region, device_id=None, device_remark=None):
        """
        生成 VM 账号名称
        格式: appType_region_deviceId(remark)_自增ID
        示例: Carousell_HK_72e8932c(我的手机)_001
        """
        try:
            setting = self.setting_manager.load()
            counters = setting.get('vm_account_counters') or {}
            if counters is None:
                counters = {}
            
            # 计数器key: appType_region_deviceId
            counter_key = f"{app_type}_{region}"
            if device_id:
                counter_key = f"{app_type}_{region}_{device_id}"
            
            current_count = counters.get(counter_key, 0)
            next_num = current_count + 1
            
            # 构建账号名称
            if device_id:
                if device_remark:
                    # 格式: appType_region_deviceId(remark)_001
                    account_name = f"{app_type}_{region}_{device_id}({device_remark})_{next_num:03d}"
                else:
                    # 格式: appType_region_deviceId_001
                    account_name = f"{app_type}_{region}_{device_id}_{next_num:03d}"
            else:
                # 兼容旧格式: appType_region_001
                account_name = f"{app_type}_{region}_{next_num:03d}"
            
            logger.info(f"生成账号名称: {account_name}")
            return True, account_name
        except Exception as e:
            logger.error(f"生成账号名称失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def increment_account_counter(self, app_type, region, device_id=None):
        """增加账号计数器"""
        try:
            setting = self.setting_manager.load()
            counters = setting.get('vm_account_counters') or {}
            if counters is None:
                counters = {}
            
            # 计数器key需要与generate_account_name一致
            counter_key = f"{app_type}_{region}"
            if device_id:
                counter_key = f"{app_type}_{region}_{device_id}"
            
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
            # 先检查设备连接状态
            if device_id:
                devices = self.adb_helper.get_devices()
                if not any(d['id'] == device_id for d in devices):
                    logger.error(f"设备 {device_id} 未连接")
                    return False, f'设备 {device_id} 未连接'
            else:
                # 如果没有指定设备ID，检查是否有任何设备连接
                devices = self.adb_helper.get_devices()
                if not devices:
                    logger.error("未找到任何ADB设备")
                    return False, '未找到任何ADB设备'
            
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
            # 先检查设备连接状态
            if device_id:
                devices = self.adb_helper.get_devices()
                if not any(d['id'] == device_id for d in devices):
                    logger.error(f"设备 {device_id} 未连接")
                    return False, f'设备 {device_id} 未连接'
            else:
                devices = self.adb_helper.get_devices()
                if not devices:
                    logger.error("未找到任何ADB设备")
                    return False, '未找到任何ADB设备'
            
            config_path = self.path_manager.get_vm_model_config_path().rstrip('/') + '/'
            logger.info(f"🔍 查找VM账号配置路径: {config_path}")
            
            command = f"ls -1 {config_path}*.conf 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/\\.conf$//' || echo ''"
            logger.info(f"🔍 执行命令: {command}")
            
            returncode, stdout, stderr = self.adb_helper.execute_shell_command(
                command=command,
                device_id=device_id,
                use_su=False,
                timeout=10
            )
            
            logger.info(f"🔍 命令返回码: {returncode}")
            logger.info(f"🔍 命令输出: {stdout[:200] if stdout else '(空)'}...")
            if stderr:
                logger.warning(f"⚠️ 命令错误输出: {stderr[:200]}...")
            
            if returncode == 0:
                accounts = []
                for line in stdout.strip().split('\n'):
                    account_name = line.strip()
                    if account_name:
                        accounts.append(account_name)
                
                logger.info(f"✅ 成功获取账号列表: {len(accounts)} 个账号")
                if accounts:
                    logger.info(f"   账号列表: {', '.join(accounts[:5])}{'...' if len(accounts) > 5 else ''}")
                return True, accounts
            else:
                logger.warning(f"⚠️ 获取账号列表失败，返回码: {returncode}")
                return True, []
        except Exception as e:
            logger.error(f"❌ 获取账号列表失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    
    # 已废弃: get_proxy_names_by_region 方法
    # 前端已改用 ProxyService.get_all_proxies() 通过 /api/proxies 接口
    # 该方法不支持 device_id 参数，导致无法按设备过滤代理
    
    # 注意：create_account, load_account, save_account 等涉及 SSE 流式响应的方法
    # 建议保留原 proxy_manager.py 中的实现，在路由层直接调用
    # 这里提供基础方法供其他地方调用

