"""
KarianaUMCP Logging Configuration
=================================
Centralized logging that outputs to stderr (not stdout) for MCP stdio transport compatibility.
Also logs to Unreal Engine output when running inside UE.
"""
import logging
import sys
from typing import Optional

# Module-level logger cache to prevent duplicate handlers
_loggers = {}

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a configured logger that outputs to stderr.

    Args:
        name: Logger name (typically __name__ of the calling module)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    full_name = f"KarianaUMCP.{name}" if not name.startswith("KarianaUMCP") else name

    if full_name in _loggers:
        return _loggers[full_name]

    logger = logging.getLogger(full_name)
    logger.setLevel(level)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    # Only add handler if none exist
    if not logger.handlers:
        # Stderr handler for MCP compatibility
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(level)
        stderr_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(stderr_handler)

        # Try to add Unreal log handler if available
        try:
            import unreal
            unreal_handler = UnrealLogHandler()
            unreal_handler.setLevel(level)
            unreal_handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(unreal_handler)
        except ImportError:
            pass

    _loggers[full_name] = logger
    return logger


class UnrealLogHandler(logging.Handler):
    """
    Custom logging handler that routes logs to Unreal Engine's output log.
    Uses appropriate log levels (log, log_warning, log_error).
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to Unreal's logging system."""
        try:
            import unreal
            msg = self.format(record)

            # Route to appropriate Unreal log function based on level
            if record.levelno >= logging.ERROR:
                unreal.log_error(f"[KarianaUMCP] {msg}")
            elif record.levelno >= logging.WARNING:
                unreal.log_warning(f"[KarianaUMCP] {msg}")
            else:
                unreal.log(f"[KarianaUMCP] {msg}")
        except Exception:
            # Silently ignore if Unreal not available or error occurs
            pass


def configure_root_logger(level: int = logging.INFO) -> None:
    """
    Configure the root KarianaUMCP logger.
    Call this once at startup to set up base logging configuration.
    """
    root = get_logger("root", level)
    root.info("KarianaUMCP logging initialized")


# Convenience functions for quick logging without getting a logger first
_default_logger: Optional[logging.Logger] = None

def _get_default_logger() -> logging.Logger:
    """Get or create the default logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger("default")
    return _default_logger

def log_info(msg: str) -> None:
    """Log an info message using the default logger."""
    _get_default_logger().info(msg)

def log_warning(msg: str) -> None:
    """Log a warning message using the default logger."""
    _get_default_logger().warning(msg)

def log_error(msg: str, exc_info: bool = False) -> None:
    """Log an error message using the default logger."""
    _get_default_logger().error(msg, exc_info=exc_info)

def log_debug(msg: str) -> None:
    """Log a debug message using the default logger."""
    _get_default_logger().debug(msg)

def log_exception(msg: str) -> None:
    """Log an exception with traceback using the default logger."""
    _get_default_logger().exception(msg)
