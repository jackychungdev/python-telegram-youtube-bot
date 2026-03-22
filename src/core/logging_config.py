"""
Logging configuration module

Sets up centralized logging with file rotation and console output.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_file: str = 'bot.log', max_size_mb: int = 10, 
                  level: int = logging.INFO, backup_count: int = 3):
    """Setup logging configuration with file rotation.
    
    Args:
        log_file: Path to log file
        max_size_mb: Maximum log file size in MB before rotation
        level: Logging level (default: INFO)
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured logger instance
    """
    log_path = Path(log_file)
    
    # Create formatter with timestamp and component name
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Setup file handler with rotation
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Reduce noise from external libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)
    logging.getLogger('aiocache').setLevel(logging.WARNING)
    
    return logger
