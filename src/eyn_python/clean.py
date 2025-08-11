from __future__ import annotations

import fnmatch
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, Tuple

from eyn_python.logging import get_logger

log = get_logger(__name__)


DEFAULT_PATTERNS: list[str] = [
    "__pycache__/",
    "*.py[cod]",
    "*.pyo",
    "*.log",
    "*.tmp",
    ".DS_Store",
    "Thumbs.db",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "*.egg-info/",
    "build/",
    "dist/",
    ".idea/",
    ".vscode/",
]

DEFAULT_EXCLUDES: list[str] = [
    ".git/",
]


@dataclass(slots=True)
class CleanSettings:
    patterns: list[str] = field(default_factory=lambda: DEFAULT_PATTERNS.copy())
    exclude: list[str] = field(default_factory=lambda: DEFAULT_EXCLUDES.copy())
    include_hidden: bool = False
    remove_empty_dirs: bool = False
    apply: bool = False  # dry-run unless True


def _iter_all(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        # Optionally skip hidden dirs here if needed; handled in matching
        pdir = Path(dirpath)
        for d in dirnames:
            yield pdir / d
        for f in filenames:
            yield pdir / f


def _match_any(rel: str, patterns: Sequence[str]) -> bool:
    for pat in patterns:
        pat = pat.strip()
        if not pat:
            continue
        # Directory-style pattern
        if pat.endswith("/"):
            # Normalize to ensure we match directory prefixes
            if rel.startswith(pat.rstrip("/")) or rel.startswith(pat):
                return True
        if fnmatch.fnmatch(rel, pat):
            return True
    return False


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def find_junk(
    root: Path,
    settings: CleanSettings,
) -> tuple[list[Path], int]:
    """Return (paths_to_delete, total_size_bytes)."""
    root = root.resolve()
    matches: list[Path] = []
    total_size = 0

    for p in _iter_all(root):
        try:
            rel = p.relative_to(root).as_posix()
        except Exception:
            # outside of root; skip
            continue

        # skip hidden if flag not set
        if not settings.include_hidden and _is_hidden(p):
            # Allow explicit pattern to override hidden filter
            if not _match_any(rel, settings.patterns):
                continue

        # exclude patterns always win
        if _match_any(rel, settings.exclude):
            continue

        if _match_any(rel, settings.patterns):
            matches.append(p)
            if p.is_file():
                try:
                    total_size += p.stat().st_size
                except Exception:
                    pass

    return matches, total_size


def _remove_path(p: Path) -> None:
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p, ignore_errors=True)
    else:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass


def delete_paths(paths: Iterable[Path]) -> None:
    for p in sorted(paths, key=lambda x: (x.is_file(), x.as_posix()), reverse=True):
        _remove_path(p)


def remove_empty_directories(root: Path, excludes: Sequence[str]) -> list[Path]:
    removed: list[Path] = []
    # walk bottom-up
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        p = Path(dirpath)
        # Do not remove root
        if p == root:
            continue
        rel = p.relative_to(root).as_posix()
        if _match_any(rel, excludes):
            continue
        # Consider directory empty if no files/dirs remain
        if not dirnames and not filenames:
            try:
                p.rmdir()
                removed.append(p)
            except Exception:
                pass
    return removed


def clean(root: Path, settings: CleanSettings) -> dict:
    matches, total_size = find_junk(root, settings)
    result = {
        "root": str(root),
        "count": len(matches),
        "bytes": int(total_size),
        "removed": 0,
        "removed_empty": 0,
        "paths": [str(p) for p in matches],
    }

    if settings.apply:
        delete_paths(matches)
        result["removed"] = len(matches)
        if settings.remove_empty_dirs:
            empties = remove_empty_directories(root, settings.exclude)
            result["removed_empty"] = len(empties)
    return result


