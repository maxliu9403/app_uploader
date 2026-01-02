"""
Proxy Service - 代理业务逻辑
负责代理的增删改查和批量操作
"""

from core.logger import get_logger
from utils.yaml_helper import format_proxy_for_display, is_transit_proxy
import os

logger = get_logger(__name__)


class ProxyService:
    """代理服务类"""
    
    def __init__(self, config_manager, setting_manager, adb_helper):
        """
        初始化代理服务
        
        Args:
            config_manager: ConfigManager 实例
            setting_manager: SettingManager 实例
            adb_helper: ADBHelper 实例
        """
        self.config_manager = config_manager
        self.setting_manager = setting_manager
        self.adb_helper = adb_helper
    
    def get_all_proxies(self, device_id=None):
        """
        获取所有普通代理（排除中转线路）
        
        Args:
            device_id: 设备ID，如果提供则获取该设备的代理
        
        Returns:
            tuple: (success, data/error_message)
        """
        try:
            logger.info(f"🔍 开始获取所有普通代理... (设备: {device_id or '默认'})")
            config = self.config_manager.load(device_id)
            all_proxies = config.get('proxies') or []
            if all_proxies is None:
                all_proxies = []
            logger.info(f"   配置文件中共有 {len(all_proxies)} 个代理条目")
            
            # 过滤出普通代理
            formatted_proxies = []
            transit_count = 0
            for idx, proxy in enumerate(all_proxies):
                formatted = format_proxy_for_display(proxy)
                if not is_transit_proxy(formatted):
                    formatted['_index'] = idx
                    formatted_proxies.append(formatted)
                else:
                    transit_count += 1
            
            logger.info(f"   过滤后: {len(formatted_proxies)} 个普通代理, {transit_count} 个中转线路")
            logger.info(f"✅ 成功返回 {len(formatted_proxies)} 个普通代理")
            return True, formatted_proxies
        except Exception as e:
            logger.error(f"❌ 获取代理列表失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def add_proxy(self, data, device_id=None):
        """
        添加新代理
        
        Args:
            data: 代理配置字典
            device_id: 设备ID，如果提供则添加到该设备的配置
            
        Returns:
            tuple: (success, data/error_message)
        """
        try:
            if not device_id:
                return False, 'device_id 是必传参数'
            logger.info(f"➕ 开始添加新代理... (设备: {device_id or '默认'})")
            logger.info(f"   代理名称: {data.get('name', 'N/A')}")
            logger.info(f"   代理类型: {data.get('type', 'socks5')}")
            logger.info(f"   服务器: {data.get('server', 'N/A')}:{data.get('port', 'N/A')}")
            logger.info(f"   地区: {data.get('region', 'N/A')}")
            logger.info(f"   中转线路: {data.get('dialer-proxy', '无')}")
            
            config = self.config_manager.load(device_id)
            
            # 确保 proxies 是列表
            if 'proxies' not in config or config['proxies'] is None:
                config['proxies'] = []
            
            # 验证数据
            logger.info("   🔍 验证代理数据...")
            error_msg = self._validate_proxy_data(data, config)
            if error_msg:
                logger.warning(f"   ❌ 数据验证失败: {error_msg}")
                return False, error_msg
            logger.info("   ✅ 数据验证通过")
            
            # 构建代理配置
            new_proxy = self._build_proxy_config(data)
            logger.info(f"   📝 构建代理配置完成")
            
            # 添加到配置
            config['proxies'].append(new_proxy)
            logger.info(f"   配置列表中现有 {len(config['proxies'])} 个代理")
            
            # 更新策略组
            logger.info("   🔄 更新策略组...")
            self._update_proxy_groups(config)
            
            # 保存配置
            logger.info("   💾 保存配置文件...")
            self.config_manager.save(config, device_id)
            logger.info("   ✅ 配置文件保存成功")
            
            # 推送到设备
            logger.info("   📱 推送配置到设备...")
            push_result = self._push_config_to_devices(device_id)
            if push_result.get('success'):
                logger.info(f"   ✅ {push_result.get('message')}")
            else:
                logger.warning(f"   ⚠️  推送失败: {push_result.get('message')}")
            
            logger.info(f"✅ 代理 '{new_proxy['name']}' 添加成功！")
            return True, {'proxy': new_proxy, 'push_result': push_result}
        except Exception as e:
            logger.error(f"❌ 添加代理失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def update_proxy(self, index, data, device_id=None):
        """
        更新代理
        
        Args:
            index: 代理索引
            data: 更新的数据
            device_id: 设备ID，如果提供则更新该设备的代理
            
        Returns:
            tuple: (success, data/error_message)
        """
        try:
            if not device_id:
                return False, 'device_id 是必传参数'
            logger.info(f"✏️  开始更新代理 (索引: {index}, 设备: {device_id or '默认'})...")
            logger.info(f"   新名称: {data.get('name', 'N/A')}")
            logger.info(f"   新服务器: {data.get('server', 'N/A')}:{data.get('port', 'N/A')}")
            
            config = self.config_manager.load(device_id)
            
            proxies = config.get('proxies') or []
            if proxies is None:
                proxies = []
                config['proxies'] = []
            
            if index < 0 or index >= len(proxies):
                logger.warning(f"   ❌ 索引超出范围: {index} (总数: {len(proxies)})")
                return False, '索引超出范围'
            
            old_proxy = config['proxies'][index]
            old_name = format_proxy_for_display(old_proxy).get('name', 'Unknown')
            logger.info(f"   原代理名称: {old_name}")
            
            # 验证数据
            logger.info("   🔍 验证更新数据...")
            error_msg = self._validate_proxy_data(data, config, exclude_index=index)
            if error_msg:
                logger.warning(f"   ❌ 数据验证失败: {error_msg}")
                return False, error_msg
            logger.info("   ✅ 数据验证通过")
            
            # 构建更新的配置
            updated_proxy = self._build_proxy_config(data, config['proxies'][index])
            
            # 更新配置
            config['proxies'][index] = updated_proxy
            
            # 更新策略组
            logger.info("   🔄 更新策略组...")
            self._update_proxy_groups(config)
            
            # 保存配置
            logger.info("   💾 保存配置文件...")
            self.config_manager.save(config, device_id)
            
            # 推送到设备
            logger.info("   📱 推送配置到设备...")
            push_result = self._push_config_to_devices(device_id)
            
            logger.info(f"✅ 代理 '{updated_proxy['name']}' (索引 {index}) 更新成功！")
            return True, {'proxy': updated_proxy, 'push_result': push_result}
        except Exception as e:
            logger.error(f"❌ 更新代理失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def update_proxy_by_name(self, proxy_name, data, device_id=None):
        """
        根据名称更新代理
        
        Args:
            proxy_name: 代理名称
            data: 新的代理配置
            device_id: 设备ID，如果提供则更新该设备的代理
            
        Returns:
            tuple: (success, data/error_message)
        """
        try:
            if not device_id:
                return False, 'device_id 是必传参数'
            logger.info(f"✏️  开始更新代理 (名称: {proxy_name}, 设备: {device_id or '默认'})...")
            logger.info(f"   新名称: {data.get('name', 'N/A')}")
            logger.info(f"   新服务器: {data.get('server', 'N/A')}:{data.get('port', 'N/A')}")
            
            config = self.config_manager.load(device_id)
            
            proxies = config.get('proxies') or []
            if proxies is None:
                proxies = []
                config['proxies'] = []
            
            # 通过名称查找代理的索引
            found_index = None
            for idx, proxy in enumerate(proxies):
                formatted = format_proxy_for_display(proxy)
                if formatted.get('name') == proxy_name:
                    found_index = idx
                    break
            
            if found_index is None:
                logger.warning(f"   ❌ 未找到名为 '{proxy_name}' 的代理")
                return False, f'未找到名为 "{proxy_name}" 的代理'
            
            logger.info(f"   找到代理，配置文件索引: {found_index}")
            
            # 验证数据
            logger.info("   🔍 验证更新数据...")
            error_msg = self._validate_proxy_data(data, config, exclude_index=found_index)
            if error_msg:
                logger.warning(f"   ❌ 数据验证失败: {error_msg}")
                return False, error_msg
            logger.info("   ✅ 数据验证通过")
            
            # 构建更新的配置
            updated_proxy = self._build_proxy_config(data, config['proxies'][found_index])
            
            # 更新配置
            old_proxy_name = config['proxies'][found_index].get('name', proxy_name)
            config['proxies'][found_index] = updated_proxy
            
            # 如果名称改变了，需要更新策略组中的引用
            if old_proxy_name != updated_proxy['name']:
                logger.info(f"   🔄 代理名称已改变: '{old_proxy_name}' -> '{updated_proxy['name']}'，更新策略组引用...")
                self._update_proxy_name_in_groups(config, old_proxy_name, updated_proxy['name'])
            
            # 更新策略组
            logger.info("   🔄 更新策略组...")
            self._update_proxy_groups(config)
            
            # 保存配置
            logger.info("   💾 保存配置文件...")
            self.config_manager.save(config, device_id)
            
            # 推送到设备
            logger.info("   📱 推送配置到设备...")
            push_result = self._push_config_to_devices(device_id)
            
            logger.info(f"✅ 代理 '{updated_proxy['name']}' 更新成功！")
            return True, {'proxy': updated_proxy, 'push_result': push_result}
        except Exception as e:
            logger.error(f"❌ 更新代理失败: {str(e)}", exc_info=True)
            return False, str(e)

    def delete_proxy(self, index, device_id=None):
        try:
            if not device_id:
                return False, 'device_id 是必传参数'
            logger.info(f"🗑️  开始删除代理 (索引: {index}, 设备: {device_id or '默认'})...")

            success, proxies = self.get_all_proxies(device_id)
            if not success:
                return False, proxies

            if index < 0 or index >= len(proxies):
                return False, '索引超出范围'

            original_index = proxies[index].get('_index')
            if original_index is None:
                return False, '索引映射失败'

            config = self.config_manager.load(device_id)
            all_proxies = config.get('proxies') or []
            if all_proxies is None:
                all_proxies = []
                config['proxies'] = []

            if original_index < 0 or original_index >= len(all_proxies):
                return False, '索引超出范围'

            deleted_proxy = all_proxies.pop(original_index)
            proxy_name = format_proxy_for_display(deleted_proxy).get('name', '未知')

            self._update_proxy_groups(config)
            self.config_manager.save(config, device_id)

            push_result = self._push_config_to_devices(device_id)
            return True, {'proxy': deleted_proxy, 'push_result': push_result}
        except Exception as e:
            logger.error(f"❌ 删除代理失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def delete_proxy_by_name(self, proxy_name, device_id=None):
        """
        通过名称删除代理（解决前端过滤列表索引与后端配置索引不匹配的问题）
        
        Args:
            proxy_name: 代理名称
            
        Returns:
            tuple: (success, data/error_message)
        """
        try:
            if not device_id:
                return False, 'device_id 是必传参数'
            logger.info(f"🗑️  开始删除代理 (名称: {proxy_name}, 设备: {device_id or '默认'})...")
            
            config = self.config_manager.load(device_id)
            
            proxies = config.get('proxies') or []
            if proxies is None:
                proxies = []
                config['proxies'] = []
            
            # 通过名称查找代理的索引
            found_index = None
            for idx, proxy in enumerate(proxies):
                formatted = format_proxy_for_display(proxy)
                if formatted.get('name') == proxy_name:
                    found_index = idx
                    break
            
            if found_index is None:
                logger.warning(f"   ❌ 未找到名为 '{proxy_name}' 的代理")
                return False, f'未找到名为 "{proxy_name}" 的代理'
            
            logger.info(f"   找到代理，配置文件索引: {found_index}")
            
            deleted_proxy = config['proxies'].pop(found_index)
            logger.info(f"   已删除代理: {format_proxy_for_display(deleted_proxy)}")
            
            # 更新策略组
            logger.info("   🔄 更新策略组...")
            self._update_proxy_groups(config)
            
            # 保存配置
            logger.info("   💾 保存配置文件...")
            self.config_manager.save(config, device_id)
            
            # 推送到设备
            logger.info("   📱 推送配置到设备...")
            push_result = self._push_config_to_devices(device_id)
            
            logger.info(f"✅ 代理 '{proxy_name}' 删除成功！")
            return True, {'proxy': deleted_proxy, 'push_result': push_result}
        except Exception as e:
            logger.error(f"❌ 删除代理失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    def batch_add_proxies(self, data, device_id=None):
        """
        批量添加代理
        
        Args:
            data: 批量导入数据
            device_id: 设备ID，如果提供则添加到该设备的配置
            
        Returns:
            tuple: (success, result/error_message)
        """
        try:
            if not device_id:
                return False, 'device_id 是必传参数'
            logger.info(f"📦 开始批量添加代理... (设备: {device_id or '默认'})")
            
            # 解析参数
            proxy_lines = data.get('proxy_lines', '').strip()
            format_type = data.get('format_type', '').strip()
            region = data.get('region', '').strip().upper()
            name_prefix = data.get('name_prefix', '').strip()
            dialer_proxy = data.get('dialer_proxy', '').strip()
            is_bak = data.get('is_bak', False)  # 是否为备用线路
            
            lines_count = len([l for l in proxy_lines.split('\n') if l.strip()])
            logger.info(f"   数据行数: {lines_count}")
            logger.info(f"   数据格式: {format_type}")
            logger.info(f"   地区: {region}")
            logger.info(f"   名称前缀: {name_prefix}")
            logger.info(f"   中转线路: {dialer_proxy or '无'}")
            logger.info(f"   是否备用线路: {'是' if is_bak else '否'}")
            
            # 验证参数
            logger.info("   🔍 验证批量导入参数...")
            if not proxy_lines:
                logger.warning("   ❌ 代理数据不能为空")
                return False, '代理数据不能为空'
            if not format_type or format_type not in ['format1', 'format2', 'format3']:
                logger.warning("   ❌ 数据格式无效")
                return False, '请选择数据格式'
            if not region:
                logger.warning("   ❌ 地区不能为空")
                return False, 'region 是必填项，请选择地区'
            if not name_prefix:
                logger.warning("   ❌ 名称前缀不能为空")
                return False, '代理名称前缀不能为空'
            
            # 验证地区
            if not self._validate_region(region):
                logger.warning(f"   ❌ 地区代码不存在: {region}")
                return False, f'地区代码 "{region}" 不存在'
            
            logger.info("   ✅ 参数验证通过")
            
            # 解析代理行
            logger.info("   📝 开始解析代理数据...")
            parsed_proxies, failed_lines = self._parse_proxy_lines(proxy_lines, format_type)
            logger.info(f"   解析结果: 成功 {len(parsed_proxies)} 个, 失败 {len(failed_lines)} 个")
            
            if not parsed_proxies:
                logger.warning("   ❌ 没有成功解析任何代理")
                return False, f'没有成功解析任何代理。失败的行:\n' + '\n'.join(failed_lines[:5])
            
            # 加载配置
            logger.info("   📂 加载配置文件...")
            config = self.config_manager.load(device_id)
            if 'proxies' not in config or config['proxies'] is None:
                config['proxies'] = []
            logger.info(f"   当前配置中有 {len(config['proxies'])} 个代理")
            
            # 批量添加
            logger.info("   ➕ 开始批量添加代理...")
            added_proxies = []
            setting = self.setting_manager.load()
            
            # 确保 proxy_name_counters 是字典，处理 None 的情况
            if 'proxy_name_counters' not in setting or setting['proxy_name_counters'] is None:
                setting['proxy_name_counters'] = {}
                logger.info("   初始化代理名称计数器为空字典")
            
            current_counter = setting['proxy_name_counters'].get(name_prefix, 0)
            logger.info(f"   名称计数器起始值: {name_prefix}_{current_counter + 1:03d}")
            
            for proxy_data in parsed_proxies:
                current_counter += 1
                proxy_name = f"{name_prefix}_{current_counter:03d}"
                
                # 检查名称是否已存在
                if self._check_name_exists(config, proxy_name):
                    logger.warning(f"代理名称 '{proxy_name}' 已存在，跳过")
                    continue
                
                # 构建代理配置
                new_proxy = {
                    'name': proxy_name,
                    'type': 'socks5',
                    'server': proxy_data['hostname'],
                    'port': proxy_data['port'],
                    'region': region,
                    'username': proxy_data['username'],
                    'password': proxy_data['password'],
                    'skip-cert-verify': True,
                    'udp': True,
                    'IsBak': bool(is_bak),  # 设置是否为备用线路
                }
                
                if dialer_proxy:
                    new_proxy['dialer-proxy'] = dialer_proxy
                
                config['proxies'].append(new_proxy)
                added_proxies.append(proxy_name)
            
            if not added_proxies:
                logger.warning("   ⚠️  所有代理名称都已存在，没有添加任何代理")
                return False, '所有代理名称都已存在，没有添加任何代理'
            
            logger.info(f"   成功生成 {len(added_proxies)} 个代理配置")
            
            # 更新计数器
            logger.info(f"   💾 更新名称计数器: {name_prefix} -> {current_counter}")
            setting['proxy_name_counters'][name_prefix] = current_counter
            self.setting_manager.save(setting)
            
            # 更新策略组
            logger.info("   🔄 更新策略组...")
            self._update_proxy_groups(config)
            
            # 保存配置
            logger.info("   💾 保存配置文件...")
            self.config_manager.save(config, device_id)
            logger.info(f"   配置文件中现有 {len(config['proxies'])} 个代理")
            
            # 推送到设备
            logger.info("   📱 推送配置到设备...")
            push_result = self._push_config_to_devices(device_id)
            
            result_message = f'成功添加 {len(added_proxies)} 个代理'
            if failed_lines:
                result_message += f'，{len(failed_lines)} 行解析失败'
            
            logger.info(f"✅ 批量添加完成！{result_message}")
            logger.info(f"   成功的代理名称: {', '.join(added_proxies[:5])}" + (' ...' if len(added_proxies) > 5 else ''))
            
            return True, {
                'message': result_message,
                'added_count': len(added_proxies),
                'failed_count': len(failed_lines),
                'added_names': added_proxies,
                'failed_lines': failed_lines[:10],
                'push_result': push_result
            }
        except Exception as e:
            logger.error(f"批量添加代理失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    # ==================== 私有辅助方法 ====================
    
    def _validate_proxy_data(self, data, config, exclude_index=None):
        """验证代理数据"""
        # 验证名称
        proxy_name = data.get('name', '').strip()
        if proxy_name:
            if self._check_name_exists(config, proxy_name, exclude_index):
                return f'代理名称 "{proxy_name}" 已存在'
        
        # 验证地区
        region = data.get('region', '').strip().upper()
        if not region:
            return 'region 是必填项，请选择地区'
        if not self._validate_region(region):
            return f'地区代码 "{region}" 不存在'
        
        # 验证用户名和密码
        if not data.get('username', '').strip():
            return '用户名是必填项'
        if not data.get('password', '').strip():
            return '密码是必填项'
        
        return None
    
    def _build_proxy_config(self, data, old_proxy=None):
        """构建代理配置"""
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
            'region': data.get('region', '').strip().upper(),
            'username': data.get('username', '').strip(),
            'password': data.get('password', '').strip(),
        }
        
        # 可选参数
        if 'sni' in data:
            new_proxy['sni'] = data['sni']
        if 'skip-cert-verify' in data:
            new_proxy['skip-cert-verify'] = data['skip-cert-verify']
        else:
            new_proxy['skip-cert-verify'] = True
        if 'udp' in data:
            new_proxy['udp'] = data['udp']
        else:
            new_proxy['udp'] = True
        
        # 处理 dialer-proxy
        if 'dialer-proxy' in data:
            if data['dialer-proxy']:
                new_proxy['dialer-proxy'] = data['dialer-proxy']
        elif old_proxy and 'dialer-proxy' in old_proxy:
            new_proxy['dialer-proxy'] = old_proxy['dialer-proxy']
        
        # 处理 IsBak（是否为备用线路）
        if 'is_bak' in data:
            new_proxy['IsBak'] = bool(data['is_bak'])
        elif old_proxy and 'IsBak' in old_proxy:
            new_proxy['IsBak'] = old_proxy['IsBak']
        else:
            new_proxy['IsBak'] = False
        
        return new_proxy
    
    def _check_name_exists(self, config, name, exclude_index=None):
        """检查代理名称是否已存在"""
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
    
    def _validate_region(self, region):
        """验证地区是否存在"""
        setting = self.setting_manager.load()
        regions = setting.get('regions') or []
        if regions is None:
            regions = []
        region_codes = [r.get('code') for r in regions if isinstance(r, dict)]
        return region in region_codes
    
    def _parse_proxy_lines(self, proxy_lines, format_type):
        """解析代理行"""
        from utils.yaml_helper import YAMLHelper
        
        lines = proxy_lines.split('\n')
        parsed_proxies = []
        failed_lines = []
        
        for idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            result = self._parse_proxy_line(line, format_type)
            if result:
                hostname, port, username, password = result
                parsed_proxies.append({
                    'hostname': hostname,
                    'port': port,
                    'username': username,
                    'password': password
                })
            else:
                failed_lines.append(f"第{idx}行: {line}")
        
        return parsed_proxies, failed_lines
    
    def _parse_proxy_line(self, line, format_type):
        """解析单行代理数据"""
        try:
            if format_type == 'format1':  # username:password:hostname:port
                parts = line.split(':')
                if len(parts) == 4:
                    username, password, hostname, port = parts
                    return (hostname.strip(), int(port.strip()), username.strip(), password.strip())
            
            elif format_type == 'format2':  # hostname:port:username:password
                parts = line.split(':')
                if len(parts) == 4:
                    hostname, port, username, password = parts
                    return (hostname.strip(), int(port.strip()), username.strip(), password.strip())
            
            elif format_type == 'format3':  # username:password@hostname:port
                if '@' in line:
                    auth_part, server_part = line.split('@', 1)
                    if ':' in auth_part and ':' in server_part:
                        username, password = auth_part.split(':', 1)
                        hostname, port = server_part.split(':', 1)
                        return (hostname.strip(), int(port.strip()), username.strip(), password.strip())
        except (ValueError, IndexError) as e:
            logger.warning(f"解析代理行失败: {line}, 错误: {str(e)}")
        
        return None
    
    def _update_proxy_name_in_groups(self, config, old_name, new_name):
        """更新策略组中的代理名称引用"""
        try:
            if 'proxy-groups' not in config:
                return
            
            updated_count = 0
            for group in config['proxy-groups']:
                if not isinstance(group, dict):
                    continue
                
                if 'proxies' in group and isinstance(group['proxies'], list):
                    proxies_list = group['proxies']
                    for i, proxy_name in enumerate(proxies_list):
                        if proxy_name == old_name:
                            proxies_list[i] = new_name
                            updated_count += 1
                            logger.info(f"   在策略组 '{group.get('name')}' 中更新引用: '{old_name}' -> '{new_name}'")
            
            if updated_count > 0:
                logger.info(f"   总共更新了 {updated_count} 个策略组引用")
        except Exception as e:
            logger.error(f"更新策略组中的代理名称引用失败: {str(e)}", exc_info=True)
    
    def _update_proxy_groups(self, config):
        """更新策略组"""
        try:
            if 'proxy-groups' not in config:
                return
            
            # 获取所有代理名称
            proxy_names = []
            proxies = config.get('proxies') or []
            if proxies is None:
                proxies = []
            for proxy in proxies:
                if isinstance(proxy, dict) and 'name' in proxy:
                    proxy_names.append(proxy['name'])
            
            # 更新每个策略组
            for group in config['proxy-groups']:
                if not isinstance(group, dict):
                    continue
                
                group_type = group.get('type', '')
                group_name = group.get('name', '')
                
                if group_type == 'select' and group_name != 'PROXY':
                    group['proxies'] = proxy_names.copy()
                    logger.info(f"更新策略组 '{group_name}'")
        except Exception as e:
            logger.error(f"更新策略组失败: {str(e)}", exc_info=True)
    
    def _push_config_to_devices(self, device_id=None):
        """推送配置到设备

        Args:
            device_id: 指定设备ID时只推送该设备；不指定则推送所有已连接设备（兼容旧行为）
        """
        try:
            logs = []
            if not device_id:
                return {'success': False, 'message': 'device_id 是必传参数，未提供 device_id，已取消推送', 'logs': logs}

            devices = self.adb_helper.get_devices()
            device_status_map = {}
            for d in devices or []:
                d_id = d.get('device_id') or d.get('id')
                if d_id:
                    device_status_map[d_id] = d.get('status')

            status = device_status_map.get(device_id)
            if not status:
                logs.append(f"未在 adb devices 中找到设备: {device_id}")
                return {'success': False, 'message': '推送失败：设备不在线', 'logs': logs}
            if status != 'device':
                logs.append(f"设备状态异常: {device_id} -> {status}")
                return {'success': False, 'message': '推送失败：设备不在线', 'logs': logs}

            logs.append('设备在线检查通过')

            config_file_path = self.config_manager.get_config_file(device_id)
            if not os.path.exists(config_file_path):
                logs.append(f"未找到设备配置文件: {config_file_path}")
                return {'success': False, 'message': f'未找到设备配置文件: {config_file_path}', 'logs': logs}

            logs.append('开始推送配置文件到设备')

            success, msg = self.adb_helper.push_file(
                local_path=config_file_path,
                remote_path='/data/adb/box/clash/config.yaml',
                device_id=device_id,
                use_su=True
            )

            logs.append(f"adb push 结果: {msg}")

            if success:
                return {'success': True, 'message': '成功推送到 1 个设备', 'logs': logs}

            lowered = (msg or '').lower()
            if 'offline' in lowered or 'device offline' in lowered:
                return {'success': False, 'message': '推送失败：设备不在线', 'logs': logs}

            return {'success': False, 'message': f'推送失败: {msg}', 'logs': logs}
        except Exception as e:
            logger.error(f"推送配置失败: {str(e)}", exc_info=True)
            return {'success': False, 'message': str(e), 'logs': [str(e)]}
