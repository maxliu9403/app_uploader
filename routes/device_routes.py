"""
Device Routes - 设备管理 API 路由
"""

from flask import Blueprint, request, jsonify


def create_blueprint(device_service):
    """创建设备管理路由蓝图"""
    bp = Blueprint('device', __name__, url_prefix='/api')
    
    @bp.route('/devices', methods=['GET'])
    def get_devices():
        """
        获取已连接的设备列表
        ---
        tags:
          - 设备管理
        responses:
          200:
            description: 成功返回设备列表
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
                      device_id:
                        type: string
                        description: 设备ID
                        example: "emulator-5554"
                      remark:
                        type: string
                        description: 设备备注
                        example: "测试设备1"
                      status:
                        type: string
                        description: 设备状态
                        example: "device"
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
            success, data = device_service.get_devices()
            if success:
                return jsonify({'success': True, 'data': data})
            else:
                return jsonify({'success': False, 'error': data}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/device-configs', methods=['GET'])
    def get_device_configs():
        """
        获取已保存的设备配置
        ---
        tags:
          - 设备管理
        responses:
          200:
            description: 成功返回设备配置列表
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
                      device_id:
                        type: string
                        description: 设备ID
                        example: "emulator-5554"
                      remark:
                        type: string
                        description: 设备备注
                        example: "测试设备1"
          500:
            description: 服务器错误
        """
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
        """
        添加或更新设备配置
        ---
        tags:
          - 设备管理
        parameters:
          - name: body
            in: body
            required: true
            description: 设备配置信息
            schema:
              type: object
              required:
                - device_id
                - remark
              properties:
                device_id:
                  type: string
                  description: 设备ID
                  example: "emulator-5554"
                remark:
                  type: string
                  description: 设备备注
                  example: "测试设备1"
        responses:
          200:
            description: 设备配置保存成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "设备配置已保存"
                data:
                  type: object
                  properties:
                    device_id:
                      type: string
                      description: 设备ID
                    remark:
                      type: string
                      description: 设备备注
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
        """
        删除设备配置
        ---
        tags:
          - 设备管理
        parameters:
          - name: device_id
            in: path
            type: string
            required: true
            description: 设备ID
            example: "emulator-5554"
        responses:
          200:
            description: 设备配置删除成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "设备配置删除成功"
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
            success, error = device_service.delete_device_config(device_id)
            if success:
                return jsonify({'success': True, 'message': '设备配置删除成功'})
            else:
                return jsonify({'success': False, 'error': error}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/current-device', methods=['GET'])
    def get_current_device():
        try:
            success, data = device_service.get_current_device_id()
            if success:
                return jsonify({'success': True, 'data': {'device_id': data}})
            return jsonify({'success': False, 'error': data}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/current-device', methods=['POST'])
    def set_current_device():
        try:
            data = request.json or {}
            device_id = (data.get('device_id') or '').strip()
            success, result = device_service.set_current_device_id(device_id)
            if success:
                return jsonify({'success': True, 'data': result})
            return jsonify({'success': False, 'error': result}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return bp
