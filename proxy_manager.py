"""
Proxy Manager - 管理 config.yaml 中的 proxies 配置
提供 Web API 和界面用于增删改查
"""

import os
import yaml
import re
import logging
from logging.handlers import RotatingFileHandler
import subprocess
import threading
import queue
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS
from pathlib import Path
from datetime import datetime

# 初始化 logger（稍后会配置）
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 项目配置文件路径（固定）
SETTING_FILE = 'config/setting.yaml'  # 项目配置文件

# 从配置文件读取的路径（动态）
# 使用全局变量缓存，避免重复读取
_cached_config_path = None
_cached_vm_script_path = None
_cached_adb_path = None
_cached_vm_accounts_file_path = None
_cached_vm_model_config_path = None

def setup_logging():
    """配置日志系统（包括控制台和文件输出）"""
    try:
        # 加载配置
        setting = load_setting()
        log_config = setting.get('logging', {})
        
        # 如果日志未启用，只配置控制台输出
        if not log_config.get('enabled', True):
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            logger.info("文件日志未启用，仅输出到控制台")
            return
        
        # 获取配置参数
        log_file = log_config.get('log_file', 'logs/proxy_manager.log')
        log_level_str = log_config.get('log_level', 'INFO')
        max_bytes = log_config.get('max_bytes', 10485760)  # 10MB
        backup_count = log_config.get('backup_count', 7)
        log_format = log_config.get('log_format', '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s')
        date_format = log_config.get('date_format', '%Y-%m-%d %H:%M:%S')
        
        # 转换日志级别
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        # 创建日志目录
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            print(f"创建日志目录: {log_dir}")
        
        # 创建格式化器
        formatter = logging.Formatter(log_format, datefmt=date_format)
        
        # 获取根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # 清除现有的处理器
        root_logger.handlers.clear()
        
        # 1. 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # 2. 文件处理器（带轮转）
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        logger.info("=" * 70)
        logger.info("📝 日志系统配置完成")
        logger.info(f"  - 日志文件: {log_file}")
        logger.info(f"  - 日志级别: {log_level_str}")
        logger.info(f"  - 单文件大小: {max_bytes / 1024 / 1024:.1f} MB")
        logger.info(f"  - 保留文件数: {backup_count}")
        logger.info(f"  - 控制台输出: 已启用")
        logger.info(f"  - 文件输出: 已启用")
        logger.info("=" * 70)
        
    except Exception as e:
        # 如果配置失败，使用基本配置
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logger.error(f"配置日志系统失败，使用默认配置: {str(e)}", exc_info=True)

def get_config_file_path():
    """获取网络配置文件路径"""
    global _cached_config_path
    if _cached_config_path is not None:
        return _cached_config_path
    
    try:
        setting = load_setting()
        config_path = setting.get('config_file_path', 'config.yaml')
        # 如果路径不存在，返回默认值
        if not config_path:
            _cached_config_path = 'config.yaml'
        else:
            _cached_config_path = config_path
        return _cached_config_path
    except:
        _cached_config_path = 'config.yaml'
        return _cached_config_path

def get_vm_script_path():
    """获取VM脚本路径"""
    global _cached_vm_script_path
    if _cached_vm_script_path is not None:
        return _cached_vm_script_path
    
    try:
        setting = load_setting()
        vm_path = setting.get('vm_script_path', 'vm.sh')
        # 如果路径不存在，返回默认值
        if not vm_path:
            _cached_vm_script_path = 'vm.sh'
        else:
            _cached_vm_script_path = vm_path
        return _cached_vm_script_path
    except:
        _cached_vm_script_path = 'vm.sh'
        return _cached_vm_script_path

def get_adb_path():
    """获取ADB可执行文件路径"""
    global _cached_adb_path
    if _cached_adb_path is not None:
        return _cached_adb_path
    
    try:
        setting = load_setting()
        adb_path = setting.get('adb_path', 'adb')
        # 如果路径不存在，返回默认值
        if not adb_path:
            _cached_adb_path = 'adb'
        else:
            _cached_adb_path = adb_path
        return _cached_adb_path
    except:
        _cached_adb_path = 'adb'
        return _cached_adb_path

def get_vm_accounts_file_path():
    """获取多账号动态配置文件路径"""
    global _cached_vm_accounts_file_path
    if _cached_vm_accounts_file_path is not None:
        return _cached_vm_accounts_file_path
    
    try:
        setting = load_setting()
        accounts_path = setting.get('vm_accounts_file_path', 'config/vm_accounts.yaml')
        # 如果路径不存在，返回默认值
        if not accounts_path:
            _cached_vm_accounts_file_path = 'config/vm_accounts.yaml'
        else:
            _cached_vm_accounts_file_path = accounts_path
        return _cached_vm_accounts_file_path
    except:
        _cached_vm_accounts_file_path = 'config/vm_accounts.yaml'
        return _cached_vm_accounts_file_path

def get_vm_model_config_path():
    """获取VM机型配置路径"""
    global _cached_vm_model_config_path
    if _cached_vm_model_config_path is not None:
        return _cached_vm_model_config_path
    
    try:
        setting = load_setting()
        model_path = setting.get('vm_model_config_path', '/data/local/tmp/vm_model_config.yaml')
        # 如果路径不存在，返回默认值
        if not model_path:
            _cached_vm_model_config_path = '/data/local/tmp/vm_model_config.yaml'
        else:
            _cached_vm_model_config_path = model_path
        return _cached_vm_model_config_path
    except:
        _cached_vm_model_config_path = '/data/local/tmp/vm_model_config.yaml'
        return _cached_vm_model_config_path

def clear_path_cache():
    """清除路径缓存（在更新路径配置后调用）"""
    global _cached_config_path, _cached_vm_script_path, _cached_adb_path, _cached_vm_accounts_file_path, _cached_vm_model_config_path
    _cached_config_path = None
    _cached_vm_script_path = None
    _cached_adb_path = None
    _cached_vm_accounts_file_path = None
    _cached_vm_model_config_path = None

def clean_yaml_line(line):
    """清理YAML行，移除末尾的错误字符"""
    # 移除行末的 } 字符（如果存在）
    line = line.rstrip()
    if line.endswith('}'):
        # 检查是否是JSON对象的一部分（proxies中的JSON格式）
        # 如果是proxies行，保留 }，否则移除
        if 'proxies:' in line or line.strip().startswith('- {'):
            return line
        # 移除末尾的 }
        line = line[:-1].rstrip()
    return line

def load_config():
    """加载 YAML 配置文件"""
    try:
        CONFIG_FILE = get_config_file_path()
        logger.info(f"开始加载配置文件: {CONFIG_FILE}")
        
        if not os.path.exists(CONFIG_FILE):
            logger.warning(f"配置文件不存在: {CONFIG_FILE}，将创建空配置")
            return {}
        
        # 读取文件内容
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug(f"文件大小: {len(content)} 字节")
        
        # 清理内容：移除行末的 } 字符（除了proxies中的JSON）
        lines = content.split('\n')
        cleaned_lines = []
        in_proxies_section = False
        
        for i, line in enumerate(lines, 1):
            original_line = line
            
            # 检测是否进入proxies部分
            if 'proxies:' in line:
                in_proxies_section = True
                cleaned_lines.append(line)
                continue
            
            # 如果不在proxies部分，清理行末的 }
            if not in_proxies_section:
                # 检查是否是列表项（以 - 开头）或普通键值对
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and not stripped.startswith('-'):
                    # 这是键值对，移除末尾的 }
                    if line.rstrip().endswith('}') and not line.strip().startswith('-'):
                        cleaned_line = line.rstrip()[:-1].rstrip()
                        if cleaned_line != line.rstrip():
                            logger.debug(f"清理第 {i} 行: 移除末尾的 }}")
                            line = cleaned_line + '\n' if line.endswith('\n') else cleaned_line
            
            cleaned_lines.append(line)
        
        cleaned_content = '\n'.join(cleaned_lines)
        
        # 尝试解析YAML
        try:
            config = yaml.safe_load(cleaned_content)
            if config is None:
                config = {}
            
            # 迁移proxies_dialer到proxies（一次性迁移，添加IsBase=true）
            if 'proxies_dialer' in config and config.get('proxies_dialer'):
                logger.info("检测到proxies_dialer，开始迁移到proxies...")
                if 'proxies' not in config:
                    config['proxies'] = []
                
                migrated_count = 0
                for proxy in config['proxies_dialer']:
                    # 确保代理是字典格式
                    if isinstance(proxy, dict):
                        # 添加IsBase=true标记
                        proxy['IsBase'] = True
                        # 添加到proxies列表的开头（保持中转线路在前面）
                        config['proxies'].insert(0, proxy)
                        migrated_count += 1
                
                # 删除proxies_dialer
                del config['proxies_dialer']
                logger.info(f"成功迁移 {migrated_count} 个中转线路到proxies，已删除proxies_dialer")
                
                # 保存迁移后的配置
                try:
                    save_config(config)
                    logger.info("已保存迁移后的配置文件")
                except Exception as e:
                    logger.warning(f"保存迁移后的配置失败: {str(e)}，将在下次保存时生效")
            
            logger.info(f"配置文件加载成功，包含 {len(config.get('proxies', []))} 个代理")
            return config
        except yaml.YAMLError as e:
            logger.error(f"YAML解析失败: {str(e)}")
            logger.error(f"错误位置: {getattr(e, 'problem_mark', '未知')}")
            
            # 尝试更激进的清理
            logger.info("尝试修复YAML格式...")
            # 移除所有行末的 }（除了proxies中的JSON对象）
            fixed_lines = []
            in_proxies = False
            for line in lines:
                if 'proxies:' in line:
                    in_proxies = True
                    fixed_lines.append(line)
                elif in_proxies and line.strip().startswith('- {'):
                    # proxies中的JSON格式，保留
                    fixed_lines.append(line)
                elif not in_proxies and line.rstrip().endswith('}') and ':' in line:
                    # 键值对行末的 }，移除
                    fixed_lines.append(line.rstrip()[:-1])
                else:
                    fixed_lines.append(line)
            
            fixed_content = '\n'.join(fixed_lines)
            try:
                config = yaml.safe_load(fixed_content)
                if config is None:
                    config = {}
                logger.info("YAML格式修复成功")
                
                # 迁移proxies_dialer到proxies（一次性迁移，添加IsBase=true）
                if 'proxies_dialer' in config and config.get('proxies_dialer'):
                    logger.info("检测到proxies_dialer，开始迁移到proxies...")
                    if 'proxies' not in config:
                        config['proxies'] = []
                    
                    migrated_count = 0
                    for proxy in config['proxies_dialer']:
                        # 确保代理是字典格式
                        if isinstance(proxy, dict):
                            # 添加IsBase=true标记
                            proxy['IsBase'] = True
                            # 添加到proxies列表的开头（保持中转线路在前面）
                            config['proxies'].insert(0, proxy)
                            migrated_count += 1
                    
                    # 删除proxies_dialer
                    del config['proxies_dialer']
                    logger.info(f"成功迁移 {migrated_count} 个中转线路到proxies，已删除proxies_dialer")
                
                # 保存修复和迁移后的内容
                try:
                    save_config(config)
                    logger.info("已保存修复和迁移后的配置文件")
                except Exception as e:
                    logger.warning(f"保存修复和迁移后的配置失败: {str(e)}")
                    # 如果save_config失败，至少保存修复后的内容
                    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    logger.info("已保存修复后的配置文件（未迁移）")
                return config
            except yaml.YAMLError as e2:
                logger.error(f"修复后仍然解析失败: {str(e2)}")
                raise Exception(f"YAML解析失败: {str(e)}。修复尝试也失败: {str(e2)}")
                
    except FileNotFoundError:
        logger.warning(f"配置文件不存在: {CONFIG_FILE}")
        return {}
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}", exc_info=True)
        raise Exception(f"加载配置文件失败: {str(e)}")

def save_config(config):
    """保存配置到 YAML 文件"""
    try:
        logger.info("开始保存配置文件...")
        
        # 读取原始文件以保留其他配置
        CONFIG_FILE = get_config_file_path()
        original_config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    original_config = yaml.safe_load(f) or {}
                logger.debug(f"读取到原始配置，包含 {len(original_config.get('proxies', []))} 个代理")
            except Exception as e:
                logger.warning(f"读取原始配置失败: {str(e)}，将使用新配置")
                pass
        
        # 合并配置：保留原始配置的其他部分，只更新 proxies
        if original_config:
            for key in original_config:
                if key not in ['proxies'] and key not in config:
                    config[key] = original_config[key]
        
        # 保存配置，proxies 使用 JSON 格式（保持原始格式风格）
        CONFIG_FILE = get_config_file_path()
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            # 写入基础设置部分
            if any(k in config for k in ['port', 'socks-port', 'mixed-port', 'tproxy-port', 
                                         'allow-lan', 'mode', 'log-level', 'ipv6', 
                                         'external-controller', 'secret', 'external-ui']):
                f.write("# ==================== 基础设置 ====================\n")
                for key in ['port', 'socks-port', 'mixed-port', 'tproxy-port', 'allow-lan', 
                           'mode', 'log-level', 'ipv6', 'external-controller', 'secret', 'external-ui']:
                    if key in config:
                        value = config[key]
                        # 直接写入值（简单类型）
                        if isinstance(value, str):
                            # 字符串需要加引号（如果包含特殊字符）
                            if value and (' ' in value or ':' in value):
                                f.write(f"{key}: '{value}'\n")
                            else:
                                f.write(f"{key}: {value}\n")
                        else:
                            f.write(f"{key}: {value}\n")
                f.write("\n")
            
            # 写入性能优化部分
            perf_keys = ['tcp-concurrent', 'global-client-fingerprint', 'keep-alive-interval']
            if any(k in config for k in perf_keys):
                f.write("# ==================== 性能优化 ====================\n")
                for key in perf_keys:
                    if key in config:
                        value = config[key]
                        # 直接写入值（简单类型）
                        if isinstance(value, str):
                            # 字符串需要加引号（如果包含特殊字符）
                            if value and (' ' in value or ':' in value):
                                f.write(f"{key}: '{value}'\n")
                            else:
                                f.write(f"{key}: {value}\n")
                        else:
                            f.write(f"{key}: {value}\n")
                f.write("\n")
            
            # 写入 DNS 配置
            if 'dns' in config:
                f.write("# ==================== DNS 设置 (DoH 防劫持版) ====================\n")
                yaml.dump({'dns': config['dns']}, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            # 写入 Tun 配置
            if 'tun' in config:
                f.write("\n# ==================== Tun 模式 (Gvisor + 198.18) ====================\n")
                yaml.dump({'tun': config['tun']}, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            # 写入 proxies（包含普通代理和中转线路，使用 JSON 格式保持原始风格）
            f.write("\n# ==================== 节点列表 ====================\n")
            f.write("proxies:\n")
            import json
            for proxy in config.get('proxies', []):
                # 创建副本，移除内部使用的 _index 字段
                proxy_copy = {k: v for k, v in proxy.items() if k != '_index'}
                proxy_json = json.dumps(proxy_copy, ensure_ascii=False, separators=(',', ':'))
                f.write(f"  - {proxy_json}\n")
            
            # 写入 proxy-groups
            if 'proxy-groups' in config:
                f.write("\n# ==================== 策略组 ====================\n")
                yaml.dump({'proxy-groups': config['proxy-groups']}, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            # 写入 rules
            if 'rules' in config:
                f.write("\n# ==================== 规则 ====================\n")
                yaml.dump({'rules': config['rules']}, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            # 写入 redir-port
            if 'redir-port' in config:
                f.write(f"redir-port: {config['redir-port']}\n")
        
        # 统计中转线路和普通代理数量
        all_proxies = config.get('proxies', [])
        transit_count = sum(1 for p in all_proxies if is_transit_proxy(format_proxy_for_display(p)))
        proxy_count = len(all_proxies) - transit_count
        logger.info(f"配置文件保存成功，包含 {transit_count} 个中转线路，{proxy_count} 个普通代理")
        return True
    except Exception as e:
        logger.error(f"保存配置文件失败: {str(e)}", exc_info=True)
        raise Exception(f"保存配置文件失败: {str(e)}")

def format_proxy_for_display(proxy):
    """格式化代理配置用于显示"""
    if isinstance(proxy, dict):
        return proxy
    elif isinstance(proxy, str):
        # 如果是字符串，尝试解析 JSON
        import json
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
    # 判断IsBase是否为true（支持布尔值和字符串）
    return is_base == True or is_base == 'true' or str(is_base).lower() == 'true'

def check_proxy_name_exists(config, name, exclude_index=None):
    """
    检查代理名称是否已存在（在proxies列表中）
    
    Args:
        config: 配置字典
        name: 要检查的名称
        exclude_index: 排除的索引（更新时使用，排除自己）
    
    Returns:
        tuple: (是否存在, 冲突位置描述)
    """
    if not name:
        return False, None
    
    # 检查所有代理（包括普通代理和中转线路，都在proxies列表中）
    proxies = config.get('proxies', [])
    for idx, proxy in enumerate(proxies):
        if exclude_index is not None and idx == exclude_index:
            continue
        formatted = format_proxy_for_display(proxy)
        if formatted.get('name') == name:
            is_base_value = is_transit_proxy(formatted)
            proxy_type_desc = '中转线路' if is_base_value else '普通代理'
            return True, f'代理列表中的第 {idx} 个{proxy_type_desc}'
    
    return False, None

@app.route('/')
def index():
    """主页面"""
    return render_template('proxy_manager.html')

@app.route('/api/proxies', methods=['GET'])
def get_proxies():
    """获取所有普通代理（从proxies读取，排除IsBase=true的中转线路）"""
    try:
        logger.info("收到获取代理列表请求")
        config = load_config()
        all_proxies = config.get('proxies', [])
        
        # 过滤出普通代理（IsBase != true）
        proxies = []
        for proxy in all_proxies:
            formatted = format_proxy_for_display(proxy)
            # 只包含非中转线路的代理
            if not is_transit_proxy(formatted):
                proxies.append(proxy)
        
        logger.debug(f"找到 {len(proxies)} 个普通代理（总共有 {len(all_proxies)} 个代理）")
        
        # 格式化代理列表（需要重新计算索引，基于过滤后的列表）
        formatted_proxies = []
        proxy_idx = 0
        for idx, proxy in enumerate(all_proxies):
            formatted = format_proxy_for_display(proxy)
            if not is_transit_proxy(formatted):
                formatted['_index'] = idx  # 使用原始索引（在proxies列表中的位置）
                formatted_proxies.append(formatted)
                proxy_idx += 1
        
        logger.info(f"成功返回 {len(formatted_proxies)} 个普通代理")
        return jsonify({
            'success': True,
            'data': formatted_proxies
        })
    except Exception as e:
        logger.error(f"获取代理列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def parse_proxy_line(line, format_type):
    """
    解析代理行数据，支持3种格式：
    1. username:password:hostname:port
    2. hostname:port:username:password
    3. username:password@hostname:port
    
    返回: (hostname, port, username, password) 或 None（解析失败）
    """
    line = line.strip()
    if not line:
        return None
    
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
    
    return None

def generate_proxy_name(prefix):
    """
    生成代理名称（前缀 + 自增数）
    例如: UK_001, UK_002, ...
    """
    setting = load_setting()
    
    # 获取或初始化计数器
    if 'proxy_name_counters' not in setting:
        setting['proxy_name_counters'] = {}
    
    counters = setting['proxy_name_counters']
    current_count = counters.get(prefix, 0)
    next_count = current_count + 1
    
    # 格式化为3位数字（001, 002, ...）
    proxy_name = f"{prefix}_{next_count:03d}"
    
    return proxy_name, next_count

def increment_proxy_name_counter(prefix, count):
    """
    更新代理名称计数器
    """
    setting = load_setting()
    
    if 'proxy_name_counters' not in setting:
        setting['proxy_name_counters'] = {}
    
    setting['proxy_name_counters'][prefix] = count
    save_setting(setting)
    logger.info(f"更新代理名称计数器: {prefix} = {count}")

@app.route('/api/proxies', methods=['POST'])
def add_proxy():
    """添加新的 proxy"""
    try:
        data = request.json
        logger.info(f"收到添加代理请求: {data.get('name', '未知')}")
        logger.debug(f"请求数据: {data}")
        
        config = load_config()
        
        if 'proxies' not in config:
            config['proxies'] = []
            logger.debug("初始化proxies列表")
        
        # 检查名称是否已存在（在proxies列表中检查）
        proxy_name = data.get('name', '').strip()
        if proxy_name:
            exists, location = check_proxy_name_exists(config, proxy_name)
            if exists:
                logger.warning(f"代理名称 '{proxy_name}' 已存在于 {location}")
                return jsonify({
                    'success': False,
                    'error': f'代理名称 "{proxy_name}" 已存在（{location}），请使用其他名称'
                }), 400
        
        # 检查 region 是否提供
        region = data.get('region', '').strip().upper()
        if not region:
            logger.warning("创建代理时未提供 region 参数")
            return jsonify({
                'success': False,
                'error': 'region 是必填项，请选择地区'
            }), 400
        
        # 验证 region 是否在配置的地区列表中
        regions = get_regions()
        region_codes = [r.get('code') for r in regions]
        if region not in region_codes:
            logger.warning(f"region '{region}' 不在配置的地区列表中")
            return jsonify({
                'success': False,
                'error': f'地区代码 "{region}" 不存在，请先在地区管理中添加该地区'
            }), 400
        
        # 检查用户名和密码是否提供（必填）
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        if not username:
            logger.warning("创建代理时未提供 username 参数")
            return jsonify({
                'success': False,
                'error': '用户名是必填项，请填写用户名'
            }), 400
        if not password:
            logger.warning("创建代理时未提供 password 参数")
            return jsonify({
                'success': False,
                'error': '密码是必填项，请填写密码'
            }), 400
        
        # 构建新的 proxy 配置
        port = data.get('port', '')
        # 将port转换为int类型
        try:
            port = int(port) if port else ''
        except (ValueError, TypeError):
            logger.warning(f"port值 '{port}' 无法转换为整数，保持原值")
        
        new_proxy = {
            'name': proxy_name,
            'type': data.get('type', 'socks5'),
            'server': data.get('server', ''),
            'port': port,
            'region': region,  # 添加 region 字段
        }
        
        logger.debug(f"基础配置: {new_proxy}")
        
        # 添加必填参数（用户名和密码）
        new_proxy['username'] = username
        new_proxy['password'] = password
        
        # 添加可选参数
        if 'sni' in data:
            new_proxy['sni'] = data['sni']
        if 'skip-cert-verify' in data:
            new_proxy['skip-cert-verify'] = data['skip-cert-verify']
        elif 'skip-cert-verify' not in new_proxy:
            new_proxy['skip-cert-verify'] = True  # 默认值
        # UDP 默认值为 true
        if 'udp' in data:
            new_proxy['udp'] = data['udp']
        else:
            new_proxy['udp'] = True  # 默认值
        # 如果指定了中转线路，添加dialer-proxy字段
        if 'dialer-proxy' in data and data['dialer-proxy']:
            new_proxy['dialer-proxy'] = data['dialer-proxy']
        
        # 添加其他自定义参数
        for key, value in data.items():
            if key not in ['name', 'type', 'server', 'port', 'password', 'username', 'sni', 'skip-cert-verify', 'udp', 'dialer-proxy', 'region']:
                if value:  # 只添加非空值
                    new_proxy[key] = value
        
        logger.debug(f"完整代理配置: {new_proxy}")
        
        # 普通代理添加到proxies列表
        config['proxies'].append(new_proxy)
        logger.info(f"添加代理到列表，当前共有 {len(config['proxies'])} 个普通代理")
        
        # 更新 proxy-groups
        update_proxy_groups(config)
        
        save_config(config)
        
        logger.info(f"代理 '{new_proxy['name']}' 添加成功")
        
        # 推送配置到设备
        push_success, push_msg = push_config_to_devices()
        
        return jsonify({
            'success': True,
            'message': '代理添加成功',
            'data': new_proxy,
            'push_result': {
                'success': push_success,
                'message': push_msg
            }
        })
    except Exception as e:
        logger.error(f"添加代理失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxies/batch', methods=['POST'])
def add_proxies_batch():
    """批量添加代理"""
    try:
        data = request.json
        logger.info(f"收到批量添加代理请求")
        logger.debug(f"请求数据: {data}")
        
        # 验证必填参数
        proxy_lines = data.get('proxy_lines', '').strip()
        format_type = data.get('format_type', '').strip()
        region = data.get('region', '').strip().upper()
        name_prefix = data.get('name_prefix', '').strip()
        dialer_proxy = data.get('dialer_proxy', '').strip()
        
        if not proxy_lines:
            return jsonify({
                'success': False,
                'error': '代理数据不能为空'
            }), 400
        
        if not format_type or format_type not in ['format1', 'format2', 'format3']:
            return jsonify({
                'success': False,
                'error': '请选择数据格式'
            }), 400
        
        if not region:
            return jsonify({
                'success': False,
                'error': 'region 是必填项，请选择地区'
            }), 400
        
        if not name_prefix:
            return jsonify({
                'success': False,
                'error': '代理名称前缀不能为空'
            }), 400
        
        # 验证 region 是否在配置的地区列表中
        regions = get_regions()
        region_codes = [r.get('code') for r in regions]
        if region not in region_codes:
            return jsonify({
                'success': False,
                'error': f'地区代码 "{region}" 不存在，请先在地区管理中添加该地区'
            }), 400
        
        # 解析代理行
        lines = proxy_lines.split('\n')
        parsed_proxies = []
        failed_lines = []
        
        for idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            result = parse_proxy_line(line, format_type)
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
        
        if not parsed_proxies:
            return jsonify({
                'success': False,
                'error': f'没有成功解析任何代理。失败的行:\n' + '\n'.join(failed_lines[:5])
            }), 400
        
        logger.info(f"成功解析 {len(parsed_proxies)} 个代理，失败 {len(failed_lines)} 个")
        
        # 加载配置
        config = load_config()
        if 'proxies' not in config:
            config['proxies'] = []
        
        # 批量添加代理
        added_proxies = []
        
        # 获取初始计数器（只读取一次）
        setting = load_setting()
        if 'proxy_name_counters' not in setting:
            setting['proxy_name_counters'] = {}
        current_counter = setting['proxy_name_counters'].get(name_prefix, 0)
        
        for proxy_data in parsed_proxies:
            # 递增计数器并生成代理名称
            current_counter += 1
            proxy_name = f"{name_prefix}_{current_counter:03d}"
            
            # 检查名称是否已存在
            exists, location = check_proxy_name_exists(config, proxy_name)
            if exists:
                logger.warning(f"代理名称 '{proxy_name}' 已存在，跳过")
                # 注意：即使跳过，计数器也已经递增，避免重复尝试相同名称
                continue
            
            # 构建代理配置
            new_proxy = {
                'name': proxy_name,
                'type': 'socks5',  # 默认使用 socks5
                'server': proxy_data['hostname'],
                'port': proxy_data['port'],
                'region': region,
                'username': proxy_data['username'],
                'password': proxy_data['password'],
                'skip-cert-verify': True,
                'udp': True,
            }
            
            # 如果指定了中转线路
            if dialer_proxy:
                new_proxy['dialer-proxy'] = dialer_proxy
            
            config['proxies'].append(new_proxy)
            added_proxies.append(proxy_name)
            logger.debug(f"添加代理: {proxy_name}")
        
        if not added_proxies:
            return jsonify({
                'success': False,
                'error': '所有代理名称都已存在，没有添加任何代理'
            }), 400
        
        # 更新计数器（保存最终的计数值）
        increment_proxy_name_counter(name_prefix, current_counter)
        
        # 更新 proxy-groups
        update_proxy_groups(config)
        
        # 保存配置
        save_config(config)
        
        result_message = f'成功添加 {len(added_proxies)} 个代理'
        if failed_lines:
            result_message += f'，{len(failed_lines)} 行解析失败'
        
        logger.info(result_message)
        
        # 推送配置到设备
        push_success, push_msg = push_config_to_devices()
        
        return jsonify({
            'success': True,
            'message': result_message,
            'data': {
                'added_count': len(added_proxies),
                'failed_count': len(failed_lines),
                'added_names': added_proxies,
                'failed_lines': failed_lines[:10]  # 最多返回前10个失败的行
            },
            'push_result': {
                'success': push_success,
                'message': push_msg
            }
        })
        
    except Exception as e:
        logger.error(f"批量添加代理失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxies/<int:index>', methods=['PUT'])
def update_proxy(index):
    """更新指定索引的 proxy"""
    try:
        data = request.json
        logger.info(f"收到更新代理请求: 索引={index}, 名称={data.get('name', '未知')}")
        logger.debug(f"请求数据: {data}")
        
        config = load_config()
        
        if 'proxies' not in config or index < 0 or index >= len(config['proxies']):
            logger.error(f"索引超出范围: {index}, 当前普通代理数量: {len(config.get('proxies', []))}")
            return jsonify({
                'success': False,
                'error': '索引超出范围'
            }), 400
        
        # 检查名称是否已存在（排除当前代理）
        proxy_name = data.get('name', '').strip()
        if proxy_name:
            exists, location = check_proxy_name_exists(config, proxy_name, exclude_index=index)
            if exists:
                logger.warning(f"代理名称 '{proxy_name}' 已存在于 {location}")
                return jsonify({
                    'success': False,
                    'error': f'代理名称 "{proxy_name}" 已存在（{location}），请使用其他名称'
                }), 400
        
        # 检查 region 是否提供
        region = data.get('region', '').strip().upper()
        if not region:
            logger.warning("更新代理时未提供 region 参数")
            return jsonify({
                'success': False,
                'error': 'region 是必填项，请选择地区'
            }), 400
        
        # 验证 region 是否在配置的地区列表中
        regions = get_regions()
        region_codes = [r.get('code') for r in regions]
        if region not in region_codes:
            logger.warning(f"region '{region}' 不在配置的地区列表中")
            return jsonify({
                'success': False,
                'error': f'地区代码 "{region}" 不存在，请先在地区管理中添加该地区'
            }), 400
        
        # 先获取旧代理配置，以便保留未修改的字段
        old_proxy = config['proxies'][index]
        
        # 构建更新的 proxy 配置
        port = data.get('port', '')
        # 将port转换为int类型
        try:
            port = int(port) if port else ''
        except (ValueError, TypeError):
            logger.warning(f"port值 '{port}' 无法转换为整数，保持原值")
        
        updated_proxy = {
            'name': proxy_name,
            'type': data.get('type', 'socks5'),
            'server': data.get('server', ''),
            'port': port,
            'region': region,  # 添加 region 字段
        }
        
        # 添加可选参数
        if 'password' in data:
            updated_proxy['password'] = data['password']
        if 'username' in data:
            updated_proxy['username'] = data['username']
        if 'sni' in data:
            updated_proxy['sni'] = data['sni']
        if 'skip-cert-verify' in data:
            updated_proxy['skip-cert-verify'] = data['skip-cert-verify']
        elif 'skip-cert-verify' not in updated_proxy:
            updated_proxy['skip-cert-verify'] = True  # 默认值
        if 'udp' in data:
            updated_proxy['udp'] = data['udp']
        
        # 处理dialer-proxy字段：如果明确提供了（包括空字符串），则设置；否则保留原值
        if 'dialer-proxy' in data:
            # 如果提供了空字符串或None，删除dialer-proxy字段
            if not data['dialer-proxy']:
                # 不添加dialer-proxy字段（表示不使用中转）
                pass
            else:
                updated_proxy['dialer-proxy'] = data['dialer-proxy']
        else:
            # 如果没有提供dialer-proxy字段，保留原代理的dialer-proxy值
            if 'dialer-proxy' in old_proxy:
                updated_proxy['dialer-proxy'] = old_proxy['dialer-proxy']
        
        # 添加其他自定义参数
        for key, value in data.items():
            if key not in ['name', 'type', 'server', 'port', 'password', 'username', 'sni', 'skip-cert-verify', 'udp', 'dialer-proxy', 'region']:
                if value:  # 只添加非空值
                    updated_proxy[key] = value
        
        logger.debug(f"旧配置: {old_proxy}")
        logger.debug(f"新配置: {updated_proxy}")
        
        config['proxies'][index] = updated_proxy
        
        # 更新 proxy-groups（确保列表包含所有当前代理的 name）
        update_proxy_groups(config)
        
        save_config(config)
        
        logger.info(f"代理 '{updated_proxy['name']}' (索引 {index}) 更新成功")
        
        # 推送配置到设备
        push_success, push_msg = push_config_to_devices()
        
        return jsonify({
            'success': True,
            'message': '代理更新成功',
            'data': updated_proxy,
            'push_result': {
                'success': push_success,
                'message': push_msg
            }
        })
    except Exception as e:
        logger.error(f"更新代理失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxies/<int:index>', methods=['DELETE'])
def delete_proxy(index):
    """删除指定索引的 proxy"""
    try:
        logger.info(f"收到删除代理请求: 索引={index}")
        
        config = load_config()
        
        if 'proxies' not in config or index < 0 or index >= len(config['proxies']):
            logger.error(f"索引超出范围: {index}, 当前普通代理数量: {len(config.get('proxies', []))}")
            return jsonify({
                'success': False,
                'error': '索引超出范围'
            }), 400
        
        deleted_proxy = config['proxies'][index]
        logger.debug(f"准备删除代理: {deleted_proxy}")
        
        config['proxies'].pop(index)
        logger.info(f"从列表中删除代理，剩余 {len(config['proxies'])} 个普通代理")
        
        # 更新 proxy-groups
        update_proxy_groups(config)
        
        save_config(config)
        
        logger.info(f"代理 '{deleted_proxy.get('name', '未知')}' (索引 {index}) 删除成功")
        
        # 推送配置到设备
        push_success, push_msg = push_config_to_devices()
        
        return jsonify({
            'success': True,
            'message': '代理删除成功',
            'data': deleted_proxy,
            'push_result': {
                'success': push_success,
                'message': push_msg
            }
        })
    except Exception as e:
        logger.error(f"删除代理失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_transit_proxies(config):
    """获取中转线路列表（从proxies中筛选IsBase=true的）"""
    all_proxies = config.get('proxies', [])
    transit_proxies = []
    for idx, proxy in enumerate(all_proxies):
        formatted = format_proxy_for_display(proxy)
        # 只包含IsBase=true的代理（中转线路）
        if is_transit_proxy(formatted):
            formatted['_index'] = idx  # 使用原始索引（在proxies列表中的位置）
            transit_proxies.append(formatted)
    return transit_proxies

@app.route('/api/transit-proxies', methods=['GET'])
def get_transit_proxies_api():
    """获取所有中转线路"""
    try:
        logger.info("收到获取中转线路列表请求")
        config = load_config()
        transit_proxies = get_transit_proxies(config)
        
        logger.debug(f"找到 {len(transit_proxies)} 个中转线路")
        logger.info(f"成功返回 {len(transit_proxies)} 个中转线路")
        return jsonify({
            'success': True,
            'data': transit_proxies
        })
    except Exception as e:
        logger.error(f"获取中转线路列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/transit-proxies/names', methods=['GET'])
def get_transit_proxy_names():
    """获取中转线路名称列表（用于下拉选择）"""
    try:
        logger.debug("收到获取中转线路名称列表请求")
        config = load_config()
        transit_proxies = get_transit_proxies(config)
        names = [proxy.get('name', '') for proxy in transit_proxies if proxy.get('name')]
        logger.debug(f"返回 {len(names)} 个中转线路名称")
        return jsonify({
            'success': True,
            'data': names
        })
    except Exception as e:
        logger.error(f"获取中转线路名称列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/transit-proxies', methods=['POST'])
def add_transit_proxy():
    """添加新的中转线路（添加到proxies中，IsBase=true）"""
    try:
        data = request.json
        logger.info(f"收到添加中转线路请求: {data.get('name', '未知')}")
        logger.debug(f"请求数据: {data}")
        
        config = load_config()
        
        if 'proxies' not in config:
            config['proxies'] = []
            logger.debug("初始化proxies列表")
        
        # 检查名称是否已存在
        proxy_name = data.get('name', '').strip()
        if proxy_name:
            exists, location = check_proxy_name_exists(config, proxy_name)
            if exists:
                logger.warning(f"中转线路名称 '{proxy_name}' 已存在于 {location}")
                return jsonify({
                    'success': False,
                    'error': f'中转线路名称 "{proxy_name}" 已存在（{location}），请使用其他名称'
                }), 400
        
        # 构建新的中转线路配置（确保没有dialer-proxy字段，添加IsBase=true）
        port = data.get('port', '')
        # 将port转换为int类型
        try:
            port = int(port) if port else ''
        except (ValueError, TypeError):
            logger.warning(f"port值 '{port}' 无法转换为整数，保持原值")
        
        new_proxy = {
            'name': proxy_name,
            'type': data.get('type', 'socks5'),
            'server': data.get('server', ''),
            'port': port,
            'IsBase': True,  # 标记为中转线路
        }
        
        logger.debug(f"基础配置: {new_proxy}")
        
        # 添加可选参数（但不包括dialer-proxy）
        if 'password' in data:
            new_proxy['password'] = data['password']
        if 'username' in data:
            new_proxy['username'] = data['username']
        if 'sni' in data:
            new_proxy['sni'] = data['sni']
        if 'skip-cert-verify' in data:
            new_proxy['skip-cert-verify'] = data['skip-cert-verify']
        elif 'skip-cert-verify' not in new_proxy:
            new_proxy['skip-cert-verify'] = True  # 默认值
        if 'udp' in data:
            new_proxy['udp'] = data['udp']
        
        # 明确不添加dialer-proxy字段（中转线路不能有dialer-proxy）
        # 添加其他自定义参数
        for key, value in data.items():
            if key not in ['name', 'type', 'server', 'port', 'password', 'username', 'sni', 
                          'skip-cert-verify', 'udp', 'dialer-proxy', 'IsBase']:
                if value:  # 只添加非空值
                    new_proxy[key] = value
        
        logger.debug(f"完整中转线路配置: {new_proxy}")
        
        # 添加到proxies列表
        config['proxies'].append(new_proxy)
        transit_count = len([p for p in config['proxies'] if format_proxy_for_display(p).get('IsBase') == True])
        logger.info(f"添加中转线路到列表，当前共有 {transit_count} 个中转线路")
        
        # 同步更新 proxy-groups（使用统一的更新函数）
        update_proxy_groups(config)
        
        save_config(config)
        
        logger.info(f"中转线路 '{new_proxy['name']}' 添加成功")
        
        # 推送配置到设备
        push_success, push_msg = push_config_to_devices()
        
        return jsonify({
            'success': True,
            'message': '中转线路添加成功',
            'data': new_proxy,
            'push_result': {
                'success': push_success,
                'message': push_msg
            }
        })
    except Exception as e:
        logger.error(f"添加中转线路失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/transit-proxies/<int:index>', methods=['PUT'])
def update_transit_proxy(index):
    """更新指定索引的中转线路（在proxies中）"""
    try:
        data = request.json
        logger.info(f"收到更新中转线路请求: 索引={index}, 名称={data.get('name', '未知')}")
        logger.debug(f"请求数据: {data}")
        
        config = load_config()
        
        # 获取所有中转线路，找到对应的原始索引
        transit_proxies = get_transit_proxies(config)
        if index < 0 or index >= len(transit_proxies):
            logger.error(f"索引超出范围: {index}, 当前中转线路数量: {len(transit_proxies)}")
            return jsonify({
                'success': False,
                'error': '索引超出范围'
            }), 400
        
        # 获取原始索引（在proxies列表中的位置）
        original_index = transit_proxies[index]['_index']
        
        # 检查名称是否已存在（排除当前中转线路）
        proxy_name = data.get('name', '').strip()
        if proxy_name:
            exists, location = check_proxy_name_exists(config, proxy_name, exclude_index=original_index)
            if exists:
                logger.warning(f"中转线路名称 '{proxy_name}' 已存在于 {location}")
                return jsonify({
                    'success': False,
                    'error': f'中转线路名称 "{proxy_name}" 已存在（{location}），请使用其他名称'
                }), 400
        
        # 构建更新的中转线路配置（确保没有dialer-proxy字段，保留IsBase=true）
        port = data.get('port', '')
        # 将port转换为int类型
        try:
            port = int(port) if port else ''
        except (ValueError, TypeError):
            logger.warning(f"port值 '{port}' 无法转换为整数，保持原值")
        
        updated_proxy = {
            'name': proxy_name,
            'type': data.get('type', 'socks5'),
            'server': data.get('server', ''),
            'port': port,
            'IsBase': True,  # 保持中转线路标记
        }
        
        # 添加可选参数（但不包括dialer-proxy）
        if 'password' in data:
            updated_proxy['password'] = data['password']
        if 'username' in data:
            updated_proxy['username'] = data['username']
        if 'sni' in data:
            updated_proxy['sni'] = data['sni']
        if 'skip-cert-verify' in data:
            updated_proxy['skip-cert-verify'] = data['skip-cert-verify']
        elif 'skip-cert-verify' not in updated_proxy:
            updated_proxy['skip-cert-verify'] = True  # 默认值
        if 'udp' in data:
            updated_proxy['udp'] = data['udp']
        
        # 明确不添加dialer-proxy字段
        # 添加其他自定义参数（但不包括IsBase，因为它已经设置了）
        for key, value in data.items():
            if key not in ['name', 'type', 'server', 'port', 'password', 'username', 'sni', 
                          'skip-cert-verify', 'udp', 'dialer-proxy', 'IsBase']:
                if value:  # 只添加非空值
                    updated_proxy[key] = value
        
        old_proxy = config['proxies'][original_index]
        logger.debug(f"旧配置: {old_proxy}")
        logger.debug(f"新配置: {updated_proxy}")
        
        config['proxies'][original_index] = updated_proxy
        
        # 同步更新 proxy-groups（使用统一的更新函数）
        update_proxy_groups(config)
        
        save_config(config)
        
        logger.info(f"中转线路 '{updated_proxy['name']}' (索引 {index}, 原始索引 {original_index}) 更新成功")
        
        # 推送配置到设备
        push_success, push_msg = push_config_to_devices()
        
        return jsonify({
            'success': True,
            'message': '中转线路更新成功',
            'data': updated_proxy,
            'push_result': {
                'success': push_success,
                'message': push_msg
            }
        })
    except Exception as e:
        logger.error(f"更新中转线路失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/transit-proxies/<int:index>', methods=['DELETE'])
def delete_transit_proxy(index):
    """删除指定索引的中转线路（从proxies中）"""
    try:
        logger.info(f"收到删除中转线路请求: 索引={index}")
        
        config = load_config()
        
        # 获取所有中转线路，找到对应的原始索引
        transit_proxies = get_transit_proxies(config)
        if index < 0 or index >= len(transit_proxies):
            logger.error(f"索引超出范围: {index}, 当前中转线路数量: {len(transit_proxies)}")
            return jsonify({
                'success': False,
                'error': '索引超出范围'
            }), 400
        
        # 获取原始索引（在proxies列表中的位置）
        original_index = transit_proxies[index]['_index']
        deleted_proxy = config['proxies'][original_index]
        logger.debug(f"准备删除中转线路: {deleted_proxy}")
        
        # 检查是否有其他代理使用这个中转线路
        proxy_name = format_proxy_for_display(deleted_proxy).get('name', '')
        if proxy_name:
            used_by = []
            for idx, proxy in enumerate(config.get('proxies', [])):
                formatted = format_proxy_for_display(proxy)
                # 只检查普通代理（非中转线路）
                if not is_transit_proxy(formatted) and formatted.get('dialer-proxy') == proxy_name:
                    used_by.append(formatted.get('name', f'代理#{idx}'))
            
            if used_by:
                logger.warning(f"中转线路 '{proxy_name}' 被以下代理使用: {used_by}")
                return jsonify({
                    'success': False,
                    'error': f'无法删除：该中转线路正被以下代理使用: {", ".join(used_by)}'
                }), 400
        
        config['proxies'].pop(original_index)
        transit_count = len([p for p in config['proxies'] if format_proxy_for_display(p).get('IsBase') == True])
        logger.info(f"从列表中删除中转线路，剩余 {transit_count} 个中转线路")
        
        # 同步更新 proxy-groups（使用统一的更新函数）
        update_proxy_groups(config)
        
        save_config(config)
        
        logger.info(f"中转线路 '{proxy_name}' (索引 {index}, 原始索引 {original_index}) 删除成功")
        
        # 推送配置到设备
        push_success, push_msg = push_config_to_devices()
        
        return jsonify({
            'success': True,
            'message': '中转线路删除成功',
            'data': deleted_proxy,
            'push_result': {
                'success': push_success,
                'message': push_msg
            }
        })
    except Exception as e:
        logger.error(f"删除中转线路失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== VM 管理功能 ====================

# ADB 路径现在从配置文件读取，使用 get_adb_path() 函数获取

def get_proxy_groups():
    """获取所有策略组名称"""
    try:
        config = load_config()
        proxy_groups = config.get('proxy-groups', [])
        groups = []
        for group in proxy_groups:
            if isinstance(group, dict) and 'name' in group:
                groups.append(group['name'])
        return groups
    except Exception as e:
        logger.error(f"获取策略组失败: {str(e)}")
        return []

def update_proxy_groups(config):
    """
    更新 proxy-groups 中的 proxies 列表，使其包含所有当前 proxies 的 name
    只更新 type 为 'select' 且 name 不为 'PROXY' 的组
    """
    try:
        if 'proxy-groups' not in config:
            logger.debug("配置中没有 proxy-groups，跳过更新")
            return
        
        # 获取所有 proxies 的 name
        proxy_names = []
        for proxy in config.get('proxies', []):
            if isinstance(proxy, dict) and 'name' in proxy:
                proxy_names.append(proxy['name'])
        
        logger.debug(f"当前有 {len(proxy_names)} 个代理: {proxy_names}")
        
        # 更新每个 proxy-group
        updated = False
        for group in config['proxy-groups']:
            if not isinstance(group, dict):
                continue
            
            group_name = group.get('name', '')
            group_type = group.get('type', '')
            
            # 只更新 type 为 'select' 且 name 不为 'PROXY' 的组
            # PROXY 组通常引用其他组，不应该包含具体的代理
            if group_type == 'select' and group_name != 'PROXY':
                old_proxies = group.get('proxies', [])
                # 更新为所有代理的 name
                group['proxies'] = proxy_names.copy()
                updated = True
                logger.info(f"更新策略组 '{group_name}' 的代理列表: {len(old_proxies)} -> {len(proxy_names)}")
        
        if updated:
            logger.info("proxy-groups 已更新")
        else:
            logger.debug("没有需要更新的策略组")
            
    except Exception as e:
        logger.error(f"更新 proxy-groups 失败: {str(e)}", exc_info=True)


def push_config_to_devices():
    """
    将配置文件推送到所有已连接的设备
    目标路径: /data/adb/box/clash/
    """
    try:
        logger.info("开始推送配置文件到设备...")
        
        # 获取配置文件路径和 ADB 路径
        config_file_path = get_config_file_path()
        adb_path = get_adb_path()
        
        if not config_file_path or not os.path.exists(config_file_path):
            logger.warning(f"配置文件不存在: {config_file_path}")
            return False, "配置文件不存在"
        
        if not adb_path or not os.path.exists(adb_path):
            logger.warning(f"ADB路径未配置或不存在: {adb_path}")
            return False, "ADB路径未配置"
        
        # 获取已连接的设备列表
        try:
            result = subprocess.run(
                [adb_path, 'devices'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"获取设备列表失败: {result.stderr}")
                return False, "获取设备列表失败"
            
            # 解析设备列表
            devices = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and '\t' in line:
                    device_id, status = line.split('\t', 1)
                    if status.strip() == 'device':
                        devices.append(device_id.strip())
            
            if not devices:
                logger.warning("没有检测到已连接的设备")
                return False, "没有已连接的设备"
            
            logger.info(f"检测到 {len(devices)} 个已连接设备: {', '.join(devices)}")
            
            # 目标路径
            target_path = '/data/adb/box/clash/'
            
            # 为每个设备推送配置文件
            success_count = 0
            failed_devices = []
            
            for device_id in devices:
                try:
                    logger.info(f"正在推送配置到设备 {device_id}...")
                    
                    # 步骤1: 先推送到临时目录 /sdcard/
                    temp_path = '/sdcard/config.yaml'
                    push_cmd = [
                        adb_path,
                        '-s',
                        device_id,
                        'push',
                        config_file_path,
                        temp_path
                    ]
                    
                    push_result = subprocess.run(
                        push_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        encoding='utf-8',
                        errors='replace',
                        timeout=30
                    )
                    
                    if push_result.returncode != 0:
                        error_msg = push_result.stderr.strip()
                        logger.error(f"❌ 设备 {device_id} 推送到临时目录失败: {error_msg}")
                        failed_devices.append(f"{device_id}: {error_msg}")
                        continue
                    
                    # 步骤2: 使用 su 权限创建目标目录（如果不存在）
                    mkdir_cmd = [
                        adb_path,
                        '-s',
                        device_id,
                        'shell',
                        'su', '-c',
                        f'mkdir -p {target_path}'
                    ]
                    
                    mkdir_result = subprocess.run(
                        mkdir_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        encoding='utf-8',
                        errors='replace',
                        timeout=10
                    )
                    
                    # 步骤3: 使用 su 权限移动文件到目标目录
                    mv_cmd = [
                        adb_path,
                        '-s',
                        device_id,
                        'shell',
                        'su', '-c',
                        f'cp {temp_path} {target_path}config.yaml'
                    ]
                    
                    mv_result = subprocess.run(
                        mv_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        encoding='utf-8',
                        errors='replace',
                        timeout=10
                    )
                    
                    if mv_result.returncode == 0:
                        logger.info(f"✅ 设备 {device_id} 推送成功")
                        success_count += 1
                        
                        # 清理临时文件
                        subprocess.run(
                            [adb_path, '-s', device_id, 'shell', 'rm', temp_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=5
                        )
                    else:
                        error_msg = mv_result.stderr.strip() if mv_result.stderr else mv_result.stdout.strip()
                        logger.error(f"❌ 设备 {device_id} 移动文件失败: {error_msg}")
                        failed_devices.append(f"{device_id}: {error_msg}")
                
                except subprocess.TimeoutExpired:
                    logger.error(f"❌ 设备 {device_id} 推送超时")
                    failed_devices.append(f"{device_id}: 超时")
                except Exception as e:
                    logger.error(f"❌ 设备 {device_id} 推送异常: {str(e)}")
                    failed_devices.append(f"{device_id}: {str(e)}")
            
            # 返回结果
            if success_count == len(devices):
                logger.info(f"🎉 配置文件推送成功！共 {success_count} 个设备")
                return True, f"成功推送到 {success_count} 个设备"
            elif success_count > 0:
                msg = f"部分成功：{success_count}/{len(devices)} 个设备，失败: {', '.join(failed_devices)}"
                logger.warning(msg)
                return True, msg
            else:
                msg = f"所有设备推送失败: {', '.join(failed_devices)}"
                logger.error(msg)
                return False, msg
        
        except subprocess.TimeoutExpired:
            logger.error("获取设备列表超时")
            return False, "获取设备列表超时"
        except Exception as e:
            logger.error(f"执行 adb devices 失败: {str(e)}", exc_info=True)
            return False, f"执行失败: {str(e)}"
    
    except Exception as e:
        logger.error(f"推送配置文件失败: {str(e)}", exc_info=True)
        return False, f"推送失败: {str(e)}"


def load_setting():
    """加载项目配置文件"""
    try:
        if not os.path.exists(SETTING_FILE):
            logger.warning(f"项目配置文件不存在: {SETTING_FILE}，将创建默认配置")
            # 创建默认配置
            os.makedirs(os.path.dirname(SETTING_FILE), exist_ok=True)
            default_setting = {
                'regions': [
                    {'code': 'GB', 'name': '英国'},
                    {'code': 'SG', 'name': '新加坡'},
                    {'code': 'HK', 'name': '香港'},
                    {'code': 'MY', 'name': '马来西亚'},
                    {'code': 'PH', 'name': '菲律宾'}
                ],
                'vm_account_counters': {},
                'devices': [],  # 设备配置列表，格式: [{'device_id': 'xxx', 'remark': '备注'}]
                'config_file_path': 'config.yaml',  # 默认网络配置文件路径
                'vm_script_path': 'vm.sh',  # 默认VM脚本路径
                'adb_path': 'adb',  # 默认ADB路径
                'vm_accounts_file_path': 'config/vm_accounts.yaml',  # 默认多账号动态配置文件路径
                'vm_model_config_path': '/data/local/tmp/vm_model_config.yaml'  # 默认VM机型配置路径
            }
            with open(SETTING_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(default_setting, f, allow_unicode=True, default_flow_style=False)
            return default_setting
        
        with open(SETTING_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"加载项目配置文件失败: {str(e)}", exc_info=True)
        return {}

def save_setting(setting):
    """保存项目配置文件"""
    try:
        os.makedirs(os.path.dirname(SETTING_FILE), exist_ok=True)
        with open(SETTING_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(setting, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info("项目配置文件保存成功")
        return True
    except Exception as e:
        logger.error(f"保存项目配置文件失败: {str(e)}", exc_info=True)
        raise Exception(f"保存项目配置文件失败: {str(e)}")

def get_regions():
    """获取所有地区配置"""
    try:
        setting = load_setting()
        regions = setting.get('regions', [])
        # 如果没有配置，返回默认值
        if not regions:
            return [
                {'code': 'GB', 'name': '英国'},
                {'code': 'SG', 'name': '新加坡'},
                {'code': 'HK', 'name': '香港'},
                {'code': 'MY', 'name': '马来西亚'},
                {'code': 'PH', 'name': '菲律宾'}
            ]
        return regions
    except Exception as e:
        logger.error(f"获取地区配置失败: {str(e)}")
        return [
            {'code': 'GB', 'name': '英国'},
            {'code': 'SG', 'name': '新加坡'},
            {'code': 'HK', 'name': '香港'},
            {'code': 'MY', 'name': '马来西亚'},
            {'code': 'PH', 'name': '菲律宾'}
        ]

def get_all_proxy_names():
    """获取所有代理名称（包括普通代理和中转线路，都在proxies列表中）"""
    try:
        config = load_config()
        names = []
        
        # 获取所有代理名称（包括普通代理和中转线路，都在proxies列表中）
        proxies = config.get('proxies', [])
        for proxy in proxies:
            formatted = format_proxy_for_display(proxy)
            if formatted.get('name'):
                names.append(formatted['name'])
        
        return names
    except Exception as e:
        logger.error(f"获取代理名称失败: {str(e)}")
        return []

def execute_vm_script(action, name, app_type=None, region=None, node=None, device_id=None):
    """
    执行 vm.sh 脚本
    
    Args:
        action: 'new', 'load', 或 'save'
        name: 账号名称
        app_type: 应用类型（仅 new 需要）
        region: 地区（仅 new 需要）
        node: 代理节点名称（仅 new 需要）
        device_id: 设备ID（可选，如果提供则使用指定设备）
    
    Yields:
        日志行
    """
    try:
        # 输出操作开始信息
        yield f"data: ========== 开始执行 VM 操作 ==========\n\n"
        yield f"data: 操作类型: {action}\n\n"
        yield f"data: 账号名称: {name}\n\n"
        if device_id:
            yield f"data: 设备ID: {device_id}\n\n"
        if action == 'new':
            yield f"data: 应用类型: {app_type}\n\n"
            yield f"data: 地区: {region}\n\n"
            yield f"data: 代理节点: {node}\n\n"
        
        # 获取VM脚本路径（设备上的路径）
        VM_SCRIPT_PATH = get_vm_script_path()
        # 如果路径是本地路径，需要转换为设备路径
        # 假设配置的路径就是设备上的路径，如 /data/local/tmp/vm.sh
        yield f"data: VM脚本路径（设备上）: {VM_SCRIPT_PATH}\n\n"
        
        # 构建命令参数（需要正确转义）
        import shlex
        if action == 'new':
            if not all([name, app_type, region, node]):
                yield f"data: ❌ 错误: new 操作需要 name, app_type, region, node 参数\n\n"
                return
            # 构建shell命令，正确转义参数
            # sh /data/local/tmp/vm.sh new NAME APP_TYPE REGION NODE
            script_path_quoted = shlex.quote(VM_SCRIPT_PATH)
            name_quoted = shlex.quote(name)
            app_type_quoted = shlex.quote(app_type)
            region_quoted = shlex.quote(region)
            node_quoted = shlex.quote(node)
            full_shell_cmd = f"sh {script_path_quoted} new {name_quoted} {app_type_quoted} {region_quoted} {node_quoted}"
            yield f"data: 📝 Shell命令: {full_shell_cmd}\n\n"
        elif action == 'load':
            if not name:
                yield f"data: ❌ 错误: load 操作需要 name 参数\n\n"
                return
            script_path_quoted = shlex.quote(VM_SCRIPT_PATH)
            name_quoted = shlex.quote(name)
            full_shell_cmd = f"sh {script_path_quoted} load {name_quoted}"
            yield f"data: 📝 Shell命令: {full_shell_cmd}\n\n"
        elif action == 'save':
            if not name:
                yield f"data: ❌ 错误: save 操作需要 name 参数\n\n"
                return
            # save 操作只需要 name 参数（AccountName）
            script_path_quoted = shlex.quote(VM_SCRIPT_PATH)
            name_quoted = shlex.quote(name)
            full_shell_cmd = f"sh {script_path_quoted} save {name_quoted}"
            yield f"data: 📝 Shell命令: {full_shell_cmd}\n\n"
            yield f"data: 📝 账号名称 (AccountName): {name}\n\n"
        else:
            yield f"data: ❌ 错误: 未知的操作类型 {action}\n\n"
            return
        
        # 检查ADB路径
        ADB_PATH = get_adb_path()
        yield f"data: ADB路径: {ADB_PATH}\n\n"
        if ADB_PATH and os.path.exists(ADB_PATH):
            yield f"data: ✅ ADB工具存在，将通过ADB执行\n\n"
            
            # 构建完整的ADB命令
            # adb [-s DEVICE_ID] shell "su -c 'sh /path/to/vm.sh ...'"
            adb_cmd = [ADB_PATH]
            
            # 如果指定了设备ID，添加 -s 参数
            if device_id:
                adb_cmd.extend(['-s', device_id])
                yield f"data: 使用指定设备: {device_id}\n\n"
            else:
                # 尝试从设备配置中获取第一个已连接设备
                try:
                    devices_response = subprocess.run(
                        [ADB_PATH, 'devices'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5,
                        creationflags=0x08000000 if os.name == 'nt' else 0
                    )
                    if devices_response.returncode == 0:
                        lines = devices_response.stdout.strip().split('\n')[1:]  # 跳过第一行
                        for line in lines:
                            if line.strip() and '\tdevice' in line:
                                device_id = line.split('\t')[0].strip()
                                adb_cmd.extend(['-s', device_id])
                                yield f"data: 自动选择设备: {device_id}\n\n"
                                break
                except:
                    pass  # 如果获取设备列表失败，继续执行（可能只有一个设备）
            
            # 构建完整的shell命令：su -c 'sh /path/to/vm.sh ...'
            su_cmd = f"su -c '{full_shell_cmd}'"
            adb_cmd.extend(['shell', su_cmd])
            
            yield f"data: ========== ADB 命令详情 ==========\n\n"
            yield f"data: ADB路径: {ADB_PATH}\n\n"
            yield f"data: Shell命令: {full_shell_cmd}\n\n"
            yield f"data: 完整ADB命令: {' '.join(adb_cmd)}\n\n"
            yield f"data: 命令参数列表: {adb_cmd}\n\n"
            yield f"data: ====================================\n\n"
            
            # 通过 ADB 执行（需要设备连接）
            yield f"data: 📱 正在通过 ADB 执行命令...\n\n"
            logger.info(f"执行ADB命令: {' '.join(adb_cmd)}")
            
            process = subprocess.Popen(
                adb_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',  # 遇到无法解码的字符时替换为占位符
                bufsize=1,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            
            yield f"data: ✅ ADB进程已启动，PID: {process.pid}\n\n"
        else:
            # ADB未配置，无法执行
            yield f"data: ❌ 错误: ADB未配置或不存在，无法执行VM脚本\n\n"
            yield f"data: 请先在路径设置中配置ADB路径\n\n"
            return
        
        yield f"data: ========== 开始接收输出 ==========\n\n"
        
        # 实时输出日志
        line_count = 0
        for line in iter(process.stdout.readline, ''):
            if line:
                line_count += 1
                # 使用 Server-Sent Events 格式
                yield f"data: {line.rstrip()}\n\n"
        
        yield f"data: ========== 输出结束 (共 {line_count} 行) ==========\n\n"
        
        # 等待进程完成
        yield f"data: ⏳ 等待进程结束...\n\n"
        process.wait()
        return_code = process.returncode
        success = (return_code == 0)
        
        yield f"data: 进程退出码: {return_code}\n\n"
        
        # 如果是创建新账号且成功，更新计数器
        if action == 'new' and success and app_type and region:
            yield f"data: 📊 更新账号计数器...\n\n"
            increment_vm_account_counter(app_type, region)
            yield f"data: ✅ 操作完成，账号计数器已更新\n\n"
        elif success:
            yield f"data: ✅ 操作完成\n\n"
        else:
            yield f"data: ❌ 操作失败，退出码: {return_code}\n\n"
        
        yield f"data: ========== VM 操作结束 ==========\n\n"
            
    except Exception as e:
        logger.error(f"执行 vm.sh 失败: {str(e)}", exc_info=True)
        yield f"data: ❌ 执行失败: {str(e)}\n\n"
        yield f"data: 错误详情: {repr(e)}\n\n"

@app.route('/api/vm/proxy-groups', methods=['GET'])
def get_vm_proxy_groups():
    """获取所有策略组名称"""
    try:
        groups = get_proxy_groups()
        return jsonify({
            'success': True,
            'data': groups
        })
    except Exception as e:
        logger.error(f"获取策略组失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/regions', methods=['GET'])
def get_regions_api():
    """获取所有地区配置"""
    try:
        logger.info("收到获取地区列表请求")
        regions = get_regions()
        logger.info(f"成功返回 {len(regions)} 个地区")
        return jsonify({
            'success': True,
            'data': regions
        })
    except Exception as e:
        logger.error(f"获取地区列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/regions', methods=['POST'])
def add_region():
    """添加新地区"""
    try:
        data = request.json
        code = data.get('code', '').strip().upper()
        name = data.get('name', '').strip()
        
        logger.info(f"收到添加地区请求: {code} - {name}")
        
        if not code or not name:
            return jsonify({
                'success': False,
                'error': '地区代码和名称不能为空'
            }), 400
        
        setting = load_setting()
        regions = get_regions()
        
        # 检查地区代码是否已存在
        for region in regions:
            if region.get('code') == code:
                logger.warning(f"地区代码 '{code}' 已存在")
                return jsonify({
                    'success': False,
                    'error': f'地区代码 "{code}" 已存在'
                }), 400
        
        # 添加新地区
        new_region = {'code': code, 'name': name}
        regions.append(new_region)
        setting['regions'] = regions
        save_setting(setting)
        
        logger.info(f"地区 '{code}' ({name}) 添加成功")
        return jsonify({
            'success': True,
            'message': '地区添加成功',
            'data': new_region
        })
    except Exception as e:
        logger.error(f"添加地区失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/regions/<string:code>', methods=['DELETE'])
def delete_region(code):
    """删除地区"""
    try:
        code = code.upper()
        logger.info(f"收到删除地区请求: {code}")
        
        setting = load_setting()
        regions = get_regions()
        
        # 查找并删除
        original_count = len(regions)
        regions = [r for r in regions if r.get('code') != code]
        
        if len(regions) == original_count:
            logger.warning(f"地区代码 '{code}' 不存在")
            return jsonify({
                'success': False,
                'error': f'地区代码 "{code}" 不存在'
            }), 400
        
        setting['regions'] = regions
        save_setting(setting)
        
        logger.info(f"地区 '{code}' 删除成功")
        return jsonify({
            'success': True,
            'message': '地区删除成功'
        })
    except Exception as e:
        logger.error(f"删除地区失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/settings/paths', methods=['GET'])
def get_path_settings():
    """获取文件路径配置"""
    try:
        setting = load_setting()
        config_file_path = setting.get('config_file_path', 'config.yaml')
        vm_script_path = setting.get('vm_script_path', 'vm.sh')
        adb_path = setting.get('adb_path', 'adb')
        vm_accounts_file_path = setting.get('vm_accounts_file_path', 'config/vm_accounts.yaml')
        vm_model_config_path = setting.get('vm_model_config_path', '/data/local/tmp/vm_model_config.yaml')
        
        return jsonify({
            'success': True,
            'data': {
                'config_file_path': config_file_path,
                'vm_script_path': vm_script_path,
                'adb_path': adb_path,
                'vm_accounts_file_path': vm_accounts_file_path,
                'vm_model_config_path': vm_model_config_path
            }
        })
    except Exception as e:
        logger.error(f"获取路径配置失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/settings/paths', methods=['POST'])
def update_path_settings():
    """更新文件路径配置"""
    try:
        data = request.json
        config_file_path = data.get('config_file_path', '').strip()
        vm_script_path = data.get('vm_script_path', '').strip()
        adb_path = data.get('adb_path', '').strip()
        vm_accounts_file_path = data.get('vm_accounts_file_path', '').strip()
        vm_model_config_path = data.get('vm_model_config_path', '').strip()
        
        logger.info(f"收到更新路径配置请求: config_file_path={config_file_path}, vm_script_path={vm_script_path}, adb_path={adb_path}, vm_accounts_file_path={vm_accounts_file_path}, vm_model_config_path={vm_model_config_path}")
        
        # 更新配置（不进行任何校验）
        setting = load_setting()
        setting['config_file_path'] = config_file_path
        setting['vm_script_path'] = vm_script_path
        setting['adb_path'] = adb_path
        setting['vm_accounts_file_path'] = vm_accounts_file_path
        setting['vm_model_config_path'] = vm_model_config_path
        save_setting(setting)
        
        # 清除缓存，使新配置立即生效
        clear_path_cache()
        
        logger.info(f"路径配置更新成功: config_file_path={config_file_path}, vm_script_path={vm_script_path}, adb_path={adb_path}, vm_accounts_file_path={vm_accounts_file_path}, vm_model_config_path={vm_model_config_path}")
        return jsonify({
            'success': True,
            'message': '路径配置已保存',
            'data': {
                'config_file_path': config_file_path,
                'vm_script_path': vm_script_path,
                'adb_path': adb_path,
                'vm_accounts_file_path': vm_accounts_file_path,
                'vm_model_config_path': vm_model_config_path
            }
        })
    except Exception as e:
        logger.error(f"更新路径配置失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """获取ADB连接的设备列表（实时扫描）"""
    try:
        logger.info("收到获取设备列表请求")
        
        # 获取ADB路径
        ADB_PATH = get_adb_path()
        if not ADB_PATH:
            logger.warning("ADB路径未配置")
            return jsonify({
                'success': False,
                'error': 'ADB路径未配置，请先在路径设置中配置ADB路径'
            }), 400
        
        # 检查ADB文件是否存在
        if not os.path.exists(ADB_PATH):
            logger.warning(f"ADB文件不存在: {ADB_PATH}")
            return jsonify({
                'success': False,
                'error': f'ADB文件不存在: {ADB_PATH}'
            }), 400
        
        # 执行 adb devices 命令
        cmd = [ADB_PATH, 'devices']
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else '未知错误'
                logger.error(f"ADB命令执行失败: {error_msg}")
                return jsonify({
                    'success': False,
                    'error': f'ADB命令执行失败: {error_msg}'
                }), 500
            
            # 解析输出
            output = result.stdout.strip()
            logger.debug(f"ADB devices 输出:\n{output}")
            
            devices = []
            lines = output.split('\n')
            
            # 跳过第一行 "List of devices attached"
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                
                # 解析设备行，格式: device_id    device/unauthorized/offline
                parts = line.split('\t')
                if len(parts) >= 2:
                    device_id = parts[0].strip()
                    status = parts[1].strip()
                    
                    # 返回所有状态的设备
                    devices.append({
                        'id': device_id,
                        'status': status
                    })
                elif len(parts) == 1 and parts[0].strip():
                    # 有些情况下可能没有状态列
                    device_id = parts[0].strip()
                    devices.append({
                        'id': device_id,
                        'status': 'unknown'
                    })
            
            logger.info(f"找到 {len(devices)} 个设备")
            return jsonify({
                'success': True,
                'data': devices,
                'raw_output': output
            })
            
        except subprocess.TimeoutExpired:
            logger.error("ADB命令执行超时")
            return jsonify({
                'success': False,
                'error': 'ADB命令执行超时，请检查设备连接'
            }), 500
        except Exception as e:
            logger.error(f"执行ADB命令时出错: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'执行ADB命令时出错: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"获取设备列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/device-configs', methods=['GET'])
def get_device_configs():
    """获取已保存的设备配置列表（包含备注）"""
    try:
        logger.info("收到获取设备配置列表请求")
        setting = load_setting()
        device_configs = setting.get('devices', [])
        logger.info(f"成功返回 {len(device_configs)} 个设备配置")
        return jsonify({
            'success': True,
            'data': device_configs
        })
    except Exception as e:
        logger.error(f"获取设备配置列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/device-configs', methods=['POST'])
def add_device_config():
    """添加或更新设备配置"""
    try:
        data = request.json
        device_id = data.get('device_id', '').strip()
        remark = data.get('remark', '').strip()
        
        logger.info(f"收到添加设备配置请求: device_id={device_id}, remark={remark}")
        
        if not device_id:
            return jsonify({
                'success': False,
                'error': '设备ID不能为空'
            }), 400
        
        setting = load_setting()
        devices = setting.get('devices', [])
        if not isinstance(devices, list):
            devices = []
        
        # 检查设备ID是否已存在
        existing_index = None
        for idx, device in enumerate(devices):
            if device.get('device_id') == device_id:
                existing_index = idx
                break
        
        device_config = {
            'device_id': device_id,
            'remark': remark
        }
        
        if existing_index is not None:
            # 更新现有配置
            devices[existing_index] = device_config
            logger.info(f"更新设备配置: {device_id}")
        else:
            # 添加新配置
            devices.append(device_config)
            logger.info(f"添加设备配置: {device_id}")
        
        setting['devices'] = devices
        save_setting(setting)
        
        return jsonify({
            'success': True,
            'message': '设备配置已保存',
            'data': device_config
        })
    except Exception as e:
        logger.error(f"保存设备配置失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/device-configs/<string:device_id>', methods=['DELETE'])
def delete_device_config(device_id):
    """删除设备配置"""
    try:
        logger.info(f"收到删除设备配置请求: device_id={device_id}")
        
        setting = load_setting()
        devices = setting.get('devices', [])
        if not isinstance(devices, list):
            devices = []
        
        # 查找并删除
        original_count = len(devices)
        devices = [d for d in devices if d.get('device_id') != device_id]
        
        if len(devices) == original_count:
            logger.warning(f"设备配置不存在: {device_id}")
            return jsonify({
                'success': False,
                'error': f'设备配置不存在: {device_id}'
            }), 400
        
        setting['devices'] = devices
        save_setting(setting)
        
        logger.info(f"设备配置 '{device_id}' 删除成功")
        return jsonify({
            'success': True,
            'message': '设备配置删除成功'
        })
    except Exception as e:
        logger.error(f"删除设备配置失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vm/proxy-names', methods=['GET'])
def get_vm_proxy_names():
    """获取代理名称，支持按region过滤，只返回proxies中的普通代理（不包括IsBase=true的中转线路）"""
    try:
        region = request.args.get('region', '').strip().upper()
        
        config = load_config()
        names = []
        
        # 只获取普通代理名称，不包括中转线路（IsBase=true）
        proxies = config.get('proxies', [])
        for proxy in proxies:
            formatted = format_proxy_for_display(proxy)
            # 排除中转线路
            if is_transit_proxy(formatted):
                continue
                
            proxy_name = formatted.get('name')
            proxy_region = formatted.get('region', '')
            
            # 如果指定了region，只返回匹配的代理
            if region:
                if proxy_region == region and proxy_name:
                    names.append(proxy_name)
            else:
                # 如果没有指定region，返回所有代理名称
                if proxy_name:
                    names.append(proxy_name)
        
        logger.debug(f"获取代理名称: region={region}, count={len(names)} (仅普通代理，不包括中转线路)")
        return jsonify({
            'success': True,
            'data': names
        })
    except Exception as e:
        logger.error(f"获取代理名称失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_vm_account_name(app_type, region):
    """
    生成VM账号名称：应用类型_地域_自增数
    例如：Vinted_GB_001, Carousell_HK_002
    只读取计数器，不更新（更新在创建成功后进行）
    """
    try:
        # 加载配置文件
        setting = load_setting()
        
        # 获取或初始化计数器字典
        counters = setting.get('vm_account_counters', {})
        if not isinstance(counters, dict):
            counters = {}
        
        # 生成计数器键：应用类型_地域
        counter_key = f"{app_type}_{region}"
        
        # 获取当前计数器值，默认为0（下一个将是1）
        current_count = counters.get(counter_key, 0)
        if not isinstance(current_count, int):
            current_count = 0
        
        # 生成下一个编号（3位数字，补零）
        next_num = current_count + 1
        account_name = f"{app_type}_{region}_{next_num:03d}"
        
        logger.info(f"生成账号名称: {account_name} (应用类型={app_type}, 地域={region}, 当前计数器={current_count}, 将使用编号={next_num})")
        return account_name
        
    except Exception as e:
        logger.error(f"生成账号名称失败: {str(e)}", exc_info=True)
        # 如果生成失败，返回默认名称
        return f"{app_type}_{region}_001"

def increment_vm_account_counter(app_type, region):
    """
    增加VM账号计数器（在创建成功后调用）
    """
    try:
        # 加载配置文件
        setting = load_setting()
        
        # 获取或初始化计数器字典
        counters = setting.get('vm_account_counters', {})
        if not isinstance(counters, dict):
            counters = {}
        
        # 生成计数器键：应用类型_地域
        counter_key = f"{app_type}_{region}"
        
        # 获取当前计数器值，默认为0
        current_count = counters.get(counter_key, 0)
        if not isinstance(current_count, int):
            current_count = 0
        
        # 增加计数器
        counters[counter_key] = current_count + 1
        setting['vm_account_counters'] = counters
        save_setting(setting)
        
        logger.info(f"更新VM账号计数器: {counter_key} = {counters[counter_key]} (应用类型={app_type}, 地域={region})")
        return True
        
    except Exception as e:
        logger.error(f"更新VM账号计数器失败: {str(e)}", exc_info=True)
        return False

@app.route('/api/vm/generate-account-name', methods=['GET'])
def generate_account_name():
    """生成VM账号名称"""
    try:
        app_type = request.args.get('app_type', 'Vinted').strip()
        region = request.args.get('region', 'GB').strip().upper()
        
        if not app_type or not region:
            return jsonify({
                'success': False,
                'error': '应用类型和地区不能为空'
            }), 400
        
        account_name = generate_vm_account_name(app_type, region)
        
        return jsonify({
            'success': True,
            'data': account_name
        })
    except Exception as e:
        logger.error(f"生成账号名称失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vm/new', methods=['POST'])
def vm_new():
    """创建新账号"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        app_type = data.get('app_type', 'Vinted')
        region = data.get('region', 'GB')
        node = data.get('node', '')
        device_id = data.get('device_id', '').strip()  # 可选的设备ID
        
        logger.info("=" * 70)
        logger.info("收到创建新账号请求")
        logger.info(f"账号名称: {name}")
        logger.info(f"应用类型: {app_type}")
        logger.info(f"地区: {region}")
        logger.info(f"代理节点: {node}")
        if device_id:
            logger.info(f"设备ID: {device_id}")
        logger.info("=" * 70)
        
        if not name:
            logger.warning("账号名称为空")
            return jsonify({
                'success': False,
                'error': '账号名称不能为空'
            }), 400
        
        if not node:
            logger.warning("代理节点名称为空")
            return jsonify({
                'success': False,
                'error': '代理节点名称不能为空'
            }), 400
        
        # 获取VM脚本路径和ADB路径用于日志
        VM_SCRIPT_PATH = get_vm_script_path()
        ADB_PATH = get_adb_path()
        logger.info(f"VM脚本路径（设备上）: {VM_SCRIPT_PATH}")
        logger.info(f"ADB路径: {ADB_PATH}")
        
        # 验证ADB路径
        if not ADB_PATH or not os.path.exists(ADB_PATH):
            logger.error("ADB路径未配置或不存在")
            return jsonify({
                'success': False,
                'error': 'ADB路径未配置或不存在，请先在路径设置中配置ADB路径'
            }), 400
        
        logger.info("开始执行VM脚本...")
        
        return Response(
            stream_with_context(execute_vm_script('new', name, app_type, region, node, device_id)),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
    except Exception as e:
        logger.error(f"创建新账号失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_vm_account_list(device_id=None):
    """
    通过ADB获取VM账号列表（从vm_model_config_path路径下的文件）
    
    Args:
        device_id: 可选的设备ID，如果提供则使用指定设备
    
    Returns:
        账号名称列表，如果失败则返回空列表
    """
    try:
        # 获取ADB路径和配置文件路径
        ADB_PATH = get_adb_path()
        VM_MODEL_CONFIG_PATH = get_vm_model_config_path()
        
        if not ADB_PATH or not os.path.exists(ADB_PATH):
            logger.error("ADB路径未配置或不存在")
            return []
        
        # 构建ADB命令：adb [-s DEVICE_ID] shell "ls -1 /path/to/dir | grep '\.conf$' | sed 's/\.conf$//'"
        adb_cmd = [ADB_PATH]
        
        # 如果指定了设备ID，添加 -s 参数
        if device_id:
            adb_cmd.extend(['-s', device_id])
        else:
            # 尝试自动选择设备
            try:
                devices_response = subprocess.run(
                    [ADB_PATH, 'devices'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5,
                    creationflags=0x08000000 if os.name == 'nt' else 0
                )
                if devices_response.returncode == 0:
                    lines = devices_response.stdout.strip().split('\n')[1:]
                    for line in lines:
                        if line.strip() and '\tdevice' in line:
                            device_id = line.split('\t')[0].strip()
                            adb_cmd.extend(['-s', device_id])
                            break
            except:
                pass
        
        # 构建shell命令：列出目录下所有 .conf 文件，提取文件名（去掉路径和扩展名）
        # 确保路径以/结尾
        config_path = VM_MODEL_CONFIG_PATH.rstrip('/') + '/'
        # 使用更可靠的命令：ls + basename + sed
        # 如果目录不存在或没有文件，返回空列表（不报错）
        shell_cmd = f"ls -1 {config_path}*.conf 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/\\.conf$//' || echo ''"
        adb_cmd.extend(['shell', shell_cmd])
        
        logger.debug(f"执行ADB命令获取账号列表: {' '.join(adb_cmd)}")
        
        # 执行ADB命令
        result = subprocess.run(
            adb_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=10,
            creationflags=0x08000000 if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            # 解析输出，每行一个账号名称
            accounts = []
            for line in result.stdout.strip().split('\n'):
                account_name = line.strip()
                if account_name:
                    accounts.append(account_name)
            
            logger.info(f"成功获取账号列表: {len(accounts)} 个账号")
            return accounts
        else:
            error_msg = result.stderr.strip() if result.stderr else '未知错误'
            logger.warning(f"ADB命令执行失败或目录为空: {error_msg}")
            # 如果目录不存在或为空，返回空列表而不是错误
            return []
            
    except subprocess.TimeoutExpired:
        logger.error("ADB命令执行超时")
        return []
    except Exception as e:
        logger.error(f"获取账号列表失败: {str(e)}", exc_info=True)
        return []

@app.route('/api/vm/account-list', methods=['GET'])
def get_vm_account_list_api():
    """
    获取VM账号列表（从设备上的配置文件目录）
    
    查询参数:
        device_id: 设备ID（可选），如果提供则使用指定设备
    """
    try:
        device_id = request.args.get('device_id', '').strip() or None
        
        logger.info(f"收到获取账号列表请求: device_id={device_id}")
        
        # 获取账号列表
        accounts = get_vm_account_list(device_id)
        
        return jsonify({
            'success': True,
            'data': accounts,
            'count': len(accounts)
        })
            
    except Exception as e:
        logger.error(f"获取账号列表失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vm/load', methods=['POST'])
def vm_load():
    """
    加载账号
    参数：账号名称（从账号列表中获取）
    """
    try:
        data = request.json
        name = data.get('name', '').strip()
        device_id = data.get('device_id', '').strip() or None
        
        logger.info("=" * 70)
        logger.info("收到加载账号请求")
        logger.info(f"账号名称: {name}")
        if device_id:
            logger.info(f"设备ID: {device_id}")
        logger.info("=" * 70)
        
        if not name:
            logger.warning("账号名称为空")
            return jsonify({
                'success': False,
                'error': '账号名称不能为空'
            }), 400
        
        # 获取VM脚本路径和ADB路径用于日志
        VM_SCRIPT_PATH = get_vm_script_path()
        ADB_PATH = get_adb_path()
        logger.info(f"VM脚本路径（设备上）: {VM_SCRIPT_PATH}")
        logger.info(f"ADB路径: {ADB_PATH}")
        
        # 验证ADB路径
        if not ADB_PATH or not os.path.exists(ADB_PATH):
            logger.error("ADB路径未配置或不存在")
            return jsonify({
                'success': False,
                'error': 'ADB路径未配置或不存在，请先在路径设置中配置ADB路径'
            }), 400
        
        logger.info("开始执行VM脚本...")
        
        return Response(
            stream_with_context(execute_vm_script('load', name, device_id=device_id)),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
    except Exception as e:
        logger.error(f"加载账号失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_vm_config_value(field_name, device_id=None):
    """
    通过ADB从设备上的配置文件中读取指定字段的值
    
    Args:
        field_name: 字段名称，如 'AccountName', 'AppType', 'Region' 等
        device_id: 可选的设备ID，如果提供则使用指定设备
    
    Returns:
        字段的值，如果不存在则返回 None
    """
    try:
        # 获取ADB路径和配置文件路径
        ADB_PATH = get_adb_path()
        CONFIG_FILE_PATH = get_vm_accounts_file_path()
        
        if not ADB_PATH or not os.path.exists(ADB_PATH):
            logger.error("ADB路径未配置或不存在")
            return None
        
        # 构建ADB命令：adb [-s DEVICE_ID] shell "cat /path/to/file | grep 'FieldName=' | cut -d= -f2"
        adb_cmd = [ADB_PATH]
        
        # 如果指定了设备ID，添加 -s 参数
        if device_id:
            adb_cmd.extend(['-s', device_id])
        else:
            # 尝试自动选择设备
            try:
                devices_response = subprocess.run(
                    [ADB_PATH, 'devices'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5,
                    creationflags=0x08000000 if os.name == 'nt' else 0
                )
                if devices_response.returncode == 0:
                    lines = devices_response.stdout.strip().split('\n')[1:]
                    for line in lines:
                        if line.strip() and '\tdevice' in line:
                            device_id = line.split('\t')[0].strip()
                            adb_cmd.extend(['-s', device_id])
                            break
            except:
                pass
        
        # 构建shell命令：cat /path/to/file | grep '^FieldName=' | cut -d= -f2- | tr -d '\r\n '
        # 使用 cut -d= -f2- 而不是 -f2，以支持值中包含 = 的情况
        shell_cmd = f"cat {CONFIG_FILE_PATH} 2>/dev/null | grep '^{field_name}=' | head -n 1 | cut -d= -f2- | tr -d '\\r\\n '"
        adb_cmd.extend(['shell', shell_cmd])
        
        logger.debug(f"执行ADB命令获取配置值: {' '.join(adb_cmd)}")
        
        # 执行ADB命令
        result = subprocess.run(
            adb_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=10,
            creationflags=0x08000000 if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            value = result.stdout.strip()
            if value:
                logger.info(f"成功获取配置值: {field_name} = {value}")
                return value
            else:
                logger.warning(f"配置文件中未找到字段: {field_name}")
                return None
        else:
            error_msg = result.stderr.strip() if result.stderr else '未知错误'
            logger.error(f"ADB命令执行失败: {error_msg}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("ADB命令执行超时")
        return None
    except Exception as e:
        logger.error(f"获取配置值失败: {str(e)}", exc_info=True)
        return None

@app.route('/api/vm/get-config-value', methods=['GET'])
def get_vm_config_value_api():
    """
    获取VM配置文件中指定字段的值
    
    查询参数:
        field_name: 字段名称（必填），如 'AccountName', 'AppType', 'Region' 等
        device_id: 设备ID（可选），如果提供则使用指定设备
    """
    try:
        field_name = request.args.get('field_name', '').strip()
        device_id = request.args.get('device_id', '').strip() or None
        
        logger.info(f"收到获取配置值请求: field_name={field_name}, device_id={device_id}")
        
        if not field_name:
            return jsonify({
                'success': False,
                'error': 'field_name 参数不能为空'
            }), 400
        
        # 获取配置值
        value = get_vm_config_value(field_name, device_id)
        
        if value is not None:
            return jsonify({
                'success': True,
                'data': {
                    'field_name': field_name,
                    'value': value
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'未找到字段 "{field_name}" 的值，请确保设备已连接且配置文件存在'
            }), 404
            
    except Exception as e:
        logger.error(f"获取配置值失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/vm/save', methods=['POST'])
def vm_save():
    """
    保存账号
    1. 通过 /api/vm/get-config-value 接口获取 AccountName
    2. 使用 AccountName 作为参数调用 vm.sh save
    """
    try:
        data = request.json
        device_id = data.get('device_id', '').strip() or None
        
        logger.info("=" * 70)
        logger.info("收到保存账号请求")
        if device_id:
            logger.info(f"设备ID: {device_id}")
        logger.info("=" * 70)
        
        # 步骤1: 通过API获取AccountName
        logger.info("步骤1: 获取AccountName...")
        account_name = get_vm_config_value('AccountName', device_id)
        
        if not account_name:
            logger.error("无法获取AccountName，请确保设备已连接且配置文件存在")
            return jsonify({
                'success': False,
                'error': '无法获取AccountName，请确保设备已连接且配置文件存在。请先创建新账号或加载已有账号。'
            }), 400
        
        logger.info(f"成功获取AccountName: {account_name}")
        
        # 步骤2: 使用AccountName执行保存操作
        logger.info(f"步骤2: 开始保存账号: {account_name}")
        
        return Response(
            stream_with_context(execute_vm_script('save', account_name, device_id=device_id)),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
    except Exception as e:
        logger.error(f"保存账号失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    import webbrowser
    import threading
    
    # 首先配置日志系统
    setup_logging()
    
    # 确保 templates 目录存在
    os.makedirs('templates', exist_ok=True)
    logger.info("检查 templates 目录...")
    
    # 检查网络配置文件是否存在
    CONFIG_FILE = get_config_file_path()
    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"网络配置文件 {CONFIG_FILE} 不存在，将创建空配置文件")
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.dump({'proxies': []}, f, allow_unicode=True)
            logger.info("空网络配置文件创建成功")
        except Exception as e:
            logger.error(f"创建网络配置文件失败: {str(e)}")
    else:
        logger.info(f"网络配置文件存在: {os.path.abspath(CONFIG_FILE)}")
        # 尝试加载一次以检查格式
        try:
            test_config = load_config()
            logger.info("网络配置文件格式检查通过")
        except Exception as e:
            logger.warning(f"网络配置文件格式检查失败: {str(e)}")
    
    # 检查项目配置文件是否存在
    if not os.path.exists(SETTING_FILE):
        logger.info(f"项目配置文件 {SETTING_FILE} 不存在，将创建默认配置")
        try:
            load_setting()  # 这会自动创建默认配置
            logger.info("项目配置文件创建成功")
        except Exception as e:
            logger.error(f"创建项目配置文件失败: {str(e)}")
    else:
        logger.info(f"项目配置文件存在: {os.path.abspath(SETTING_FILE)}")
        try:
            test_setting = load_setting()
            logger.info("项目配置文件加载成功")
        except Exception as e:
            logger.warning(f"项目配置文件加载失败: {str(e)}")
    
    CONFIG_FILE = get_config_file_path()
    VM_SCRIPT_PATH = get_vm_script_path()
    
    print("=" * 70)
    print("🚀 Proxy Manager - 代理配置管理工具")
    print("=" * 70)
    print(f"📁 配置文件: {os.path.abspath(CONFIG_FILE)}")
    print(f"📜 VM脚本: {os.path.abspath(VM_SCRIPT_PATH)}")
    print(f"🌐 访问地址: http://localhost:5000")
    print(f"📊 日志级别: INFO")
    print("=" * 70)
    print("💡 提示: 浏览器将自动打开，或手动访问上述地址")
    print("💡 提示: 按 Ctrl+C 停止服务")
    print("=" * 70)
    print()
    
    logger.info("=" * 70)
    logger.info("Proxy Manager 服务启动中...")
    logger.info(f"配置文件路径: {os.path.abspath(CONFIG_FILE)}")
    logger.info(f"VM脚本路径: {os.path.abspath(VM_SCRIPT_PATH)}")
    logger.info(f"服务地址: http://localhost:5000")
    logger.info("=" * 70)
    
    # 延迟打开浏览器，确保服务已启动
    def open_browser():
        import time
        time.sleep(1.5)  # 等待服务启动
        logger.info("正在打开浏览器...")
        try:
            webbrowser.open('http://localhost:5000')
            logger.info("浏览器已打开")
        except Exception as e:
            logger.warning(f"打开浏览器失败: {str(e)}")
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        logger.info("Flask 服务启动中...")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务...")
        print("\n\n👋 服务已停止")
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}", exc_info=True)
        print(f"\n\n❌ 服务启动失败: {str(e)}")

