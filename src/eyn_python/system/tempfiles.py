from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

from eyn_python.paths import ensure_dir


@dataclass(frozen=True)
class TempCleanSettings:
    older_than_hours: float = 24.0
    include_hidden: bool = True
    apply: bool = False
    remove_empty_dirs: bool = True


def default_temp_dir() -> Path:
    return Path(tempfile.gettempdir()).resolve()


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def _iter_all(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        pdir = Path(dirpath)
        for f in filenames:
            yield pdir / f
        for d in dirnames:
            yield pdir / d


def _older_than(p: Path, threshold_epoch: float) -> bool:
    try:
        return p.stat().st_mtime < threshold_epoch
    except Exception:
        return False


def _remove_path(p: Path) -> None:
    try:
        if p.is_dir() and not p.is_symlink():
            # Attempt directory removal if empty after file deletions
            p.rmdir()
        else:
            p.unlink(missing_ok=True)
    except Exception:
        pass


def _remove_empty_dirs(root: Path) -> int:
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        p = Path(dirpath)
        if p == root:
            continue
        try:
            # Only remove if fully empty now
            if not any(Path(dirpath).iterdir()):
                p.rmdir()
                removed += 1
        except Exception:
            continue
    return removed


def clean_temp(root: Path | None, settings: TempCleanSettings) -> dict:
    base = Path(root or default_temp_dir()).resolve()
    ensure_dir(base)
    threshold = time.time() - max(0.0, settings.older_than_hours) * 3600.0

    targets: list[Path] = []
    total_bytes = 0

    for p in _iter_all(base):
        # Skip hidden if disabled
        if not settings.include_hidden and _is_hidden(p):
            continue
        # Only consider files (delete files first); directories handled separately
        if p.is_file() and _older_than(p, threshold):
            targets.append(p)
            try:
                total_bytes += p.stat().st_size
            except Exception:
                pass

    removed = 0
    removed_empty = 0
    if settings.apply:
        # Delete files first
        for t in sorted(targets, key=lambda x: x.as_posix()):
            _remove_path(t)
            removed += 1
        if settings.remove_empty_dirs:
            removed_empty = _remove_empty_dirs(base)

    return {
        "root": str(base),
        "count": len(targets),
        "bytes": int(total_bytes),
        "removed": removed,
        "removed_empty": removed_empty,
        "paths": [str(p) for p in targets],
    }


