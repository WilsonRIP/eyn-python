from __future__ import annotations

import psutil
from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class Proc:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    username: str
    cmdline: str


def _bytes_to_mb(n: int) -> float:
    return round(n / (1024**2), 1)


def top_processes(limit: int = 10) -> Dict[str, List[Dict[str, object]]]:
    # Prime CPU percent measurement
    for p in psutil.process_iter(attrs=["pid"]):
        try:
            p.cpu_percent(interval=None)
        except Exception:
            continue
    # short sampling window
    psutil.time.sleep(0.15)  # type: ignore[attr-defined]

    procs: list[Proc] = []
    for p in psutil.process_iter(attrs=["pid", "name", "username", "cmdline", "memory_info"]):
        try:
            cpu = p.cpu_percent(interval=None)
            mem = p.info.get("memory_info")
            rss = getattr(mem, "rss", 0) if mem else 0
            cmd = " ".join(p.info.get("cmdline") or [])
            procs.append(
                Proc(
                    pid=p.info.get("pid", 0),
                    name=p.info.get("name") or "",
                    cpu_percent=round(cpu, 1),
                    memory_mb=_bytes_to_mb(rss),
                    username=p.info.get("username") or "",
                    cmdline=cmd,
                )
            )
        except Exception:
            continue

    procs_sorted = sorted(procs, key=lambda x: (x.cpu_percent, x.memory_mb), reverse=True)[: max(1, limit)]
    return {"top": [asdict(p) for p in procs_sorted]}


