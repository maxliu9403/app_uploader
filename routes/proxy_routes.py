"""
Proxy Routes - 代理 API 路由
"""

from flask import Blueprint, request, jsonify


def create_blueprint(proxy_service):
    """
    创建代理路由蓝图
    
    Args:
        proxy_service: ProxyService 实例
    """
    bp = Blueprint('proxy', __name__, url_prefix='/api/proxies')
    
    @bp.route('', methods=['GET'])
    def get_proxies():
        """获取所有普通代理"""
        try:
            success, data = proxy_service.get_all_proxies()
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
            success, result = proxy_service.add_proxy(data)
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
            success, result = proxy_service.batch_add_proxies(data)
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
        """更新代理（通过索引 - 仅用于向后兼容）"""
        try:
            data = request.json
            success, result = proxy_service.update_proxy(index, data)
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
        """更新代理（通过名称 - 推荐使用）"""
        try:
            data = request.json
            success, result = proxy_service.update_proxy_by_name(proxy_name, data)
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
        """删除代理（通过索引 - 仅用于向后兼容）"""
        try:
            success, result = proxy_service.delete_proxy(index)
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
        """删除代理（通过名称 - 推荐使用）"""
        try:
            success, result = proxy_service.delete_proxy_by_name(proxy_name)
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
    
    return bp

