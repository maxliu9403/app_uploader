"""
Proxy Manager - 重构后的主应用入口
采用分层架构：核心层 -> 工具层 -> 服务层 -> 路由层
"""

import os
from flask import Flask, render_template, request, Response, jsonify
from flask_cors import CORS
from flasgger import Swagger

# 核心模块
from core.config import ConfigManager, SettingManager
from core.path_manager import PathManager
from core.logger import setup_logging, get_logger

# 工具模块
from utils.adb_helper import ADBHelper
from utils.yaml_helper import YAMLHelper, to_json

# 服务模块
from services.proxy_service import ProxyService
from services.transit_service import TransitService
from services.vm_service import VMService
from services.device_service import DeviceService
from services.region_service import RegionService

# 路由模块
from routes import proxy_routes, transit_routes, vm_routes, device_routes, region_routes, setting_routes

# ==================== 初始化应用 ====================

# 配置日志
setting_manager_temp = SettingManager()
setup_logging(setting_manager_temp.load())
logger = get_logger(__name__)

# 创建 Flask 应用
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['JSON_AS_ASCII'] = False
CORS(app)

# 配置 Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Proxy Manager API",
        "description": "代理管理系统 API 文档 - 提供代理、中转线路、VM账号、设备和地区管理等功能",
        "version": "1.0.0",
        "contact": {
            "name": "API Support"
        }
    },
    "host": "localhost:5000",
    "basePath": "/",
    "schemes": [
        "http",
        "https"
    ],
    "tags": [
        {"name": "代理管理", "description": "普通代理的增删改查操作"},
        {"name": "中转线路", "description": "中转线路的管理操作"},
        {"name": "VM账号", "description": "虚拟机账号的创建、加载、保存等操作"},
        {"name": "设备管理", "description": "Android设备的管理和配置"},
        {"name": "地区管理", "description": "地区代码和名称的管理"},
        {"name": "配置管理", "description": "系统路径和配置的管理"}
    ]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# ==================== 初始化核心组件 ====================

# 设置管理器（首先初始化，因为其他组件依赖它）
setting_manager = SettingManager()

# 路径管理器
path_manager = PathManager(setting_manager)

# 配置管理器
config_manager = ConfigManager(path_manager)

# ADB 辅助工具
adb_helper = ADBHelper(path_manager)

# ==================== 初始化服务层 ====================

proxy_service = ProxyService(config_manager, setting_manager, adb_helper)
transit_service = TransitService(config_manager, adb_helper, setting_manager)
vm_service = VMService(path_manager, adb_helper, setting_manager, config_manager)
device_service = DeviceService(adb_helper, setting_manager)
region_service = RegionService(setting_manager)

# ==================== 注册路由蓝图 ====================

app.register_blueprint(proxy_routes.create_blueprint(proxy_service))
app.register_blueprint(transit_routes.create_blueprint(transit_service))
app.register_blueprint(vm_routes.create_blueprint(vm_service))
app.register_blueprint(device_routes.create_blueprint(device_service))
app.register_blueprint(region_routes.create_blueprint(region_service))
app.register_blueprint(setting_routes.create_blueprint(path_manager, setting_manager))

# ==================== 中间件：请求日志记录 ====================

@app.before_request
def log_request():
    """记录所有请求信息"""
    logger.info("=" * 80)
    logger.info(f"📥 收到请求: {request.method} {request.path}")
    logger.info(f"   客户端: {request.remote_addr}")
    logger.info(f"   User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
    
    if request.method in ['POST', 'PUT', 'PATCH']:
        if request.is_json:
            # 记录请求体（敏感数据脱敏）
            data = request.get_json(silent=True) or {}
            sanitized_data = _sanitize_log_data(data.copy())
            logger.info(f"   请求数据: {sanitized_data}")
        elif request.form:
            logger.info(f"   表单数据: {dict(request.form)}")
    
    if request.args:
        logger.info(f"   查询参数: {dict(request.args)}")


@app.after_request
def log_response(response):
    """记录所有响应信息"""
    logger.info(f"📤 响应状态: {response.status_code} {response.status}")
    logger.info(f"   内容类型: {response.content_type}")
    
    # 记录响应体（仅 JSON，且限制长度）
    if response.content_type and 'application/json' in response.content_type:
        try:
            data = response.get_json()
            if data:
                success = data.get('success', 'N/A')
                logger.info(f"   响应结果: success={success}")
                if not data.get('success'):
                    error = data.get('error', 'Unknown')
                    logger.warning(f"   ❌ 错误信息: {error}")
        except:
            pass
    
    logger.info("=" * 80)
    return response


def _sanitize_log_data(data):
    """脱敏日志数据（隐藏密码等敏感信息）"""
    if isinstance(data, dict):
        for key in ['password', 'token', 'secret', 'api_key']:
            if key in data:
                data[key] = '******'
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                data[key] = _sanitize_log_data(value)
    elif isinstance(data, list):
        return [_sanitize_log_data(item) for item in data]
    return data


# ==================== 基础路由 ====================

@app.route('/')
def index():
    """
    主页
    ---
    tags:
      - 页面
    responses:
      200:
        description: 返回主页HTML
    """
    logger.info("🏠 访问主页")
    return render_template('proxy_manager.html')

# ==================== VM 操作的 SSE 流式接口 ====================
# 注意：这些接口涉及复杂的流式响应，从原 proxy_manager.py 迁移过来

@app.route('/api/vm/new', methods=['POST'])
def vm_create_account():
    """
    创建新的 VM 账号（SSE 流式响应）
    ---
    tags:
      - VM账号
    parameters:
      - name: body
        in: body
        required: true
        description: VM账号创建参数
        schema:
          type: object
          required:
            - name
            - app_type
            - node
            - region
          properties:
            name:
              type: string
              description: VM账号名称
              example: "TT_US_001"
            app_type:
              type: string
              description: 应用类型（如TT、IG等）
              example: "TT"
            node:
              type: string
              description: 代理节点名称
              example: "proxy_us_01"
            region:
              type: string
              description: 地区代码
              example: "US"
            device_id:
              type: string
              description: 设备ID（可选）
              example: "emulator-5554"
    responses:
      200:
        description: SSE流式响应，实时返回创建进度和日志
        schema:
          type: object
          properties:
            type:
              type: string
              enum: [log, success, error]
              description: 消息类型
            message:
              type: string
              description: 消息内容
    """
    import subprocess
    import shlex
    from datetime import datetime
    
    # ⚠️ 重要：在生成器外部获取请求数据，避免上下文错误
    data = request.json
    
    def generate(data):
        try:
            name = data.get('name', '').strip()
            app_type = data.get('app_type', '').strip()
            node = data.get('node', '').strip()
            region = data.get('region', '').strip().upper()
            device_id = data.get('device_id', '').strip()
            
            if not all([name, app_type, node, region]):
                yield f"data: {to_json({'type': 'error', 'message': '缺少必需参数'})}\n\n"
                return
            
            adb_path = path_manager.get_adb_path()
            vm_script_path = path_manager.get_vm_script_path()
            
            if not adb_path:
                yield f"data: {to_json({'type': 'error', 'message': 'ADB 路径未配置'})}\n\n"
                return
            
            # 构建 ADB 命令
            args = ['new', name, app_type, node, region]
            escaped_args = ' '.join([shlex.quote(arg) for arg in args])
            shell_cmd = f"su -c 'sh {vm_script_path} {escaped_args}'"
            
            cmd = [adb_path, 'shell', shell_cmd]
            if device_id:
                cmd = [adb_path, '-s', device_id, 'shell', shell_cmd]
            
            logger.info(f"执行 VM 创建命令: {' '.join(cmd)}")
            timestamp = datetime.now().strftime("%H:%M:%S")
            yield f"data: {to_json({'type': 'log', 'message': f'[{timestamp}] 开始创建 VM 账号: {name}'})}\n\n"
            
            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            # 实时读取输出
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield f"data: {to_json({'type': 'log', 'message': line.rstrip()})}\n\n"
            
            process.wait()
            
            # 检查返回码
            if process.returncode == 0:
                # 只有创建成功才更新计数器
                vm_service.increment_account_counter(app_type, region)
                yield f"data: {to_json({'type': 'success', 'message': f'VM 账号 {name} 创建成功'})}\n\n"
                logger.info(f"✅ VM 账号 '{name}' 创建成功")
            else:
                yield f"data: {to_json({'type': 'error', 'message': f'创建失败 (返回码: {process.returncode})'})}\n\n"
                logger.error(f"❌ VM 账号创建失败，返回码: {process.returncode}")
        
        except Exception as e:
            logger.error(f"VM 创建失败: {str(e)}", exc_info=True)
            yield f"data: {to_json({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(generate(data), mimetype='text/event-stream')


@app.route('/api/vm/save', methods=['POST'])
def vm_save_account():
    """
    保存 VM 账号（SSE 流式响应）
    ---
    tags:
      - VM账号
    parameters:
      - name: body
        in: body
        required: false
        description: 设备ID（可选）
        schema:
          type: object
          properties:
            device_id:
              type: string
              description: 设备ID
              example: "emulator-5554"
    responses:
      200:
        description: SSE流式响应，实时返回保存进度和日志
        schema:
          type: object
          properties:
            type:
              type: string
              enum: [log, success, error]
              description: 消息类型
            message:
              type: string
              description: 消息内容
    """
    import subprocess
    import shlex
    from datetime import datetime
    
    # ⚠️ 重要：在生成器外部获取请求数据
    data = request.json
    
    def generate(data):
        try:
            device_id = data.get('device_id', '').strip()
            
            # 先获取 AccountName
            timestamp = datetime.now().strftime("%H:%M:%S")
            yield f"data: {to_json({'type': 'log', 'message': f'[{timestamp}] 正在获取账号名称...'})}\n\n"
            success, account_name = vm_service.get_config_value('AccountName', device_id or None)
            
            if not success:
                yield f"data: {to_json({'type': 'error', 'message': f'获取账号名称失败: {account_name}'})}\n\n"
                return
            
            if not account_name:
                yield f"data: {to_json({'type': 'error', 'message': '账号名称为空'})}\n\n"
                return
            
            yield f"data: {to_json({'type': 'log', 'message': f'账号名称: {account_name}'})}\n\n"
            
            # 执行保存命令
            adb_path = path_manager.get_adb_path()
            vm_script_path = path_manager.get_vm_script_path()
            
            args = ['save', account_name]
            escaped_args = ' '.join([shlex.quote(arg) for arg in args])
            shell_cmd = f"su -c 'sh {vm_script_path} {escaped_args}'"
            
            cmd = [adb_path, 'shell', shell_cmd]
            if device_id:
                cmd = [adb_path, '-s', device_id, 'shell', shell_cmd]
            
            logger.info(f"执行 VM 保存命令: {' '.join(cmd)}")
            timestamp = datetime.now().strftime("%H:%M:%S")
            yield f"data: {to_json({'type': 'log', 'message': f'[{timestamp}] 开始保存账号: {account_name}'})}\n\n"
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield f"data: {to_json({'type': 'log', 'message': line.rstrip()})}\n\n"
            
            process.wait()
            
            if process.returncode == 0:
                yield f"data: {to_json({'type': 'success', 'message': f'账号 {account_name} 保存成功'})}\n\n"
                logger.info(f"✅ VM 账号 '{account_name}' 保存成功")
            else:
                yield f"data: {to_json({'type': 'error', 'message': f'保存失败 (返回码: {process.returncode})'})}\n\n"
        
        except Exception as e:
            logger.error(f"VM 保存失败: {str(e)}", exc_info=True)
            yield f"data: {to_json({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(generate(data), mimetype='text/event-stream')


@app.route('/api/vm/load', methods=['POST'])
def vm_load_account():
    """
    加载 VM 账号（SSE 流式响应）
    ---
    tags:
      - VM账号
    parameters:
      - name: body
        in: body
        required: true
        description: 加载账号参数
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
              description: 要加载的账号名称
              example: "TT_US_001"
            device_id:
              type: string
              description: 设备ID（可选）
              example: "emulator-5554"
    responses:
      200:
        description: SSE流式响应，实时返回加载进度和日志
        schema:
          type: object
          properties:
            type:
              type: string
              enum: [log, success, error]
              description: 消息类型
            message:
              type: string
              description: 消息内容
    """
    import subprocess
    import shlex
    from datetime import datetime
    
    # ⚠️ 重要：在生成器外部获取请求数据
    data = request.json

    def generate(data):
        try:
            name = data.get('name', '').strip()
            device_id = data.get('device_id', '').strip()
            logger.info(f"🔍 VM Load - Name: {name}, Device ID: {device_id or 'NOT PROVIDED'}")
            
            if not name:
                yield f"data: {to_json({'type': 'error', 'message': '账号名称不能为空'})}\n\n"
                return
            
            adb_path = path_manager.get_adb_path()
            vm_script_path = path_manager.get_vm_script_path()
            
            args = ['load', name]
            escaped_args = ' '.join([shlex.quote(arg) for arg in args])
            shell_cmd = f"su -c 'sh {vm_script_path} {escaped_args}'"
            
            cmd = [adb_path, 'shell', shell_cmd]
            if device_id:
                cmd = [adb_path, '-s', device_id, 'shell', shell_cmd]
            
            logger.info(f"执行 VM 加载命令: {' '.join(cmd)}")
            timestamp = datetime.now().strftime("%H:%M:%S")
            yield f"data: {to_json({'type': 'log', 'message': f'[{timestamp}] 开始加载账号: {name}'})}\n\n"
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield f"data: {to_json({'type': 'log', 'message': line.rstrip()})}\n\n"
            
            process.wait()
            
            if process.returncode == 0:
                yield f"data: {to_json({'type': 'success', 'message': f'账号 {name} 加载成功'})}\n\n"
                logger.info(f"✅ VM 账号 '{name}' 加载成功")
            else:
                yield f"data: {to_json({'type': 'error', 'message': f'加载失败 (返回码: {process.returncode})'})}\n\n"
        
        except Exception as e:
            logger.error(f"VM 加载失败: {str(e)}", exc_info=True)
            yield f"data: {to_json({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(generate(data), mimetype='text/event-stream')


# ==================== 应用启动 ====================

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🚀 Proxy Manager 应用启动")
    logger.info("=" * 70)
    logger.info(f"📂 工作目录: {os.getcwd()}")
    logger.info(f"📝 配置文件: {path_manager.get_config_file_path()}")
    logger.info(f"📱 ADB 路径: {path_manager.get_adb_path()}")
    logger.info(f"🔧 VM 脚本: {path_manager.get_vm_script_path()}")
    logger.info("=" * 70)
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("\n👋 应用已停止")
    except Exception as e:
        logger.error(f"❌ 应用运行失败: {str(e)}", exc_info=True)

