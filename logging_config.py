"""
Structured logging configuration for the SA Lotto AI Predictor.

Provides:
- File logging with rotation (detailed logs)
- Console logging (errors only by default, to not disrupt Rich output)
- Configurable verbosity levels
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


LOG_DIR = Path(__file__).parent / "logs"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    verbose: bool = False,
    debug: bool = False,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging for CLI-friendly output.

    Args:
        verbose: If True, show INFO level logs in console
        debug: If True, show DEBUG level logs (implies verbose)
        log_file: Custom log file path (default: logs/lotto_YYYYMMDD.log)

    Returns:
        Configured root logger
    """
    # Create logs directory
    LOG_DIR.mkdir(exist_ok=True)

    # Determine log file path
    if log_file:
        log_path = Path(log_file)
    else:
        log_path = LOG_DIR / f"lotto_{datetime.now().strftime('%Y%m%d')}.log"

    # File handler - detailed logs with rotation
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))

    # Console handler - minimal output to not disrupt Rich
    console_handler = logging.StreamHandler(sys.stderr)

    if debug:
        console_handler.setLevel(logging.DEBUG)
    elif verbose:
        console_handler.setLevel(logging.INFO)
    else:
        console_handler.setLevel(logging.ERROR)

    console_handler.setFormatter(logging.Formatter(
        "%(levelname)s: %(message)s"
    ))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    root_logger.info(f"Logging initialized. Log file: {log_path}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(name)


class CLILogHandler(logging.Handler):
    """
    Custom log handler that integrates with Rich console output.
    Only shows important messages as styled Rich output.
    """

    def __init__(self, console):
        super().__init__()
        self.console = console
        self.setLevel(logging.WARNING)

    def emit(self, record):
        try:
            msg = self.format(record)

            if record.levelno >= logging.ERROR:
                self.console.print(f"[red][ERROR][/red] {msg}")
            elif record.levelno >= logging.WARNING:
                self.console.print(f"[yellow][WARN][/yellow] {msg}")

        except Exception:
            self.handleError(record)


def cleanup_old_logs(max_age_days: int = 30) -> int:
    """
    Remove log files older than specified days.

    Args:
        max_age_days: Maximum age of log files to keep

    Returns:
        Number of files deleted
    """
    if not LOG_DIR.exists():
        return 0

    from datetime import timedelta

    cutoff = datetime.now() - timedelta(days=max_age_days)
    count = 0

    for log_file in LOG_DIR.glob("*.log*"):
        try:
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff:
                log_file.unlink()
                count += 1
        except Exception:
            pass

    return count
