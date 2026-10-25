"""
Upload route — accepts a PDF file, extracts text, and returns results.
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB, UPLOAD_DIR
from app.services.pdf_extractor import extract_text

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/upload-pdf",
    summary="Upload an insurance policy PDF",
    description=(
        "Accepts a PDF file (scanned, unscanned, or hybrid). "
        "Extracts all text and returns it along with page-level metadata."
    ),
)
async def upload_pdf(file: UploadFile = File(..., description="Insurance policy PDF file")):
    """
    Upload endpoint workflow:
      1. Validate content type (must be application/pdf).
      2. Read the file and validate size.
      3. Persist to disk with a unique filename.
      4. Run the extraction pipeline.
      5. Clean up and return results.
    """
    # ── Validate content type ─────────────────────────────────────────
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: '{file.content_type}'. Only PDF files are accepted.",
        )

    # ── Read & validate size ──────────────────────────────────────────
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB} MB.",
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # ── Persist to disk ───────────────────────────────────────────────
    unique_filename = f"{uuid.uuid4().hex}.pdf"
    saved_path = UPLOAD_DIR / unique_filename

    try:
        saved_path.write_bytes(contents)
        logger.info("Saved uploaded file to %s (%d bytes)", saved_path, len(contents))
    except OSError as exc:
        logger.exception("Failed to save uploaded file.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the uploaded file.",
        ) from exc

    # ── Extract text ──────────────────────────────────────────────────
    try:
        result = extract_text(str(saved_path))
    except Exception as exc:
        logger.exception("Text extraction failed for %s", saved_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text extraction failed: {str(exc)}",
        ) from exc
    finally:
        # Clean up the uploaded file — we only needed it for extraction
        try:
            saved_path.unlink()
        except OSError:
            pass

    # ── Return results ────────────────────────────────────────────────
    extraction_data = result.to_dict()

    if not extraction_data["text"].strip():
        return {
            "status": "warning",
            "message": "The PDF was processed but no readable text could be extracted. "
                       "The document may consist entirely of images that could not be OCR'd.",
            "data": extraction_data,
        }

    return {
        "status": "success",
        "message": "Text extracted successfully.",
        "data": extraction_data,
    }
