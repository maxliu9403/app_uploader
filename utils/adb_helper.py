"""
ADB Helper - ADB 命令辅助模块
封装所有 ADB 相关的操作
"""

import os
import subprocess
from core.logger import get_logger

logger = get_logger(__name__)


class ADBHelper:
    """ADB 命令辅助类"""
    
    def __init__(self, path_manager):
        """
        初始化 ADB Helper
        
        Args:
            path_manager: PathManager 实例
        """
        self.path_manager = path_manager
    
    def get_adb_path(self):
        """获取 ADB 路径"""
        return self.path_manager.get_adb_path()
    
    def get_devices(self):
        """
        获取已连接的设备列表
        
        Returns:
            list: 设备列表，每个元素为 {'id': device_id, 'status': status}
        """
        adb_path = self.get_adb_path()
        
        if not adb_path or not os.path.exists(adb_path):
            logger.error(f"ADB路径未配置或不存在: {adb_path}")
            return []
        
        try:
            result = subprocess.run(
                [adb_path, 'devices'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            
            if result.returncode != 0:
                logger.error(f"获取设备列表失败: {result.stderr}")
                return []
            
            devices = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines[1:]:  # 跳过第一行 "List of devices attached"
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 2:
                    device_id = parts[0].strip()
                    status = parts[1].strip()
                    devices.append({'id': device_id, 'status': status})
                elif len(parts) == 1 and parts[0].strip():
                    device_id = parts[0].strip()
                    devices.append({'id': device_id, 'status': 'unknown'})
            
            logger.info(f"找到 {len(devices)} 个设备")
            return devices
            
        except subprocess.TimeoutExpired:
            logger.error("获取设备列表超时")
            return []
        except Exception as e:
            logger.error(f"获取设备列表失败: {str(e)}", exc_info=True)
            return []
    
    def push_file(self, local_path, remote_path, device_id=None, use_su=True):
        """
        推送文件到设备
        
        Args:
            local_path: 本地文件路径
            remote_path: 设备上的目标路径
            device_id: 设备ID（可选）
            use_su: 是否使用 su 权限
            
        Returns:
            tuple: (success, message)
        """
        adb_path = self.get_adb_path()
        
        if not adb_path or not os.path.exists(adb_path):
            return False, "ADB路径未配置或不存在"
        
        if not os.path.exists(local_path):
            return False, f"本地文件不存在: {local_path}"
        
        try:
            # 步骤1: 先推送到临时目录 /sdcard/
            temp_path = f'/sdcard/{os.path.basename(local_path)}'
            push_cmd = [adb_path]
            
            if device_id:
                push_cmd.extend(['-s', device_id])
            
            push_cmd.extend(['push', local_path, temp_path])
            
            push_result = subprocess.run(
                push_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )
            
            if push_result.returncode != 0:
                error_msg = push_result.stderr.strip()
                return False, f"推送到临时目录失败: {error_msg}"
            
            if use_su:
                # 步骤2: 创建目标目录
                mkdir_cmd = [adb_path]
                if device_id:
                    mkdir_cmd.extend(['-s', device_id])
                
                target_dir = os.path.dirname(remote_path)
                mkdir_cmd.extend(['shell', 'su', '-c', f'mkdir -p {target_dir}'])
                
                subprocess.run(mkdir_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                
                # 步骤3: 使用 su 权限移动文件
                mv_cmd = [adb_path]
                if device_id:
                    mv_cmd.extend(['-s', device_id])
                
                mv_cmd.extend(['shell', 'su', '-c', f'cp {temp_path} {remote_path}'])
                
                mv_result = subprocess.run(
                    mv_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace',
                    timeout=10
                )
                
                if mv_result.returncode != 0:
                    error_msg = mv_result.stderr.strip() if mv_result.stderr else mv_result.stdout.strip()
                    return False, f"移动文件失败: {error_msg}"
                
                # 清理临时文件
                subprocess.run(
                    [adb_path] + (['-s', device_id] if device_id else []) + ['shell', 'rm', temp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
            
            return True, "推送成功"
            
        except subprocess.TimeoutExpired:
            return False, "推送超时"
        except Exception as e:
            return False, f"推送失败: {str(e)}"
    
    def execute_shell_command(self, command, device_id=None, use_su=False, timeout=10):
        """
        执行 shell 命令
        
        Args:
            command: shell 命令
            device_id: 设备ID（可选）
            use_su: 是否使用 su 权限
            timeout: 超时时间（秒）
            
        Returns:
            tuple: (returncode, stdout, stderr)
        """
        adb_path = self.get_adb_path()
        
        if not adb_path or not os.path.exists(adb_path):
            return -1, "", "ADB路径未配置或不存在"
        
        try:
            adb_cmd = [adb_path]
            
            if device_id:
                adb_cmd.extend(['-s', device_id])
            
            if use_su:
                adb_cmd.extend(['shell', 'su', '-c', command])
            else:
                adb_cmd.extend(['shell', command])
            
            # 🔥 记录完整的ADB命令到日志
            cmd_str = ' '.join(adb_cmd)
            logger.info(f"🔧 执行ADB命令: {cmd_str}")
            
            result = subprocess.run(
                adb_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            
            # 记录命令结果
            logger.info(f"   └─ 返回码: {result.returncode}")
            if result.stdout and len(result.stdout.strip()) > 0:
                stdout_preview = result.stdout[:200] if len(result.stdout) > 200 else result.stdout
                logger.info(f"   └─ 输出: {stdout_preview}")
            if result.stderr and len(result.stderr.strip()) > 0:
                stderr_preview = result.stderr[:200] if len(result.stderr) > 200 else result.stderr
                logger.warning(f"   └─ 错误: {stderr_preview}")
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ ADB命令执行超时 (>{timeout}s)")
            return -1, "", "命令执行超时"
        except Exception as e:
            logger.error(f"❌ ADB命令执行异常: {str(e)}")
            return -1, "", str(e)

