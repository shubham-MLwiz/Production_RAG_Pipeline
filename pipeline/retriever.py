"""
pipeline/retriever.py

Retrieves the most relevant chunks for a question from Qdrant.

Process:
  1. Embed the question text with the same Ollama model used for the chunks.
  2. Query Qdrant for the top-k closest vectors (by cosine similarity).
  3. Return each result's payload (text, page, source) plus its similarity score.

Output: a list of dicts, one per retrieved chunk:
    [
        {
            "chunk_index": 42,
            "score":       0.87,
            "text":        "...",
            "page":        9,
            "source":      "test_file",
        },
        ...
    ]
"""

import os

import httpx
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

QDRANT_HOST       = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT       = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "rag_chunks")

# Default number of chunks to return if the caller does not specify.
DEFAULT_TOP_K = 5


def _embed_query(question: str) -> list[float]:
    """
    Embed a single question string with Ollama.

    Uses the same model that was used to embed the chunks, so the vectors
    live in the same space and cosine similarity is meaningful.
    """
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/embed",
        json={"model": OLLAMA_EMBED_MODEL, "input": [question]},
        timeout=60,
    )
    response.raise_for_status()
    # /api/embed returns {"embeddings": [[...], ...]} — we sent one string
    # so we get back one vector.
    return response.json()["embeddings"][0]


def retrieve(question: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    Find the top-k most relevant chunks for a question.

    Args:
        question: The user's question text.
        top_k:    How many chunks to return (default 5).

    Returns:
        A list of dicts, each containing:
            - chunk_index  (int)   — position in the original chunk list
            - score        (float) — cosine similarity (0–1, higher = more relevant)
            - text         (str)   — the chunk text
            - page         (int)   — source page number
            - source       (str)   — stem of the PDF filename
    """
    query_vector = _embed_query(question)

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # with_payload=True means Qdrant returns the stored metadata (text, page, source)
    # alongside each matching vector.
    results = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    ).points

    return [
        {
            "chunk_index": hit.id,
            "score":       round(hit.score, 4),
            "text":        hit.payload.get("text", ""),
            "page":        hit.payload.get("page"),
            "source":      hit.payload.get("source", ""),
        }
        for hit in results
    ]
