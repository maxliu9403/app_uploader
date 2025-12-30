"""
VM Routes - VM 管理 API 路由
注意：VM 操作涉及 SSE 流式响应，需要保留原 proxy_manager.py 中的实现逻辑
"""

from flask import Blueprint, request, jsonify, Response


def create_blueprint(vm_service):
    """创建 VM 管理路由蓝图"""
    bp = Blueprint('vm', __name__, url_prefix='/api/vm')
    
    @bp.route('/generate-name', methods=['GET'])
    def generate_name():
        """生成 VM 账号名称"""
        try:
            app_type = request.args.get('app_type', '').strip()
            region = request.args.get('region', '').strip().upper()
            
            if not app_type or not region:
                return jsonify({'success': False, 'error': '缺少必需参数'}), 400
            
            success, result = vm_service.generate_account_name(app_type, region)
            if success:
                return jsonify({'success': True, 'data': result})
            else:
                return jsonify({'success': False, 'error': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/get-config-value', methods=['GET'])
    def get_config_value():
        """获取设备配置值"""
        try:
            field_name = request.args.get('field_name', '').strip()
            device_id = request.args.get('device_id', '').strip()
            
            if not field_name:
                return jsonify({'success': False, 'error': 'field_name 是必需的'}), 400
            
            success, result = vm_service.get_config_value(field_name, device_id or None)
            if success:
                return jsonify({'success': True, 'data': result})
            else:
                return jsonify({'success': False, 'error': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/account-list', methods=['GET'])
    def get_account_list():
        """获取 VM 账号列表"""
        try:
            device_id = request.args.get('device_id', '').strip()
            success, result = vm_service.get_account_list(device_id or None)
            if success:
                return jsonify({'success': True, 'data': result})
            else:
                return jsonify({'success': False, 'error': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # 注意：/new、/save、/load 等涉及 SSE 流式响应的接口
    # 建议保留原 proxy_manager.py 中的实现，因为它们依赖于复杂的流式逻辑
    # 这里仅提供基础接口作为示例
    
    return bp

