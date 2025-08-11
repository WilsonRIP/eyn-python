from __future__ import annotations

from rich.console import Console
from rich.logging import RichHandler
import logging

_console = Console()

def get_logger(name: str = "eyn") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RichHandler(console=_console, show_time=True, show_level=True, show_path=False)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger

def console() -> Console:
    return _console


