"""
VM Routes - VM 管理 API 路由
注意：VM 操作涉及 SSE 流式响应，需要保留原 proxy_manager.py 中的实现逻辑
"""

from flask import Blueprint, request, jsonify, Response


def create_blueprint(vm_service):
    """创建 VM 管理路由蓝图"""
    bp = Blueprint('vm', __name__, url_prefix='/api/vm')
    
    @bp.route('/generate-account-name', methods=['GET'])
    def generate_account_name():
        """
        生成 VM 账号名称
        ---
        tags:
          - VM账号
        parameters:
          - name: app_type
            in: query
            type: string
            required: true
            description: 应用类型（如TT、IG等）
            example: "TT"
          - name: region
            in: query
            type: string
            required: true
            description: 地区代码
            example: "US"
        responses:
          200:
            description: 成功生成账号名称
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                data:
                  type: object
                  properties:
                    account_name:
                      type: string
                      description: 生成的账号名称
                      example: "TT_US_001"
          400:
            description: 缺少必需参数
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: false
                error:
                  type: string
                  example: "缺少必需参数"
          500:
            description: 服务器错误
        """
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
    
    @bp.route('/proxy-names', methods=['GET'])
    def get_proxy_names():
        """
        获取代理节点名称列表（根据地区过滤）
        ---
        tags:
          - VM账号
        parameters:
          - name: region
            in: query
            type: string
            required: false
            description: 地区代码（可选，用于过滤）
            example: "US"
        responses:
          200:
            description: 成功返回代理节点名称列表
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
                  description: 代理节点名称列表
                  example: ["proxy_us_01", "proxy_us_02"]
          500:
            description: 服务器错误
        """
        try:
            region = request.args.get('region', '').strip().upper()
            
            # 调用 vm_service 获取代理名称列表
            success, result = vm_service.get_proxy_names_by_region(region)
            if success:
                return jsonify({'success': True, 'data': result})
            else:
                return jsonify({'success': False, 'error': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/get-config-value', methods=['GET'])
    def get_config_value():
        """
        获取设备配置值
        ---
        tags:
          - VM账号
        parameters:
          - name: field_name
            in: query
            type: string
            required: true
            description: 配置字段名称
            example: "AccountName"
          - name: device_id
            in: query
            type: string
            required: false
            description: 设备ID（可选）
            example: "emulator-5554"
        responses:
          200:
            description: 成功获取配置值
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                data:
                  type: object
                  properties:
                    value:
                      type: string
                      description: 配置值
                      example: "TT_US_001"
          400:
            description: 缺少必需参数
          500:
            description: 服务器错误
        """
        try:
            field_name = request.args.get('field_name', '').strip()
            device_id = request.args.get('device_id', '').strip()
            
            if not field_name:
                return jsonify({'success': False, 'error': 'field_name 是必需的'}), 400
            
            success, result = vm_service.get_config_value(field_name, device_id or None)
            if success:
                # 包装成对象格式，符合前端期望的 data.value 结构
                return jsonify({'success': True, 'data': {'value': result}})
            else:
                return jsonify({'success': False, 'error': result}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/account-list', methods=['GET'])
    def get_account_list():
        """
        获取 VM 账号列表
        ---
        tags:
          - VM账号
        parameters:
          - name: device_id
            in: query
            type: string
            required: false
            description: 设备ID（可选）
            example: "emulator-5554"
        responses:
          200:
            description: 成功返回VM账号列表
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
                  description: VM账号名称列表
                  example: ["TT_US_001", "TT_US_002", "IG_JP_001"]
          500:
            description: 服务器错误
        """
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
