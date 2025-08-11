from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence

from eyn_python.logging import get_logger
from eyn_python.utils import run, which

log = get_logger(__name__)


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def get_common_browser_app_names(include_extended: bool = True) -> list[str]:
    base = [
        "Safari",
        "Google Chrome",
        "Microsoft Edge",
        "Brave Browser",
        "Firefox",
        "Arc",
        "Opera",
        "Vivaldi",
        "Chromium",
    ]
    if include_extended:
        base += [
            "Opera GX",
            "Orion",
            "LibreWolf",
            "Waterfox",
            "Yandex",
            "Tor Browser",
            "DuckDuckGo",
        ]
    return base


def _windows_exe_map() -> Mapping[str, str]:
    return {
        "Google Chrome": "chrome.exe",
        "Microsoft Edge": "msedge.exe",
        "Brave Browser": "brave.exe",
        "Firefox": "firefox.exe",
        "Opera": "opera.exe",
        "Opera GX": "opera.exe",
        "Vivaldi": "vivaldi.exe",
        "Chromium": "chromium.exe",
        "Arc": "arc.exe",
        "Yandex": "browser.exe",
        "LibreWolf": "librewolf.exe",
        "Waterfox": "waterfox.exe",
        "DuckDuckGo": "duckduckgo.exe",
        "Tor Browser": "firefox.exe",
        "Safari": "safari.exe",
        "Orion": "orion.exe",
        "Opera Beta": "opera_beta.exe",
    }


def _posix_match_patterns_for(name: str) -> tuple[str, ...]:
    patterns: List[str] = [name]
    alt = {
        "Google Chrome": ("Google Chrome", "chrome"),
        "Microsoft Edge": ("Microsoft Edge", "msedge", "edge"),
        "Brave Browser": ("Brave Browser", "brave"),
        "Firefox": ("Firefox", "firefox"),
        "Opera": ("Opera", "opera"),
        "Opera GX": ("Opera GX", "opera"),
        "Vivaldi": ("Vivaldi", "vivaldi"),
        "Chromium": ("Chromium", "chromium"),
        "Arc": ("Arc", "arc"),
        "Safari": ("Safari", "WebKitWebProcess", "SafariWebContent"),
        "Orion": ("Orion", "orion"),
        "LibreWolf": ("LibreWolf", "librewolf"),
        "Waterfox": ("Waterfox", "waterfox"),
        "Yandex": ("Yandex", "yandex"),
        "Tor Browser": ("Tor Browser", "tor-browser", "firefox"),
        "DuckDuckGo": ("DuckDuckGo", "duckduckgo"),
    }
    patterns = list(dict.fromkeys(alt.get(name, (name,))))
    return tuple(patterns)


def _have(cmd: str) -> bool:
    try:
        return which(cmd) is not None
    except Exception:
        return False


def _pgrep_any(pattern: str) -> bool:
    if not _have("pgrep"):
        return False
    cp = run(["pgrep", "-if", pattern], check=False)
    return cp.returncode == 0 and bool((cp.stdout or "").strip())


def _pgrep_pids(pattern: str) -> list[int]:
    if not _have("pgrep"):
        return []
    cp = run(["pgrep", "-if", pattern], check=False)
    if cp.returncode != 0:
        return []
    out = (cp.stdout or "").strip()
    if not out:
        return []
    pids: list[int] = []
    for tok in out.split():
        try:
            pids.append(int(tok))
        except ValueError:
            continue
    return pids


def _osascript_quit(app_name: str) -> None:
    if not _have("osascript"):
        return
    script = f'tell application "{app_name}" to if it is running then quit'
    run(["osascript", "-e", script], check=False)


def _killall(name: str) -> None:
    if _have("killall"):
        run(["killall", "-9", name], check=False)


def _pkill(pattern: str, force: bool) -> None:
    if not _have("pkill"):
        return
    sig = "-9" if force else "-15"
    run(["pkill", sig, "-if", pattern], check=False)


def _win_tasklist_has(image_name: str) -> bool:
    if not _have("tasklist"):
        return False
    cp = run(["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV", "/NH"], check=False)
    out = (cp.stdout or "").strip().strip('"')
    return bool(out) and not out.upper().startswith("INFO:")


def _taskkill_windows(image_name: str, force: bool) -> None:
    if not _have("taskkill"):
        return
    args = ["taskkill", "/IM", image_name, "/T"]
    if force:
        args.insert(2, "/F")
    run(args, check=False)


@dataclass(frozen=True)
class AppCloseReport:
    name: str
    was_running: bool
    closed_gracefully: bool
    forced: bool
    still_running: bool
    attempted_patterns: tuple[str, ...] = ()
    attempted_exe_names: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class CloseResult:
    attempted: list[str]
    closed: list[str]
    forced: list[str]
    not_running: list[str] = field(default_factory=list)
    still_running: list[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    reports: list[AppCloseReport] = field(default_factory=list)


def close_browsers(
    apps: Sequence[str] | None = None,
    *,
    timeout_seconds: float = 5.0,
    force: bool = False,
    dry_run: bool = False,
    exclude: Sequence[str] | None = None,
    only_if_running: bool = True,
) -> CloseResult:
    targets = list(apps or get_common_browser_app_names())
    if exclude:
        excl = set(exclude)
        targets = [t for t in targets if t not in excl]

    closed: list[str] = []
    forced_list: list[str] = []
    not_running: list[str] = []
    still_running: list[str] = []
    errors: Dict[str, str] = {}
    reports: List[AppCloseReport] = []  # type: ignore[name-defined]

    start_deadline = time.time() + max(0.0, timeout_seconds)

    def _wait_until(predicate, remaining_time: float, step: float = 0.2) -> None:
        end = time.time() + max(0.0, remaining_time)
        while time.time() < end:
            if predicate():
                return
            time.sleep(step)

    if is_macos() or is_linux():
        have_pgrep = _have("pgrep")
        have_pkill = _have("pkill")
        if not have_pgrep:
            log.warning("pgrep not available; detection may be limited.")
        if is_macos() and not _have("osascript"):
            log.warning("osascript not available; graceful quit may be limited on macOS.")

        for name in targets:
            patterns = _posix_match_patterns_for(name)

            running_now = any(_pgrep_any(p) for p in patterns) if have_pgrep else False
            if not running_now and only_if_running:
                not_running.append(name)
                reports.append(AppCloseReport(
                    name=name,
                    was_running=False,
                    closed_gracefully=False,
                    forced=False,
                    still_running=False,
                    attempted_patterns=patterns
                ))
                continue

            if dry_run:
                reports.append(AppCloseReport(
                    name=name,
                    was_running=running_now,
                    closed_gracefully=False,
                    forced=False,
                    still_running=running_now,
                    attempted_patterns=patterns
                ))
                continue

            closed_graceful = False
            forced_this = False
            error_msg: str | None = None

            try:
                if is_macos():
                    _osascript_quit(name)
                else:
                    if have_pkill:
                        for p in patterns:
                            _pkill(p, force=False)

                def _none_running() -> bool:
                    return not any(_pgrep_any(p) for p in patterns) if have_pgrep else True

                remaining_for_app = max(0.0, start_deadline - time.time())
                if remaining_for_app > 0:
                    _wait_until(_none_running, remaining_for_app)

                if _none_running():
                    closed.append(name)
                    closed_graceful = True
                elif force:
                    if is_macos():
                        _killall(name)
                        for p in patterns:
                            _pkill(p, force=True)
                    else:
                        for p in patterns:
                            _pkill(p, force=True)

                    def _none_running_after_force() -> bool:
                        return not any(_pgrep_any(p) for p in patterns) if have_pgrep else True

                    _wait_until(_none_running_after_force, 2.0)
                    if _none_running_after_force():
                        forced_list.append(name)
                        forced_this = True
                    else:
                        still_running.append(name)
                else:
                    still_running.append(name)

            except Exception as exc:  # noqa: BLE001
                error_msg = f"{type(exc).__name__}: {exc}"
                errors[name] = error_msg
                log.exception("Failed to close %s", name)

            reports.append(AppCloseReport(
                name=name,
                was_running=True,
                closed_gracefully=closed_graceful,
                forced=forced_this,
                still_running=name in still_running,
                attempted_patterns=patterns,
                error=error_msg,
            ))

    elif is_windows():
        exe_map = _windows_exe_map()
        have_taskkill = _have("taskkill")
        have_tasklist = _have("tasklist")
        if not have_taskkill or not have_tasklist:
            log.warning("taskkill/tasklist not available; Windows control limited.")

        for name in targets:
            exe = exe_map.get(name, f"{name}.exe")

            running_now = _win_tasklist_has(exe) if have_tasklist else False
            if not running_now and only_if_running:
                not_running.append(name)
                reports.append(AppCloseReport(
                    name=name,
                    was_running=False,
                    closed_gracefully=False,
                    forced=False,
                    still_running=False,
                    attempted_exe_names=(exe,)
                ))
                continue

            if dry_run:
                reports.append(AppCloseReport(
                    name=name,
                    was_running=running_now,
                    closed_gracefully=False,
                    forced=False,
                    still_running=running_now,
                    attempted_exe_names=(exe,)
                ))
                continue

            closed_graceful = False
            forced_this = False
            error_msg: str | None = None

            try:
                _taskkill_windows(exe, force=False)

                def _gone() -> bool:
                    return not _win_tasklist_has(exe) if have_tasklist else True

                remaining_for_app = max(0.0, start_deadline - time.time())
                if remaining_for_app > 0:
                    end = time.time() + remaining_for_app
                    while time.time() < end and not _gone():
                        time.sleep(0.2)

                if _gone():
                    closed.append(name)
                    closed_graceful = True
                elif force:
                    _taskkill_windows(exe, force=True)
                    end2 = time.time() + 2.0
                    while time.time() < end2 and not _gone():
                        time.sleep(0.2)
                    if _gone():
                        forced_list.append(name)
                        forced_this = True
                    else:
                        still_running.append(name)
                else:
                    still_running.append(name)

            except Exception as exc:  # noqa: BLE001
                error_msg = f"{type(exc).__name__}: {exc}"
                errors[name] = error_msg
                log.exception("Failed to close %s", name)

            reports.append(AppCloseReport(
                name=name,
                was_running=True,
                closed_gracefully=closed_graceful,
                forced=forced_this,
                still_running=name in still_running,
                attempted_exe_names=(exe,),
                error=error_msg,
            ))

    else:
        log.warning("Unsupported platform for close_browsers: %s", sys.platform)

    return CloseResult(
        attempted=targets,
        closed=closed,
        forced=forced_list,
        not_running=not_running,
        still_running=still_running,
        errors=errors,
        reports=reports,
    )


