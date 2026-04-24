import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile

from pipeline.extractor import extract_text_from_pdf

# Directory where uploaded PDFs will be saved.
RAW_DATA_DIR = Path("data/raw")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Create the FastAPI application instance.
# The `title` appears in the auto-generated docs at /docs.
app = FastAPI(title="RAG Pipeline API")


@app.get("/health/live")
def health_live():
    """Return a simple liveness signal."""
    return {"status": "ok"}


@app.post("/upload")
def upload_pdf(file: UploadFile):
    """Accept a PDF file, save it to data/raw/, and return its metadata."""

    # Reject anything that is not a PDF.
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    destination = RAW_DATA_DIR / file.filename

    # Write the uploaded bytes to disk.
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": file.filename,
        "saved_to": str(destination),
        "size_bytes": destination.stat().st_size,
    }


@app.post("/extract/{filename}")
def extract_pdf(filename: str):
    """
    Extract text from a previously uploaded PDF.

    The PDF must already exist in data/raw/.
    Extracted pages are saved to data/extracted/<stem>.json.
    """
    # Only allow filenames that end in .pdf to prevent path traversal.
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    pdf_path = RAW_DATA_DIR / filename

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{filename} not found in data/raw/. Upload it first.",
        )

    pages = extract_text_from_pdf(pdf_path)

    return {
        "filename": filename,
        "pages_extracted": len(pages),
        "output_file": f"data/extracted/{pdf_path.stem}.json",
    }
