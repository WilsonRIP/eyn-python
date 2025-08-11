from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class AudioExtractOptions:
    codec: Optional[str] = None
    bitrate: Optional[str] = None


def extract_audio(src: Path, out: Optional[Path], to_ext: str, options: AudioExtractOptions) -> Path:
    _require_ffmpeg()
    dst = _dst_with_ext(src, out, to_ext)

    args: list[str] = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-i",
        str(src),
        "-vn",
    ]

    if options.codec:
        args += ["-c:a", options.codec]
    if options.bitrate and to_ext.lower() not in {"flac", "wav"}:
        args += ["-b:a", options.bitrate]

    args.append(str(dst))
    log.info(f"Extracting audio: {src.name} -> {dst.name}")
    run(args)
    return dst


