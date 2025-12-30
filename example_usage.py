"""
重构后模块使用示例
演示如何使用新的模块化架构
"""

# ==================== 示例 1: 日志系统 ====================
from core.logger import get_logger, setup_logging
from core.config import SettingManager

# 初始化日志
setting_mgr = SettingManager()
setting = setting_mgr.load()
setup_logging(setting)

# 使用日志
logger = get_logger(__name__)
logger.info("应用启动")
logger.debug("这是调试信息")
logger.error("这是错误信息")

# ==================== 示例 2: 配置管理 ====================
from core.config import ConfigManager
from core.path_manager import PathManager

# 初始化管理器
path_mgr = PathManager(setting_mgr)
config_mgr = ConfigManager(path_mgr)

# 加载配置
config = config_mgr.load()
logger.info(f"加载配置成功，包含 {len(config.get('proxies', []))} 个代理")

# 修改配置
# config['proxies'].append({'name': 'test', 'type': 'socks5'})

# 保存配置
# config_mgr.save(config)

# ==================== 示例 3: 路径管理 ====================
print("\n" + "=" * 50)
print("📁 配置路径信息")
print("=" * 50)
print(f"网络配置文件: {path_mgr.get_config_file_path()}")
print(f"VM 脚本路径: {path_mgr.get_vm_script_path()}")
print(f"ADB 路径: {path_mgr.get_adb_path()}")
print(f"VM 账号文件: {path_mgr.get_vm_accounts_file_path()}")
print(f"VM 机型配置: {path_mgr.get_vm_model_config_path()}")

# ==================== 示例 4: ADB 操作 ====================
from utils.adb_helper import ADBHelper

adb_helper = ADBHelper(path_mgr)

# 获取设备列表
print("\n" + "=" * 50)
print("📱 已连接设备")
print("=" * 50)
devices = adb_helper.get_devices()
if devices:
    for device in devices:
        print(f"  - 设备ID: {device['id']}, 状态: {device['status']}")
else:
    print("  无已连接设备")

# 推送文件示例（注释掉，避免实际执行）
# success, msg = adb_helper.push_file(
#     local_path='config.yaml',
#     remote_path='/data/adb/box/clash/config.yaml',
#     device_id=None,  # 自动选择设备
#     use_su=True
# )
# logger.info(f"推送结果: {msg}")

# ==================== 示例 5: YAML 处理 ====================
from utils.yaml_helper import YAMLHelper, format_proxy_for_display, is_transit_proxy

yaml_helper = YAMLHelper()

# 统计代理类型
print("\n" + "=" * 50)
print("📊 代理统计")
print("=" * 50)
proxies = config.get('proxies', [])
transit_count = 0
normal_count = 0

for proxy in proxies:
    formatted = format_proxy_for_display(proxy)
    if is_transit_proxy(formatted):
        transit_count += 1
    else:
        normal_count += 1

print(f"  - 普通代理: {normal_count} 个")
print(f"  - 中转线路: {transit_count} 个")
print(f"  - 总计: {len(proxies)} 个")

# ==================== 示例 6: 项目配置管理 ====================
print("\n" + "=" * 50)
print("⚙️  项目配置信息")
print("=" * 50)

# 读取配置
regions = setting.get('regions', [])
print(f"  - 配置地区数量: {len(regions)}")
for region in regions:
    print(f"    • {region['code']}: {region['name']}")

vm_counters = setting.get('vm_account_counters', {})
print(f"\n  - VM 账号计数器:")
for key, value in vm_counters.items():
    print(f"    • {key}: {value}")

proxy_counters = setting.get('proxy_name_counters', {})
print(f"\n  - 代理名称计数器:")
for key, value in list(proxy_counters.items())[:5]:  # 只显示前5个
    print(f"    • {key}: {value}")

devices = setting.get('devices', [])
print(f"\n  - 已保存设备: {len(devices)} 个")
for device in devices:
    print(f"    • {device['device_id']}: {device.get('remark', '无备注')}")

print("\n" + "=" * 50)
print("✅ 示例执行完成")
print("=" * 50)

