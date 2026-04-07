"""
Utilities — Logging setup and retry helpers.
No external data exfiltration. All logging is local.
"""

import logging
import time
import functools
from pathlib import Path
from . import config


def setup_logger(name: str = "copybot") -> logging.Logger:
    """Configure and return a logger that writes to both console and file."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    log_path = Path(config.LOG_FILE)
    fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator that retries a function with exponential backoff.
    Useful for flaky RPC calls and API requests.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger("copybot")
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(
                            f"[RETRY] {func.__name__} failed after {max_retries} attempts: {e}"
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        f"[RETRY] {func.__name__} attempt {attempt}/{max_retries} "
                        f"failed: {e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)

        return wrapper

    return decorator


def format_usdc(amount_wei: int) -> float:
    """Convert USDC amount from wei (6 decimals) to float."""
    return amount_wei / 1e6


def format_token_amount(amount_wei: int) -> float:
    """Convert conditional token amount from wei (6 decimals) to float."""
    return amount_wei / 1e6
