from __future__ import annotations

from typing import Dict, Optional

import psutil


def battery_info() -> Dict[str, Optional[object]]:
    try:
        b = psutil.sensors_battery()
    except Exception:
        b = None
    if not b:
        return {"present": False}
    return {
        "present": True,
        "percent": b.percent,
        "plugged": b.power_plugged,
        "secs_left": b.secsleft,
    }


