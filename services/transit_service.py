"""
Transit Service - 中转线路业务逻辑
负责中转线路的增删改查
"""

from core.logger import get_logger
from utils.yaml_helper import format_proxy_for_display, is_transit_proxy

logger = get_logger(__name__)


class TransitService:
    """中转线路服务类"""
    
    def __init__(self, config_manager, adb_helper):
        """初始化中转线路服务"""
        self.config_manager = config_manager
        self.adb_helper = adb_helper
    
    def get_all_transits(self):
        """获取所有中转线路"""
        try:
            logger.info("🔍 开始获取所有中转线路...")
            config = self.config_manager.load()
            all_proxies = config.get('proxies') or []
            if all_proxies is None:
                all_proxies = []
            logger.info(f"   配置文件中共有 {len(all_proxies)} 个代理条目")
            
            transit_proxies = []
            normal_count = 0
            for idx, proxy in enumerate(all_proxies):
                formatted = format_proxy_for_display(proxy)
                if is_transit_proxy(formatted):
                    formatted['_index'] = idx
                    transit_proxies.append(formatted)
                else:
                    normal_count += 1
            
            logger.info(f"   过滤后: {len(transit_proxies)} 个中转线路, {normal_count} 个普通代理")
            logger.info(f"✅ 成功返回 {len(transit_proxies)} 个中转线路")
            return True, transit_proxies
        except Exception as e:
            logger.error(f"❌ 获取中转线路列表失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def get_transit_names(self):
        """获取中转线路名称列表"""
        try:
            success, transits = self.get_all_transits()
            if success:
                names = [t.get('name', '') for t in transits if t.get('name')]
                return True, names
            return False, transits
        except Exception as e:
            return False, str(e)
    
    def add_transit(self, data):
        """添加中转线路"""
        try:
            logger.info("➕ 开始添加新中转线路...")
            logger.info(f"   线路名称: {data.get('name', 'N/A')}")
            logger.info(f"   服务器: {data.get('server', 'N/A')}:{data.get('port', 'N/A')}")
            logger.info(f"   类型: {data.get('type', 'socks5')}")
            
            config = self.config_manager.load()
            
            # 确保 proxies 是列表
            if 'proxies' not in config or config['proxies'] is None:
                config['proxies'] = []
            
            # 验证名称
            logger.info("   🔍 验证线路名称...")
            proxy_name = data.get('name', '').strip()
            if self._check_name_exists(config, proxy_name):
                logger.warning(f"   ❌ 线路名称已存在: {proxy_name}")
                return False, f'中转线路名称 "{proxy_name}" 已存在'
            logger.info("   ✅ 名称验证通过")
            
            # 构建配置
            logger.info("   📝 构建中转线路配置...")
            new_proxy = self._build_transit_config(data)
            config['proxies'].append(new_proxy)
            logger.info(f"   配置列表中现有 {len(config['proxies'])} 个代理")
            
            # 更新策略组
            logger.info("   🔄 更新策略组...")
            self._update_proxy_groups(config)
            
            # 保存配置
            logger.info("   💾 保存配置文件...")
            self.config_manager.save(config)
            
            # 推送到设备
            logger.info("   📱 推送配置到设备...")
            push_result = self._push_config_to_devices()
            
            logger.info(f"✅ 中转线路 '{new_proxy['name']}' 添加成功！")
            return True, {'proxy': new_proxy, 'push_result': push_result}
        except Exception as e:
            logger.error(f"❌ 添加中转线路失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def update_transit(self, index, data):
        """更新中转线路"""
        try:
            config = self.config_manager.load()
            success, transits = self.get_all_transits()
            
            if not success or index < 0 or index >= len(transits):
                return False, '索引超出范围'
            
            original_index = transits[index]['_index']
            
            # 验证名称
            proxy_name = data.get('name', '').strip()
            if self._check_name_exists(config, proxy_name, exclude_index=original_index):
                return False, f'中转线路名称 "{proxy_name}" 已存在'
            
            # 构建配置
            updated_proxy = self._build_transit_config(data)
            config['proxies'][original_index] = updated_proxy
            
            # 更新策略组
            logger.info("   🔄 更新策略组...")
            self._update_proxy_groups(config)
            
            # 保存配置
            self.config_manager.save(config)
            
            # 推送到设备
            push_result = self._push_config_to_devices()
            
            logger.info(f"中转线路 '{updated_proxy['name']}' 更新成功")
            return True, {'proxy': updated_proxy, 'push_result': push_result}
        except Exception as e:
            logger.error(f"更新中转线路失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def delete_transit(self, index):
        """删除中转线路"""
        try:
            logger.info(f"🗑️  开始删除中转线路 (索引: {index})...")
            
            config = self.config_manager.load()
            success, transits = self.get_all_transits()
            
            if not success or index < 0 or index >= len(transits):
                logger.warning(f"   ❌ 索引超出范围: {index} (总数: {len(transits) if success else 0})")
                return False, '索引超出范围'
            
            original_index = transits[index]['_index']
            deleted_proxy = config['proxies'][original_index]
            proxy_name = format_proxy_for_display(deleted_proxy).get('name', '')
            logger.info(f"   线路名称: {proxy_name}")
            logger.info(f"   服务器: {deleted_proxy.get('server', 'N/A')}:{deleted_proxy.get('port', 'N/A')}")
            
            # 检查是否有代理使用这个中转线路
            logger.info("   🔍 检查中转线路使用情况...")
            if proxy_name:
                used_by = self._check_transit_usage(config, proxy_name, original_index)
                if used_by:
                    logger.warning(f"   ❌ 该中转线路正被 {len(used_by)} 个代理使用: {', '.join(used_by[:3])}")
                    return False, f'无法删除：该中转线路正被以下代理使用: {", ".join(used_by)}'
                logger.info("   ✅ 该中转线路未被任何代理使用")
            
            config['proxies'].pop(original_index)
            logger.info(f"   配置列表中剩余 {len(config['proxies'])} 个代理")
            
            # 更新策略组
            logger.info("   🔄 更新策略组...")
            self._update_proxy_groups(config)
            
            # 保存配置
            logger.info("   💾 保存配置文件...")
            self.config_manager.save(config)
            
            # 推送到设备
            logger.info("   📱 推送配置到设备...")
            push_result = self._push_config_to_devices()
            
            logger.info(f"✅ 中转线路 '{proxy_name}' 删除成功！")
            return True, {'proxy': deleted_proxy, 'push_result': push_result}
        except Exception as e:
            logger.error(f"❌ 删除中转线路失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    # ==================== 私有方法 ====================
    
    def _build_transit_config(self, data):
        """构建中转线路配置"""
        port = data.get('port', '')
        try:
            port = int(port) if port else ''
        except (ValueError, TypeError):
            pass
        
        new_proxy = {
            'name': data.get('name', '').strip(),
            'type': data.get('type', 'socks5'),
            'server': data.get('server', ''),
            'port': port,
            'IsBase': True,
        }
        
        if 'password' in data:
            new_proxy['password'] = data['password']
        if 'username' in data:
            new_proxy['username'] = data['username']
        if 'sni' in data:
            new_proxy['sni'] = data['sni']
        if 'skip-cert-verify' in data:
            new_proxy['skip-cert-verify'] = data['skip-cert-verify']
        else:
            new_proxy['skip-cert-verify'] = True
        if 'udp' in data:
            new_proxy['udp'] = data['udp']
        
        return new_proxy
    
    def _check_name_exists(self, config, name, exclude_index=None):
        """检查名称是否已存在"""
        proxies = config.get('proxies') or []
        if proxies is None:
            proxies = []
        for idx, proxy in enumerate(proxies):
            if exclude_index is not None and idx == exclude_index:
                continue
            formatted = format_proxy_for_display(proxy)
            if formatted.get('name') == name:
                return True
        return False
    
    def _check_transit_usage(self, config, transit_name, exclude_index):
        """检查中转线路是否被使用"""
        used_by = []
        proxies = config.get('proxies') or []
        if proxies is None:
            proxies = []
        for idx, proxy in enumerate(proxies):
            if idx == exclude_index:
                continue
            formatted = format_proxy_for_display(proxy)
            if not is_transit_proxy(formatted) and formatted.get('dialer-proxy') == transit_name:
                used_by.append(formatted.get('name', f'代理#{idx}'))
        return used_by
    
    def _push_config_to_devices(self):
        """推送配置到所有设备"""
        try:
            config_file_path = self.config_manager.get_config_file()
            devices = self.adb_helper.get_devices()
            
            if not devices:
                return {'success': False, 'message': '没有已连接的设备'}
            
            success_count = 0
            for device in devices:
                success, _ = self.adb_helper.push_file(
                    local_path=config_file_path,
                    remote_path='/data/adb/box/clash/config.yaml',
                    device_id=device['id'],
                    use_su=True
                )
                if success:
                    success_count += 1
            
            if success_count == len(devices):
                return {'success': True, 'message': f'成功推送到 {success_count} 个设备'}
            elif success_count > 0:
                return {'success': True, 'message': f'部分成功：{success_count}/{len(devices)} 个设备'}
            else:
                return {'success': False, 'message': '所有设备推送失败'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _update_proxy_groups(self, config):
        """更新策略组"""
        try:
            if 'proxy-groups' not in config:
                logger.warning("配置中没有 proxy-groups，跳过更新")
                return
            
            # 获取所有代理名称（包括中转线路和普通代理）
            proxy_names = []
            proxies = config.get('proxies') or []
            if proxies is None:
                proxies = []
            
            for proxy in proxies:
                if isinstance(proxy, dict) and 'name' in proxy:
                    proxy_names.append(proxy['name'])
            
            logger.info(f"   当前共有 {len(proxy_names)} 个代理（包括中转线路）")
            
            # 更新每个策略组（除了 PROXY 组）
            updated_count = 0
            for group in config['proxy-groups']:
                if not isinstance(group, dict):
                    continue
                
                group_type = group.get('type', '')
                group_name = group.get('name', '')
                
                # 只更新 select 类型的策略组，且不是 PROXY 组
                if group_type == 'select' and group_name != 'PROXY':
                    # 确保 proxies 是列表
                    if 'proxies' not in group or group['proxies'] is None:
                        group['proxies'] = []
                    
                    # 更新为所有代理名称
                    group['proxies'] = proxy_names.copy()
                    updated_count += 1
                    logger.info(f"   ✅ 更新策略组 '{group_name}': {len(group['proxies'])} 个代理")
            
            logger.info(f"   共更新 {updated_count} 个策略组")
        except Exception as e:
            logger.error(f"   ❌ 更新策略组失败: {str(e)}", exc_info=True)

