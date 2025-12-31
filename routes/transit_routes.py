"""
Transit Routes - 中转线路 API 路由
"""

from flask import Blueprint, request, jsonify


def create_blueprint(transit_service):
    """创建中转线路路由蓝图"""
    bp = Blueprint('transit', __name__, url_prefix='/api/transit-proxies')
    
    @bp.route('', methods=['GET'])
    def get_transits():
        """
        获取所有中转线路
        ---
        tags:
          - 中转线路
        responses:
          200:
            description: 成功返回中转线路列表
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
                        description: 中转线路名称
                      server:
                        type: string
                        description: 中转服务器地址
                      port:
                        type: integer
                        description: 中转端口
                      username:
                        type: string
                        description: 用户名
                      password:
                        type: string
                        description: 密码
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
            success, data = transit_service.get_all_transits()
            if success:
                return jsonify({'success': True, 'data': data})
            else:
                return jsonify({'success': False, 'error': data}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/names', methods=['GET'])
    def get_transit_names():
        """
        获取中转线路名称列表
        ---
        tags:
          - 中转线路
        responses:
          200:
            description: 成功返回中转线路名称列表
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                data:
                  type: array
                  items:
                    type: string
                  description: 中转线路名称列表
                  example: ["transit_us_01", "transit_jp_01"]
          500:
            description: 服务器错误
        """
        try:
            success, data = transit_service.get_transit_names()
            if success:
                return jsonify({'success': True, 'data': data})
            else:
                return jsonify({'success': False, 'error': data}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('', methods=['POST'])
    def add_transit():
        """
        添加中转线路
        ---
        tags:
          - 中转线路
        parameters:
          - name: body
            in: body
            required: true
            description: 中转线路信息
            schema:
              type: object
              required:
                - name
                - server
                - port
                - username
                - password
              properties:
                name:
                  type: string
                  description: 中转线路名称
                  example: "transit_us_01"
                server:
                  type: string
                  description: 中转服务器地址
                  example: "192.168.1.200"
                port:
                  type: integer
                  description: 中转端口
                  example: 8080
                username:
                  type: string
                  description: 用户名
                  example: "transit_user"
                password:
                  type: string
                  description: 密码
                  example: "transit_pass"
        responses:
          200:
            description: 中转线路添加成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "中转线路添加成功"
                data:
                  type: object
                  description: 添加的中转线路信息
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
            success, result = transit_service.add_transit(data)
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
        """
        更新中转线路
        ---
        tags:
          - 中转线路
        parameters:
          - name: index
            in: path
            type: integer
            required: true
            description: 中转线路索引
          - name: body
            in: body
            required: true
            description: 更新的中转线路信息
            schema:
              type: object
              properties:
                name:
                  type: string
                  description: 中转线路名称
                server:
                  type: string
                  description: 中转服务器地址
                port:
                  type: integer
                  description: 中转端口
                username:
                  type: string
                  description: 用户名
                password:
                  type: string
                  description: 密码
        responses:
          200:
            description: 中转线路更新成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "中转线路更新成功"
                data:
                  type: object
                  description: 更新后的中转线路信息
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
            success, result = transit_service.update_transit(index, data)
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
        """
        删除中转线路
        ---
        tags:
          - 中转线路
        parameters:
          - name: index
            in: path
            type: integer
            required: true
            description: 中转线路索引
        responses:
          200:
            description: 中转线路删除成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "中转线路删除成功"
                data:
                  type: object
                  description: 删除的中转线路信息
                push_result:
                  type: object
                  description: 推送到设备的结果
          400:
            description: 请求参数错误
          500:
            description: 服务器错误
        """
        try:
            success, result = transit_service.delete_transit(index)
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
