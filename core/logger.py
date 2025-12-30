"""
Logger Module - 日志系统配置
提供统一的日志配置和管理
"""

import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(setting_config):
    """
    配置日志系统（包括控制台和文件输出）
    
    Args:
        setting_config: 项目配置字典，包含 logging 配置项
    """
    logger = logging.getLogger(__name__)
    
    try:
        log_config = setting_config.get('logging', {})
        
        # 如果日志未启用，只配置控制台输出
        if not log_config.get('enabled', True):
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            logger.info("文件日志未启用，仅输出到控制台")
            return
        
        # 获取配置参数
        log_file = log_config.get('log_file', 'logs/proxy_manager.log')
        log_level_str = log_config.get('log_level', 'INFO')
        max_bytes = log_config.get('max_bytes', 10485760)  # 10MB
        backup_count = log_config.get('backup_count', 7)
        log_format = log_config.get('log_format', '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s')
        date_format = log_config.get('date_format', '%Y-%m-%d %H:%M:%S')
        
        # 转换日志级别
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        # 创建日志目录
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            print(f"创建日志目录: {log_dir}")
        
        # 创建格式化器
        formatter = logging.Formatter(log_format, datefmt=date_format)
        
        # 获取根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # 清除现有的处理器
        root_logger.handlers.clear()
        
        # 1. 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # 2. 文件处理器（带轮转）
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        logger.info("=" * 70)
        logger.info("📝 日志系统配置完成")
        logger.info(f"  - 日志文件: {log_file}")
        logger.info(f"  - 日志级别: {log_level_str}")
        logger.info(f"  - 单文件大小: {max_bytes / 1024 / 1024:.1f} MB")
        logger.info(f"  - 保留文件数: {backup_count}")
        logger.info(f"  - 控制台输出: 已启用")
        logger.info(f"  - 文件输出: 已启用")
        logger.info("=" * 70)
        
    except Exception as e:
        # 如果配置失败，使用基本配置
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logger.error(f"配置日志系统失败，使用默认配置: {str(e)}", exc_info=True)


def get_logger(name):
    """
    获取日志记录器
    
    Args:
        name: 模块名称
        
    Returns:
        Logger 实例
    """
    return logging.getLogger(name)

