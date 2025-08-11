from __future__ import annotations

import concurrent.futures
import contextlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Literal, Sequence, Protocol, TypedDict, cast

from eyn_python.logging import get_logger
from eyn_python.paths import ensure_dir
from eyn_python.utils import run, which
from eyn_python.config import ConvertSettings

log = get_logger(__name__)


# ---- Protocols for structural typing (we don't control ConvertSettings internals)
class _VideoSettingsProto(Protocol):
    video_codec: str            # e.g., "libx264"
    preset: str                 # e.g., "medium"
    crf: int                    # e.g., 23
    tune: str | None            # e.g., "film" or None
    audio_codec: str | None     # e.g., "aac"
    audio_bitrate: str | None   # e.g., "192k"


# ---- Data model
@dataclass(frozen=True)
class ConvertJob:
    src: Path
    dst: Path
    settings: ConvertSettings


# ---- Capability checks
def _require_ffmpeg() -> None:
    if which("ffmpeg") is None or which("ffprobe") is None:
        raise RuntimeError(
            "FFmpeg not found on PATH. Install FFmpeg and ensure `ffmpeg` and `ffprobe` are available."
        )


# ---- Filesystem helpers
def _iter_files(root: Path, recursive: bool) -> Iterator[Path]:
    """
    Yield files under root. If root is a file, yield it.
    """
    if root.is_file():
        yield root
        return

    it = root.rglob("*") if recursive else root.glob("*")
    for p in it:
        if p.is_file():
            yield p


def _dst_path(src: Path, base_out: Path | None, new_ext: str) -> Path:
    """
    Build destination path: (base_out or src.parent)/src.stem + new_ext
    """
    parent = base_out if base_out else src.parent
    ext = "." + new_ext.lstrip(".")
    return (parent / src.stem).with_suffix(ext)


def _is_up_to_date(src: Path, dst: Path) -> bool:
    """
    Consider up-to-date if dst exists, has nonzero size, and is newer or same mtime.
    """
    if not dst.exists():
        return False
    try:
        return dst.stat().st_size > 0 and dst.stat().st_mtime >= src.stat().st_mtime
    except FileNotFoundError:
        return False


# ---- Probing & heuristics
def _ffprobe_streams(path: Path) -> list[dict]:
    """
    Return ffprobe JSON 'streams' array, or [] on failure.
    """
    try:
        cp = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-print_format", "json",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(cp.stdout or "{}")
        streams = data.get("streams", [])
        if isinstance(streams, list):
            return streams
    except Exception:
        pass
    return []


def _first_codec(streams: list[dict], kind: Literal["video", "audio"]) -> str | None:
    for s in streams:
        if s.get("codec_type") == kind:
            c = s.get("codec_name")
            if isinstance(c, str) and c:
                return c.lower()
    return None


def _container_allows_codecs(container: str, vcodec: str | None, acodec: str | None) -> bool:
    """
    Minimal container compatibility checks for safe stream copy.
    This is intentionally conservative.
    """
    c = container.lower()
    v = (vcodec or "").lower()
    a = (acodec or "").lower()

    if c == "mp4" or c == ".mp4":
        return v in {"h264", "hevc", "h265", "av1"} and a in {"aac", "mp3"}
    if c in {"mov", ".mov"}:
        return v in {"h264", "hevc", "h265", "prores"} and a in {"aac", "pcm_s16le", "pcm_s24le"}
    if c in {"webm", ".webm"}:
        return v in {"vp8", "vp9", "av1"} and a in {"vorbis", "opus"}
    if c in {"mkv", ".mkv"}:
        # Matroska is permissive; assume OK.
        return True
    if c in {"m4a", ".m4a"}:
        # Audio-only MP4
        return v is None and a in {"aac", "alac"}
    if c in {"mp3", ".mp3"}:
        return v is None and a == "mp3"
    if c in {"ogg", ".ogg"}:
        return v is None and a in {"vorbis", "opus"}
    if c in {"flac", ".flac"}:
        return v is None and a == "flac"
    if c in {"wav", ".wav"}:
        return v is None and a.startswith("pcm_")
    return False


# ---- Argument builder
def _build_args(job: ConvertJob, *, smart_copy: bool = True) -> list[str]:
    """
    Build ffmpeg CLI based on target extension and settings.
    smart_copy: attempt stream copy when codecs/container are already compatible.
    """
    s = job.settings
    video = cast(_VideoSettingsProto, s.video)  # structural typing

    args: list[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-i", str(job.src)]

    to_ext = job.dst.suffix.lstrip(".").lower()

    # Optional smart stream-copy
    if smart_copy:
        streams = _ffprobe_streams(job.src)
        v_in = _first_codec(streams, "video")
        a_in = _first_codec(streams, "audio")
        if _container_allows_codecs(to_ext, v_in, a_in):
            # Preserve metadata & timestamps on copy
            args += ["-map", "0", "-c", "copy", "-movflags", "+faststart"]
            args.append(str(job.dst))
            return args

    # Otherwise, choose a sane encode path by container
    if to_ext in {"mp4", "mkv", "mov", "webm"}:
        # Video transcode (defaults: H.264 + AAC if unspecified)
        vcodec = getattr(video, "video_codec", "libx264")
        preset = getattr(video, "preset", "medium")
        crf = getattr(video, "crf", 23)
        tune = getattr(video, "tune", None)
        acodec = getattr(video, "audio_codec", "aac")
        abitrate = getattr(video, "audio_bitrate", "192k")

        if to_ext == "webm":
            # Prefer VP9+Opus unless user explicitly overrides
            vcodec = "libvpx-vp9" if vcodec in {"libx264", "h264"} else vcodec
            acodec = "libopus" if acodec in {"aac"} else acodec

        args += ["-map", "0"]
        args += ["-c:v", vcodec, "-preset", preset, "-crf", str(crf)]
        if tune:
            args += ["-tune", tune]
        if acodec:
            args += ["-c:a", acodec]
        if abitrate and acodec not in {"flac", "pcm_s16le", "pcm_s24le"}:
            args += ["-b:a", str(abitrate)]
        # Faststart for MP4/MOV for better streaming
        if to_ext in {"mp4", "mov"}:
            args += ["-movflags", "+faststart"]

    elif to_ext in {"mp3", "aac", "flac", "m4a", "wav", "ogg"}:
        # Audio-only
        acodec_by_ext = {
            "mp3": "libmp3lame",
            "aac": "aac",
            "flac": "flac",
            "m4a": "aac",
            "ogg": "libvorbis",
            "wav": "pcm_s16le",
        }
        acodec = acodec_by_ext[to_ext]
        abitrate = getattr(cast(_VideoSettingsProto, s.video), "audio_bitrate", "192k")

        args += ["-vn", "-map", "0:a:0?"]  # select first audio stream if present
        args += ["-c:a", acodec]
        if to_ext not in {"flac", "wav"} and abitrate:
            args += ["-b:a", str(abitrate)]
    else:
        # Unknown container; try stream copy (ffmpeg will error if incompatible)
        args += ["-map", "0", "-c", "copy"]

    args.append(str(job.dst))
    return args


# ---- Planning
def plan_conversions(src: Path, settings: ConvertSettings) -> list[ConvertJob]:
    """
    Plan conversions under src (file or directory) according to settings.
    """
    _require_ffmpeg()

    files = list(_iter_files(src, getattr(settings, "recursive", True)))
    if not files:
        raise FileNotFoundError(f"No input files found at: {src}")

    jobs: list[ConvertJob] = []
    for f in files:
        # Skip hidden/system junk files proactively
        if f.name.startswith(".") or f.name.lower() in {"thumbs.db", "desktop.ini"}:
            continue
        dst = _dst_path(f, getattr(settings, "output_dir", None), getattr(settings, "to"))
        # Avoid accidental self-overwrite in-place when ext matches
        if f.resolve() == dst.resolve():
            dst = dst.with_suffix(f".conv{dst.suffix}")
        jobs.append(ConvertJob(src=f, dst=dst, settings=settings))
    return jobs


# ---- Execution
def _run_one(job: ConvertJob, *, smart_copy: bool, dry_run: bool, skip_if_up_to_date: bool) -> tuple[ConvertJob, bool]:
    """
    Run a single conversion. Returns (job, success).
    """
    try:
        ensure_dir(job.dst.parent)

        if skip_if_up_to_date and _is_up_to_date(job.src, job.dst):
            log.info(f"Up-to-date, skipping: {job.src.name}")
            return job, True

        # Write atomically
        tmp_out = job.dst.with_suffix(job.dst.suffix + ".part")
        if tmp_out.exists():
            try:
                tmp_out.unlink()
            except Exception:
                pass

        args = _build_args(ConvertJob(job.src, tmp_out, job.settings), smart_copy=smart_copy)
        log.info(f"Converting: {job.src.name} -> {job.dst.name}")
        if dry_run:
            log.info("DRY-RUN: %s", " ".join(args))
            return job, True

        cp = run(args, check=False)  # rely on project run(); returns CompletedProcess
        rc = getattr(cp, "returncode", 1)
        if rc != 0:
            # Clean partial file on failure
            if tmp_out.exists():
                with contextlib.suppress(Exception):
                    tmp_out.unlink()
            log.error(f"ffmpeg failed ({rc}): {job.src}")
            return job, False

        # Commit atomically
        if job.dst.exists():
            with contextlib.suppress(Exception):
                job.dst.unlink()
        tmp_out.replace(job.dst)
        return job, True

    except Exception as e:
        log.exception(f"Error converting {job.src}: {e}")
        return job, False


def convert_all(
    jobs: Sequence[ConvertJob],
    *,
    workers: int | None = None,
    smart_copy: bool = True,
    dry_run: bool = False,
    skip_if_up_to_date: bool = True,
) -> None:
    """
    Execute all conversions.

    Parameters
    ----------
    workers:
        Max concurrent ffmpeg processes. Defaults to max(1, os.cpu_count() // 2).
    smart_copy:
        If True, uses ffprobe to attempt stream copy when container/codec compatible.
    dry_run:
        If True, only logs planned commands without running them.
    skip_if_up_to_date:
        If True, skip when destination exists, is non-empty, and not older than source.
    """
    if not jobs:
        log.info("No jobs to process.")
        return

    # Ensure outputs exist (best-effort)
    for j in jobs:
        ensure_dir(j.dst.parent)

    max_workers = workers or max(1, (os.cpu_count() or 2) // 2)
    successes = 0

    if max_workers == 1:
        for j in jobs:
            _, ok = _run_one(j, smart_copy=smart_copy, dry_run=dry_run, skip_if_up_to_date=skip_if_up_to_date)
            successes += int(ok)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = [
                ex.submit(_run_one, j, smart_copy=smart_copy, dry_run=dry_run, skip_if_up_to_date=skip_if_up_to_date)
                for j in jobs
            ]
            for fut in concurrent.futures.as_completed(futs):
                _, ok = fut.result()
                successes += int(ok)

    log.info("Completed %d/%d conversions.", successes, len(jobs))
