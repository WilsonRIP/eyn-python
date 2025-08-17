from __future__ import annotations

import os
import json
import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, cast
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse

import httpx
from PIL import Image
from PIL.ExifTags import TAGS

# Try to import magic, fallback gracefully if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

from eyn_python.logging import get_logger
from eyn_python.scrape.extract import extract_metadata as extract_web_meta
from eyn_python.media.ffprobe import ffprobe_json

log = get_logger(__name__)


@dataclass
class FileMetadata:
    """Basic file metadata."""
    path: str
    name: str
    size: int
    extension: str
    mime_type: Optional[str]
    magic_type: Optional[str]
    created: Optional[datetime]
    modified: Optional[datetime]
    accessed: Optional[datetime]
    is_text: bool
    encoding: Optional[str]
    hash_md5: Optional[str]
    hash_sha256: Optional[str]


@dataclass
class WebMetadata:
    """Web page metadata."""
    url: str
    title: Optional[str]
    description: Optional[str]
    keywords: Optional[str]
    language: Optional[str]
    canonical: Optional[str]
    robots: Optional[str]
    opengraph: Dict[str, str]
    twitter: Dict[str, str]
    headings: Dict[str, int]
    images: Dict[str, Any]
    word_count: int
    status_code: int
    content_type: Optional[str]
    content_length: Optional[int]
    last_modified: Optional[str]
    etag: Optional[str]


@dataclass
class ImageMetadata:
    """Image-specific metadata."""
    dimensions: tuple[int, int]
    mode: str
    format: Optional[str]
    dpi: Optional[tuple[float, float]]
    exif: Dict[str, Any]
    icc_profile: Optional[bool]
    transparency: Optional[bool]
    animation: Optional[bool]


@dataclass
class VideoMetadata:
    """Video-specific metadata."""
    duration: Optional[float]
    dimensions: Optional[tuple[int, int]]
    fps: Optional[float]
    bitrate: Optional[int]
    codec: Optional[str]
    audio_codec: Optional[str]
    audio_channels: Optional[int]
    audio_sample_rate: Optional[int]


@dataclass
class AudioMetadata:
    """Audio-specific metadata."""
    duration: Optional[float]
    bitrate: Optional[int]
    codec: Optional[str]
    channels: Optional[int]
    sample_rate: Optional[int]
    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    year: Optional[int]
    genre: Optional[str]


@dataclass
class DocumentMetadata:
    """Document-specific metadata."""
    pages: Optional[int]
    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    creator: Optional[str]
    producer: Optional[str]
    creation_date: Optional[str]
    modification_date: Optional[str]
    keywords: Optional[List[str]]


@dataclass
class ArchiveMetadata:
    """Archive-specific metadata."""
    format: str
    compression: Optional[str]
    file_count: Optional[int]
    total_size: Optional[int]
    comment: Optional[str]


@dataclass
class MetadataResult:
    """Complete metadata result."""
    file_metadata: FileMetadata
    web_metadata: Optional[WebMetadata]
    image_metadata: Optional[ImageMetadata]
    video_metadata: Optional[VideoMetadata]
    audio_metadata: Optional[AudioMetadata]
    document_metadata: Optional[DocumentMetadata]
    archive_metadata: Optional[ArchiveMetadata]
    raw_data: Dict[str, Any]


def _serialize_datetime(obj):
    """Helper function to serialize datetime objects for JSON."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _calculate_file_hashes(file_path: Path) -> tuple[Optional[str], Optional[str]]:
    """Calculate MD5 and SHA256 hashes of a file."""
    try:
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
                sha256_hash.update(chunk)
        
        return md5_hash.hexdigest(), sha256_hash.hexdigest()
    except Exception as e:
        log.debug(f"Hash calculation failed: {e}")
        return None, None


def _get_file_timestamps(file_path: Path) -> tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
    """Get file timestamps."""
    try:
        stat = file_path.stat()
        created = datetime.fromtimestamp(stat.st_ctime) if hasattr(stat, 'st_ctime') else None
        modified = datetime.fromtimestamp(stat.st_mtime) if hasattr(stat, 'st_mtime') else None
        accessed = datetime.fromtimestamp(stat.st_atime) if hasattr(stat, 'st_atime') else None
        return created, modified, accessed
    except Exception as e:
        log.debug(f"Timestamp extraction failed: {e}")
        return None, None, None


def extract_file_metadata(file_path: Union[str, Path]) -> FileMetadata:
    """Extract basic file metadata."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Basic file info
    size = file_path.stat().st_size
    name = file_path.name
    extension = file_path.suffix.lower()
    
    # MIME type detection
    mime_type, encoding = mimetypes.guess_type(str(file_path))
    
    # Magic type detection
    magic_type = None
    if MAGIC_AVAILABLE:
        try:
            with open(file_path, 'rb') as f:
                magic_type = magic.from_buffer(f.read(2048), mime=True)  # type: ignore
        except Exception as e:
            log.debug(f"Magic detection failed: {e}")
    
    # Timestamps
    created, modified, accessed = _get_file_timestamps(file_path)
    
    # Text detection
    is_text = False
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(1024)
            is_text = sample.isascii() and b'\x00' not in sample
    except Exception as e:
        log.debug(f"Text detection failed: {e}")
    
    # Hashes
    hash_md5, hash_sha256 = _calculate_file_hashes(file_path)
    
    return FileMetadata(
        path=str(file_path),
        name=name,
        size=size,
        extension=extension,
        mime_type=mime_type,
        magic_type=magic_type,
        created=created,
        modified=modified,
        accessed=accessed,
        is_text=is_text,
        encoding=encoding,
        hash_md5=hash_md5,
        hash_sha256=hash_sha256
    )


def extract_web_metadata(url: str, timeout: float = 30.0) -> WebMetadata:
    """Extract metadata from a web page."""
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        
        html = response.text
        meta_data = extract_web_meta(html, url)
        
        return WebMetadata(
            url=url,
            title=str(meta_data.get("title")) if meta_data.get("title") is not None else None,
            description=str(meta_data.get("description")) if meta_data.get("description") is not None else None,
            keywords=str(meta_data.get("keywords")) if meta_data.get("keywords") is not None else None,
            language=str(meta_data.get("lang")) if meta_data.get("lang") is not None else None,
            canonical=str(meta_data.get("canonical")) if meta_data.get("canonical") is not None else None,
            robots=str(meta_data.get("robots")) if meta_data.get("robots") is not None else None,
            opengraph=cast(Dict[str, str], meta_data.get("opengraph", {})),
            twitter=cast(Dict[str, str], meta_data.get("twitter", {})),
            headings=cast(Dict[str, int], meta_data.get("headings", {})),
            images=cast(Dict[str, Any], meta_data.get("images", {})),
            word_count=int(str(meta_data.get("word_count", 0))),
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            content_length=int(response.headers.get("content-length", 0)) if response.headers.get("content-length") else None,
            last_modified=response.headers.get("last-modified"),
            etag=response.headers.get("etag")
        )


def extract_image_metadata(file_path: Union[str, Path]) -> ImageMetadata:
    """Extract image-specific metadata."""
    file_path = Path(file_path)
    
    try:
        with Image.open(file_path) as img:
            # Basic image info
            dimensions = img.size
            mode = img.mode
            format_name = img.format
            
            # DPI info
            dpi = img.info.get('dpi')
            
            # EXIF data
            exif_data = {}
            if hasattr(img, '_getexif') and img._getexif():  # type: ignore
                exif = img._getexif()  # type: ignore
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = value
            
            # Additional info
            icc_profile = 'icc_profile' in img.info
            transparency = img.info.get('transparency') is not None
            animation = hasattr(img, 'n_frames') and img.n_frames > 1  # type: ignore
            
            return ImageMetadata(
                dimensions=dimensions,
                mode=mode,
                format=format_name,
                dpi=dpi,
                exif=exif_data,
                icc_profile=icc_profile,
                transparency=transparency,
                animation=animation
            )
    except Exception as e:
        log.debug(f"Image metadata extraction failed: {e}")
        raise


def extract_video_metadata(file_path: Union[str, Path]) -> VideoMetadata:
    """Extract video-specific metadata using ffprobe."""
    file_path = Path(file_path)
    
    try:
        probe_data = ffprobe_json(file_path)
        
        # Get video stream
        video_stream = None
        audio_stream = None
        
        for stream in probe_data.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
            elif stream.get('codec_type') == 'audio':
                audio_stream = stream
        
        # Extract video metadata
        duration = None
        if 'format' in probe_data:
            duration = float(probe_data['format'].get('duration', 0))
        
        dimensions = None
        fps = None
        codec = None
        if video_stream:
            width = video_stream.get('width')
            height = video_stream.get('height')
            if width and height:
                dimensions = (width, height)
            
            fps_str = video_stream.get('r_frame_rate')
            if fps_str:
                try:
                    num, den = map(int, fps_str.split('/'))
                    fps = num / den if den != 0 else None
                except (ValueError, ZeroDivisionError):
                    pass
            
            codec = video_stream.get('codec_name')
        
        # Extract audio metadata
        audio_codec = None
        audio_channels = None
        audio_sample_rate = None
        if audio_stream:
            audio_codec = audio_stream.get('codec_name')
            audio_channels = audio_stream.get('channels')
            audio_sample_rate = audio_stream.get('sample_rate')
        
        bitrate = None
        if 'format' in probe_data:
            bitrate = int(probe_data['format'].get('bit_rate', 0))
        
        return VideoMetadata(
            duration=duration,
            dimensions=dimensions,
            fps=fps,
            bitrate=bitrate,
            codec=codec,
            audio_codec=audio_codec,
            audio_channels=audio_channels,
            audio_sample_rate=audio_sample_rate
        )
    except Exception as e:
        log.debug(f"Video metadata extraction failed: {e}")
        raise


def extract_audio_metadata(file_path: Union[str, Path]) -> AudioMetadata:
    """Extract audio-specific metadata using ffprobe."""
    file_path = Path(file_path)
    
    try:
        probe_data = ffprobe_json(file_path)
        
        # Get audio stream
        audio_stream = None
        for stream in probe_data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break
        
        # Extract metadata
        duration = None
        if 'format' in probe_data:
            duration = float(probe_data['format'].get('duration', 0))
        
        bitrate = None
        if 'format' in probe_data:
            bitrate = int(probe_data['format'].get('bit_rate', 0))
        
        codec = None
        channels = None
        sample_rate = None
        if audio_stream:
            codec = audio_stream.get('codec_name')
            channels = audio_stream.get('channels')
            sample_rate = audio_stream.get('sample_rate')
        
        # Try to extract ID3 tags or other metadata
        title = None
        artist = None
        album = None
        year = None
        genre = None
        
        if 'format' in probe_data:
            tags = probe_data['format'].get('tags', {})
            title = tags.get('title')
            artist = tags.get('artist')
            album = tags.get('album')
            year_str = tags.get('date') or tags.get('year')
            if year_str:
                try:
                    year = int(year_str[:4])  # Take first 4 digits
                except (ValueError, TypeError):
                    pass
            genre = tags.get('genre')
        
        return AudioMetadata(
            duration=duration,
            bitrate=bitrate,
            codec=codec,
            channels=channels,
            sample_rate=sample_rate,
            title=title,
            artist=artist,
            album=album,
            year=year,
            genre=genre
        )
    except Exception as e:
        log.debug(f"Audio metadata extraction failed: {e}")
        raise


def extract_document_metadata(file_path: Union[str, Path]) -> DocumentMetadata:
    """Extract document-specific metadata."""
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    try:
        if extension == '.pdf':
            from eyn_python.media.pdf_tools import pdf_get_info
            pdf_info = pdf_get_info(file_path)
            
            return DocumentMetadata(
                pages=pdf_info.get('pages'),
                title=pdf_info.get('title'),
                author=pdf_info.get('author'),
                subject=pdf_info.get('subject'),
                creator=pdf_info.get('creator'),
                producer=pdf_info.get('producer'),
                creation_date=pdf_info.get('creation_date'),
                modification_date=pdf_info.get('modification_date'),
                keywords=pdf_info.get('keywords', '').split(',') if pdf_info.get('keywords') else None
            )
        else:
            # For other document types, return basic info
            return DocumentMetadata(
                pages=None,
                title=None,
                author=None,
                subject=None,
                creator=None,
                producer=None,
                creation_date=None,
                modification_date=None,
                keywords=None
            )
    except Exception as e:
        log.debug(f"Document metadata extraction failed: {e}")
        raise


def extract_archive_metadata(file_path: Union[str, Path]) -> ArchiveMetadata:
    """Extract archive-specific metadata."""
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    try:
        import zipfile
        import tarfile
        
        if extension == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zf:
                file_count = len(zf.namelist())
                total_size = sum(info.file_size for info in zf.infolist())
                comment = zf.comment.decode('utf-8') if zf.comment else None
                
                return ArchiveMetadata(
                    format='ZIP',
                    compression=None,
                    file_count=file_count,
                    total_size=total_size,
                    comment=comment
                )
        
        elif extension in ['.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz']:
            with tarfile.open(file_path, 'r:*') as tf:
                file_count = len(tf.getnames())
                total_size = sum(member.size for member in tf.getmembers())
                
                return ArchiveMetadata(
                    format='TAR',
                    compression=extension.split('.')[-1] if '.' in extension else None,
                    file_count=file_count,
                    total_size=total_size,
                    comment=None
                )
        
        else:
            return ArchiveMetadata(
                format='UNKNOWN',
                compression=None,
                file_count=None,
                total_size=None,
                comment=None
            )
    except Exception as e:
        log.debug(f"Archive metadata extraction failed: {e}")
        raise


def extract_comprehensive_metadata(file_path: Union[str, Path], include_specialized: bool = True) -> MetadataResult:
    """Extract comprehensive metadata from a file."""
    file_path = Path(file_path)
    
    # Basic file metadata
    file_meta = extract_file_metadata(file_path)
    
    # Initialize specialized metadata
    web_meta = None
    image_meta = None
    video_meta = None
    audio_meta = None
    document_meta = None
    archive_meta = None
    
    if include_specialized:
        extension = file_path.suffix.lower()
        
        # Image metadata
        if extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            try:
                image_meta = extract_image_metadata(file_path)
            except Exception as e:
                log.debug(f"Image metadata extraction failed: {e}")
        
        # Video metadata
        elif extension in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']:
            try:
                video_meta = extract_video_metadata(file_path)
            except Exception as e:
                log.debug(f"Video metadata extraction failed: {e}")
        
        # Audio metadata
        elif extension in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a']:
            try:
                audio_meta = extract_audio_metadata(file_path)
            except Exception as e:
                log.debug(f"Audio metadata extraction failed: {e}")
        
        # Document metadata
        elif extension in ['.pdf', '.doc', '.docx', '.txt']:
            try:
                document_meta = extract_document_metadata(file_path)
            except Exception as e:
                log.debug(f"Document metadata extraction failed: {e}")
        
        # Archive metadata
        elif extension in ['.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz', '.rar', '.7z']:
            try:
                archive_meta = extract_archive_metadata(file_path)
            except Exception as e:
                log.debug(f"Archive metadata extraction failed: {e}")
    
    # Build raw data
    raw_data = {
        'file': asdict(file_meta),
        'image': asdict(image_meta) if image_meta else None,
        'video': asdict(video_meta) if video_meta else None,
        'audio': asdict(audio_meta) if audio_meta else None,
        'document': asdict(document_meta) if document_meta else None,
        'archive': asdict(archive_meta) if archive_meta else None,
    }
    
    return MetadataResult(
        file_metadata=file_meta,
        web_metadata=web_meta,
        image_metadata=image_meta,
        video_metadata=video_meta,
        audio_metadata=audio_meta,
        document_metadata=document_meta,
        archive_metadata=archive_meta,
        raw_data=raw_data
    )
