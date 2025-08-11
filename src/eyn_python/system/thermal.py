from __future__ import annotations

from typing import Any, Dict, List

import psutil


def temperatures_info() -> Dict[str, List[Dict[str, object]]]:
    out: Dict[str, List[Dict[str, object]]] = {}
    try:
        sensors_func: Any = getattr(psutil, "sensors_temperatures", None)
        temps = sensors_func(fahrenheit=False) if sensors_func else {}
    except Exception:
        temps = {}
    for label, entries in (temps or {}).items():
        out[label] = [
            {
                "label": getattr(e, "label", None),
                "current_c": getattr(e, "current", None),
                "high_c": getattr(e, "high", None),
                "critical_c": getattr(e, "critical", None),
            }
            for e in entries
        ]
    return out


