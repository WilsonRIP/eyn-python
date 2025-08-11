from __future__ import annotations

from pathlib import Path
import os

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def user_downloads_dir() -> Path:
    """Best-effort to locate the user's Downloads folder across OSes."""
    home = Path.home()

    # Respect XDG on POSIX systems
    if os.name == "posix":
        xdg = os.environ.get("XDG_DOWNLOAD_DIR")
        if xdg:
            p = Path(xdg)
            if p.is_dir():
                return p

    # Common fallback: ~/Downloads if it exists, else home
    downloads = home / "Downloads"
    return downloads if downloads.exists() else home


