from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from eyn_python.logging import get_logger
from eyn_python.utils import run, which

log = get_logger(__name__)


def _require_ffmpeg() -> None:
    if which("ffmpeg") is None or which("ffprobe") is None:
        raise RuntimeError(
            "FFmpeg not found on PATH. Install FFmpeg and ensure `ffmpeg` and `ffprobe` are available."
        )


def ffprobe_json(src: Path) -> Dict[str, Any]:
    _require_ffmpeg()
    cp = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(src),
        ],
        capture_output=True,
    )
    return json.loads(cp.stdout or "{}")


