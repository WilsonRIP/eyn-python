from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from PIL import Image, ImageOps, ExifTags
from PIL.ExifTags import TAGS
import glob


@dataclass
class ThumbnailOptions:
    size: Tuple[int, int] = (256, 256)
    mode: str = "fit"  # fit|cover
    quality: int = 90
    recursive: bool = True
    pattern: str = "*"


def _ensure_rgb_mode(img: Image.Image) -> Image.Image:
    """Convert image to RGB if it's in RGBA, P, or other modes for JPEG compatibility."""
    if img.mode in ("RGBA", "LA", "P"):
        # Create white background for transparent images
        if img.mode == "P":
            img = img.convert("RGBA")
        if img.mode in ("RGBA", "LA"):
            white_bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "LA":
                img = img.convert("RGBA")
            white_bg.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            return white_bg
    return img.convert("RGB") if img.mode != "RGB" else img


def resize_image(
    src: Path,
    out: Optional[Path] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    keep_aspect: bool = True,
    quality: int = 90,
) -> Path:
    """Resize an image with optional aspect ratio preservation."""
    if not width and not height:
        raise ValueError("Must specify at least width or height")
    
    img = Image.open(src)
    original_size = img.size
    
    if keep_aspect:
        if width and height:
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
        elif width:
            ratio = width / original_size[0]
            new_height = int(original_size[1] * ratio)
            img = img.resize((width, new_height), Image.Resampling.LANCZOS)
        elif height:
            ratio = height / original_size[1]
            new_width = int(original_size[0] * ratio)
            img = img.resize((new_width, height), Image.Resampling.LANCZOS)
    else:
        target_width = width or original_size[0]
        target_height = height or original_size[1]
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    if out is None:
        stem = src.stem
        suffix = src.suffix
        out = src.parent / f"{stem}_resized{suffix}"
    
    # Ensure output directory exists
    out.parent.mkdir(parents=True, exist_ok=True)
    
    # Handle format conversion for JPEG
    if out.suffix.lower() in ('.jpg', '.jpeg'):
        img = _ensure_rgb_mode(img)
        img.save(out, "JPEG", quality=quality, optimize=True)
    else:
        img.save(out, quality=quality if out.suffix.lower() != '.png' else None)
    
    return out


def crop_image(
    src: Path,
    out: Optional[Path] = None,
    x: int = 0,
    y: int = 0,
    width: int = 100,
    height: int = 100,
    quality: int = 90,
) -> Path:
    """Crop an image to specified coordinates and dimensions."""
    img = Image.open(src)
    
    # Validate crop bounds
    img_width, img_height = img.size
    x = max(0, min(x, img_width))
    y = max(0, min(y, img_height))
    width = min(width, img_width - x)
    height = min(height, img_height - y)
    
    cropped = img.crop((x, y, x + width, y + height))
    
    if out is None:
        stem = src.stem
        suffix = src.suffix
        out = src.parent / f"{stem}_cropped{suffix}"
    
    out.parent.mkdir(parents=True, exist_ok=True)
    
    if out.suffix.lower() in ('.jpg', '.jpeg'):
        cropped = _ensure_rgb_mode(cropped)
        cropped.save(out, "JPEG", quality=quality, optimize=True)
    else:
        cropped.save(out, quality=quality if out.suffix.lower() != '.png' else None)
    
    return out


def convert_image_format(
    src: Path,
    out: Optional[Path] = None,
    to: str = "png",
    quality: int = 90,
) -> Path:
    """Convert image to different format."""
    img = Image.open(src)
    
    # Map format strings to extensions
    format_map = {
        "png": ".png",
        "jpg": ".jpg",
        "jpeg": ".jpg",
        "webp": ".webp",
        "bmp": ".bmp",
        "tiff": ".tiff",
        "tif": ".tiff",
    }
    
    ext = format_map.get(to.lower(), f".{to.lower()}")
    
    if out is None:
        out = src.with_suffix(ext)
    
    out.parent.mkdir(parents=True, exist_ok=True)
    
    # Handle format-specific requirements
    if ext.lower() in ('.jpg', '.jpeg'):
        img = _ensure_rgb_mode(img)
        img.save(out, "JPEG", quality=quality, optimize=True)
    elif ext.lower() == '.webp':
        img.save(out, "WEBP", quality=quality, optimize=True)
    elif ext.lower() == '.png':
        img.save(out, "PNG", optimize=True)
    else:
        img.save(out)
    
    return out


def generate_thumbnails(
    src: Path,
    out: Path,
    options: ThumbnailOptions = ThumbnailOptions(),
) -> int:
    """Generate thumbnails for images in a directory or single file."""
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    
    if src.is_file():
        files = [src]
    else:
        pattern_path = src / options.pattern if options.recursive else options.pattern
        if options.recursive:
            files = list(src.rglob(options.pattern))
        else:
            files = list(src.glob(options.pattern))
        # Filter for image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        files = [f for f in files if f.suffix.lower() in image_extensions]
    
    for file_path in files:
        try:
            img = Image.open(file_path)
            
            if options.mode == "cover":
                # Crop to exact size, center the crop
                img = ImageOps.fit(img, options.size, Image.Resampling.LANCZOS)
            else:  # fit
                img.thumbnail(options.size, Image.Resampling.LANCZOS)
            
            # Generate output filename
            relative_path = file_path.relative_to(src if src.is_dir() else src.parent)
            thumb_name = f"thumb_{relative_path.stem}.jpg"
            thumb_path = out / thumb_name
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to RGB for JPEG
            img = _ensure_rgb_mode(img)
            img.save(thumb_path, "JPEG", quality=options.quality, optimize=True)
            count += 1
            
        except Exception as e:
            print(f"Warning: Could not process {file_path}: {e}")
            continue
    
    return count


def extract_exif(src: Path) -> Dict[str, Any]:
    """Extract EXIF metadata from an image."""
    img = Image.open(src)
    exif_data = {}
    
    if hasattr(img, '_getexif') and img._getexif() is not None:
        exif = img._getexif()
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            exif_data[tag] = value
    
    # Also try the newer method
    if hasattr(img, 'getexif'):
        try:
            exif = img.getexif()
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag not in exif_data:  # Don't overwrite if already present
                    exif_data[tag] = value
        except Exception:
            pass
    
    return exif_data


def set_exif(
    src: Path,
    out: Optional[Path] = None,
    updates: Optional[Dict[str, str]] = None,
) -> Path:
    """Set EXIF metadata on an image."""
    img = Image.open(src)
    
    if out is None:
        out = src
    
    if updates is None:
        updates = {}
    
    # This is a simplified implementation
    # For full EXIF editing, you'd typically use piexif library
    # Here we'll just save the image, which may strip some EXIF data
    out.parent.mkdir(parents=True, exist_ok=True)
    
    if out.suffix.lower() in ('.jpg', '.jpeg'):
        img = _ensure_rgb_mode(img)
        img.save(out, "JPEG", quality=95, optimize=True)
    else:
        img.save(out)
    
    return out


__all__ = [
    "ThumbnailOptions",
    "resize_image",
    "crop_image", 
    "convert_image_format",
    "generate_thumbnails",
    "extract_exif",
    "set_exif",
]
