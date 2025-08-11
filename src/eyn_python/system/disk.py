from __future__ import annotations

import psutil
from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class Partition:
    device: str
    mountpoint: str
    fstype: str
    opts: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


def _bytes_to_gb(n: int) -> float:
    return round(n / (1024**3), 2)


def partitions_info() -> Dict[str, List[Dict[str, object]]]:
    items: list[Dict[str, object]] = []
    for p in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(p.mountpoint)
        except Exception:
            # skip inaccessible mounts
            continue
        items.append(
            asdict(
                Partition(
                    device=p.device,
                    mountpoint=p.mountpoint,
                    fstype=p.fstype,
                    opts=p.opts,
                    total_gb=_bytes_to_gb(u.total),
                    used_gb=_bytes_to_gb(u.used),
                    free_gb=_bytes_to_gb(u.free),
                    percent=u.percent,
                )
            )
        )
    return {"partitions": items}


