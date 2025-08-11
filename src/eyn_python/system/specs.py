from __future__ import annotations

import os
import platform
import shutil
import socket
from dataclasses import asdict, dataclass
from typing import Dict, Optional

import psutil


@dataclass(frozen=True)
class CpuInfo:
    model: str
    cores_physical: int
    cores_logical: int
    freq_current_mhz: Optional[float]
    freq_max_mhz: Optional[float]


@dataclass(frozen=True)
class MemoryInfo:
    total_gb: float
    available_gb: float
    used_gb: float


@dataclass(frozen=True)
class DiskInfo:
    total_gb: float
    used_gb: float
    free_gb: float
    mount: str


@dataclass(frozen=True)
class GpuInfo:
    name: Optional[str]  # best-effort; may be None on many systems without extra deps


@dataclass(frozen=True)
class SystemSpecs:
    os: str
    os_version: str
    hostname: str
    python: str
    cpu: CpuInfo
    memory: MemoryInfo
    disk: DiskInfo
    gpu: GpuInfo


def _bytes_to_gb(n: int) -> float:
    return round(n / (1024**3), 2)


def detect_specs() -> Dict[str, object]:
    uname = platform.uname()
    cpu_freq = psutil.cpu_freq()
    vm = psutil.virtual_memory()
    du = shutil.disk_usage(os.path.expanduser("~"))

    cpu = CpuInfo(
        model=uname.processor or platform.processor() or "Unknown",
        cores_physical=psutil.cpu_count(logical=False) or 0,
        cores_logical=psutil.cpu_count(logical=True) or 0,
        freq_current_mhz=cpu_freq.current if cpu_freq else None,
        freq_max_mhz=cpu_freq.max if cpu_freq else None,
    )
    mem = MemoryInfo(
        total_gb=_bytes_to_gb(vm.total),
        available_gb=_bytes_to_gb(vm.available),
        used_gb=_bytes_to_gb(vm.used),
    )
    disk = DiskInfo(
        total_gb=_bytes_to_gb(du.total),
        used_gb=_bytes_to_gb(du.used),
        free_gb=_bytes_to_gb(du.free),
        mount=os.path.expanduser("~"),
    )
    gpu = GpuInfo(name=None)

    specs = SystemSpecs(
        os=uname.system,
        os_version=uname.version,
        hostname=socket.gethostname(),
        python=platform.python_version(),
        cpu=cpu,
        memory=mem,
        disk=disk,
        gpu=gpu,
    )
    return {
        "os": specs.os,
        "os_version": specs.os_version,
        "hostname": specs.hostname,
        "python": specs.python,
        "cpu": asdict(specs.cpu),
        "memory": asdict(specs.memory),
        "disk": asdict(specs.disk),
        "gpu": asdict(specs.gpu),
    }


