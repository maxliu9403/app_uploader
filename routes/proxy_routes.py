"""
Proxy Routes - 代理 API 路由
"""

from flask import Blueprint, request, jsonify


def create_blueprint(proxy_service):
    """创建代理路由蓝图"""
    bp = Blueprint('proxy', __name__, url_prefix='/api/proxies')
    
    @bp.route('', methods=['GET'])
    def get_proxies():
        """获取所有普通代理"""
        try:
            device_id = request.args.get('device_id')
            success, data = proxy_service.get_all_proxies(device_id)
            if success:
                return jsonify({'success': True, 'data': data})
            else:
                return jsonify({'success': False, 'error': data}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('', methods=['POST'])
    def add_proxy():
        """添加新代理"""
        try:
            data = request.json
            device_id = request.args.get('device_id')
            if not device_id:
                return jsonify({'success': False, 'error': 'device_id 是必传参数'}), 400
            success, result = proxy_service.add_proxy(data, device_id)
            if success:
                return jsonify({
                    'success': True,
                    'message': '代理添加成功',
                    'data': result.get('proxy'),
                    'push_result': result.get('push_result')
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/batch', methods=['POST'])
    def batch_add_proxies():
        """批量添加代理"""
        try:
            data = request.json
            device_id = request.args.get('device_id')
            if not device_id:
                return jsonify({'success': False, 'error': 'device_id 是必传参数'}), 400
            success, result = proxy_service.batch_add_proxies(data, device_id)
            if success:
                return jsonify({
                    'success': True,
                    'message': result.get('message'),
                    'data': {
                        'added_count': result.get('added_count'),
                        'failed_count': result.get('failed_count'),
                        'added_names': result.get('added_names'),
                        'failed_lines': result.get('failed_lines')
                    },
                    'push_result': result.get('push_result')
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/<int:index>', methods=['PUT'])
    def update_proxy(index):
        """更新代理（通过索引）"""
        try:
            data = request.json
            device_id = request.args.get('device_id')
            if not device_id:
                return jsonify({'success': False, 'error': 'device_id 是必传参数'}), 400
            success, result = proxy_service.update_proxy(index, data, device_id)
            if success:
                return jsonify({
                    'success': True,
                    'message': '代理更新成功',
                    'data': result.get('proxy'),
                    'push_result': result.get('push_result')
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/by-name/<string:proxy_name>', methods=['PUT'])
    def update_proxy_by_name(proxy_name):
        """更新代理（通过名称）"""
        try:
            data = request.json
            device_id = request.args.get('device_id')
            if not device_id:
                return jsonify({'success': False, 'error': 'device_id 是必传参数'}), 400
            success, result = proxy_service.update_proxy_by_name(proxy_name, data, device_id)
            if success:
                return jsonify({
                    'success': True,
                    'message': '代理更新成功',
                    'data': result.get('proxy'),
                    'push_result': result.get('push_result')
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/<int:index>', methods=['DELETE'])
    def delete_proxy(index):
        """删除代理（通过索引）"""
        try:
            device_id = request.args.get('device_id')
            if not device_id:
                return jsonify({'success': False, 'error': 'device_id 是必传参数'}), 400
            success, result = proxy_service.delete_proxy(index, device_id)
            if success:
                return jsonify({
                    'success': True,
                    'message': '代理删除成功',
                    'data': result.get('proxy'),
                    'push_result': result.get('push_result')
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/by-name/<string:proxy_name>', methods=['DELETE'])
    def delete_proxy_by_name(proxy_name):
        """删除代理（通过名称）"""
        try:
            device_id = request.args.get('device_id')
            if not device_id:
                return jsonify({'success': False, 'error': 'device_id 是必传参数'}), 400
            success, result = proxy_service.delete_proxy_by_name(proxy_name, device_id)
            if success:
                return jsonify({
                    'success': True,
                    'message': '代理删除成功',
                    'data': result.get('proxy'),
                    'push_result': result.get('push_result')
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/backup-lines/get-available', methods=['GET'])
    def get_available_backup_line():
        """获取可用备用线路"""
        try:
            device_id = request.args.get('device_id')
            region = request.args.get('region')
            
            if not device_id or not region:
                return jsonify({'success': False, 'error': 'device_id 和 region 是必传参数'}), 400
                
            success, result = proxy_service.get_available_backup_line(device_id, region)
            
            if success:
                return jsonify({'success': True, 'data': result})
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/backup-lines/occupancy', methods=['POST'])
    def update_line_occupancy():
        """更新线路占用状态"""
        try:
            data = request.json
            device_id = data.get('device_id')
            line_name = data.get('line_name')
            status = data.get('status')  # true=占用, false=释放
            region = data.get('region')
            
            if not device_id or not line_name:
                return jsonify({'success': False, 'error': 'device_id 和 line_name 是必传参数'}), 400
                
            if status is None:
                return jsonify({'success': False, 'error': 'status 是必传参数'}), 400
                
            success, result = proxy_service.update_line_occupancy(
                device_id, line_name, status, region
            )
            
            if success:
                return jsonify({'success': True, 'data': result})
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    return bp
