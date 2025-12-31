"""
Proxy Routes - 代理 API 路由
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from


def create_blueprint(proxy_service):
    """
    创建代理路由蓝图
    
    Args:
        proxy_service: ProxyService 实例
    """
    bp = Blueprint('proxy', __name__, url_prefix='/api/proxies')
    
    @bp.route('', methods=['GET'])
    def get_proxies():
        """
        获取所有普通代理
        ---
        tags:
          - 代理管理
        responses:
          200:
            description: 成功返回代理列表
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                data:
                  type: array
                  items:
                    type: object
                    properties:
                      name:
                        type: string
                        description: 代理名称
                      server:
                        type: string
                        description: 代理服务器地址
                      port:
                        type: integer
                        description: 代理端口
                      username:
                        type: string
                        description: 用户名
                      password:
                        type: string
                        description: 密码
                      region:
                        type: string
                        description: 地区代码
          500:
            description: 服务器错误
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: false
                error:
                  type: string
                  description: 错误信息
        """
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
        """
        添加新代理
        ---
        tags:
          - 代理管理
        parameters:
          - name: body
            in: body
            required: true
            description: 代理信息
            schema:
              type: object
              required:
                - name
                - server
                - port
                - username
                - password
                - region
              properties:
                name:
                  type: string
                  description: 代理名称
                  example: "proxy_us_01"
                server:
                  type: string
                  description: 代理服务器地址
                  example: "192.168.1.100"
                port:
                  type: integer
                  description: 代理端口
                  example: 1080
                username:
                  type: string
                  description: 用户名
                  example: "user123"
                password:
                  type: string
                  description: 密码
                  example: "pass123"
                region:
                  type: string
                  description: 地区代码
                  example: "US"
        responses:
          200:
            description: 代理添加成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "代理添加成功"
                data:
                  type: object
                  description: 添加的代理信息
                push_result:
                  type: object
                  description: 推送到设备的结果
          400:
            description: 请求参数错误
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: false
                error:
                  type: string
          500:
            description: 服务器错误
        """
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
        """
        批量添加代理
        ---
        tags:
          - 代理管理
        parameters:
          - name: body
            in: body
            required: true
            description: 批量代理信息（每行一个代理，格式：名称|服务器|端口|用户名|密码|地区）
            schema:
              type: object
              required:
                - proxy_list
              properties:
                proxy_list:
                  type: string
                  description: 代理列表，每行一个代理
                  example: "proxy_us_01|192.168.1.100|1080|user1|pass1|US\nproxy_us_02|192.168.1.101|1080|user2|pass2|US"
        responses:
          200:
            description: 批量添加成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "成功添加2个代理，失败0个"
                data:
                  type: object
                  properties:
                    added_count:
                      type: integer
                      description: 成功添加的数量
                    failed_count:
                      type: integer
                      description: 失败的数量
                    added_names:
                      type: array
                      items:
                        type: string
                      description: 成功添加的代理名称列表
                    failed_lines:
                      type: array
                      items:
                        type: string
                      description: 失败的行
                push_result:
                  type: object
                  description: 推送到设备的结果
          400:
            description: 请求参数错误
          500:
            description: 服务器错误
        """
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
        """
        更新代理（通过索引 - 仅用于向后兼容）
        ---
        tags:
          - 代理管理
        parameters:
          - name: index
            in: path
            type: integer
            required: true
            description: 代理索引
          - name: body
            in: body
            required: true
            description: 更新的代理信息
            schema:
              type: object
              properties:
                name:
                  type: string
                  description: 代理名称
                server:
                  type: string
                  description: 代理服务器地址
                port:
                  type: integer
                  description: 代理端口
                username:
                  type: string
                  description: 用户名
                password:
                  type: string
                  description: 密码
                region:
                  type: string
                  description: 地区代码
        responses:
          200:
            description: 代理更新成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "代理更新成功"
                data:
                  type: object
                  description: 更新后的代理信息
                push_result:
                  type: object
                  description: 推送到设备的结果
          400:
            description: 请求参数错误
          500:
            description: 服务器错误
        """
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
        """
        更新代理（通过名称 - 推荐使用）
        ---
        tags:
          - 代理管理
        parameters:
          - name: proxy_name
            in: path
            type: string
            required: true
            description: 代理名称
          - name: body
            in: body
            required: true
            description: 更新的代理信息
            schema:
              type: object
              properties:
                server:
                  type: string
                  description: 代理服务器地址
                port:
                  type: integer
                  description: 代理端口
                username:
                  type: string
                  description: 用户名
                password:
                  type: string
                  description: 密码
                region:
                  type: string
                  description: 地区代码
        responses:
          200:
            description: 代理更新成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "代理更新成功"
                data:
                  type: object
                  description: 更新后的代理信息
                push_result:
                  type: object
                  description: 推送到设备的结果
          400:
            description: 请求参数错误
          500:
            description: 服务器错误
        """
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
        """
        删除代理（通过索引 - 仅用于向后兼容）
        ---
        tags:
          - 代理管理
        parameters:
          - name: index
            in: path
            type: integer
            required: true
            description: 代理索引
        responses:
          200:
            description: 代理删除成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "代理删除成功"
                data:
                  type: object
                  description: 删除的代理信息
                push_result:
                  type: object
                  description: 推送到设备的结果
          400:
            description: 请求参数错误
          500:
            description: 服务器错误
        """
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
        """
        删除代理（通过名称 - 推荐使用）
        ---
        tags:
          - 代理管理
        parameters:
          - name: proxy_name
            in: path
            type: string
            required: true
            description: 代理名称
        responses:
          200:
            description: 代理删除成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "代理删除成功"
                data:
                  type: object
                  description: 删除的代理信息
                push_result:
                  type: object
                  description: 推送到设备的结果
          400:
            description: 请求参数错误
          500:
            description: 服务器错误
        """
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
