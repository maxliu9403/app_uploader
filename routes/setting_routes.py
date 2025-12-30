"""
Setting Routes - 配置管理 API 路由
"""

from flask import Blueprint, request, jsonify


def create_blueprint(path_manager, setting_manager):
    """创建配置管理路由蓝图"""
    bp = Blueprint('setting', __name__, url_prefix='/api')
    
    @bp.route('/path-settings', methods=['GET'])
    def get_path_settings():
        """获取所有路径配置"""
        try:
            settings = {
                'config_file_path': path_manager.get_config_file(),
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
        """更新路径配置"""
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

