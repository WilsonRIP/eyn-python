from __future__ import annotations

from pathlib import Path

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def user_downloads_dir() -> Path:
    """Best-effort to locate the user's Downloads folder across OSes."""
    # Respect XDG on Linux
    try:
        import os
        home = Path.home()
        if os.name == "posix":
            xdg = os.environ.get("XDG_DOWNLOAD_DIR")
            if xdg:
                p = Path(xdg)
                if p.is_dir():
                    return p
        # Common fallback
        downloads = home / "Downloads"
        if downloads.exists():
            return downloads
        return home
    except Exception:
        return Path.cwd()


