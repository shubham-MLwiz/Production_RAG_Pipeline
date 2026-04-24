"""
pipeline/extractor.py

Reads a PDF file from disk and extracts the text from every page.

Output structure (one item per page):
    [
        {"page": 1, "text": "..."},
        {"page": 2, "text": "..."},
        ...
    ]

The result is also saved as a JSON file alongside the raw PDF in
data/extracted/<stem>.json so it can be inspected manually.
"""

import json
from pathlib import Path

from pypdf import PdfReader

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
    reader = PdfReader(str(pdf_path))

    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        # extract_text() returns an empty string if a page has no extractable text.
        text = page.extract_text() or ""
        pages.append({"page": page_number, "text": text.strip()})

    # Save to disk so we can inspect the output without running code again.
    output_path = EXTRACTED_DIR / (pdf_path.stem + ".json")
    output_path.write_text(json.dumps(pages, indent=2, ensure_ascii=False))

    return pages
