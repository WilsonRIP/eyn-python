from __future__ import annotations

from .ffprobe import ffprobe_json
from .audio import AudioExtractOptions, extract_audio
from .trim import trim_media
from .image import (
    ThumbnailOptions,
    resize_image,
    crop_image,
    convert_image_format,
    generate_thumbnails,
    extract_exif,
    set_exif,
)
from .pdf_tools import (
    pdf_merge,
    pdf_split,
    pdf_extract_text,
    pdf_extract_images,
    pdf_get_info,
)
from .ocr import (
    OCRResult,
    ocr_image,
    ocr_image_detailed,
    get_tesseract_languages,
    preprocess_image_for_ocr,
)

__all__ = [
    "ffprobe_json",
    "AudioExtractOptions",
    "extract_audio",
    "trim_media",
    # Image processing
    "ThumbnailOptions",
    "resize_image",
    "crop_image",
    "convert_image_format",
    "generate_thumbnails",
    "extract_exif",
    "set_exif",
    # PDF tools
    "pdf_merge",
    "pdf_split",
    "pdf_extract_text",
    "pdf_extract_images",
    "pdf_get_info",
    # OCR
    "OCRResult",
    "ocr_image",
    "ocr_image_detailed",
    "get_tesseract_languages",
    "preprocess_image_for_ocr",
]


