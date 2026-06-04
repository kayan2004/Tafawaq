"""pdfplumber text-only extraction from PDF bytes."""
import io

import pdfplumber


def extract_pages(pdf_bytes: bytes) -> dict[int, str]:
    """Extract text from each page of a PDF.

    Returns a dict mapping 1-indexed page number to page text.
    Pages with no extractable text (image-only) are omitted.
    """
    pages: dict[int, str] = {}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                pages[i] = text
    return pages
