"""
Logger Setup Module
==================
Handles console and file logging configurations with color codes.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from colorlog import ColoredFormatter

def setup_logger(name: str, log_level: str = "INFO", log_dir: str = "./logs") -> logging.Logger:
    """Sets up a logger with a rotating file handler and a color console handler."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(log_level)
    
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Color Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    console_format = (
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s"
    )
    console_formatter = ColoredFormatter(
        console_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File Handler (rotating)
    file_path = os.path.join(log_dir, f"{name}.log")
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Returns an existing logger or sets up a new one."""
    return setup_logger(name, os.getenv("LOG_LEVEL", "INFO"), os.getenv("LOG_DIR", "./logs"))
