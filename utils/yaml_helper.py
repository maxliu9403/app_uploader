"""
YAML Helper - YAML 文件处理辅助模块
提供 YAML 文件的加载、保存和清理功能
"""

import os
import yaml
import json
from core.logger import get_logger

logger = get_logger(__name__)


def format_proxy_for_display(proxy):
    """格式化代理配置用于显示"""
    if isinstance(proxy, dict):
        return proxy
    elif isinstance(proxy, str):
        try:
            return json.loads(proxy)
        except:
            return {"raw": proxy}
    return proxy


def is_transit_proxy(proxy_dict):
    """判断代理是否为中转线路（IsBase=true）"""
    if not isinstance(proxy_dict, dict):
        return False
    is_base = proxy_dict.get('IsBase', False)
    return is_base == True or is_base == 'true' or str(is_base).lower() == 'true'


class YAMLHelper:
    """YAML 文件处理辅助类"""
    
    @staticmethod
    def load_yaml_file(file_path):
        """
        加载 YAML 文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 解析后的配置字典
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 清理内容
            cleaned_content = YAMLHelper._clean_yaml_content(content)
            
            # 尝试解析
            try:
                config = yaml.safe_load(cleaned_content)
                return config if config else {}
            except yaml.YAMLError as e:
                logger.error(f"YAML解析失败: {str(e)}")
                # 尝试修复
                fixed_content = YAMLHelper._fix_yaml_content(content)
                config = yaml.safe_load(fixed_content)
                return config if config else {}
                
        except Exception as e:
            logger.error(f"加载YAML文件失败: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def save_yaml_file(file_path, config):
        """
        保存配置到 YAML 文件
        
        ⚠️ 重要：只修改 proxies 和 proxy-groups 两个区域，其他所有内容保持不变
        
        Args:
            file_path: 文件路径
            config: 配置字典
        """
        try:
            # 读取原文件
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在，创建新文件: {file_path}")
                YAMLHelper._write_new_config_file(file_path, config)
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # 生成新的 proxies 内容
            new_proxies_content = YAMLHelper._generate_proxies_section(config)
            
            # 生成新的 proxy-groups 内容
            new_proxy_groups_content = YAMLHelper._generate_proxy_groups_section(config)
            
            # 替换 proxies 部分
            import re
            
            # 匹配 proxies 部分：
            # - 从 "proxies:" 后的换行符开始
            # - 匹配所有内容（包括注释、空行、代理条目）
            # - 直到遇到 "# ====" 开头的注释行（不包括该行）
            proxies_pattern = r'(proxies:\n)((?:.*\n)*?)(?=# ====)'
            original_content = re.sub(
                proxies_pattern,
                f'\\1{new_proxies_content}\n',
                original_content,
                count=1,
                flags=re.MULTILINE
            )
            
            # 替换 proxy-groups 部分：
            # - 从 "proxy-groups:" 后的换行符开始
            # - 匹配所有内容
            # - 直到遇到 "# ====" 开头的注释行（不包括该行）
            proxy_groups_pattern = r'(proxy-groups:\n)((?:.*\n)*?)(?=# ====)'
            original_content = re.sub(
                proxy_groups_pattern,
                f'\\1{new_proxy_groups_content}\n',
                original_content,
                count=1,
                flags=re.MULTILINE
            )
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            logger.info(f"✅ 配置文件保存成功（只修改了 proxies 和 proxy-groups）: {file_path}")
            
        except Exception as e:
            logger.error(f"❌ 保存配置文件失败: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def _generate_proxies_section(config):
        """生成 proxies 部分的内容"""
        lines = []
        proxies = config.get('proxies', [])
        
        # 分类代理
        transit_proxies = [p for p in proxies if is_transit_proxy(p)]
        normal_proxies = [p for p in proxies if not is_transit_proxy(p)]
        
        # 写入中转线路
        if transit_proxies:
            lines.append('  # 1. 中转基座 (Trojan)')
            for proxy in transit_proxies:
                proxy_copy = {k: v for k, v in proxy.items() if k != '_index'}
                proxy_json = json.dumps(proxy_copy, ensure_ascii=False, separators=(',', ':'))
                lines.append(f'  - {proxy_json}')
            lines.append('')
        
        # 写入普通代理
        if normal_proxies:
            # 检测地域
            region = ''
            if normal_proxies:
                first_proxy = normal_proxies[0]
                region = first_proxy.get('Region') or first_proxy.get('region') or 'HK'
            
            region_name = {'HK': '香港', 'GB': '英国', 'SG': '新加坡', 'MY': '马来西亚', 
                           'PH': '菲律宾', 'FR': '法国'}.get(region, region)
            
            lines.append(f'  # 2. {region_name}出口 (绑定中转)')
            for proxy in normal_proxies:
                proxy_copy = {k: v for k, v in proxy.items() if k != '_index'}
                proxy_json = json.dumps(proxy_copy, ensure_ascii=False, separators=(',', ':'))
                lines.append(f'  - {proxy_json}')
            lines.append(' ')
        
        return '\n'.join(lines)
    
    @staticmethod
    def _generate_proxy_groups_section(config):
        """生成 proxy-groups 部分的内容"""
        lines = []
        proxy_groups = config.get('proxy-groups', [])
        
        for group in proxy_groups:
            lines.append(f'  - name: "{group["name"]}"')
            lines.append(f'    type: {group["type"]}')
            if 'proxies' in group:
                lines.append('    proxies:')
                for proxy_name in group['proxies']:
                    lines.append(f'      - "{proxy_name}"')
            lines.append('       ')  # 空行分隔
        
        return '\n'.join(lines)
    
    @staticmethod
    def _write_new_config_file(file_path, config):
        """写入新配置文件（用于文件不存在的情况）"""
        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入基础设置
            YAMLHelper._write_basic_settings(f, config)
            
            # 写入性能优化
            YAMLHelper._write_performance_settings(f, config)
            
            # 写入 DNS 配置
            if 'dns' in config:
                f.write("# ==================== DNS 设置 (防污染) ====================\n")
                YAMLHelper._write_dns_config(f, config['dns'])
            
            # 写入 Tun 配置
            if 'tun' in config:
                f.write("\n# ==================== Tun/TProxy 配合设置 ====================\n")
                YAMLHelper._write_tun_config(f, config['tun'])
            
            # 写入 proxies
            f.write("\n# ==================== 节点列表 ====================\n")
            f.write("proxies:\n")
            f.write(YAMLHelper._generate_proxies_section(config) + '\n')
            
            # 写入 proxy-groups
            if 'proxy-groups' in config:
                f.write("\n# ==================== 策略组 ====================\n")
                f.write("proxy-groups:\n")
                f.write(YAMLHelper._generate_proxy_groups_section(config) + '\n')
            
            # 写入 rules
            if 'rules' in config:
                f.write("\n# ==================== 规则 ====================\n")
                yaml.dump({'rules': config['rules']}, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            # 写入 redir-port
            if 'redir-port' in config:
                f.write(f"redir-port: {config['redir-port']}\n")
    
    @staticmethod
    def _clean_yaml_content(content):
        """
        清理 YAML 内容
        注意：不再移除行尾的 }，因为这是合法的行内字典格式
        """
        # 直接返回原内容，不做任何清理
        # 之前的清理逻辑会破坏行内字典格式，如 { geoip: true, ipcidr: [...] }
        return content
    
    @staticmethod
    def _fix_yaml_content(content):
        """
        修复 YAML 内容（备用方法）
        注意：保持行内字典格式不变
        """
        # 如果标准解析失败，直接返回原内容
        # 不做任何修复，因为可能会破坏合法的格式
        return content
    
    @staticmethod
    def _write_basic_settings(f, config):
        """写入基础设置"""
        basic_keys = ['port', 'socks-port', 'mixed-port', 'tproxy-port', 'allow-lan', 
                     'mode', 'log-level', 'ipv6', 'external-controller', 'secret', 'external-ui']
        
        if any(k in config for k in basic_keys):
            f.write("# ==================== 基础设置 ====================\n")
            for key in basic_keys:
                if key in config:
                    value = config[key]
                    if isinstance(value, str):
                        if value and (' ' in value or ':' in value):
                            f.write(f"{key}: '{value}'\n")
                        else:
                            f.write(f"{key}: {value}\n")
                    else:
                        f.write(f"{key}: {value}\n")
            f.write("\n")
    
    @staticmethod
    def _write_performance_settings(f, config):
        """写入性能优化设置"""
        perf_keys = ['tcp-concurrent', 'global-client-fingerprint', 'keep-alive-interval']
        
        if any(k in config for k in perf_keys):
            f.write("# ==================== 性能优化 ====================\n")
            for key in perf_keys:
                if key in config:
                    value = config[key]
                    if isinstance(value, str):
                        if value and (' ' in value or ':' in value):
                            f.write(f"{key}: '{value}'\n")
                        else:
                            f.write(f"{key}: {value}\n")
                    else:
                        f.write(f"{key}: {value}\n")
            f.write("\n")
    
    @staticmethod
    def _write_dns_config(f, dns_config):
        """写入 DNS 配置（保持行内字典格式）"""
        if not dns_config:
            return
        
        f.write("dns:\n")
        for key, value in dns_config.items():
            if key == 'fallback-filter' and isinstance(value, dict):
                # 保持 fallback-filter 的行内字典格式
                filter_str = "{ "
                filter_items = []
                for k, v in value.items():
                    if isinstance(v, list):
                        v_str = json.dumps(v)
                        filter_items.append(f"{k}: {v_str}")
                    elif isinstance(v, bool):
                        filter_items.append(f"{k}: {str(v).lower()}")
                    else:
                        filter_items.append(f"{k}: {v}")
                filter_str += ", ".join(filter_items) + " }"
                f.write(f"  {key}: {filter_str}\n")
            elif isinstance(value, bool):
                f.write(f"  {key}: {str(value).lower()}\n")
            elif isinstance(value, (int, float)):
                f.write(f"  {key}: {value}\n")
            elif isinstance(value, str):
                if ':' in value or ' ' in value:
                    f.write(f"  {key}: '{value}'\n")
                else:
                    f.write(f"  {key}: {value}\n")
            elif isinstance(value, list):
                f.write(f"  {key}:\n")
                for item in value:
                    if isinstance(item, str):
                        f.write(f"  - {item}\n")
                    else:
                        f.write(f"  - {json.dumps(item, ensure_ascii=False)}\n")
            elif isinstance(value, dict):
                f.write(f"  {key}:\n")
                for k, v in value.items():
                    if isinstance(v, str):
                        f.write(f"    {k}: {v}\n")
                    else:
                        f.write(f"    {k}: {json.dumps(v, ensure_ascii=False)}\n")
        f.write("\n")
    
    @staticmethod
    def _write_tun_config(f, tun_config):
        """写入 Tun 配置"""
        if not tun_config:
            return
        
        f.write("tun:\n")
        for key, value in tun_config.items():
            if isinstance(value, bool):
                f.write(f"  {key}: {str(value).lower()}\n")
            elif isinstance(value, (int, float)):
                f.write(f"  {key}: {value}\n")
            elif isinstance(value, str):
                f.write(f"  {key}: {value}\n")
            elif isinstance(value, list):
                f.write(f"  {key}:\n")
                for item in value:
                    f.write(f"    - {item}\n")
            elif isinstance(value, dict):
                f.write(f"  {key}:\n")
                for k, v in value.items():
                    f.write(f"    {k}: {v}\n")
    
    @staticmethod
    def _write_proxies(f, config):
        """写入 proxies"""
        f.write("\n# ==================== 节点列表 ====================\n")
        f.write("proxies:\n")
        
        proxies = config.get('proxies', [])
        if not proxies:
            f.write(" \n")  # 空代理列表
            return
        
        for proxy in proxies:
            proxy_copy = {k: v for k, v in proxy.items() if k != '_index'}
            proxy_json = json.dumps(proxy_copy, ensure_ascii=False, separators=(',', ':'))
            f.write(f"  - {proxy_json}\n")

