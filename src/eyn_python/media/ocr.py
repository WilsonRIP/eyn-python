from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


@dataclass
class OCRResult:
    text: str
    confidence: Optional[float] = None
    word_data: Optional[List[Dict]] = None


def _ensure_tesseract() -> None:
    if not TESSERACT_AVAILABLE:
        raise ImportError(
            "pytesseract and Pillow are required for OCR. "
            "Install with: pip install pytesseract pillow"
        )


def ocr_image(
    src: Path,
    lang: str = "eng",
    psm: Optional[int] = None,
    oem: Optional[int] = None,
    config: Optional[str] = None,
) -> str:
    """Extract text from an image using Tesseract OCR.
    
    Args:
        src: Path to image file
        lang: Language code (e.g., 'eng', 'fra', 'deu', 'spa')
        psm: Page segmentation mode (0-13)
        oem: OCR Engine mode (0-3)
        config: Additional Tesseract config options
    """
    _ensure_tesseract()
    
    if not src.exists():
        raise FileNotFoundError(f"Image file not found: {src}")
    
    img = Image.open(src)
    
    # Build config string
    config_parts = []
    if psm is not None:
        config_parts.append(f"--psm {psm}")
    if oem is not None:
        config_parts.append(f"--oem {oem}")
    if config:
        config_parts.append(config)
    
    final_config = " ".join(config_parts) if config_parts else ""
    
    try:
        text = pytesseract.image_to_string(
            img,
            lang=lang,
            config=final_config if final_config else None
        )
        return text.strip()
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract executable not found. Please install Tesseract OCR:\n"
            "- macOS: brew install tesseract\n"
            "- Ubuntu: apt-get install tesseract-ocr\n"
            "- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
        )


def ocr_image_detailed(
    src: Path,
    lang: str = "eng", 
    psm: Optional[int] = None,
    oem: Optional[int] = None,
    config: Optional[str] = None,
) -> OCRResult:
    """Extract text with detailed information (confidence, word positions)."""
    _ensure_tesseract()
    
    if not src.exists():
        raise FileNotFoundError(f"Image file not found: {src}")
    
    img = Image.open(src)
    
    # Build config string
    config_parts = []
    if psm is not None:
        config_parts.append(f"--psm {psm}")
    if oem is not None:
        config_parts.append(f"--oem {oem}")
    if config:
        config_parts.append(config)
    
    final_config = " ".join(config_parts) if config_parts else ""
    
    try:
        # Get basic text
        text = pytesseract.image_to_string(
            img,
            lang=lang,
            config=final_config if final_config else None
        ).strip()
        
        # Get detailed data
        data = pytesseract.image_to_data(
            img,
            lang=lang,
            config=final_config if final_config else None,
            output_type=pytesseract.Output.DICT
        )
        
        # Calculate average confidence
        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Build word data
        word_data = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 0 and data['text'][i].strip():
                word_data.append({
                    'text': data['text'][i],
                    'confidence': int(data['conf'][i]),
                    'left': data['left'][i],
                    'top': data['top'][i], 
                    'width': data['width'][i],
                    'height': data['height'][i],
                })
        
        return OCRResult(
            text=text,
            confidence=avg_confidence,
            word_data=word_data
        )
        
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract executable not found. Please install Tesseract OCR:\n"
            "- macOS: brew install tesseract\n" 
            "- Ubuntu: apt-get install tesseract-ocr\n"
            "- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
        )


def get_tesseract_languages() -> List[str]:
    """Get list of available languages for Tesseract."""
    _ensure_tesseract()
    
    try:
        return pytesseract.get_languages()
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError("Tesseract executable not found")


def preprocess_image_for_ocr(src: Path, out: Path) -> Path:
    """Preprocess an image to improve OCR accuracy."""
    try:
        from PIL import ImageEnhance, ImageFilter
    except ImportError:
        raise ImportError("Pillow is required for image preprocessing")
    
    img = Image.open(src)
    
    # Convert to grayscale
    if img.mode != 'L':
        img = img.convert('L')
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    
    # Apply slight blur to reduce noise
    img = img.filter(ImageFilter.MedianFilter(size=3))
    
    # Ensure output directory exists
    out.parent.mkdir(parents=True, exist_ok=True)
    
    # Save as high-quality PNG
    img.save(out, 'PNG', optimize=True)
    
    return out


__all__ = [
    "OCRResult",
    "ocr_image",
    "ocr_image_detailed", 
    "get_tesseract_languages",
    "preprocess_image_for_ocr",
]
