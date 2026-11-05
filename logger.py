"""
Error logging module with weekly rotation
Fixed to use AppData folder for write permissions
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import traceback
import sys
import os

class ErrorLogger:
    """Handle error logging with rotation using AppData folder"""
    
    def __init__(self):
        # Determine the correct location for log files
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            app_name = "BybitDataFetcher"
            # Use AppData folder for Windows
            if os.name == 'nt':  # Windows
                app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
                self.log_dir = Path(app_data) / app_name / "logs"
            else:  # Linux/Mac
                self.log_dir = Path.home() / f".{app_name.lower()}" / "logs"
        else:
            # Running as script
            self.log_dir = Path("logs")
        
        # Create log directory with proper permissions
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fallback to temp folder if can't create in current location
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "BybitDataFetcher_logs"
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.log_dir = temp_dir
            print(f"Warning: Using temporary log location: {self.log_dir}")
        
        # Create logger
        self.logger = logging.getLogger('BybitFetcher')
        self.logger.setLevel(logging.ERROR)
        
        # Remove existing handlers to avoid duplicates
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with rotation
        log_file = self.log_dir / "error.log"
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=4
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.ERROR)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file: {e}")
        
        # Also add console handler for errors (helps with debugging)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.ERROR)
        self.logger.addHandler(console_handler)
    
    def log_error(self, error_message, error_details=None):
        """Log error with optional details"""
        try:
            if error_details:
                self.logger.error(f"{error_message}\nDetails: {error_details}")
            else:
                self.logger.error(error_message)
        except Exception:
            print(f"ERROR: {error_message}")
    
    def log_exception(self, exception, context=""):
        """Log exception with traceback"""
        try:
            error_msg = f"Exception in {context}: {str(exception)}"
            error_details = traceback.format_exc()
            self.logger.error(f"{error_msg}\n{error_details}")
        except Exception:
            print(f"EXCEPTION in {context}: {exception}")
            traceback.print_exc()
    
    def log_info(self, message):
        """Log info message (for debugging)"""
        try:
            info_logger = logging.getLogger('BybitFetcherInfo')
            info_logger.setLevel(logging.INFO)
            
            # Only add handler if not already added
            if not info_logger.handlers:
                log_file = self.log_dir / "info.log"
                handler = RotatingFileHandler(
                    log_file,
                    maxBytes=10*1024*1024,
                    backupCount=4
                )
                formatter = logging.Formatter(
                    '%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                handler.setFormatter(formatter)
                info_logger.addHandler(handler)
            
            info_logger.info(message)
        except Exception:
            print(f"INFO: {message}")