from __future__ import annotations

from typing import Dict, List

import psutil


def listening_ports() -> Dict[str, List[Dict[str, object]]]:
    items: list[Dict[str, object]] = []
    for c in psutil.net_connections(kind="inet"):
        try:
            if c.status != psutil.CONN_LISTEN:
                continue
            laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else None
            raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None
            items.append(
                {
                    "pid": c.pid,
                    "fd": c.fd,
                    "type": str(c.type),
                    "family": str(c.family),
                    "status": c.status,
                    "local": laddr,
                    "remote": raddr,
                    "process": psutil.Process(c.pid).name() if c.pid else None,
                }
            )
        except Exception:
            continue
    return {"listening": items}


