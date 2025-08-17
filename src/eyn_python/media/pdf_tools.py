from __future__ import annotations

import io
from pathlib import Path
from typing import List, Optional
try:
    import PyPDF2
    from PyPDF2 import PdfReader, PdfWriter
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


def _ensure_pypdf2() -> None:
    if not PYPDF2_AVAILABLE:
        raise ImportError("PyPDF2 is required for PDF operations. Install with: pip install PyPDF2")


def _ensure_pymupdf() -> None:
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF is required for advanced PDF operations. Install with: pip install PyMuPDF")


def pdf_merge(files: List[Path], out: Path) -> Path:
    """Merge multiple PDF files into one."""
    _ensure_pypdf2()
    
    writer = PdfWriter()
    
    for file_path in files:
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        reader = PdfReader(str(file_path))
        for page in reader.pages:
            writer.add_page(page)
    
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'wb') as output_file:
        writer.write(output_file)
    
    return out


def pdf_split(src: Path, out: Path) -> int:
    """Split a PDF into individual pages."""
    _ensure_pypdf2()
    
    if not src.exists():
        raise FileNotFoundError(f"PDF file not found: {src}")
    
    reader = PdfReader(str(src))
    num_pages = len(reader.pages)
    
    out.mkdir(parents=True, exist_ok=True)
    
    for page_num, page in enumerate(reader.pages, 1):
        writer = PdfWriter()
        writer.add_page(page)
        
        page_file = out / f"page_{page_num:03d}.pdf"
        with open(page_file, 'wb') as page_output:
            writer.write(page_output)
    
    return num_pages


def pdf_extract_text(src: Path) -> str:
    """Extract all text from a PDF."""
    if PYMUPDF_AVAILABLE:
        return _pdf_extract_text_pymupdf(src)
    elif PYPDF2_AVAILABLE:
        return _pdf_extract_text_pypdf2(src)
    else:
        raise ImportError("Either PyPDF2 or PyMuPDF is required for text extraction")


def _pdf_extract_text_pypdf2(src: Path) -> str:
    """Extract text using PyPDF2."""
    reader = PdfReader(str(src))
    text_parts = []
    
    for page in reader.pages:
        text_parts.append(page.extract_text())
    
    return "\n\n".join(text_parts)


def _pdf_extract_text_pymupdf(src: Path) -> str:
    """Extract text using PyMuPDF (better quality)."""
    doc = fitz.open(str(src))
    text_parts = []
    
    for page_num in range(doc.page_count):
        page = doc[page_num]
        text_parts.append(page.get_text())
    
    doc.close()
    return "\n\n".join(text_parts)


def pdf_extract_images(src: Path, out: Path) -> int:
    """Extract images from a PDF."""
    _ensure_pymupdf()
    
    if not src.exists():
        raise FileNotFoundError(f"PDF file not found: {src}")
    
    doc = fitz.open(str(src))
    out.mkdir(parents=True, exist_ok=True)
    
    image_count = 0
    
    for page_num in range(doc.page_count):
        page = doc[page_num]
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            
            if pix.n - pix.alpha < 4:  # GRAY or RGB
                img_filename = out / f"page_{page_num + 1:03d}_img_{img_index + 1:03d}.png"
                pix.save(str(img_filename))
                image_count += 1
            else:  # CMYK: convert to RGB first
                pix1 = fitz.Pixmap(fitz.csRGB, pix)
                img_filename = out / f"page_{page_num + 1:03d}_img_{img_index + 1:03d}.png"
                pix1.save(str(img_filename))
                pix1 = None
                image_count += 1
            
            pix = None
    
    doc.close()
    return image_count


def pdf_get_info(src: Path) -> dict:
    """Get PDF metadata and information."""
    if not src.exists():
        raise FileNotFoundError(f"PDF file not found: {src}")
    
    if PYMUPDF_AVAILABLE:
        doc = fitz.open(str(src))
        info = {
            "page_count": doc.page_count,
            "metadata": doc.metadata,
            "is_encrypted": doc.is_encrypted,
            "is_repaired": doc.is_repaired,
        }
        doc.close()
        return info
    else:
        _ensure_pypdf2()
        reader = PdfReader(str(src))
        return {
            "page_count": len(reader.pages),
            "metadata": dict(reader.metadata) if reader.metadata else {},
            "is_encrypted": reader.is_encrypted,
        }


__all__ = [
    "pdf_merge",
    "pdf_split", 
    "pdf_extract_text",
    "pdf_extract_images",
    "pdf_get_info",
]
