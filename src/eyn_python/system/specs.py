from __future__ import annotations

"""
System specification detection (cross-platform, zero extra deps beyond psutil).

Highlights
- CPU model detection tuned per-OS:
  * macOS: sysctl machdep.cpu.brand_string
  * Linux: /proc/cpuinfo, then lscpu (fallback)
  * Windows: registry (ProcessorNameString), then CIM/WMI
- Memory with percentage and GiB rounding
- Disks: keeps your original single 'disk' entry (home mount) and adds 'disks' list
- GPU best-effort:
  * NVIDIA: nvidia-smi (name + VRAM)
  * macOS: system_profiler SPDisplaysDataType (Chipset Model + VRAM)
  * Windows: Get-CimInstance Win32_VideoController (Name + AdapterRAM)
  * Linux: lspci/glxinfo fallback (renderer string)
- Strong typing and dataclasses; expose both dict and dataclass APIs
"""

import os
import platform
import shutil
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import psutil


# --------------------------
# Data models
# --------------------------

@dataclass(frozen=True)
class CpuInfo:
    model: str
    architecture: str
    cores_physical: int
    cores_logical: int
    freq_current_mhz: Optional[float]
    freq_max_mhz: Optional[float]


@dataclass(frozen=True)
class MemoryInfo:
    total_gb: float
    available_gb: float
    used_gb: float
    percent: float


@dataclass(frozen=True)
class DiskInfo:
    total_gb: float
    used_gb: float
    free_gb: float
    mount: str
    filesystem: Optional[str] = None


@dataclass(frozen=True)
class GpuInfo:
    name: Optional[str]
    vram_gb: Optional[float] = None
    driver: Optional[str] = None


@dataclass(frozen=True)
class SystemSpecs:
    os: str
    os_version: str
    os_release: str
    machine: str
    hostname: str
    python: str
    python_implementation: str
    cpu: CpuInfo
    memory: MemoryInfo
    disk: DiskInfo                    # kept for backward-compat (home drive)
    disks: List[DiskInfo] = field(default_factory=list)  # new: all mounted disks
    gpu: GpuInfo = field(default_factory=lambda: GpuInfo(name=None))


# --------------------------
# OS helpers
# --------------------------

def _is_macos() -> bool:
    return sys.platform == "darwin"


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _is_linux() -> bool:
    return sys.platform.startswith("linux")


# --------------------------
# Utils
# --------------------------

def _bytes_to_gb(n: int) -> float:
    # Use GiB (base-1024) and round to 2 decimals
    return round(n / (1024 ** 3), 2)


def _safe_first_line(s: str) -> str:
    s = (s or "").strip()
    return s.splitlines()[0].strip() if s else ""


def _run_cmd(cmd: Sequence[str], timeout: float = 2.5) -> Tuple[int, str, str]:
    """
    Run a command without shell, return (returncode, stdout, stderr).
    Never raises; on error returns nonzero code and empty out/err.
    """
    try:
        cp = subprocess.run(
            list(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            text=True,
        )
        return cp.returncode, cp.stdout or "", cp.stderr or ""
    except Exception:
        return 1, "", ""


def _which(prog: str) -> bool:
    from shutil import which as _which
    return _which(prog) is not None


# --------------------------
# CPU detection
# --------------------------

def _cpu_model() -> str:
    # Fast path: platform.processor is fine on Windows, often empty on Linux
    proc = platform.processor()
    if proc:
        # On Apple Silicon it may show "arm" – prefer sysctl below if macOS
        if not (_is_macos() and proc.lower() in {"arm", "arm64"}):
            return proc

    if _is_macos():
        rc, out, _ = _run_cmd(["sysctl", "-n", "machdep.cpu.brand_string"])
        return _safe_first_line(out) or "Unknown"

    if _is_linux():
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "model name" in line:
                        _, val = line.split(":", 1)
                        return val.strip()
        except Exception:
            pass
        if _which("lscpu"):
            rc, out, _ = _run_cmd(["lscpu"])
            for line in out.splitlines():
                if "Model name:" in line:
                    return line.split(":", 1)[1].strip()

    if _is_windows():
        # 1) Registry (reliable)
        try:
            import winreg  # type: ignore
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            if val:
                return str(val).strip()
        except Exception:
            pass
        # 2) CIM / WMI fallbacks
        if _which("powershell"):
            rc, out, _ = _run_cmd([
                "powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)"
            ])
            if out.strip():
                return _safe_first_line(out)
        if _which("wmic"):
            rc, out, _ = _run_cmd(["wmic", "cpu", "get", "Name"])
            lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
            if len(lines) >= 2:
                return lines[1]

    return "Unknown"


def _cpu_freq_mhz() -> Tuple[Optional[float], Optional[float]]:
    try:
        f = psutil.cpu_freq()
        if not f:
            return None, None
        cur = round(float(f.current), 1) if f.current else None
        mx = round(float(f.max), 1) if f.max else None
        return cur, mx
    except Exception:
        return None, None


# --------------------------
# Memory detection
# --------------------------

def _memory_info() -> MemoryInfo:
    vm = psutil.virtual_memory()
    return MemoryInfo(
        total_gb=_bytes_to_gb(vm.total),
        available_gb=_bytes_to_gb(vm.available),
        used_gb=_bytes_to_gb(vm.used),
        percent=float(vm.percent),
    )


# --------------------------
# Disk detection
# --------------------------

def _disk_for_path(path: str) -> DiskInfo:
    usage = shutil.disk_usage(path)
    fs = None
    # Try to find filesystem type via psutil (if mount is present)
    try:
        # Normalize to handle Windows drive roots & UNC
        norm = os.path.abspath(path)
        for p in psutil.disk_partitions(all=False):
            # On Windows, mountpoint for C: is like 'C:\\'
            if os.path.abspath(p.mountpoint) == os.path.abspath(norm if os.path.isdir(norm) else os.path.dirname(norm)):
                fs = p.fstype or None
                break
    except Exception:
        pass
    return DiskInfo(
        total_gb=_bytes_to_gb(usage.total),
        used_gb=_bytes_to_gb(usage.used),
        free_gb=_bytes_to_gb(usage.free),
        mount=path,
        filesystem=fs,
    )


def _all_disks() -> List[DiskInfo]:
    infos: List[DiskInfo] = []
    seen: set[str] = set()
    try:
        for p in psutil.disk_partitions(all=False):
            # Skip non-real mounts
            if hasattr(p, "fstype") and not p.fstype:
                continue
            m = p.mountpoint
            if not m or m in seen:
                continue
            seen.add(m)
            try:
                usage = psutil.disk_usage(m)
            except Exception:
                continue
            infos.append(DiskInfo(
                total_gb=_bytes_to_gb(usage.total),
                used_gb=_bytes_to_gb(usage.used),
                free_gb=_bytes_to_gb(usage.free),
                mount=m,
                filesystem=p.fstype or None,
            ))
    except Exception:
        pass
    # Sort by mount path for stable output
    infos.sort(key=lambda d: d.mount.lower())
    return infos


# --------------------------
# GPU detection (best-effort)
# --------------------------

def _gpu_from_nvidia_smi() -> Optional[GpuInfo]:
    if not _which("nvidia-smi"):
        return None
    rc, out, _ = _run_cmd(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                           "--format=csv,noheader,nounits"])
    if rc != 0 or not out.strip():
        return None
    # If multiple GPUs, pick the first
    line = _safe_first_line(out)
    parts = [p.strip() for p in line.split(",")]
    name = parts[0] if parts else None
    vram = float(parts[1]) / 1024.0 if len(parts) > 1 and parts[1].isdigit() else None
    driver = parts[2] if len(parts) > 2 else None
    return GpuInfo(name=name or None, vram_gb=(round(vram, 2) if vram else None), driver=driver)


def _gpu_macos_sp() -> Optional[GpuInfo]:
    if not _is_macos():
        return None
    rc, out, _ = _run_cmd(["system_profiler", "SPDisplaysDataType"])
    if rc != 0 or not out:
        return None
    name: Optional[str] = None
    vram_gb: Optional[float] = None
    driver: Optional[str] = None
    for raw in out.splitlines():
        line = raw.strip()
        if line.lower().startswith("chipset model:"):
            name = line.split(":", 1)[1].strip()
        elif "VRAM" in line:
            # Handles "VRAM (Total): 8 GB" or "VRAM (Dynamic, Max): 1536 MB"
            try:
                val = line.split(":", 1)[1].strip()
                if val.upper().endswith("GB"):
                    vram_gb = round(float(val[:-2].strip()), 2)
                elif val.upper().endswith("MB"):
                    vram_gb = round(float(val[:-2].strip()) / 1024.0, 2)
            except Exception:
                pass
        elif line.lower().startswith("vendor:"):
            driver = line.split(":", 1)[1].strip()
    if not (name or vram_gb or driver):
        return None
    return GpuInfo(name=name, vram_gb=vram_gb, driver=driver)


def _gpu_windows_cim() -> Optional[GpuInfo]:
    if not _is_windows() or not _which("powershell"):
        return None
    # We request the first active controller
    rc, out, _ = _run_cmd([
        "powershell", "-NoProfile", "-Command",
        "(Get-CimInstance Win32_VideoController | "
        " Where-Object {$_.PNPDeviceID -and $_.AdapterRAM -gt 0} | "
        " Select-Object -First 1 Name,AdapterRAM,DriverVersion | "
        " ForEach-Object {\"$($_.Name)|$($_.AdapterRAM)|$($_.DriverVersion)\"})"
    ])
    if rc != 0 or not out.strip():
        return None
    parts = _safe_first_line(out).split("|")
    if not parts:
        return None
    name = parts[0].strip() or None
    vram_gb = None
    driver = None
    try:
        if len(parts) > 1 and parts[1].strip().isdigit():
            vram_gb = round(int(parts[1].strip()) / (1024 ** 3), 2)
    except Exception:
        pass
    if len(parts) > 2:
        driver = parts[2].strip() or None
    return GpuInfo(name=name, vram_gb=vram_gb, driver=driver)


def _gpu_linux_lspci_glx() -> Optional[GpuInfo]:
    if not _is_linux():
        return None
    # Prefer glxinfo (renderer string) if present
    if _which("glxinfo"):
        rc, out, _ = _run_cmd(["glxinfo", "-B"])
        if rc == 0 and out:
            renderer = None
            version = None
            for line in out.splitlines():
                if "OpenGL renderer string" in line:
                    renderer = line.split(":", 1)[1].strip()
                elif "OpenGL version string" in line:
                    version = line.split(":", 1)[1].strip()
            if renderer:
                return GpuInfo(name=renderer, driver=version)
    # Fallback: lspci VGA line
    if _which("lspci"):
        rc, out, _ = _run_cmd(["lspci"])
        if rc == 0:
            for line in out.splitlines():
                if " VGA " in line or "3D controller" in line:
                    # e.g., "01:00.0 VGA compatible controller: NVIDIA Corporation ... (rev a1)"
                    desc = line.split(":", 2)[-1].strip()
                    return GpuInfo(name=desc)
    return None


def _gpu_info() -> GpuInfo:
    # Attempt in order of highest fidelity on each OS.
    for getter in (_gpu_from_nvidia_smi, _gpu_macos_sp, _gpu_windows_cim, _gpu_linux_lspci_glx):
        try:
            info = getter()
            if info and (info.name or info.vram_gb or info.driver):
                return info
        except Exception:
            continue
    return GpuInfo(name=None)


# --------------------------
# Public API
# --------------------------

def detect_specs() -> SystemSpecs:
    uname = platform.uname()
    arch = platform.machine() or uname.machine or ""
    cpu_cur_mhz, cpu_max_mhz = _cpu_freq_mhz()

    cpu = CpuInfo(
        model=_cpu_model(),
        architecture=arch,
        cores_physical=psutil.cpu_count(logical=False) or 0,
        cores_logical=psutil.cpu_count(logical=True) or 0,
        freq_current_mhz=cpu_cur_mhz,
        freq_max_mhz=cpu_max_mhz,
    )

    mem = _memory_info()

    # Keep original single-disk behavior (home), but add full inventory.
    home = os.path.expanduser("~")
    disk_home = _disk_for_path(home)

    disks = _all_disks()

    specs = SystemSpecs(
        os=uname.system,
        os_version=uname.version,
        os_release=uname.release,
        machine=uname.machine,
        hostname=socket.gethostname(),
        python=platform.python_version(),
        python_implementation=platform.python_implementation(),
        cpu=cpu,
        memory=mem,
        disk=disk_home,
        disks=disks,
        gpu=_gpu_info(),
    )
    return specs


def detect_specs_dict() -> Dict[str, object]:
    """
    Backward-compatible dict output mirroring your original structure,
    plus additional fields ('os_release', 'machine', 'python_implementation', 'disks').
    """
    s = detect_specs()
    out: Dict[str, object] = {
        "os": s.os,
        "os_version": s.os_version,
        "os_release": s.os_release,
        "machine": s.machine,
        "hostname": s.hostname,
        "python": s.python,
        "python_implementation": s.python_implementation,
        "cpu": asdict(s.cpu),
        "memory": asdict(s.memory),
        "disk": asdict(s.disk),      # original single entry (home mount)
        "disks": [asdict(d) for d in s.disks],  # new: all mounts
        "gpu": asdict(s.gpu),
    }
    return out
