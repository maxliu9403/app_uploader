"""
VM Routes - VM 管理 API 路由
"""

from flask import Blueprint, request, jsonify


def create_blueprint(vm_service):
    """创建 VM 管理路由蓝图"""
    bp = Blueprint('vm', __name__, url_prefix='/api/vm')
    
    @bp.route('/generate-account-name', methods=['GET'])
    def generate_account_name():
        """生成 VM 账号名称"""
        try:
            app_type = request.args.get('app_type', '').strip()
            region = request.args.get('region', '').strip().upper()
            device_id = request.args.get('device_id', '').strip()
            device_remark = request.args.get('device_remark', '').strip()
            
            if not app_type or not region:
                return jsonify({'success': False, 'error': '缺少必需参数'}), 400
            
            success, result = vm_service.generate_account_name(
                app_type, region, device_id or None, device_remark or None
            )
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
                return jsonify({'success': True, 'data': {'value': result}})
            else:
                return jsonify({'success': False, 'error': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/account-list', methods=['GET'])
    def get_account_list():
        """获取 VM 账号列表（支持过滤）"""
        try:
            device_id = request.args.get('device_id', '').strip()
            app_type = request.args.get('app_type', '').strip()
            region = request.args.get('region', '').strip()
            success, result = vm_service.get_account_list(
                device_id=device_id or None,
                app_type=app_type or None,
                region=region or None
            )
            if success:
                return jsonify({'success': True, 'data': result})
            else:
                return jsonify({'success': False, 'error': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return bp
