"""
Ask route — answers user questions about a previously analyzed policy.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.qa_service import ask_question
from app.services.vector_store import document_exists

logger = logging.getLogger(__name__)

router = APIRouter()


class AskRequest(BaseModel):
    """Request body for the Q&A endpoint."""
    document_id: str = Field(
        ...,
        description="The document ID returned by the /analyze endpoint.",
        examples=["abc123def456"],
    )
    question: str = Field(
        ...,
        description="Your question about the insurance policy, in plain English.",
        examples=["Am I covered for hospitalization abroad?"],
    )


@router.post(
    "/ask",
    summary="Ask a question about an analyzed policy",
    description=(
        "Submit a natural-language question about a previously analyzed insurance "
        "policy. The system retrieves relevant sections from the policy and uses "
        "AI to provide a grounded, cited answer."
    ),
)
async def ask(request: AskRequest):
    """
    Q&A endpoint workflow:
      1. Validate that the document exists in the vector store.
      2. Retrieve relevant chunks via semantic search.
      3. Send question + context to Gemini.
      4. Return the answer with source citations.
    """
    # ── Check document exists ─────────────────────────────────────────
    if not document_exists(request.document_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{request.document_id}' not found. "
                   "Please upload and analyze an insurance policy PDF first using the analyzer above.",
        )

    # ── Get answer ────────────────────────────────────────────────────
    try:
        result = ask_question(
            document_id=request.document_id,
            question=request.question,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Q&A failed for document %s", request.document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(exc)}",
        ) from exc

    return {
        "status": "success",
        "data": {
            "document_id": request.document_id,
            "question": request.question,
            **result,
        },
    }
