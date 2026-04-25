import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile

from pipeline.chunker import chunk_extracted_file
from pipeline.embedder import embed_chunks
from pipeline.extractor import extract_text_from_pdf
from pipeline.indexer import index_embeddings

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


@app.post("/chunk/{filename}")
def chunk_pdf(filename: str):
    """
    Chunk the extracted text for a previously extracted PDF.

    The extraction JSON must already exist in data/extracted/.
    Run /extract/{filename} first if it does not.
    Chunks are saved to data/chunks/<stem>.json.
    """
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    stem = Path(filename).stem

    try:
        chunks = chunk_extracted_file(stem)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "filename": filename,
        "total_chunks": len(chunks),
        "output_file": f"data/chunks/{stem}.json",
    }


@app.post("/embed/{filename}")
def embed_pdf(filename: str):
    """
    Generate embeddings for all chunks of a previously chunked PDF.

    The chunks JSON must already exist in data/chunks/.
    Run /chunk/{filename} first if it does not.
    Embeddings are saved to data/embeddings/<stem>.json.

    Note: this may take a few minutes for large PDFs — each batch of 32 chunks
    is sent to the local Ollama embedding model as a single HTTP request.
    """
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    stem = Path(filename).stem

    try:
        enriched = embed_chunks(stem)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        # Ollama may not be running or the model may not be pulled.
        raise HTTPException(
            status_code=502,
            detail=f"Embedding failed: {exc}. Is Ollama running?",
        ) from exc

    # Report the embedding dimension so the caller knows what to expect.
    vector_dim = len(enriched[0]["embedding"]) if enriched else 0

    return {
        "filename": filename,
        "total_chunks": len(enriched),
        "vector_dimensions": vector_dim,
        "output_file": f"data/embeddings/{stem}.json",
    }


@app.post("/index/{filename}")
def index_pdf(filename: str):
    """
    Upsert all chunk vectors for a previously embedded PDF into Qdrant.

    The embeddings JSON must already exist in data/embeddings/.
    Run /embed/{filename} first if it does not.

    Safe to call multiple times — upsert is idempotent.
    """
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    stem = Path(filename).stem

    try:
        total = index_embeddings(stem)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        # Collection vector-size mismatch
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Qdrant indexing failed: {exc}. Is Qdrant running?",
        ) from exc

    return {
        "filename": filename,
        "indexed_chunks": total,
        "collection": "rag_chunks",
    }
