"""
Region Routes - 地区管理 API 路由
"""

from flask import Blueprint, request, jsonify


def create_blueprint(region_service):
    """创建地区管理路由蓝图"""
    bp = Blueprint('region', __name__, url_prefix='/api/regions')
    
    @bp.route('', methods=['GET'])
    def get_regions():
        """
        获取所有地区
        ---
        tags:
          - 地区管理
        responses:
          200:
            description: 成功返回地区列表
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
                      code:
                        type: string
                        description: 地区代码
                        example: "US"
                      name:
                        type: string
                        description: 地区名称
                        example: "美国"
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
            success, data = region_service.get_all_regions()
            if success:
                return jsonify({'success': True, 'data': data})
            else:
                return jsonify({'success': False, 'error': data}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('', methods=['POST'])
    def add_region():
        """
        添加新地区
        ---
        tags:
          - 地区管理
        parameters:
          - name: body
            in: body
            required: true
            description: 地区信息
            schema:
              type: object
              required:
                - code
                - name
              properties:
                code:
                  type: string
                  description: 地区代码（大写）
                  example: "US"
                name:
                  type: string
                  description: 地区名称
                  example: "美国"
        responses:
          200:
            description: 地区添加成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "地区添加成功"
                data:
                  type: object
                  properties:
                    code:
                      type: string
                      description: 地区代码
                    name:
                      type: string
                      description: 地区名称
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
            code = data.get('code', '').strip()
            name = data.get('name', '').strip()
            
            success, result = region_service.add_region(code, name)
            if success:
                return jsonify({
                    'success': True,
                    'message': '地区添加成功',
                    'data': result
                })
            else:
                return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/<string:code>', methods=['DELETE'])
    def delete_region(code):
        """
        删除地区
        ---
        tags:
          - 地区管理
        parameters:
          - name: code
            in: path
            type: string
            required: true
            description: 地区代码
            example: "US"
        responses:
          200:
            description: 地区删除成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "地区删除成功"
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
            success, error = region_service.delete_region(code)
            if success:
                return jsonify({'success': True, 'message': '地区删除成功'})
            else:
                return jsonify({'success': False, 'error': error}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return bp
