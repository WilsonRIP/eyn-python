from __future__ import annotations

import fnmatch
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Iterable, Iterator, List, Literal, Optional, Sequence

from eyn_python.logging import get_logger
from eyn_python.paths import ensure_dir

log = get_logger(__name__)

# Canonical formats we produce
ArchiveFormat = Literal["zip", "tar", "tar.gz", "tar.bz2", "tar.xz"]
SUPPORTED_FORMATS: Final[set[ArchiveFormat]] = {"zip", "tar", "tar.gz", "tar.bz2", "tar.xz"}

# Recognized suffixes we can *extract* (aliases included)
ZIP_SUFFIXES: Final[tuple[str, ...]] = (".zip",)
TAR_SUFFIXES: Final[tuple[str, ...]] = (
    ".tar",
    ".tar.gz", ".tgz",
    ".tar.bz2", ".tbz2",
    ".tar.xz", ".txz",
)

@dataclass(slots=True)
class ArchiveSettings:
    """
    Settings controlling archive creation.

    - format: one of SUPPORTED_FORMATS
    - level: compression level (0-9 typical). For ZIP, 0 => stored (no compression).
    - recursive: include files in subdirectories (if src is a directory)
    - exclude: fnmatch-style patterns relative to the root (directory src or src.parent for a file).
               Examples: "node_modules/**", "*.pyc", "dist/", ".git/**"
    """
    format: ArchiveFormat = "zip"
    level: int = 6  # 0-9 typical
    recursive: bool = True
    exclude: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.format not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported archive format: {self.format!r}")
        if not (0 <= self.level <= 9):
            raise ValueError("level must be in [0, 9]")


def _determine_dest(src: Path, out: Optional[Path], fmt: ArchiveFormat) -> Path:
    """
    Decide the destination archive path.
    - If out is None: put archive next to src, named src.name + proper suffix.
    - If out points to an existing directory: place archive inside using src.name.
    - If out looks like a file path without a valid suffix: append the proper suffix.
    """
    ext_map: dict[ArchiveFormat, str] = {
        "zip": ".zip",
        "tar": ".tar",
        "tar.gz": ".tar.gz",
        "tar.bz2": ".tar.bz2",
        "tar.xz": ".tar.xz",
    }
    suffix = ext_map[fmt]

    if out is None:
        return (src.parent / (src.name + suffix))

    # If user passed a directory (existing), drop archive inside
    if out.exists() and out.is_dir():
        return out / (src.name + suffix)

    # If user passed a path that already ends with any known suffix, trust it
    if any(str(out).lower().endswith(s) for s in (*ZIP_SUFFIXES, *TAR_SUFFIXES)):
        return out

    # Otherwise, append the canonical suffix
    return Path(str(out) + suffix)


def _iter_paths(src: Path, recursive: bool) -> Iterator[Path]:
    """Yield files from src deterministically (sorted, depth-first-ish)"""
    if src.is_file():
        yield src
        return

    it: Iterable[Path]
    it = src.rglob("*") if recursive else src.glob("*")
    # Deterministic ordering for reproducible archives
    for p in sorted((p for p in it if p.is_file()), key=lambda x: x.as_posix()):
        yield p


def _is_excluded(root: Path, p: Path, patterns: Sequence[str]) -> bool:
    """
    Exclude if rel path matches any pattern. Supports simple dir patterns ending with '/'.
    Patterns are matched with fnmatch against POSIX-like relpaths.
    """
    if not patterns:
        return False

    rel = p.relative_to(root).as_posix()

    for pat in patterns:
        pat_norm = pat.strip()
        if not pat_norm:
            continue

        # Directory-style pattern: "foo/" means anything under foo/
        if pat_norm.endswith("/"):
            prefix = pat_norm
            if not prefix.startswith("/"):
                # ensure POSIX
                prefix = prefix.lstrip("/")
            if rel.startswith(prefix):
                return True

        # Standard fnmatch
        if fnmatch.fnmatch(rel, pat_norm):
            return True

    return False


def _zip_compression_for(level: int) -> tuple[int, Optional[int]]:
    """
    Return (compression, compresslevel) for zipfile.
    level=0 => ZIP_STORED (no compression).
    """
    if level <= 0:
        return (zipfile.ZIP_STORED, None)
    return (zipfile.ZIP_DEFLATED, level)


def create_archive(
    src: Path | str,
    out: Optional[Path | str],
    settings: ArchiveSettings,
    *,
    overwrite: bool = True,
) -> Path:
    """
    Create an archive from 'src'.

    - If src is a file: archive contains that file (at arcname=src.name).
    - If src is a dir: archive contains its contents (relative to src).

    Returns the destination archive path.
    """
    src = Path(src).resolve()
    if out is not None:
        out = Path(out)

    if not src.exists():
        raise FileNotFoundError(src)

    fmt = settings.format
    dst = _determine_dest(src, out, fmt).resolve()
    ensure_dir(dst.parent)

    if dst.exists() and not overwrite:
        raise FileExistsError(dst)

    base_dir = src if src.is_dir() else src.parent
    root = src if src.is_dir() else src.parent

    # Prevent archiving the output file if it's inside the source tree
    def _should_skip(fp: Path) -> bool:
        return (dst in fp.parents) or _is_excluded(root, fp, settings.exclude)

    if fmt == "zip":
        compression, compresslevel = _zip_compression_for(settings.level)
        # zipfile handles compresslevel=None fine (ignored for stored)
        with zipfile.ZipFile(
            dst, mode="w", compression=compression, compresslevel=compresslevel  # type: ignore[arg-type]
        ) as zf:
            for fp in _iter_paths(src, settings.recursive):
                if _should_skip(fp):
                    continue
                arcname = fp.relative_to(base_dir) if src.is_dir() else fp.name
                zf.write(fp, arcname.as_posix() if isinstance(arcname, Path) else arcname)
    else:
        mode_map: dict[ArchiveFormat, str] = {
            "tar": "w",
            "tar.gz": "w:gz",
            "tar.bz2": "w:bz2",
            "tar.xz": "w:xz",
        }
        mode = mode_map[fmt]
        # Only pass compresslevel for compressed modes
        kw = {}
        if mode != "w":
            kw["compresslevel"] = settings.level

        with tarfile.open(dst, mode=mode, **kw) as tf:
            for fp in _iter_paths(src, settings.recursive):
                if _should_skip(fp):
                    continue
                arcname = (fp.relative_to(base_dir) if src.is_dir() else Path(fp.name)).as_posix()
                tf.add(fp, arcname=arcname)

    log.info("Created archive -> %s", dst)
    return dst


def _is_within_directory(directory: Path, target: Path) -> bool:
    """Check that 'target' is within 'directory' (prevents traversal)."""
    try:
        target.resolve().relative_to(directory.resolve())
        return True
    except Exception:
        return False


def _safe_extract_zip(zf: zipfile.ZipFile, out_dir: Path) -> None:
    for info in zf.infolist():
        # Normalize to posix, disallow absolute/drive roots
        name = Path(info.filename)
        if name.is_absolute() or any(part in ("..", "") for part in name.parts):
            raise ValueError(f"Unsafe path in ZIP: {info.filename}")

        dest = (out_dir / name).resolve()
        if not _is_within_directory(out_dir, dest):
            raise ValueError(f"Path traversal detected in ZIP: {info.filename}")

        # Create parent dirs and extract
        ensure_dir(dest.parent)
        if info.is_dir():
            ensure_dir(dest)
            continue
        with zf.open(info, "r") as src, open(dest, "wb") as dst:
            dst.write(src.read())


def _safe_extract_tar(tf: tarfile.TarFile, out_dir: Path) -> None:
    for member in tf.getmembers():
        name = Path(member.name)
        if name.is_absolute() or any(part in ("..", "") for part in name.parts):
            raise ValueError(f"Unsafe path in TAR: {member.name}")

        dest = (out_dir / name).resolve()
        if not _is_within_directory(out_dir, dest):
            raise ValueError(f"Path traversal detected in TAR: {member.name}")

        # Ensure parent exists; tarfile handles file/dir creation.
        ensure_dir(dest.parent)
        tf.extract(member, path=out_dir)


def extract_archive(archive_path: Path | str, out_dir: Optional[Path | str] = None) -> Path:
    """
    Safely extract an archive to 'out_dir' (created if needed).
    ZIP and TAR (including .tgz/.tbz2/.txz) are supported.
    Returns the extraction directory.
    """
    apath = Path(archive_path).resolve()
    if not apath.exists():
        raise FileNotFoundError(apath)

    if out_dir is None:
        # Include full suffix (e.g., .tar.gz) by using with_suffixes-like behavior
        stem = apath.name
        for suf in (*TAR_SUFFIXES, *ZIP_SUFFIXES):
            if stem.lower().endswith(suf):
                stem = stem[: -len(suf)]
                break
        target = apath.parent / f"{stem}_extracted"
    else:
        target = Path(out_dir)

    target = ensure_dir(target)

    name_lower = apath.name.lower()
    if name_lower.endswith(ZIP_SUFFIXES):
        with zipfile.ZipFile(apath) as zf:
            _safe_extract_zip(zf, target)
    elif name_lower.endswith(TAR_SUFFIXES):
        with tarfile.open(apath) as tf:
            _safe_extract_tar(tf, target)
    else:
        raise ValueError(f"Unsupported archive type: {apath.suffix}")

    log.info("Extracted -> %s", target)
    return target
