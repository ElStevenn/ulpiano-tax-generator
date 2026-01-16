"""
PDF utility functions for processing PDF documents.
"""

import io
from pathlib import Path
import fitz  # pymupdf


def pdf_to_images(pdf_input: bytes | str | Path, dpi: int = 150) -> list[bytes]:
    """
    Convert a PDF to a list of images (one per page).
    
    Args:
        pdf_input: PDF as bytes, file path string, or Path object
        dpi: Resolution for rendering (default 150 for good balance of quality/size)
        
    Returns:
        List of PNG image bytes, one per page
    """
    # Open PDF from bytes or file path
    if isinstance(pdf_input, bytes):
        doc = fitz.open(stream=pdf_input, filetype="pdf")
    else:
        doc = fitz.open(str(pdf_input))
    
    images = []
    
    # Calculate zoom factor from DPI (default PDF is 72 DPI)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Render page to pixmap (image)
        pixmap = page.get_pixmap(matrix=matrix)
        
        # Convert to PNG bytes
        png_bytes = pixmap.tobytes("png")
        images.append(png_bytes)
    
    doc.close()
    
    return images


def pdf_page_count(pdf_input: bytes | str | Path) -> int:
    """
    Get the number of pages in a PDF.
    
    Args:
        pdf_input: PDF as bytes, file path string, or Path object
        
    Returns:
        Number of pages in the PDF
    """
    if isinstance(pdf_input, bytes):
        doc = fitz.open(stream=pdf_input, filetype="pdf")
    else:
        doc = fitz.open(str(pdf_input))
    
    count = len(doc)
    doc.close()
    
    return count


def extract_text_from_pdf(pdf_input: bytes | str | Path) -> str:
    """
    Extract all text from a PDF (for basic text extraction).
    
    Args:
        pdf_input: PDF as bytes, file path string, or Path object
        
    Returns:
        Concatenated text from all pages
    """
    if isinstance(pdf_input, bytes):
        doc = fitz.open(stream=pdf_input, filetype="pdf")
    else:
        doc = fitz.open(str(pdf_input))
    
    text_parts = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text_parts.append(page.get_text())
    
    doc.close()
    
    return "\n\n".join(text_parts)


def is_valid_pdf(data: bytes) -> bool:
    """
    Check if the given bytes represent a valid PDF.
    
    Args:
        data: Bytes to check
        
    Returns:
        True if valid PDF, False otherwise
    """
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        is_valid = len(doc) > 0
        doc.close()
        return is_valid
    except Exception:
        return False
