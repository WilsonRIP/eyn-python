from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar
import shutil

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from eyn_python.logging import get_logger
from eyn_python.paths import ensure_dir, user_downloads_dir
from eyn_python.config import DownloadSettings
from eyn_python.download.progress import create_youtube_progress_hook

log = get_logger(__name__)
T = TypeVar("T")


@dataclass(frozen=True)
class DownloadJob:
    url: str
    output_dir: Path
    settings: DownloadSettings  # see fields referenced via _get()


# ---------------- helpers ----------------
def _get(settings: Any, name: str, default: T) -> T:
    return getattr(settings, name, default)  # type: ignore[return-value]


def _progress_hook_factory() -> Callable[[Dict[str, Any]], None]:
    """Create a progress hook for YouTube downloads with Rich progress bars."""
    return create_youtube_progress_hook()


def _detect_ffmpeg(ffmpeg_location: Optional[str]) -> None:
    exe = ffmpeg_location or "ffmpeg"
    if shutil.which(exe) is None:
        log.warning(
            f"ffmpeg not found ({exe}). Install ffmpeg and/or set settings.ffmpeg_location."
        )


# ---------------- options builder ----------------
def build_ydl_opts(job: DownloadJob) -> Dict[str, Any]:
    """
    Resilient defaults. Optional DownloadSettings fields honored when present:
      - format: str
      - playlist: bool
      - metadata: bool
      - embed_thumbnail: bool
      - audio_only: bool            # <— use to allow thumbnail embedding
      - concurrent_fragments: int
      - cookiefile: str | Path
      - cookiesfrombrowser: tuple[str, Optional[str], Optional[str]]
      - rate_limit: str | int
      - timeout: int
      - proxy: str
      - ffmpeg_location: str | Path
      - container: str              # "mp4" (default) or "mkv"
    """
    # Safer default format chain for YouTube (caps at 4K/60)
    default_format = (
        "bestvideo[ext=mp4][height<=2160][fps<=60]+bestaudio[ext=m4a]/"
        "bestvideo[height<=2160][fps<=60]+bestaudio/"
        "best"
    )

    fmt = _get(job.settings, "format", default_format)
    want_playlist = bool(_get(job.settings, "playlist", False))
    with_metadata = bool(_get(job.settings, "metadata", True))
    embed_thumb_req = bool(_get(job.settings, "embed_thumbnail", False))
    audio_only = bool(_get(job.settings, "audio_only", False))  # you can expose this in your CLI if useful
    concurrent = int(_get(job.settings, "concurrent_fragments", 5))
    cookiefile: Optional[str] = _get(job.settings, "cookiefile", None)
    cookiesfrombrowser: Optional[tuple[str, Optional[str], Optional[str]]] = _get(
        job.settings, "cookiesfrombrowser", None
    )
    rate_limit = _get(job.settings, "rate_limit", None)
    timeout = int(_get(job.settings, "timeout", 30))
    proxy = _get(job.settings, "proxy", None)
    ffmpeg_location = _get(job.settings, "ffmpeg_location", None)
    container = str(_get(job.settings, "container", "mp4")).lower()

    # Output template (+ playlist index for playlists)
    base_tmpl = "%(uploader)s - %(title)s [%(id)s].%(ext)s"
    if want_playlist:
        base_tmpl = "%(playlist_index>03)s - " + base_tmpl
    outtmpl = str(job.output_dir / base_tmpl)

    # Post-processors
    pp: list[dict[str, Any]] = []
    if with_metadata:
        pp.append({"key": "FFmpegMetadata"})

    # Only embed thumbnails for audio outputs (m4a/mp3/opus/etc.).
    # Doing this for MP4 video often fails and can cause ffmpeg exit code 8.
    if embed_thumb_req and audio_only:
        pp.append({"key": "EmbedThumbnail"})

    # Keep final container explicit and simple
    pp.append({"key": "FFmpegVideoRemuxer", "preferedformat": container})

    ydl_opts: Dict[str, Any] = {
        # Output / filenames
        "outtmpl": outtmpl,
        "outtmpl_na_placeholder": "NA",        "restrictfilenames": True,

        # Selection
        "format": fmt,
        "noplaylist": not want_playlist,

        # Do NOT ignore errors; we want to fail fast if post-processing breaks
        "ignoreerrors": False,

        # Network hardening
        "retries": 15,
        "fragment_retries": 15,
        "continuedl": True,
        "concurrent_fragment_downloads": max(1, min(concurrent, 20)),
        "timeout": timeout,
        "source_address": "0.0.0.0",
        "hls_prefer_native": False,
        "skip_unavailable_fragments": True,
        **({"ratelimit": rate_limit} if rate_limit else {}),
        **({"proxy": proxy} if proxy else {}),

        # Post-processing
        "merge_output_format": container,
        "postprocessors": pp,
        "postprocessor_args": {
            "FFmpeg": ["-movflags", "+faststart"]
        },
        "writethumbnail": bool(embed_thumb_req and audio_only),

        # Logging
        "progress_hooks": [_progress_hook_factory()],
        "quiet": True,
        "no_warnings": True,

        # Headers / extractor tuning
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        "extractor_args": {
            "youtube": {"player_client": ["android", "ios", "web"]},
        },
    }

    # Cookies (choose one)
    if cookiefile:
        ydl_opts["cookiefile"] = str(cookiefile)
    elif cookiesfrombrowser:
        ydl_opts["cookiesfrombrowser"] = cookiesfrombrowser

    if ffmpeg_location:
        ydl_opts["ffmpeg_location"] = str(ffmpeg_location)

    return ydl_opts


# ---------------- public API ----------------
def download(job: DownloadJob) -> None:
    # Default to ~/Downloads when output_dir is unset or equals CWD/out
    out = job.output_dir
    if not out or str(out).endswith("/out") or str(out).lower().endswith("\\out"):
        try:
            default_dl = user_downloads_dir()
            out = default_dl
        except Exception:
            out = job.output_dir
    ensure_dir(out)
    ffmpeg_location = _get(job.settings, "ffmpeg_location", None)
    _detect_ffmpeg(ffmpeg_location)

    # Rebuild options with possibly updated output dir
    job = DownloadJob(url=job.url, output_dir=out, settings=job.settings)
    ydl_opts = build_ydl_opts(job)
    log.info(f"Downloading -> {job.output_dir}")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([job.url])
    except DownloadError as e:
        log.error(f"yt-dlp failed: {e!s}")
        log.error(
            "Hints: update yt-dlp, provide cookies for age/region restrictions, "
            "ensure ffmpeg is installed, and try again."
        )
        raise
    except Exception as e:
        log.exception("Unexpected error during download")
        raise
    else:
        log.info("Done.")
