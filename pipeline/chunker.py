"""
pipeline/chunker.py

Splits extracted page text into fixed-size, overlapping chunks.

Input: data/extracted/<stem>.json  (list of {"page": N, "text": "..."})

Chunking strategy: words from all pages are concatenated into a single stream
first, then a sliding window cuts overlapping chunks across the whole document.
This means overlap is preserved even at page boundaries, which is important when
sentences continue across pages (common in reference guides).

Each chunk is tagged with the page number where its first word appears.

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


def chunk_extracted_file(stem: str) -> list[dict]:
    """
    Load data/extracted/<stem>.json and split the full document text into
    overlapping chunks across page boundaries.

    Strategy:
      1. Build a flat list of (word, page_number) pairs from all pages.
      2. Slide a window of CHUNK_SIZE words across the whole list, stepping
         by (CHUNK_SIZE - CHUNK_OVERLAP) each time.
      3. Tag each chunk with the page number of its first word.

    Args:
        stem: The PDF filename without extension, e.g. "test_file".

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

    # Build a flat list of (word, page_number) pairs across the whole document.
    # This is what makes cross-page overlap possible.
    word_page_pairs: list[tuple[str, int]] = []
    for page_entry in pages:
        page_number = page_entry["page"]
        page_text = page_entry["text"].strip()
        if not page_text:
            continue  # skip blank pages
        for word in page_text.split():
            word_page_pairs.append((word, page_number))

    all_chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP

    for chunk_index, start in enumerate(range(0, len(word_page_pairs), step)):
        window = word_page_pairs[start : start + CHUNK_SIZE]
        if not window:
            break

        chunk_text = " ".join(w for w, _ in window)
        # Tag the chunk with the page where its first word appears.
        first_page = window[0][1]

        all_chunks.append(
            {
                "chunk_index": chunk_index,
                "page": first_page,
                "text": chunk_text,
            }
        )

    # Save to disk for inspection and for the embedding step.
    output_path = CHUNKS_DIR / (stem + ".json")
    output_path.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))

    return all_chunks
