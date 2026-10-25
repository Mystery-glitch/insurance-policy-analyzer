"""
PDF Text Extraction Service
============================
Handles text extraction from insurance policy PDFs that may contain:
  - Born-digital (unscanned) pages  →  extracted via PyMuPDF
  - Scanned / image-based pages     →  OCR'd via ocrmypdf, then extracted
  - Hybrid documents (mix of both)  →  each page handled appropriately

Strategy:
  1. Open the PDF with PyMuPDF and inspect every page.
  2. If a page yields meaningful text (> threshold chars), treat it as digital.
  3. If a page has little/no text, flag the document as needing OCR.
  4. If any page needs OCR, run ocrmypdf on the *entire* file with
     `skip_text=True` so born-digital pages are left untouched.
  5. Re-open the (now fully searchable) PDF and extract all text with PyMuPDF.
"""

import logging
import tempfile
from pathlib import Path

import pymupdf  # PyMuPDF
import ocrmypdf

from app.core.config import OCR_DPI, OCR_LANGUAGE

logger = logging.getLogger(__name__)

# If a page has fewer characters than this, we consider it scanned / image-only.
_MIN_CHARS_FOR_DIGITAL_PAGE = 30


class PDFExtractionResult:
    """Container for extraction results and metadata."""

    def __init__(
        self,
        text: str,
        total_pages: int,
        digital_pages: int,
        scanned_pages: int,
        ocr_applied: bool,
    ):
        self.text = text
        self.total_pages = total_pages
        self.digital_pages = digital_pages
        self.scanned_pages = scanned_pages
        self.ocr_applied = ocr_applied

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "total_pages": self.total_pages,
            "digital_pages": self.digital_pages,
            "scanned_pages": self.scanned_pages,
            "ocr_applied": self.ocr_applied,
        }


def _classify_pages(pdf_path: str) -> tuple[int, int, int]:
    """
    Open the PDF and classify each page as digital or scanned.

    Returns:
        (total_pages, digital_page_count, scanned_page_count)
    """
    doc = pymupdf.open(pdf_path)
    digital = 0
    scanned = 0

    for page in doc:
        text = page.get_text("text").strip()
        if len(text) >= _MIN_CHARS_FOR_DIGITAL_PAGE:
            digital += 1
        else:
            scanned += 1

    total = len(doc)
    doc.close()
    return total, digital, scanned


def _run_ocr(input_path: str, output_path: str) -> None:
    """
    Run ocrmypdf on the input PDF.

    Uses `skip_text=True` so pages that already have a text layer
    are left untouched — only truly scanned pages get OCR'd.
    """
    logger.info("Running OCR on %s → %s", input_path, output_path)
    ocrmypdf.ocr(
        input_file=input_path,
        output_file=output_path,
        skip_text=True,
        deskew=True,
        optimize=1,
        language=OCR_LANGUAGE,
        progress_bar=False,
    )
    logger.info("OCR complete.")


def _extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a (presumably searchable) PDF using PyMuPDF.

    Returns the concatenated text of all pages, with page separators.
    """
    doc = pymupdf.open(pdf_path)
    pages_text: list[str] = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages_text.append(f"--- Page {page_num} ---\n{text}")

    doc.close()
    return "\n\n".join(pages_text)


def extract_text(pdf_path: str) -> PDFExtractionResult:
    """
    Main entry point — extracts text from any kind of PDF.

    Args:
        pdf_path: Absolute path to the uploaded PDF file.

    Returns:
        PDFExtractionResult with the extracted text and page-level metadata.
    """
    pdf_path_str = str(pdf_path)

    # ── Step 1: Classify pages ────────────────────────────────────────
    total_pages, digital_pages, scanned_pages = _classify_pages(pdf_path_str)
    logger.info(
        "PDF analysis — total: %d, digital: %d, scanned: %d",
        total_pages,
        digital_pages,
        scanned_pages,
    )

    ocr_applied = False

    # ── Step 2: OCR if necessary ──────────────────────────────────────
    if scanned_pages > 0:
        ocr_applied = True
        # Create a temp file for the OCR'd output so the original is untouched
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            ocr_output_path = tmp.name

        try:
            _run_ocr(pdf_path_str, ocr_output_path)
            extraction_source = ocr_output_path
        except ocrmypdf.exceptions.PriorOcrFoundError:
            # The PDF already has an OCR layer; just use the original
            logger.warning("Prior OCR layer detected; using original PDF.")
            extraction_source = pdf_path_str
            ocr_applied = False
        except Exception:
            logger.exception("OCR failed; falling back to raw extraction.")
            extraction_source = pdf_path_str
            ocr_applied = False
    else:
        extraction_source = pdf_path_str

    # ── Step 3: Extract text ──────────────────────────────────────────
    text = _extract_text_from_pdf(extraction_source)

    # Clean up the temp OCR file if we created one
    if ocr_applied and extraction_source != pdf_path_str:
        try:
            Path(extraction_source).unlink()
        except OSError:
            pass

    return PDFExtractionResult(
        text=text,
        total_pages=total_pages,
        digital_pages=digital_pages,
        scanned_pages=scanned_pages,
        ocr_applied=ocr_applied,
    )
