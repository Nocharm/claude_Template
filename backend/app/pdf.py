"""Render PDF pages to JPEG for Claude vision input."""

import io
from pathlib import Path

import pypdfium2 as pdfium

from app.extraction import PageImage

# Long edge in px. Claude downsamples beyond ~1568px, so higher only costs upload size.
OCR_EDGE = 1568
# Enough to read a "DAY n" heading; keeps 495-page classification cheap.
CLASSIFY_EDGE = 640
JPEG_QUALITY = 85


def count_pages(pdf_path: Path) -> int:
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        return len(pdf)
    finally:
        pdf.close()


def render_pages(pdf_path: Path, pages: list[int], max_edge: int) -> list[PageImage]:
    """Render 1-based page numbers so the longer side is max_edge px."""
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        images = []
        for page_no in pages:
            page = pdf[page_no - 1]
            width, height = page.get_size()
            bitmap = page.render(scale=max_edge / max(width, height))
            buffer = io.BytesIO()
            bitmap.to_pil().convert("RGB").save(buffer, format="JPEG", quality=JPEG_QUALITY)
            images.append(PageImage(page=page_no, jpeg=buffer.getvalue()))
        return images
    finally:
        pdf.close()
