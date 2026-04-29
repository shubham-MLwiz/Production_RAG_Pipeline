import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from pipeline.chunker import chunk_extracted_file
from pipeline.embedder import embed_chunks
from pipeline.extractor import extract_text_from_pdf
from pipeline.generator import generate_answer
from pipeline.indexer import index_embeddings
from pipeline.retriever import retrieve

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


@app.get("/retrieve")
def retrieve_chunks(question: str, top_k: int = 5):
    """
    Embed a question and return the top-k most relevant chunks from Qdrant.

    Query parameters:
      - question: the user's question text (required)
      - top_k:    how many chunks to return (default 5, max sensible value ~20)

    Returns the matched chunks with their similarity scores, page numbers,
    and source document. No answer generation — retrieval only.
    """
    if not question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty.")

    if top_k < 1 or top_k > 50:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 50.")

    try:
        chunks = retrieve(question, top_k=top_k)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Retrieval failed: {exc}. Are Ollama and Qdrant running?",
        ) from exc

    return {
        "question":      question,
        "top_k":         top_k,
        "results_count": len(chunks),
        "results":       chunks,
    }


# ── Request model for POST /generate ─────────────────────────────────────────

class GenerateRequest(BaseModel):
    question: str
    top_k: int = 5


@app.post("/generate")
def generate(req: GenerateRequest):
    """
    Retrieve the most relevant chunks for a question, then generate an answer.

    This is the first end-to-end RAG endpoint:
      1. Embed the question with Ollama (same embedding model used for chunks).
      2. Retrieve the top-k closest chunks from Qdrant.
      3. Build a context prompt from those chunks.
      4. Call the Ollama LLM to generate an answer grounded in that context.

    Request body (JSON):
      - question: the user's question (required)
      - top_k:    how many chunks to retrieve (default 5)

    Returns:
      - question:    echoed back
      - answer:      the LLM's generated answer
      - chunks_used: number of chunks passed to the LLM
      - chunks:      the retrieved chunks (for inspection / future citations)
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty.")

    if req.top_k < 1 or req.top_k > 50:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 50.")

    # Step 1 — retrieve
    try:
        chunks = retrieve(req.question, top_k=req.top_k)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Retrieval failed: {exc}. Are Ollama and Qdrant running?",
        ) from exc

    # Step 2 — generate
    try:
        answer = generate_answer(req.question, chunks)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Generation failed: {exc}. Is Ollama running with the LLM model pulled?",
        ) from exc

    # Build a compact citation list.
    # The ref number (1, 2, 3…) matches the [N] numbers in the LLM context
    # block, so the caller can map "[1] in the answer" → citation ref=1.
    citations = [
        {
            "ref":         i,
            "chunk_index": c["chunk_index"],
            "page":        c["page"],
            "source":      c["source"],
        }
        for i, c in enumerate(chunks, start=1)
    ]

    return {
        "question":    req.question,
        "answer":      answer,
        "chunks_used": len(chunks),
        "citations":   citations,
        "chunks":      chunks,
    }
