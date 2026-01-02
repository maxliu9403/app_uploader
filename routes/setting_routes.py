"""
Setting Routes - 配置管理 API 路由
"""

from flask import Blueprint, request, jsonify


def create_blueprint(path_manager, setting_manager):
    """创建配置管理路由蓝图"""
    bp = Blueprint('setting', __name__, url_prefix='/api')
    
    @bp.route('/path-settings', methods=['GET'])
    def get_path_settings():
        """
        获取所有路径配置
        ---
        tags:
          - 配置管理
        responses:
          200:
            description: 成功返回路径配置
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                data:
                  type: object
                  properties:
                    config_file_path:
                      type: string
                      description: 配置文件路径
                      example: "D:/app_uploader/config.yaml"
                    vm_script_path:
                      type: string
                      description: VM脚本路径
                      example: "/data/local/tmp/vm.sh"
                    adb_path:
                      type: string
                      description: ADB工具路径
                      example: "D:/platform-tools/adb.exe"
                    vm_accounts_file_path:
                      type: string
                      description: VM账号文件路径
                      example: "/sdcard/vm_accounts.txt"
                    vm_model_config_path:
                      type: string
                      description: VM模型配置路径
                      example: "/data/data/bin.mt.plus/model.conf"
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
            settings = {
                'config_file_path': path_manager.get_config_file_path(),
                'vm_script_path': path_manager.get_vm_script_path(),
                'adb_path': path_manager.get_adb_path(),
                'vm_accounts_file_path': path_manager.get_vm_accounts_file_path(),
                'vm_model_config_path': path_manager.get_vm_model_config_path()
            }
            return jsonify({'success': True, 'data': settings})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/path-settings', methods=['POST'])
    def update_path_settings():
        """
        更新路径配置
        ---
        tags:
          - 配置管理
        parameters:
          - name: body
            in: body
            required: true
            description: 路径配置信息（可选字段，只更新提供的字段）
            schema:
              type: object
              properties:
                config_file_path:
                  type: string
                  description: 配置文件路径
                  example: "D:/app_uploader/config.yaml"
                vm_script_path:
                  type: string
                  description: VM脚本路径
                  example: "/data/local/tmp/vm.sh"
                adb_path:
                  type: string
                  description: ADB工具路径
                  example: "D:/platform-tools/adb.exe"
                vm_accounts_file_path:
                  type: string
                  description: VM账号文件路径
                  example: "/sdcard/vm_accounts.txt"
                vm_model_config_path:
                  type: string
                  description: VM模型配置路径
                  example: "/data/data/bin.mt.plus/model.conf"
        responses:
          200:
            description: 路径配置更新成功
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                message:
                  type: string
                  example: "路径配置已更新"
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
        """
        try:
            data = request.json
            setting = setting_manager.load()
            
            if 'config_file_path' in data:
                setting['config_file_path'] = data['config_file_path']
            if 'vm_script_path' in data:
                setting['vm_script_path'] = data['vm_script_path']
            if 'adb_path' in data:
                setting['adb_path'] = data['adb_path']
            if 'vm_accounts_file_path' in data:
                setting['vm_accounts_file_path'] = data['vm_accounts_file_path']
            if 'vm_model_config_path' in data:
                setting['vm_model_config_path'] = data['vm_model_config_path']
            
            setting_manager.save(setting)
            path_manager.clear_cache()
            
            return jsonify({'success': True, 'message': '路径配置已更新'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return bp
