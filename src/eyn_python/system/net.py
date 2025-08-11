from __future__ import annotations

import socket
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

import psutil


@dataclass(frozen=True)
class NicInfo:
    name: str
    ipv4: List[str]
    ipv6: List[str]
    mac: Optional[str]
    is_up: bool
    speed_mbps: Optional[int]


def _addresses_for(nic: str) -> tuple[list[str], list[str], Optional[str]]:
    ipv4: list[str] = []
    ipv6: list[str] = []
    mac: Optional[str] = None
    addrs = psutil.net_if_addrs().get(nic, [])
    for a in addrs:
        if a.family == socket.AF_INET:
            ipv4.append(a.address)
        elif a.family == socket.AF_INET6:
            # strip %scope if present
            ipv6.append(a.address.split("%")[0])
        elif hasattr(psutil, "AF_LINK") and a.family == psutil.AF_LINK:
            mac = a.address
    return ipv4, ipv6, mac


def network_info() -> Dict[str, object]:
    nics: list[Dict[str, object]] = []
    stats = psutil.net_if_stats()
    for name, st in stats.items():
        ipv4, ipv6, mac = _addresses_for(name)
        nics.append(
            asdict(
                NicInfo(
                    name=name,
                    ipv4=ipv4,
                    ipv6=ipv6,
                    mac=mac,
                    is_up=st.isup,
                    speed_mbps=st.speed if st.speed and st.speed > 0 else None,
                )
            )
        )

    io = psutil.net_io_counters()
    return {
        "interfaces": nics,
        "bytes_sent": io.bytes_sent,
        "bytes_recv": io.bytes_recv,
        "packets_sent": io.packets_sent,
        "packets_recv": io.packets_recv,
    }


