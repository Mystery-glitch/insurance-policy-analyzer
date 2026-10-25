"""
Q&A Service
=============
Answers user questions about a specific insurance policy by:
  1. Retrieving the most relevant text chunks from the vector store
  2. Sending them as context to Gemini along with the question
  3. Returning a grounded answer with source citations

Every answer is tied to the actual policy text — no hallucination.
"""

import json
import logging
import re

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.vector_store import retrieve_relevant_chunks

logger = logging.getLogger(__name__)


QA_PROMPT = """You are an expert insurance advisor helping a policyholder understand their insurance policy. Answer the question based ONLY on the provided policy excerpts.

RULES:
1. Answer in plain, simple English — no jargon.
2. Be specific — cite actual numbers, limits, dates, and conditions from the policy.
3. If the answer is clearly stated in the excerpts, provide it confidently.
4. If the excerpts don't contain enough information to answer, say so honestly: "Based on the available policy text, I couldn't find specific information about this. You may want to check with your insurance provider."
5. Always reference which part of the policy your answer comes from using the page hints provided.
6. Structure your answer clearly with bullet points where helpful.

Return your response as a JSON object with these fields:
- "answer": Your plain-English answer to the question.
- "confidence": "high" | "medium" | "low" — how confident you are based on the available context.
- "sources": An array of objects, each with "page" (the page reference) and "excerpt" (a brief quote from the relevant text, max 100 chars).
- "follow_up_questions": An array of 2-3 related questions the user might also want to ask.

Return ONLY valid JSON, no markdown fences, no extra text.

---

POLICY EXCERPTS:
{context}

---

QUESTION: {question}
"""


def _get_gemini_client() -> genai.Client:
    """Create a Gemini client."""
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _parse_response(response_text: str) -> dict:
    """
    Parse Gemini response, supporting structured JSON, markdown-wrapped JSON,
    and graceful fallback to plain text if the model outputs unstructured prose.
    """
    if not response_text or not response_text.strip():
        return {
            "answer": "I received an empty response. Please ask your question again.",
            "confidence": "low",
            "sources": [],
            "follow_up_questions": [],
        }

    text = response_text.strip()

    # 1. Try direct JSON parsing
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 2. Try extracting from markdown code block ```json ... ```
    code_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if code_match:
        try:
            data = json.loads(code_match.group(1))
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # 3. Try finding any outer JSON object {...}
    obj_match = re.search(r"(\{[\s\S]*\})", text)
    if obj_match:
        try:
            data = json.loads(obj_match.group(1))
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # 4. Fallback: return raw text as the answer so user is never blocked!
    return {
        "answer": text,
        "confidence": "medium",
        "sources": [],
        "follow_up_questions": [],
    }


def _build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string for the prompt."""
    context_parts = []
    for i, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"[Excerpt {i} — {chunk['page_hint']}]\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(context_parts)


def ask_question(document_id: str, question: str, top_k: int = 5) -> dict:
    """
    Answer a user question about a specific policy document.

    Args:
        document_id: The document to query against.
        question: The user's question in natural language.
        top_k: Number of relevant chunks to retrieve.

    Returns:
        A dict with 'answer', 'confidence', 'sources', and 'follow_up_questions'.
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    # ── Retrieve relevant chunks ──────────────────────────────────────
    chunks = retrieve_relevant_chunks(document_id, question, top_k=top_k)

    if not chunks:
        return {
            "answer": "No relevant information was found in the policy document for your question. "
                      "The document may not have been indexed properly.",
            "confidence": "low",
            "sources": [],
            "follow_up_questions": [],
        }

    # ── Build prompt with context ─────────────────────────────────────
    context = _build_context(chunks)
    prompt = QA_PROMPT.format(context=context, question=question)

    # ── Call Gemini with JSON mode ─────────────────────────────────────
    logger.info(
        "Answering question for document %s: '%s' (using %d chunks)",
        document_id, question[:80], len(chunks),
    )
    client = _get_gemini_client()
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        logger.warning("GenerateContent with application/json failed (%s), retrying without mime_type...", exc)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )

    raw_text = response.text or ""
    logger.info("Q&A response received (%d chars).", len(raw_text))

    # ── Parse response ────────────────────────────────────────────────
    result = _parse_response(raw_text)

    # ── Validate and fill defaults ────────────────────────────────────
    result.setdefault("answer", "Unable to generate an answer.")
    result.setdefault("confidence", "medium")
    result.setdefault("sources", [])
    result.setdefault("follow_up_questions", [])

    return result
