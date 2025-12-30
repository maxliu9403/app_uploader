"""
Device Routes - 设备管理 API 路由
"""

from flask import Blueprint, request, jsonify


def create_blueprint(device_service):
    """创建设备管理路由蓝图"""
    bp = Blueprint('device', __name__, url_prefix='/api')
    
    @bp.route('/devices', methods=['GET'])
    def get_devices():
        """获取已连接的设备列表"""
        try:
            success, data = device_service.get_devices()
            if success:
                return jsonify({'success': True, 'data': data})
            else:
                return jsonify({'success': False, 'error': data}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/device-configs', methods=['GET'])
    def get_device_configs():
        """获取已保存的设备配置"""
        try:
            success, data = device_service.get_device_configs()
            if success:
                return jsonify({'success': True, 'data': data})
            else:
                return jsonify({'success': False, 'error': data}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/device-configs', methods=['POST'])
    def add_device_config():
        """添加或更新设备配置"""
        try:
            data = request.json
            device_id = data.get('device_id', '').strip()
            remark = data.get('remark', '').strip()
            
            success, result = device_service.save_device_config(device_id, remark)
            if success:
                return jsonify({
                    'success': True,
                    'message': '设备配置已保存',
                    'data': result
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/device-configs/<string:device_id>', methods=['DELETE'])
    def delete_device_config(device_id):
        """删除设备配置"""
        try:
            success, error = device_service.delete_device_config(device_id)
            if success:
                return jsonify({'success': True, 'message': '设备配置删除成功'})
            else:
                return jsonify({'success': False, 'error': error}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return bp

