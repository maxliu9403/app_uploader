"""
Transit Routes - 中转线路 API 路由
"""

from flask import Blueprint, request, jsonify


def create_blueprint(transit_service):
    """创建中转线路路由蓝图"""
    bp = Blueprint('transit', __name__, url_prefix='/api/transit-proxies')
    
    @bp.route('', methods=['GET'])
    def get_transits():
        """获取所有中转线路"""
        try:
            device_id = request.args.get('device_id')
            success, data = transit_service.get_all_transits(device_id)
            if success:
                return jsonify({'success': True, 'data': data})
            else:
                return jsonify({'success': False, 'error': data}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/names', methods=['GET'])
    def get_transit_names():
        """获取中转线路名称列表"""
        try:
            device_id = request.args.get('device_id')
            success, data = transit_service.get_transit_names(device_id)
            if success:
                return jsonify({'success': True, 'data': data})
            else:
                return jsonify({'success': False, 'error': data}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('', methods=['POST'])
    def add_transit():
        """添加中转线路"""
        try:
            data = request.json
            device_id = request.args.get('device_id')
            if not device_id:
                return jsonify({'success': False, 'error': 'device_id 是必传参数'}), 400
            success, result = transit_service.add_transit(data, device_id)
            if success:
                return jsonify({
                    'success': True,
                    'message': '中转线路添加成功',
                    'data': result.get('proxy'),
                    'push_result': result.get('push_result')
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/<int:index>', methods=['PUT'])
    def update_transit(index):
        """更新中转线路"""
        try:
            data = request.json
            device_id = request.args.get('device_id')
            if not device_id:
                return jsonify({'success': False, 'error': 'device_id 是必传参数'}), 400
            success, result = transit_service.update_transit(index, data, device_id)
            if success:
                return jsonify({
                    'success': True,
                    'message': '中转线路更新成功',
                    'data': result.get('proxy'),
                    'push_result': result.get('push_result')
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/<int:index>', methods=['DELETE'])
    def delete_transit(index):
        """删除中转线路"""
        try:
            device_id = request.args.get('device_id')
            if not device_id:
                return jsonify({'success': False, 'error': 'device_id 是必传参数'}), 400
            success, result = transit_service.delete_transit(index, device_id)
            if success:
                return jsonify({
                    'success': True,
                    'message': '中转线路删除成功',
                    'data': result.get('proxy'),
                    'push_result': result.get('push_result')
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return bp
