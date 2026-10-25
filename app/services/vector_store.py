"""
Vector Store Service
=====================
Manages ChromaDB collections for storing and retrieving policy text chunks.

Uses Gemini Embedding API to create dense vectors for each chunk,
then stores them in a persistent ChromaDB collection keyed by document_id.

Retrieval returns the top-k most relevant chunks for a given query.
"""

import logging
from pathlib import Path

import chromadb
from google import genai

from app.core.config import settings
from app.services.text_chunker import TextChunk

logger = logging.getLogger(__name__)

# ── ChromaDB setup ─────────────────────────────────────────────────────
_CHROMA_DIR = settings.BASE_DIR / "chroma_db"
_CHROMA_DIR.mkdir(parents=True, exist_ok=True)

_chroma_client = chromadb.PersistentClient(path=str(_CHROMA_DIR))

# Gemini embedding model from settings
_EMBEDDING_MODEL = settings.EMBEDDING_MODEL


def _get_genai_client() -> genai.Client:
    """Create a Gemini client for embeddings."""
    if not settings.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using Gemini Embedding API.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each a list of floats).
    """
    client = _get_genai_client()
    embeddings = []

    # Process in batches of 100 (API limit)
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.models.embed_content(
            model=_EMBEDDING_MODEL,
            contents=batch,
        )
        for embedding in response.embeddings:
            embeddings.append(embedding.values)

    return embeddings


def _collection_name(document_id: str) -> str:
    """Sanitize document_id into a valid ChromaDB collection name."""
    # ChromaDB collection names: 3-63 chars, alphanumeric + underscores/hyphens
    name = f"doc_{document_id}"
    return name[:63]


def index_document(document_id: str, chunks: list[TextChunk]) -> int:
    """
    Embed and store all chunks for a document in ChromaDB.

    Args:
        document_id: Unique identifier for this policy document.
        chunks: List of TextChunk objects to index.

    Returns:
        Number of chunks indexed.
    """
    if not chunks:
        logger.warning("No chunks to index for document %s.", document_id)
        return 0

    col_name = _collection_name(document_id)

    # Delete existing collection if re-indexing
    try:
        _chroma_client.delete_collection(name=col_name)
    except Exception:
        pass  # Collection doesn't exist yet

    collection = _chroma_client.create_collection(
        name=col_name,
        metadata={"document_id": document_id},
    )

    # Prepare data
    texts = [chunk.text for chunk in chunks]
    ids = [f"{document_id}_chunk_{chunk.chunk_index}" for chunk in chunks]
    metadatas = [
        {
            "chunk_index": chunk.chunk_index,
            "page_hint": chunk.page_hint,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
        }
        for chunk in chunks
    ]

    # Generate embeddings
    logger.info("Generating embeddings for %d chunks...", len(texts))
    embeddings = _generate_embeddings(texts)

    # Store in ChromaDB
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info("Indexed %d chunks for document %s.", len(chunks), document_id)
    return len(chunks)


def retrieve_relevant_chunks(
    document_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve the most relevant chunks for a query from a stored document.

    Args:
        document_id: The document to search within.
        query: The user's question.
        top_k: Number of chunks to retrieve.

    Returns:
        List of dicts with 'text', 'page_hint', 'chunk_index', and 'distance'.
    """
    col_name = _collection_name(document_id)

    try:
        collection = _chroma_client.get_collection(name=col_name)
    except Exception:
        raise ValueError(
            f"Document '{document_id}' not found. "
            "Please upload and analyze the document first using /api/v1/analyze."
        )

    # Embed the query
    query_embedding = _generate_embeddings([query])[0]

    # Query ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    # Format results
    retrieved = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            retrieved.append({
                "text": doc,
                "page_hint": meta.get("page_hint", "Unknown"),
                "chunk_index": meta.get("chunk_index", -1),
                "distance": dist,
            })

    logger.info(
        "Retrieved %d chunks for query on document %s.",
        len(retrieved), document_id,
    )
    return retrieved


def document_exists(document_id: str) -> bool:
    """Check if a document has been indexed."""
    col_name = _collection_name(document_id)
    try:
        collection = _chroma_client.get_collection(name=col_name)
        return collection.count() > 0
    except Exception:
        return False
