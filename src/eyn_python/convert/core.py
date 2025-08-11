from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from eyn_python.logging import get_logger
from eyn_python.paths import ensure_dir
from eyn_python.utils import run, which
from eyn_python.config import ConvertSettings

log = get_logger(__name__)

@dataclass(frozen=True)
class ConvertJob:
    src: Path
    dst: Path
    settings: ConvertSettings

def _require_ffmpeg() -> None:
    if which("ffmpeg") is None or which("ffprobe") is None:
        raise RuntimeError(
            "FFmpeg not found on PATH. Install FFmpeg and ensure `ffmpeg` and `ffprobe` are available."
        )

def _iter_files(root: Path, recursive: bool) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    if recursive:
        for p in root.rglob("*"):
            if p.is_file():
                yield p
    else:
        for p in root.glob("*"):
            if p.is_file():
                yield p

def _dst_path(src: Path, base_out: Path | None, new_ext: str) -> Path:
    parent = base_out if base_out else src.parent
    return (parent / src.stem).with_suffix("." + new_ext.lstrip("."))

def _build_args(job: ConvertJob) -> list[str]:
    s = job.settings
    args: list[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-i", str(job.src)]

    # Choose path by target extension (basic heuristic)
    to_ext = s.to.lower()

    if to_ext in {"mp4", "mkv", "mov", "webm"}:
        # Video transcode (defaults to H.264 + AAC)
        args += ["-c:v", s.video.video_codec, "-preset", s.video.preset, "-crf", str(s.video.crf)]
        if s.video.tune:
            args += ["-tune", s.video.tune]
        if s.video.audio_codec:
            args += ["-c:a", s.video.audio_codec]
        if s.video.audio_bitrate:
            args += ["-b:a", s.video.audio_bitrate]
    elif to_ext in {"mp3", "aac", "flac", "m4a", "wav", "ogg"}:
        # Audio-only
        args += ["-vn"]
        if to_ext == "mp3":
            args += ["-c:a", "libmp3lame"]
        elif to_ext == "aac":
            args += ["-c:a", "aac"]
        elif to_ext == "flac":
            args += ["-c:a", "flac"]
        elif to_ext == "m4a":
            args += ["-c:a", "aac"]
        elif to_ext == "ogg":
            args += ["-c:a", "libvorbis"]
        elif to_ext == "wav":
            args += ["-c:a", "pcm_s16le"]
        if s.video.audio_bitrate and to_ext not in {"flac", "wav"}:
            args += ["-b:a", s.video.audio_bitrate]
    else:
        # Generic remux or attempt transcode with stream copy
        # If unknown, attempt stream copy; ffmpeg will error if incompatible
        args += ["-c", "copy"]

    args.append(str(job.dst))
    return args

def plan_conversions(src: Path, settings: ConvertSettings) -> list[ConvertJob]:
    _require_ffmpeg()
    files = list(_iter_files(src, settings.recursive))
    if not files:
        raise FileNotFoundError(f"No input files found at: {src}")

    jobs: list[ConvertJob] = []
    for f in files:
        dst = _dst_path(f, settings.output_dir, settings.to)
        jobs.append(ConvertJob(src=f, dst=dst, settings=settings))
    return jobs

def convert_all(jobs: Sequence[ConvertJob]) -> None:
    # Ensure output dir exists (best-effort)
    for j in jobs:
        ensure_dir(j.dst.parent)

    for j in jobs:
        log.info(f"Converting: {j.src.name} -> {j.dst.name}")
        args = _build_args(j)
        run(args)
    log.info("All conversions done.")


