from __future__ import annotations

from pydantic import BaseModel, Field
from pathlib import Path

class GlobalSettings(BaseModel):
    default_output: Path = Field(default_factory=lambda: Path.cwd() / "out")
    overwrite: bool = False

class DownloadSettings(BaseModel):
    # More flexible default: best video+audio with fallback to single best
    format: str = "bv*+ba/b"
    playlist: bool = False
    metadata: bool = True
    embed_thumbnail: bool = True
    concurrent_fragments: int = 8

class ConvertVideoSettings(BaseModel):
    crf: int = 23
    preset: str = "medium"
    tune: str | None = None
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str | None = "192k"

class ConvertSettings(BaseModel):
    to: str
    recursive: bool = False
    output_dir: Path | None = None
    video: ConvertVideoSettings = Field(default_factory=ConvertVideoSettings)


