from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import httpx

from eyn_python.paths import ensure_dir
from eyn_python.download.progress import download_with_progress


def download_asset(url: str, out_dir: Path) -> Path:
    ensure_dir(out_dir)
    name = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1] or "index.html"
    dst = out_dir / name
    
    # Download with progress bar
    download_with_progress(url, dst, name)
    
    return dst


def save_page(url: str, out_dir: Path) -> Dict[str, str]:
    ensure_dir(out_dir)
    with httpx.Client(follow_redirects=True, timeout=15.0) as c:
        r = c.get(url)
        r.raise_for_status()
        html = r.text
    fname = (out_dir / "page.html")
    fname.write_text(html, encoding="utf-8")
    return {"url": url, "path": str(fname)}


