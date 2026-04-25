"""
pipeline/indexer.py

Loads chunk embeddings from disk and upserts them into a Qdrant collection.

Reads:  data/embeddings/<stem>.json
Writes: Qdrant collection (configured via .env)

Each chunk becomes one Qdrant point:
  - id      = chunk_index  (integer, unique per chunk)
  - vector  = the 1024-dim float list from the embeddings file
  - payload = {"text": "...", "page": N, "source": "<stem>"}

The payload is what Qdrant returns alongside each search result — it is how
we will display citations (page number + source file) in Step 11.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

load_dotenv()

QDRANT_HOST       = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT       = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "rag_chunks")

EMBEDDINGS_DIR = Path("data/embeddings")

# Batch size for Qdrant upserts — keeps each HTTP payload small.
UPSERT_BATCH_SIZE = 100


def _get_client() -> QdrantClient:
    """Return a connected Qdrant client."""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def _ensure_collection(client: QdrantClient, vector_size: int) -> None:
    """
    Create the Qdrant collection if it does not already exist.

    If it exists with a different vector size, raise an error — the caller
    should delete and recreate it rather than silently producing bad results.
    """
    existing = [c.name for c in client.get_collections().collections]

    if QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        print(f"Created collection '{QDRANT_COLLECTION}' (vector_size={vector_size})")
    else:
        # Verify the existing collection has the right vector size.
        info = client.get_collection(QDRANT_COLLECTION)
        existing_size = info.config.params.vectors.size
        if existing_size != vector_size:
            raise ValueError(
                f"Collection '{QDRANT_COLLECTION}' exists with vector_size="
                f"{existing_size}, but the embeddings have size {vector_size}. "
                f"Delete the collection first: "
                f"DELETE http://localhost:{QDRANT_PORT}/collections/{QDRANT_COLLECTION}"
            )
        print(f"Collection '{QDRANT_COLLECTION}' already exists — reusing it.")


def index_embeddings(stem: str) -> int:
    """
    Upsert all chunks from data/embeddings/<stem>.json into Qdrant.

    Args:
        stem: The PDF filename without extension, e.g. "test_file".

    Returns:
        The total number of points upserted.

    Behaviour:
        - Creates the collection if it does not exist.
        - Upserts in batches of UPSERT_BATCH_SIZE (idempotent — safe to re-run).
        - Each point's payload includes "text", "page", and "source" (stem).
    """
    embeddings_path = EMBEDDINGS_DIR / (stem + ".json")

    if not embeddings_path.exists():
        raise FileNotFoundError(
            f"Embeddings file not found: {embeddings_path}. Run /embed first."
        )

    chunks: list[dict] = json.loads(embeddings_path.read_text())

    if not chunks:
        return 0

    vector_size = len(chunks[0]["embedding"])
    client = _get_client()
    _ensure_collection(client, vector_size)

    total_upserted = 0

    for batch_start in range(0, len(chunks), UPSERT_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + UPSERT_BATCH_SIZE]

        points = [
            PointStruct(
                id=chunk["chunk_index"],
                vector=chunk["embedding"],
                payload={
                    "text":   chunk["text"],
                    "page":   chunk["page"],
                    "source": stem,          # which PDF this chunk came from
                },
            )
            for chunk in batch
        ]

        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        total_upserted += len(points)
        print(
            f"  Indexed {batch_start + len(batch)}/{len(chunks)} chunks"
        )

    return total_upserted
