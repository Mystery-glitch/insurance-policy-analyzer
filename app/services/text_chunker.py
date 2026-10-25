"""
Text Chunking Service
======================
Splits extracted policy text into overlapping chunks suitable for
embedding and retrieval in the RAG pipeline.

Strategy:
  1. Try to split on section-level boundaries (headings, numbered sections)
  2. Within each section, split on paragraph boundaries
  3. If a chunk is still too large, split on sentence boundaries
  4. Apply overlap so that context isn't lost between chunks
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Defaults ───────────────────────────────────────────────────────────
DEFAULT_CHUNK_SIZE = 1000       # characters per chunk (target)
DEFAULT_CHUNK_OVERLAP = 200     # overlap between consecutive chunks


@dataclass
class TextChunk:
    """A single chunk of policy text with metadata."""
    text: str
    chunk_index: int
    page_hint: str              # best-effort page reference (e.g. "Page 3")
    start_char: int             # position in the original text
    end_char: int


def _detect_page_hint(text: str, position: int, full_text: str) -> str:
    """
    Look backward from `position` in `full_text` for the nearest
    '--- Page N ---' marker and return 'Page N'.
    """
    prefix = full_text[:position]
    matches = list(re.finditer(r"--- Page (\d+) ---", prefix))
    if matches:
        return f"Page {matches[-1].group(1)}"
    return "Page 1"


def _split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[tuple[int, int]]:
    """
    Split text into (start, end) character ranges with overlap.

    Tries to break on paragraph boundaries (\n\n) first,
    then sentence boundaries (. or \n), then hard-cuts.
    """
    if len(text) <= chunk_size:
        return [(0, len(text))]

    ranges: list[tuple[int, int]] = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            ranges.append((start, len(text)))
            break

        # Try to find a paragraph break near the end
        search_window = text[end - 100 : end + 100]
        para_break = search_window.rfind("\n\n")
        if para_break != -1:
            end = (end - 100) + para_break + 2  # +2 to include the \n\n
        else:
            # Try sentence boundary
            sentence_break = search_window.rfind(". ")
            if sentence_break != -1:
                end = (end - 100) + sentence_break + 2
            else:
                # Try any newline
                newline_break = search_window.rfind("\n")
                if newline_break != -1:
                    end = (end - 100) + newline_break + 1

        ranges.append((start, end))

        # Move start forward, minus the overlap
        start = end - chunk_overlap
        if start < 0:
            start = 0

    return ranges


def chunk_text(
    full_text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[TextChunk]:
    """
    Split extracted policy text into overlapping chunks.

    Args:
        full_text: The complete extracted text (with page markers).
        chunk_size: Target number of characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.

    Returns:
        A list of TextChunk objects ready for embedding.
    """
    if not full_text or not full_text.strip():
        return []

    ranges = _split_text(full_text, chunk_size, chunk_overlap)

    chunks: list[TextChunk] = []
    for idx, (start, end) in enumerate(ranges):
        chunk_text_content = full_text[start:end].strip()
        if not chunk_text_content:
            continue

        page_hint = _detect_page_hint(chunk_text_content, start, full_text)

        chunks.append(TextChunk(
            text=chunk_text_content,
            chunk_index=idx,
            page_hint=page_hint,
            start_char=start,
            end_char=end,
        ))

    logger.info(
        "Split text (%d chars) into %d chunks (size=%d, overlap=%d).",
        len(full_text), len(chunks), chunk_size, chunk_overlap,
    )
    return chunks
