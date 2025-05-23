"""
Qbitcoin Logger - Production-grade logging system

This module provides a centralized logging configuration and custom logger 
factory for the Qbitcoin application. Features include:

- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Console and file logging with different formatting
- Log rotation based on size with backup count
- Structured logging with timestamps, log levels, and source information
- JSON formatting option for machine parsing
"""

import sys
import json
import logging
import logging.handlers
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Define log levels as constants
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

# Default log directory
DEFAULT_LOG_DIR = Path.home() / ".qbitcoin" / "logs"
DEFAULT_LOG_FILE = "qbitcoin.log"

# Default log format strings
DEFAULT_CONSOLE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
DEFAULT_JSON_FORMAT = {"timestamp": "%(asctime)s", "level": "%(levelname)s", 
                      "name": "%(name)s", "file": "%(filename)s", 
                      "line": "%(lineno)d", "message": "%(message)s"}

# Singleton dictionary to store logger instances
_loggers = {}


class JsonFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format"""
    
    def __init__(self, fmt_dict: Dict[str, str]):
        super().__init__()
        self.fmt_dict = fmt_dict
        
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string"""
        log_record = {}
        
        # Apply the format dictionary to the log record
        for key, value in self.fmt_dict.items():
            log_record[key] = value % record.__dict__
        
        # Add exception info if available
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_record)


def setup_logging(
    level: int = INFO,
    log_dir: Path = DEFAULT_LOG_DIR,
    log_file: str = DEFAULT_LOG_FILE,
    console: bool = True,
    file: bool = True,
    rotation_size_mb: int = 10,
    backup_count: int = 5,
    json_format: bool = False,
    add_timestamp_to_filename: bool = True,
) -> None:
    """
    Set up the global logging configuration.
    
    Args:
        level: The minimum log level to capture
        log_dir: Directory to store log files
        log_file: Base name of the log file
        console: Whether to enable console logging
        file: Whether to enable file logging
        rotation_size_mb: Maximum size of a log file in MB before rotation
        backup_count: Number of backup log files to keep
        json_format: Whether to format logs as JSON
        add_timestamp_to_filename: Whether to add a timestamp to the log filename
    """
    # Create log directory if it doesn't exist
    if file and log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to log filename if requested
        if add_timestamp_to_filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_parts = log_file.split('.')
            if len(filename_parts) > 1:
                log_file = f"{filename_parts[0]}_{timestamp}.{'.'.join(filename_parts[1:])}"
            else:
                log_file = f"{log_file}_{timestamp}"
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create and add handlers
    handlers = []
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        if json_format:
            console_handler.setFormatter(JsonFormatter(DEFAULT_JSON_FORMAT))
        else:
            console_handler.setFormatter(logging.Formatter(DEFAULT_CONSOLE_FORMAT))
        handlers.append(console_handler)
    
    # File handler with rotation
    if file and log_dir:
        log_path = log_dir / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, 
            maxBytes=rotation_size_mb * 1024 * 1024,
            backupCount=backup_count
        )
        file_handler.setLevel(level)
        if json_format:
            file_handler.setFormatter(JsonFormatter(DEFAULT_JSON_FORMAT))
        else:
            file_handler.setFormatter(logging.Formatter(DEFAULT_FILE_FORMAT))
        handlers.append(file_handler)
    
    # Add handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)


def get_logger(
    name: str, 
    level: Optional[int] = None,
    json_format: Optional[bool] = None
) -> logging.Logger:
    """
    Get or create a logger with the specified name.
    
    Args:
        name: The name of the logger, typically the module name
        level: Override the default log level for this logger
        json_format: Whether this logger should use JSON formatting
        
    Returns:
        logging.Logger: A configured logger instance
    """
    # Return existing logger if it exists
    if name in _loggers:
        logger = _loggers[name]
        if level is not None:
            logger.setLevel(level)
        return logger
    
    # Create a new logger
    logger = logging.getLogger(name)
    
    # Set specific level if provided
    if level is not None:
        logger.setLevel(level)
    
    # Store the logger for future reference
    _loggers[name] = logger
    
    # Configure JSON formatting if specified
    if json_format is not None and json_format:
        # Remove existing handlers and add a new one with JSON formatting
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter(DEFAULT_JSON_FORMAT))
        logger.addHandler(handler)
    
    return logger


class StructuredLogger:
    """
    A structured logger wrapper that adds context to log messages.
    Useful for adding consistent metadata to logs in specific components.
    """
    
    def __init__(
        self, 
        name: str, 
        context: Optional[Dict[str, Any]] = None,
        level: Optional[int] = None,
        json_format: bool = False
    ):
        """
        Initialize a structured logger with context.
        
        Args:
            name: Name of the logger
            context: Dictionary of context data to include in all logs
            level: Log level
            json_format: Whether to use JSON formatting
        """
        self.logger = get_logger(name, level, json_format)
        self.context = context or {}
        self.json_format = json_format
    
    def add_context(self, **kwargs) -> None:
        """Add additional context to this logger."""
        self.context.update(kwargs)
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Format a message with the context and additional kwargs for non-JSON logging."""
        if (not self.context and not kwargs) or self.json_format:
            return message
        
        # Combine permanent context and per-log context
        all_context = {**self.context, **kwargs}
        context_str = " ".join(f"{k}={v}" for k, v in all_context.items() if k != 'exc_info')
        return f"{message} [{context_str}]" if context_str else message
    
    def _log(self, level: int, message: str, *args, **kwargs) -> None:
        """Internal method to handle structured logging."""
        # Extract any standard logging parameters
        exc_info = kwargs.pop('exc_info', None)
        extra = kwargs.pop('extra', {})
        stack_info = kwargs.pop('stack_info', None)
        stacklevel = kwargs.pop('stacklevel', None)
        
        # Standard logging parameters
        log_kwargs = {}
        if exc_info is not None:
            log_kwargs['exc_info'] = exc_info
        if stack_info is not None:
            log_kwargs['stack_info'] = stack_info
        if stacklevel is not None:
            log_kwargs['stacklevel'] = stacklevel
            
        # For JSON logging, add context to the extra dict
        if self.json_format:
            combined_extra = {**extra, **self.context, **kwargs}
            log_kwargs['extra'] = combined_extra
            self.logger.log(level, message, *args, **log_kwargs)
        else:
            # For text logging, add context to the message
            formatted_message = self._format_message(message, **kwargs)
            if extra:
                log_kwargs['extra'] = extra
            self.logger.log(level, formatted_message, *args, **log_kwargs)
    
    def debug(self, message: str, *args, **kwargs) -> None:
        """Log a debug message."""
        self._log(DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs) -> None:
        """Log an info message."""
        self._log(INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs) -> None:
        """Log a warning message."""
        self._log(WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs) -> None:
        """Log an error message."""
        self._log(ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs) -> None:
        """Log a critical message."""
        self._log(CRITICAL, message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs) -> None:
        """Log an exception with traceback."""
        # Force exc_info=True to include the traceback
        kwargs['exc_info'] = True
        self._log(ERROR, message, *args, **kwargs)


# Setup a default configuration that sends logs to console only
# This can be overridden by calling setup_logging()
setup_logging(level=INFO, file=False)


# Create an alias for get_logger for backwards compatibility
create_logger = get_logger


# Example usage:
if __name__ == "__main__":
    # Configure logging
    setup_logging(
        level=DEBUG,
        file=True,
        rotation_size_mb=5,
        backup_count=3,
        json_format=False
    )
    
    # Get a simple logger
    logger = get_logger("example")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Get a structured logger
    slogger = StructuredLogger(
        "wallet",
        context={"user_id": "1234", "wallet_address": "QXjc3wU7fs..."}
    )
    slogger.info("Wallet created")
    
    # Add more context
    slogger.add_context(block_height=1024)
    slogger.warning("Low balance detected")
    
    # Log an exception with traceback
    try:
        1 / 0
    except Exception as e:
        slogger.exception(f"Error occurred: {e}")