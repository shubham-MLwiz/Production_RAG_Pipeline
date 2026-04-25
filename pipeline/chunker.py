"""
pipeline/chunker.py

Splits extracted page text into fixed-size, overlapping chunks.

Input: data/extracted/<stem>.json  (list of {"page": N, "text": "..."})

Output structure (one item per chunk):
    [
        {
            "chunk_index": 0,
            "page":        1,
            "text":        "first 200 words ...",
        },
        {
            "chunk_index": 1,
            "page":        1,
            "text":        "words 150-350 ... (50-word overlap with previous)",
        },
        ...
    ]

The result is saved to data/chunks/<stem>.json.
"""

import json
from pathlib import Path

# Where chunk JSON files will be written.
CHUNKS_DIR = Path("data/chunks")
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

# Where extracted page JSON files live (produced by Step 4).
EXTRACTED_DIR = Path("data/extracted")

# Chunking parameters.
# CHUNK_SIZE   — maximum number of words per chunk.
# CHUNK_OVERLAP — number of words shared between consecutive chunks.
# These values are intentionally small so the output is easy to inspect manually.
# A production system might use 400/80 or similar.
CHUNK_SIZE = 200
CHUNK_OVERLAP = 50


def _split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split a string into overlapping word-level chunks.

    Args:
        text:       The text to split.
        chunk_size: Maximum number of words per chunk.
        overlap:    Number of words that the next chunk shares with the previous one.

    Returns:
        A list of text strings, each at most `chunk_size` words long.
    """
    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))

        # Advance the window, stepping back by `overlap` words so the next
        # chunk begins with the last `overlap` words of this chunk.
        start += chunk_size - overlap

    return chunks


def chunk_extracted_file(stem: str) -> list[dict]:
    """
    Load data/extracted/<stem>.json and split every page's text into chunks.

    Args:
        stem: The PDF filename without extension, e.g. "my_document".

    Returns:
        A flat list of chunk dicts, each with "chunk_index", "page", and "text".

    Side effect:
        Writes the chunk list to data/chunks/<stem>.json.
    """
    extracted_path = EXTRACTED_DIR / (stem + ".json")

    if not extracted_path.exists():
        raise FileNotFoundError(
            f"Extracted file not found: {extracted_path}. Run /extract first."
        )

    pages: list[dict] = json.loads(extracted_path.read_text())

    all_chunks = []
    chunk_index = 0

    for page_entry in pages:
        page_number = page_entry["page"]
        page_text = page_entry["text"]

        # Skip entirely empty pages (blank title pages, etc.).
        if not page_text.strip():
            continue

        page_chunks = _split_into_chunks(page_text, CHUNK_SIZE, CHUNK_OVERLAP)

        for chunk_text in page_chunks:
            all_chunks.append(
                {
                    "chunk_index": chunk_index,
                    "page": page_number,
                    "text": chunk_text,
                }
            )
            chunk_index += 1

    # Save to disk for manual inspection and for future pipeline steps.
    output_path = CHUNKS_DIR / (stem + ".json")
    output_path.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))

    return all_chunks
