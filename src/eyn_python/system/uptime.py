from __future__ import annotations

import os
import time
from typing import Dict, Optional

import psutil


def _format_duration(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def uptime_info() -> Dict[str, object]:
    bt = psutil.boot_time()
    now = time.time()
    uptime_sec = max(0.0, now - bt)

    load1: Optional[float] = None
    load5: Optional[float] = None
    load15: Optional[float] = None
    try:
        l1, l5, l15 = os.getloadavg()  # type: ignore[attr-defined]
        load1, load5, load15 = float(l1), float(l5), float(l15)
    except Exception:
        pass

    return {
        "boot_time": int(bt),
        "uptime_seconds": int(uptime_sec),
        "uptime_human": _format_duration(uptime_sec),
        "load": {
            "1m": load1,
            "5m": load5,
            "15m": load15,
        },
    }


