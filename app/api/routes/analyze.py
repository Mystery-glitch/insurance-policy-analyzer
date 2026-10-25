"""
Analyze route — uploads a PDF, extracts text, returns AI analysis,
and indexes the document for Q&A.
"""

import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB, UPLOAD_DIR
from app.services.pdf_extractor import extract_text
from app.services.policy_analyzer import analyze_policy
from app.services.text_chunker import chunk_text
from app.services.vector_store import index_document

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    summary="Upload and analyze an insurance policy",
    description=(
        "Accepts a PDF file (scanned, unscanned, or hybrid). "
        "Extracts text and uses AI to produce a plain-English analysis "
        "including summary, coverages, exclusions, risk alerts, and more."
    ),
)
async def analyze_pdf(file: UploadFile = File(..., description="Insurance policy PDF file")):
    """
    Full pipeline: upload → extract → analyze → index for Q&A.

    Returns structured AI analysis and a document_id for follow-up questions.
    """
    # Generate a unique document ID for this policy
    document_id = uuid.uuid4().hex[:12]
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
        extraction_result = extract_text(str(saved_path))
    except Exception as exc:
        logger.exception("Text extraction failed for %s", saved_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text extraction failed: {str(exc)}",
        ) from exc
    finally:
        # Clean up the uploaded file
        try:
            saved_path.unlink()
        except OSError:
            pass

    extracted_text = extraction_result.text

    if not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text could be extracted from the PDF. "
                   "The document may consist entirely of images that could not be OCR'd.",
        )

    # ── AI analysis ───────────────────────────────────────────────────
    try:
        analysis = analyze_policy(extracted_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("AI analysis failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analysis failed: {str(exc)}",
        ) from exc

    # ── Index for Q&A ─────────────────────────────────────────────────
    try:
        chunks = chunk_text(extracted_text)
        num_chunks = index_document(document_id, chunks)
        logger.info("Indexed %d chunks for document %s.", num_chunks, document_id)
    except Exception as exc:
        # Indexing failure is non-fatal — analysis still returned
        logger.exception("Document indexing failed for %s", document_id)
        num_chunks = 0

    # ── Return results ────────────────────────────────────────────────
    return {
        "status": "success",
        "message": "Policy analyzed successfully.",
        "data": {
            "document_id": document_id,
            "extraction_metadata": {
                "total_pages": extraction_result.total_pages,
                "digital_pages": extraction_result.digital_pages,
                "scanned_pages": extraction_result.scanned_pages,
                "ocr_applied": extraction_result.ocr_applied,
            },
            "analysis": analysis,
            "qa_ready": num_chunks > 0,
            "indexed_chunks": num_chunks,
        },
    }
