"""Logging utilities — Windows UTF-8 safe"""
import logging
import sys
import io
from datetime import datetime


def _make_utf8_stream(stream):
    """Wrap a stream so it never raises UnicodeEncodeError on Windows."""
    try:
        # If the stream already supports UTF-8 (e.g. redirected), use it directly
        if getattr(stream, 'encoding', '').lower() in ('utf-8', 'utf_8', 'utf8'):
            return stream
        # Wrap in a UTF-8 recoded writer (errors='replace' swaps bad chars with ?)
        return io.TextIOWrapper(
            stream.buffer if hasattr(stream, 'buffer') else stream,
            encoding='utf-8',
            errors='replace',
            line_buffering=True,
        )
    except Exception:
        return stream


def _sanitize(message: str) -> str:
    """Replace non-ASCII chars that would crash cp1252 with safe equivalents."""
    try:
        message.encode('cp1252')
        return message  # Already safe
    except (UnicodeEncodeError, AttributeError):
        return message.encode('ascii', 'replace').decode('ascii')


def setup_logger(name: str = "SmartStudyInstructor") -> logging.Logger:
    """Setup and return a configured logger with UTF-8 support on Windows."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Console handler — force UTF-8 wrapper on Windows
        safe_stdout = _make_utf8_stream(sys.stdout)
        console_handler = logging.StreamHandler(safe_stdout)
        console_handler.setLevel(logging.DEBUG)

        # File handler always UTF-8
        file_handler = logging.FileHandler("debug_server.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logger()


def log_info(message: str):
    """Log info message (Windows-safe)."""
    logger.info(_sanitize(str(message)))


def log_error(message: str, exc_info=False):
    """Log error message (Windows-safe)."""
    logger.error(_sanitize(str(message)), exc_info=exc_info)


def log_debug(message: str):
    """Log debug message (Windows-safe)."""
    logger.debug(_sanitize(str(message)))


def log_warning(message: str):
    """Log warning message (Windows-safe)."""
    logger.warning(_sanitize(str(message)))
