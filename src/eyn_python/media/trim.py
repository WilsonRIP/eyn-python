from __future__ import annotations

from pathlib import Path
from typing import Optional

from eyn_python.logging import get_logger
from eyn_python.utils import run, which

log = get_logger(__name__)


def _require_ffmpeg() -> None:
    if which("ffmpeg") is None or which("ffprobe") is None:
        raise RuntimeError(
            "FFmpeg not found on PATH. Install FFmpeg and ensure `ffmpeg` and `ffprobe` are available."
        )


def _dst_with_ext(src: Path, out: Optional[Path], new_ext: str) -> Path:
    parent = out if out else src.parent
    return (parent / src.stem).with_suffix("." + new_ext.lstrip("."))


def trim_media(
    src: Path,
    out: Optional[Path],
    to_ext: Optional[str],
    start: str,
    end: Optional[str],
    copy: bool = True,
) -> Path:
    _require_ffmpeg()
    target_ext = to_ext or src.suffix.lstrip(".") or "mp4"
    dst = _dst_with_ext(src, out, target_ext)

    args: list[str] = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-ss",
        start,
        "-i",
        str(src),
    ]

    if end:
        args += ["-to", end]

    if copy:
        args += ["-c", "copy"]

    args.append(str(dst))
    log.info(f"Trimming: {src.name} [{start}{' -> ' + end if end else ''}] -> {dst.name}")
    run(args)
    return dst


