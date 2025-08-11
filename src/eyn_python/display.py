from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .logging import console


def _kv_lines(items: Iterable[Tuple[str, Any]]) -> str:
    return "\n".join(f"[bold]{k}[/]: {v}" for k, v in items)


def print_data(data: Any, renderable: Any, as_json: bool) -> None:
    if as_json:
        console().print_json(data=data)
    else:
        console().print(renderable)


def build_specs_render(data: Dict[str, Any]) -> Panel:
    os_info = _kv_lines([
        ("OS", f"{data.get('os')}"),
        ("Version", f"{data.get('os_version')}")
    ])
    py_info = _kv_lines([
        ("Python", data.get("python")),
        ("Hostname", data.get("hostname")),
    ])

    cpu = data.get("cpu", {}) or {}
    cpu_tbl = Table(box=box.SIMPLE_HEAVY, show_lines=False, title="CPU")
    for h in ("Model", "Physical", "Logical", "Current MHz", "Max MHz"):
        cpu_tbl.add_column(h)
    cpu_tbl.add_row(
        str(cpu.get("model", "")),
        str(cpu.get("cores_physical", "")),
        str(cpu.get("cores_logical", "")),
        str(cpu.get("freq_current_mhz", "")),
        str(cpu.get("freq_max_mhz", "")),
    )

    mem = data.get("memory", {}) or {}
    disk = data.get("disk", {}) or {}
    mem_disk_tbl = Table(box=box.SIMPLE_HEAVY, show_lines=False, title="Memory / Disk")
    mem_disk_tbl.add_column("Memory (GB)")
    mem_disk_tbl.add_column("Disk (GB)")
    mem_disk_tbl.add_row(
        f"Total: {mem.get('total_gb')}  Used: {mem.get('used_gb')}  Avail: {mem.get('available_gb')}",
        f"Total: {disk.get('total_gb')}  Used: {disk.get('used_gb')}  Free: {disk.get('free_gb')}",
    )

    group = Group(
        Panel(os_info, title="OS", box=box.ROUNDED),
        Panel(py_info, title="Runtime", box=box.ROUNDED),
        cpu_tbl,
        mem_disk_tbl,
    )
    return Panel(group, title="System Specs", box=box.DOUBLE)


def build_netinfo_render(data: Dict[str, Any]) -> Table:
    table = Table(title="Network Interfaces", box=box.SIMPLE_HEAVY, show_lines=False)
    for col in ("Name", "Up", "Speed (Mbps)", "IPv4", "IPv6", "MAC"):
        table.add_column(col)
    for nic in data.get("interfaces", []) or []:
        table.add_row(
            str(nic.get("name", "")),
            "✅" if nic.get("is_up") else "❌",
            str(nic.get("speed_mbps") or "-"),
            ", ".join(nic.get("ipv4", []) or []),
            ", ".join(nic.get("ipv6", []) or []),
            str(nic.get("mac") or ""),
        )
    return table


def build_uptime_render(data: Dict[str, Any]) -> Panel:
    load = data.get("load", {}) or {}
    content = _kv_lines([
        ("Uptime", data.get("uptime_human")),
        ("Boot (epoch)", data.get("boot_time")),
        ("Load 1m", load.get("1m")),
        ("Load 5m", load.get("5m")),
        ("Load 15m", load.get("15m")),
    ])
    return Panel(content, title="Uptime", box=box.SIMPLE_HEAVY)


def build_disks_render(data: Dict[str, Any]) -> Table:
    t = Table(title="Disk Partitions", box=box.SIMPLE_HEAVY, show_lines=False)
    for h in ("Device", "Mount", "FS", "Total GB", "Used GB", "Free GB", "%"):
        t.add_column(h)
    for p in data.get("partitions", []) or []:
        t.add_row(
            str(p.get("device", "")),
            str(p.get("mountpoint", "")),
            str(p.get("fstype", "")),
            str(p.get("total_gb", "")),
            str(p.get("used_gb", "")),
            str(p.get("free_gb", "")),
            str(p.get("percent", "")),
        )
    return t


def build_top_render(data: Dict[str, Any]) -> Table:
    t = Table(title="Top Processes", box=box.SIMPLE_HEAVY, show_lines=False)
    for h in ("PID", "Name", "CPU%", "Mem MB", "User"):
        t.add_column(h)
    for p in data.get("top", []) or []:
        t.add_row(
            str(p.get("pid", "")),
            str(p.get("name", "")),
            str(p.get("cpu_percent", "")),
            str(p.get("memory_mb", "")),
            str(p.get("username", "")),
        )
    return t


def build_battery_render(data: Dict[str, Any]) -> Panel:
    if not data.get("present"):
        return Panel("No battery detected.", title="Battery")
    content = _kv_lines([
        ("Percent", data.get("percent")),
        ("Plugged", "Yes" if data.get("plugged") else "No"),
        ("Seconds Left", data.get("secs_left")),
    ])
    return Panel(content, title="Battery", box=box.SIMPLE)


def build_temps_render(data: Dict[str, Any]) -> Union[Group, Panel]:
    tables: List[Table] = []
    for label, entries in (data or {}).items():
        t = Table(title=f"{label}", box=box.SIMPLE_HEAVY, show_lines=False)
        for h in ("Label", "Current °C", "High °C", "Critical °C"):
            t.add_column(h)
        for e in entries:
            t.add_row(
                str(e.get("label", "")),
                str(e.get("current_c", "")),
                str(e.get("high_c", "")),
                str(e.get("critical_c", "")),
            )
        tables.append(t)
    return Group(*tables) if tables else Panel("No temperature sensors.", title="Temps")


def build_ports_render(data: Dict[str, Any]) -> Table:
    t = Table(title="Listening Ports", box=box.SIMPLE_HEAVY, show_lines=False)
    for h in ("PID", "Process", "Local", "Remote", "Family", "Type"):
        t.add_column(h)
    for c in data.get("listening", []) or []:
        t.add_row(
            str(c.get("pid", "")),
            str(c.get("process", "")),
            str(c.get("local", "")),
            str(c.get("remote", "")),
            str(c.get("family", "")),
            str(c.get("type", "")),
        )
    return t


def build_pubip_render(data: Dict[str, Any]) -> Panel:
    return Panel(_kv_lines([("Public IP", data.get("ip"))]), title="Network")


def build_latency_render(data: Dict[str, Any]) -> Panel:
    content = _kv_lines([
        ("URL", data.get("url")),
        ("Attempts", data.get("attempts")),
        ("Min (ms)", data.get("min_ms")),
        ("Avg (ms)", data.get("avg_ms")),
        ("Max (ms)", data.get("max_ms")),
    ])
    return Panel(content, title="HTTP Latency", box=box.ROUNDED)


# ---------------- Generic/simple builders for other tools ----------------

def build_saved_panel(title: str, path: str) -> Panel:
    return Panel(_kv_lines([("Path", path)]), title=title, box=box.ROUNDED)


def build_clean_render(data: Dict[str, Any]) -> Panel:
    content = _kv_lines([
        ("Root", data.get("root")),
        ("Matched", data.get("count")),
        ("Bytes", data.get("bytes")),
        ("Removed", data.get("removed")),
        ("Removed Empty Dirs", data.get("removed_empty")),
    ])
    return Panel(content, title="Clean", box=box.SIMPLE_HEAVY)


def build_list_render(title: str, header: str, items: Sequence[str]) -> Table:
    t = Table(title=title, box=box.SIMPLE_HEAVY)
    t.add_column("#", justify="right")
    t.add_column(header)
    for i, it in enumerate(items, 1):
        t.add_row(str(i), it)
    return t


def build_forms_render(forms: Sequence[Dict[str, Any]]) -> Table:
    t = Table(title="Forms", box=box.SIMPLE_HEAVY)
    for h in ("Method", "Action", "Inputs"):
        t.add_column(h)
    for f in forms or []:
        t.add_row(str(f.get("method", "")), str(f.get("action", "")), str(len(f.get("inputs", []) or [])))
    return t


def build_assets_summary_render(assets: Dict[str, Any]) -> Panel:
    content = _kv_lines([
        ("Images", len(assets.get("images", []) or [])),
        ("Scripts", len(assets.get("scripts", []) or [])),
        ("Styles", len(assets.get("styles", []) or [])),
        ("Media", len(assets.get("media", []) or [])),
    ])
    return Panel(content, title="Assets", box=box.SIMPLE)


def build_meta_render(meta: Dict[str, Any]) -> Panel:
    headings = meta.get("headings", {}) or {}
    images = meta.get("images", {}) or {}
    content = _kv_lines([
        ("Title", meta.get("title")),
        ("Lang", meta.get("lang")),
        ("Desc?", "yes" if meta.get("description") else "no"),
        ("Canonical", meta.get("canonical")),
        ("Words", meta.get("word_count")),
        ("H1..H6", ", ".join(f"h{i}:{headings.get(f'h{i}',0)}" for i in range(1,7))),
        ("Images", images.get("count")),
        ("Imgs missing alt", images.get("missing_alt")),
    ])
    return Panel(content, title="Page Meta", box=box.ROUNDED)


def build_get_render(url: str, size: int) -> Panel:
    return Panel(_kv_lines([("URL", url), ("Bytes", size)]), title="GET", box=box.SIMPLE_HEAVY)


def build_select_render(selector: str, count: int) -> Panel:
    return Panel(_kv_lines([("Selector", selector), ("Matches", count)]), title="Select", box=box.SIMPLE_HEAVY)


def build_crawl_render(results: Sequence[Tuple[str, int]]) -> Table:
    t = Table(title="Crawl Results", box=box.SIMPLE_HEAVY)
    t.add_column("#", justify="right")
    t.add_column("URL")
    t.add_column("Bytes")
    for i, (u, n) in enumerate(results, 1):
        t.add_row(str(i), u, str(n))
    return t


def build_search_render(hits: Sequence[Dict[str, Any]]) -> Table:
    t = Table(title="Search Hits", box=box.SIMPLE_HEAVY)
    t.add_column("#", justify="right")
    t.add_column("URL")
    t.add_column("Total Matches", justify="right")
    for i, h in enumerate(hits, 1):
        total = 0
        matches = h.get("matches", {}) or {}
        try:
            total = sum(int(v) for v in matches.values())
        except Exception:
            total = 0
        t.add_row(str(i), str(h.get("url", "")), str(total))
    return t


def build_robots_render(info: Dict[str, Any]) -> Panel:
    return Panel(_kv_lines([("URL", info.get("url")), ("Status", info.get("status"))]), title="robots.txt")


def build_bool_panel(title: str, key: str, data: Dict[str, Any]) -> Panel:
    val = data.get(key)
    return Panel(_kv_lines([(title, "✅" if val else "❌")]), title=title)


