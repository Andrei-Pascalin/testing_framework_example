import logging
import sys
from pathlib import Path
from typing import Optional

# asta e generata de claudelu ... mititelu, manca-lar ... sa-l mânce...

class ProjectLogger:
    """
    Centralized logging for the project.
    Logs to both stdout and a file in project_root/logs/
    """
    _instance = None
    _loggers = {}

    def __new__(cls):
        """Singleton pattern — maintain one logger per file."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_logger(cls, name: str = "runner", log_filename: str = "runner.log") -> logging.Logger:
        """
        Get or create a logger with the specified name and log file.

        Args:
            name: Logger identifier (e.g., "runner", "tests", "server")
            log_filename: Log file name (default: "runner.log")

        Returns:
            logging.Logger: Configured logger instance
        """
        logger_key = f"{name}:{log_filename}"

        # Return cached logger if already configured
        if logger_key in cls._loggers:
            return cls._loggers[logger_key]

        # Create logs directory if it doesn't exist
        project_root = Path(__file__).parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()

        # Format for log messages
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Stream handler (stdout)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # File handler
        log_file = logs_dir / log_filename
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Prevent propagation to root logger
        logger.propagate = False

        # Cache the logger
        cls._loggers[logger_key] = logger

        return logger


def get_logger(name: str = "runner", log_filename: str = "runner.log") -> logging.Logger:
    """
    Convenience function to get a logger.

    Usage:
        from utils.my_logger import get_logger
        log = get_logger()
        log.info("Server started")
    """
    return ProjectLogger.get_logger(name, log_filename)
