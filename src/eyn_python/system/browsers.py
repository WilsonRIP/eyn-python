from __future__ import annotations

"""
Cross-platform browser closer with an expanded browser catalog.

- Adds many browsers and dev/beta/nightly channels (Chrome/Edge/Brave/Firefox),
  plus Chromium forks and alternates (Vivaldi Snapshot, Ungoogled Chromium, Floorp, Zen, Mullvad, etc.).
- Centralizes process/bundle signatures for macOS, Linux, and Windows.
- Keeps your public API: get_common_browser_app_names(), close_browsers(...).
"""

import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence, Tuple

from eyn_python.logging import get_logger
from eyn_python.utils import run, which

log = get_logger(__name__)


# ---------------------------
# OS helpers
# ---------------------------

def is_macos() -> bool:
    return sys.platform == "darwin"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def _have(cmd: str) -> bool:
    try:
        return which(cmd) is not None
    except Exception:
        return False


# ---------------------------
# Browser signatures
# ---------------------------

@dataclass(frozen=True)
class BrowserSignature:
    """Per-browser detection/kill hints."""
    name: str
    # macOS: names usable with AppleScript "tell application"
    mac_app_names: Tuple[str, ...] = ()
    # Windows: process image names (tasklist/taskkill)
    win_image_names: Tuple[str, ...] = ()
    # POSIX (macOS/Linux): patterns to match with pgrep/pkill -if
    posix_patterns: Tuple[str, ...] = ()


def _sig(
    name: str,
    *,
    mac: Sequence[str] = (),
    win: Sequence[str] = (),
    posix: Sequence[str] = (),
) -> BrowserSignature:
    return BrowserSignature(
        name=name,
        mac_app_names=tuple(mac) if mac else (name,),
        win_image_names=tuple(win) if win else (f"{name}.exe",),
        posix_patterns=tuple(dict.fromkeys(posix or (name,)))  # dedupe, preserve order
    )


# Note on channels: many channels share the same process image (e.g., chrome.exe or msedge.exe).
# Killing the image typically terminates all channels for that browser family.

_BROWSERS: Tuple[BrowserSignature, ...] = (
    # Apple/WebKit
    _sig("Safari", mac=["Safari"], win=["safari.exe"], posix=["Safari", "WebKitWebProcess", "SafariWebContent"]),
    _sig("Safari Technology Preview", mac=["Safari Technology Preview"], posix=["Safari Technology Preview", "WebKitWebProcess"]),
    _sig("Orion", mac=["Orion"], win=["orion.exe"], posix=["Orion", "orion"]),

    # Chrome family (Google)
    _sig("Google Chrome",
         mac=["Google Chrome"],
         win=["chrome.exe"],
         posix=["Google Chrome", "chrome", "google-chrome", "google-chrome-stable"]),
    _sig("Google Chrome Beta",
         mac=["Google Chrome Beta"],
         win=["chrome.exe"],
         posix=["google-chrome-beta", "chrome"]),
    _sig("Google Chrome Dev",
         mac=["Google Chrome Dev"],
         win=["chrome.exe"],
         posix=["google-chrome-unstable", "google-chrome-dev", "chrome"]),
    _sig("Google Chrome Canary",
         mac=["Google Chrome Canary"],
         win=["chrome.exe"],
         posix=["chrome-canary", "chrome"]),

    # Microsoft Edge
    _sig("Microsoft Edge",
         mac=["Microsoft Edge"],
         win=["msedge.exe"],
         posix=["microsoft-edge", "microsoft-edge-stable", "msedge", "edge"]),
    _sig("Microsoft Edge Beta",
         mac=["Microsoft Edge Beta"],
         win=["msedge.exe"],
         posix=["microsoft-edge-beta", "msedge", "edge"]),
    _sig("Microsoft Edge Dev",
         mac=["Microsoft Edge Dev"],
         win=["msedge.exe"],
         posix=["microsoft-edge-dev", "msedge", "edge"]),
    _sig("Microsoft Edge Canary",
         mac=["Microsoft Edge Canary"],
         win=["msedge.exe"],
         posix=["msedge-canary", "edge"]),

    # Brave
    _sig("Brave Browser",
         mac=["Brave Browser"],
         win=["brave.exe"],
         posix=["Brave Browser", "brave", "brave-browser", "brave-browser-stable"]),
    _sig("Brave Beta",
         mac=["Brave Browser Beta"],
         win=["brave.exe"],
         posix=["brave-beta", "brave"]),
    _sig("Brave Nightly",
         mac=["Brave Browser Nightly"],
         win=["brave.exe"],
         posix=["brave-nightly", "brave"]),

    # Firefox family
    _sig("Firefox",
         mac=["Firefox"],
         win=["firefox.exe"],
         posix=["Firefox", "firefox", "firefox-esr"]),
    _sig("Firefox Developer Edition",
         mac=["Firefox Developer Edition"],
         win=["firefox.exe"],
         posix=["firefox-developer-edition", "firefox-developer", "firefox"]),
    _sig("Firefox Nightly",
         mac=["Firefox Nightly"],
         win=["firefox.exe"],
         posix=["firefox-nightly", "firefox"]),
    _sig("LibreWolf",
         mac=["LibreWolf"],
         win=["librewolf.exe"],
         posix=["LibreWolf", "librewolf"]),
    _sig("Waterfox",
         mac=["Waterfox"],
         win=["waterfox.exe"],
         posix=["Waterfox", "waterfox"]),
    _sig("Floorp",
         mac=["Floorp"],
         win=["floorp.exe"],
         posix=["floorp"]),
    _sig("Zen Browser",
         mac=["Zen Browser", "Zen"],
         win=["zen.exe", "zenbrowser.exe"],
         posix=["zen", "zen-browser"]),
    _sig("Mullvad Browser",
         mac=["Mullvad Browser"],
         win=["mullvadbrowser.exe", "firefox.exe"],
         posix=["mullvadbrowser", "mullvad-browser", "firefox"]),
    _sig("Tor Browser",
         mac=["Tor Browser"],
         win=["firefox.exe"],
         posix=["Tor Browser", "tor-browser", "firefox"]),

    # Chromium & forks
    _sig("Chromium",
         mac=["Chromium"],
         win=["chromium.exe", "chrome.exe"],
         posix=["Chromium", "chromium", "chromium-browser"]),
    _sig("Ungoogled Chromium",
         mac=["Chromium"],  # bundle presents as Chromium
         win=["ungoogled-chromium.exe", "chromium.exe", "chrome.exe"],
         posix=["ungoogled-chromium", "chromium", "chromium-browser"]),
    _sig("Vivaldi",
         mac=["Vivaldi"],
         win=["vivaldi.exe"],
         posix=["Vivaldi", "vivaldi"]),
    _sig("Vivaldi Snapshot",
         mac=["Vivaldi Snapshot"],
         win=["vivaldi.exe"],
         posix=["vivaldi-snapshot", "vivaldi"]),
    _sig("Opera",
         mac=["Opera"],
         win=["opera.exe"],
         posix=["Opera", "opera"]),
    _sig("Opera Beta",
         mac=["Opera Beta"],
         win=["opera_beta.exe", "opera.exe"],
         posix=["opera-beta", "opera"]),
    _sig("Opera Developer",
         mac=["Opera Developer"],
         win=["opera_developer.exe", "opera.exe"],
         posix=["opera-developer", "opera"]),
    _sig("Opera GX",
         mac=["Opera GX"],
         win=["opera.exe"],
         posix=["Opera GX", "opera"]),
    _sig("Arc",
         mac=["Arc"],
         win=["arc.exe"],
         posix=["Arc", "arc"]),
    _sig("Yandex",
         mac=["Yandex"],
         win=["browser.exe", "yandex.exe"],
         posix=["Yandex", "yandex", "yandex_browser"]),
    _sig("SRWare Iron",
         mac=["Iron"],
         win=["iron.exe"],
         posix=["iron", "srwareiron"]),
    _sig("Slimjet",
         mac=["Slimjet"],
         win=["slimjet.exe"],
         posix=["slimjet", "flashpeak-slimjet"]),
    _sig("Comodo Dragon",
         mac=["Comodo Dragon"],
         win=["dragon.exe"],
         posix=["dragon", "comodo-dragon"]),
    _sig("Iridium",
         mac=["Iridium"],
         win=["iridium.exe"],
         posix=["iridium"]),
    _sig("Epic Privacy Browser",
         mac=["Epic"],
         win=["epic.exe"],
         posix=["epic", "epic-browser"]),
    _sig("Sidekick",
         mac=["Sidekick"],
         win=["sidekick.exe"],
         posix=["sidekick", "sidekick-browser"]),
    _sig("Wavebox",
        mac=["Wavebox"],
        win=["wavebox.exe"],
        posix=["wavebox"]),
    _sig("Ghost Browser",
         mac=["Ghost Browser"],
         win=["ghostbrowser.exe", "ghost.exe"],
         posix=["ghost-browser", "ghostbrowser"]),
    _sig("Thorium",
         mac=["Thorium"],
         win=["thorium.exe"],
         posix=["thorium"]),
    _sig("Supermium",
         mac=["Supermium"],
         win=["supermium.exe"],
         posix=["supermium"]),

    # Others (Linux-oriented)
    _sig("GNOME Web",
         mac=["Web"],
         win=["epiphany.exe"],
         posix=["epiphany", "gnome-web"]),
    _sig("Midori",
         mac=["Midori"],
         win=["midori.exe"],
         posix=["midori"]),
    _sig("Falkon",
         mac=["Falkon"],
         win=["falkon.exe"],
         posix=["falkon"]),
    _sig("Konqueror",
         mac=["Konqueror"],
         win=["konqueror.exe"],
         posix=["konqueror"]),
    _sig("SeaMonkey",
         mac=["SeaMonkey"],
         win=["seamonkey.exe"],
         posix=["seamonkey"]),
    _sig("Pale Moon",
         mac=["Pale Moon"],
         win=["palemoon.exe"],
         posix=["palemoon"]),
    _sig("DuckDuckGo",
         mac=["DuckDuckGo"],
         win=["duckduckgo.exe"],
         posix=["DuckDuckGo", "duckduckgo"]),
    _sig("Orion Nightly",
         mac=["Orion Nightly"],
         win=["orion.exe"],
         posix=["orion-nightly", "orion"]),
)


def _registry_by_name() -> Mapping[str, BrowserSignature]:
    return {b.name: b for b in _BROWSERS}


def _known_names() -> List[str]:
    return [b.name for b in _BROWSERS]


# ---------------------------
# Public: names
# ---------------------------

def get_common_browser_app_names(include_extended: bool = True) -> list[str]:
    """
    Returns an ordered list of browser names. If include_extended is False,
    returns a smaller, mainstream subset.
    """
    core = [
        "Safari",
        "Google Chrome",
        "Microsoft Edge",
        "Brave Browser",
        "Firefox",
        "Opera",
        "Vivaldi",
        "Chromium",
        "Arc",
    ]
    if not include_extended:
        return core

    # Extended adds channels + alternates.
    extended = [
        # Apple
        "Safari Technology Preview", "Orion",
        # Chrome family channels
        "Google Chrome Beta", "Google Chrome Dev", "Google Chrome Canary",
        # Edge channels
        "Microsoft Edge Beta", "Microsoft Edge Dev", "Microsoft Edge Canary",
        # Brave channels
        "Brave Beta", "Brave Nightly",
        # Firefox family and forks
        "Firefox Developer Edition", "Firefox Nightly", "LibreWolf", "Waterfox", "Floorp",
        "Zen Browser", "Mullvad Browser", "Tor Browser",
        # Chromium & forks
        "Vivaldi Snapshot", "Opera GX", "Opera Beta", "Opera Developer",
        "Ungoogled Chromium", "Yandex", "SRWare Iron", "Slimjet", "Comodo Dragon", "Iridium",
        "Epic Privacy Browser", "Sidekick", "Wavebox", "Ghost Browser", "Thorium", "Supermium",
        # Others
        "GNOME Web", "Midori", "Falkon", "Konqueror", "SeaMonkey", "Pale Moon", "DuckDuckGo",
        "Orion Nightly",
    ]
    # preserve order, dedupe
    seen = set()
    out: List[str] = []
    for n in [*core, *extended]:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


# ---------------------------
# Platform-specific helpers
# ---------------------------

def _windows_exe_map() -> Mapping[str, str]:
    reg = _registry_by_name()
    mapping: Dict[str, str] = {}
    for name, sig in reg.items():
        # Prefer the first declared image name
        exe = sig.win_image_names[0] if sig.win_image_names else f"{name}.exe"
        mapping[name] = exe
    return mapping


def _posix_match_patterns_for(name: str) -> tuple[str, ...]:
    sig = _registry_by_name().get(name)
    if sig:
        return sig.posix_patterns or (name,)
    # Fallback heuristics
    alt = {
        "Microsoft Edge": ("Microsoft Edge", "msedge", "edge"),
        "Brave Browser": ("Brave Browser", "brave", "brave-browser"),
        "Google Chrome": ("Google Chrome", "chrome", "google-chrome"),
        "Opera": ("Opera", "opera"),
        "Vivaldi": ("Vivaldi", "vivaldi"),
        "Chromium": ("Chromium", "chromium", "chromium-browser"),
        "Arc": ("Arc", "arc"),
        "Safari": ("Safari", "WebKitWebProcess", "SafariWebContent"),
        "LibreWolf": ("LibreWolf", "librewolf"),
        "Waterfox": ("Waterfox", "waterfox"),
        "Yandex": ("Yandex", "yandex", "yandex_browser"),
        "Tor Browser": ("Tor Browser", "tor-browser", "firefox"),
        "DuckDuckGo": ("DuckDuckGo", "duckduckgo"),
    }
    return tuple(dict.fromkeys(alt.get(name, (name,))))


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


# ---------------------------
# Result types
# ---------------------------

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


# ---------------------------
# Main API
# ---------------------------

def close_browsers(
    apps: Sequence[str] | None = None,
    *,
    timeout_seconds: float = 5.0,
    force: bool = False,
    dry_run: bool = False,
    exclude: Sequence[str] | None = None,
    only_if_running: bool = True,
) -> CloseResult:
    """
    Attempt to close the given browsers.

    Note: Several channels/forks share the same process image (e.g., chrome.exe, msedge.exe, firefox.exe).
    On Windows, terminating the image typically affects all channels of that family.
    """
    reg = _registry_by_name()
    targets = list(apps or get_common_browser_app_names())
    if exclude:
        excl = set(exclude)
        targets = [t for t in targets if t not in excl]

    closed: list[str] = []
    forced_list: list[str] = []
    not_running: list[str] = []
    still_running: list[str] = []
    errors: Dict[str, str] = {}
    reports: List[AppCloseReport] = []

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
            sig = reg.get(name)
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
                    # Prefer quitting the declared app bundle if known; fall back to name.
                    if sig and sig.mac_app_names:
                        for app in sig.mac_app_names:
                            _osascript_quit(app)
                    else:
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
                        # Some apps register under their brand names in killall; also try pkill -9
                        if sig and sig.mac_app_names:
                            for app in sig.mac_app_names:
                                _killall(app)
                        else:
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
                was_running=running_now or closed_graceful or forced_this,
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
                was_running=running_now or closed_graceful or forced_this,
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
