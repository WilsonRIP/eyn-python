from __future__ import annotations

from .browsers import (
    close_browsers,
    get_common_browser_app_names,
)
from .specs import detect_specs
from .net import network_info

__all__ = [
    "close_browsers",
    "get_common_browser_app_names",
    "detect_specs",
    "network_info",
]


