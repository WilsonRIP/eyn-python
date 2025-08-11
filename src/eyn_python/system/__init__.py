from __future__ import annotations

from .browsers import (
    close_browsers,
    get_common_browser_app_names,
)
from .specs import detect_specs
from .net import network_info
from .uptime import uptime_info
from .disk import partitions_info
from .procs import top_processes
from .power import battery_info
from .thermal import temperatures_info
from .ports import listening_ports
from .net_ext import public_ip, http_latency
from .tempfiles import TempCleanSettings, default_temp_dir, clean_temp

__all__ = [
    "close_browsers",
    "get_common_browser_app_names",
    "detect_specs",
    "network_info",
    "uptime_info",
    "partitions_info",
    "top_processes",
    "battery_info",
    "temperatures_info",
    "listening_ports",
    "public_ip",
    "http_latency",
    "TempCleanSettings",
    "default_temp_dir",
    "clean_temp",
]


