"""
pipeline/extractor.py

Reads a PDF file from disk and extracts the text from every page using PyMuPDF.

PyMuPDF (fitz) uses the C-based MuPDF engine which:
- correctly reconstructs character-spaced text (no merged words)
- preserves reading order across multi-column layouts
- natively detects tables via page.find_tables() (v1.23+)

Output structure (one item per page):
    [
        {"page": 1, "text": "..."},
        {"page": 2, "text": "..."},
        ...
    ]

The result is also saved as a JSON file in data/extracted/<stem>.json
so it can be inspected manually.
"""

import json
from pathlib import Path

import fitz  # pymupdf

# Where extracted JSON files will be written.
EXTRACTED_DIR = Path("data/extracted")
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """
    Extract text from every page of a PDF file.

    Args:
        pdf_path: Absolute or relative path to a .pdf file.

    Returns:
        A list of dicts, one per page:
            [{"page": 1, "text": "..."}, {"page": 2, "text": "..."}, ...]

    Side effect:
        Writes the same list as JSON to data/extracted/<stem>.json.
    """
    pages = []

    # fitz.open() works with Path objects and strings.
    with fitz.open(pdf_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            # get_text("text") extracts plain text with correct spacing.
            # Returns an empty string for image-only pages.
            text = page.get_text("text") or ""
            pages.append({"page": page_number, "text": text.strip()})

    # Save to disk so we can inspect the output without running code again.
    output_path = EXTRACTED_DIR / (pdf_path.stem + ".json")
    output_path.write_text(json.dumps(pages, indent=2, ensure_ascii=False))

    return pages
