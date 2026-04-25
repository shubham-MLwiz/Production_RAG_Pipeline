"""
pipeline/embedder.py

Generates one embedding vector per chunk using a locally running Ollama model.

Reads:  data/chunks/<stem>.json
Writes: data/embeddings/<stem>.json

Output structure (one item per chunk):
    [
        {
            "chunk_index": 0,
            "page":        1,
            "text":        "...",
            "embedding":   [0.021, -0.134, ...],   # vector length depends on the model
        },
        ...
    ]

Ollama's /api/embed endpoint accepts a list of strings in a single request,
so we process chunks in batches to avoid making thousands of individual HTTP calls.
"""

import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

# Read configuration from .env — fall back to sensible local defaults.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

# How many chunks to send to Ollama in a single HTTP request.
# Larger batches are faster but use more memory.
BATCH_SIZE = 32

CHUNKS_DIR = Path("data/chunks")
EMBEDDINGS_DIR = Path("data/embeddings")
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Call the Ollama /api/embed endpoint with a list of strings.

    Returns a list of embedding vectors, one per input string.
    Raises httpx.HTTPStatusError if Ollama returns a non-200 response.
    """
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/embed",
        json={"model": OLLAMA_EMBED_MODEL, "input": texts},
        # Generous timeout: a large batch may take several seconds on CPU.
        timeout=120,
    )
    response.raise_for_status()
    # Ollama returns {"embeddings": [[...], [...], ...]}
    return response.json()["embeddings"]


def embed_chunks(stem: str) -> list[dict]:
    """
    Load data/chunks/<stem>.json, generate an embedding for every chunk,
    and save the enriched list to data/embeddings/<stem>.json.

    Args:
        stem: The PDF filename without extension, e.g. "test_file".

    Returns:
        The enriched chunk list (each dict now includes an "embedding" key).

    Side effect:
        Writes data/embeddings/<stem>.json.
    """
    chunks_path = CHUNKS_DIR / (stem + ".json")

    if not chunks_path.exists():
        raise FileNotFoundError(
            f"Chunks file not found: {chunks_path}. Run /chunk first."
        )

    chunks: list[dict] = json.loads(chunks_path.read_text())

    enriched: list[dict] = []

    # Process in batches so we make fewer HTTP round-trips.
    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]
        texts = [chunk["text"] for chunk in batch]

        vectors = _embed_batch(texts)

        for chunk, vector in zip(batch, vectors):
            enriched.append({**chunk, "embedding": vector})

        print(
            f"  Embedded chunks {batch_start + 1}–{batch_start + len(batch)}"
            f" of {len(chunks)}"
        )

    # Save to disk for inspection and for the indexing step.
    output_path = EMBEDDINGS_DIR / (stem + ".json")
    output_path.write_text(json.dumps(enriched, indent=2, ensure_ascii=False))

    return enriched
