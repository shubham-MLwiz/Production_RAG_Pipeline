# Learning Log — RAG Pipeline

This file records each completed step: what was built, why it matters, what was tested, and what to remember.

---

## Step 0 — Project skeleton only

### What I added
- `pyproject.toml` — project metadata, all runtime and dev dependencies declared in one place
- `.env.example` — documents every environment variable the system will need (no secrets committed)
- `app/`, `pipeline/`, `ui/`, `data/raw/`, `tests/` — empty folders tracked by `.gitkeep` files

### Why this matters
Without a defined folder structure and a `pyproject.toml`, every future file would land in an ad-hoc location. Having the skeleton first means Steps 1–23 can each drop one file into a predictable home. The dependency list in `pyproject.toml` also means anyone can reproduce the environment with a single `pip install -e ".[dev]"`.

### Files changed
- `pyproject.toml`: created — declares project name, Python ≥ 3.11, all runtime dependencies (fastapi, uvicorn, streamlit, pypdf, qdrant-client, httpx, pydantic, python-dotenv, python-multipart), and dev dependencies (pytest, pytest-asyncio)
- `.env.example`: created — documents `OLLAMA_BASE_URL`, `OLLAMA_LLM_MODEL`, `OLLAMA_EMBED_MODEL`, `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`, `API_PORT`, `RAW_DATA_DIR`
- `app/.gitkeep`, `pipeline/.gitkeep`, `ui/.gitkeep`, `data/raw/.gitkeep`, `tests/.gitkeep`: created — zero-byte files that force Git to track the otherwise empty directories

### How I tested
- Ran `find . -name ".gitkeep"` and confirmed all five files appeared
- Ran `pip install -e ".[dev]"` and confirmed all packages installed without errors
- Ran `ls app pipeline ui data/raw tests` and confirmed all folders existed

### Notes to future me
- `.env` (the real secrets file) must never be committed — add it to `.gitignore` before Step 1
- The `pyproject.toml` dependency list is intentionally complete for all early steps; nothing needs adding until LangGraph or an evaluation harness
- Next step: create `app/main.py` and boot the FastAPI server

---

## Step 1 — Health-only FastAPI app

### What I added
- `app/main.py` — a minimal FastAPI application with a single `GET /health/live` endpoint that returns `{"status": "ok"}`

### Why this matters
Every future route (upload, query, retrieve, generate) will be added to this same `app` object. Proving the server boots cleanly before adding any logic means the foundation is confirmed working. It also introduces the two key concepts used in every subsequent step: the FastAPI app object and route decorators.

### Files changed
- `app/main.py`: created — imports `FastAPI`, creates the `app` instance with a human-readable title, and registers one GET route at `/health/live`

### How I tested
- Started the server with `uvicorn app.main:app --reload --port 8000`
- Opened `http://localhost:8000/health/live` in the browser and saw `{"status":"ok"}`
- Opened `http://localhost:8000/docs` and saw the Swagger UI listing the health endpoint
- Hit the endpoint with `curl http://localhost:8000/health/live` and confirmed the JSON response

### Notes to future me
- `uvicorn app.main:app` means: file `app/main.py`, object named `app` — the colon separates module path from attribute name
- `--reload` is for development only; remove it in production
- All future routes will be added to this same `app` object in `app/main.py` (or imported routers mounted onto it)
- Next step: create the Streamlit UI shell and verify it can reach the backend

---

## Step 2 — Minimal Streamlit UI shell

### What I added
- `ui/app.py` — a Streamlit page with a title, a backend health check banner (green / red), a question text input, and a placeholder caption for future answer output

### Why this matters
Before wiring real retrieval or generation, verifying that the Streamlit process can reach the FastAPI process over HTTP catches network or port problems early. The text input box with `key="question"` is already set up so future steps can read `st.session_state.question` without changing the widget.

### Files changed
- `ui/app.py`: created — imports `httpx` and `streamlit`, defines `check_backend_health()` which does a 3-second-timeout GET to `/health/live`, then renders a success or error banner, a divider, a text input, and a placeholder caption

### How I tested
- Started FastAPI (`uvicorn app.main:app --reload --port 8000`) and Streamlit (`streamlit run ui/app.py`) in two separate terminals
- Opened `http://localhost:8501` and confirmed the green "Backend is running" banner appeared
- Stopped the FastAPI server, refreshed the Streamlit page, and confirmed the red "Backend is not reachable" banner appeared
- Confirmed the text input box was visible and accepted keyboard input

### Notes to future me
- `BACKEND_URL` is a hard-coded constant for now; it should be read from `.env` (via `pydantic-settings`) once a config module is introduced
- Streamlit reruns the entire script on every interaction — `check_backend_health()` is therefore called on every page load, which is fine for development
- The `key="question"` on the text input is important: it means the value will be accessible as `st.session_state.question` in Step 9 without any widget changes
- Next step: add `POST /upload` to the FastAPI app to accept a PDF file and save it to `data/raw/`

---

## Step 3 — PDF upload endpoint

### What I added
- `POST /upload` route in `app/main.py` that accepts a single PDF file via multipart form upload
- Extension validation — returns HTTP 400 if the uploaded file is not a `.pdf`
- Saves the file to `data/raw/` using `shutil.copyfileobj` (streaming, no full file in memory)
- Returns `filename`, `saved_to` path, and `size_bytes` read back from disk after writing

### Why this matters
The entire RAG pipeline begins here. Before any text can be extracted, chunked, embedded, or indexed, a PDF must land on disk in a known location. Every step from Step 4 onwards reads files from `data/raw/`.

### Files changed
- `app/main.py`: added `shutil`, `Path`, `HTTPException`, and `UploadFile` imports; added `RAW_DATA_DIR` constant with `mkdir` guard; added the `upload_pdf` function registered at `POST /upload`

### How I tested
- Started the server with `uvicorn app.main:app --reload --port 8000`
- Used Swagger UI at `http://localhost:8000/docs` to upload a real PDF and confirmed a 200 response with `filename`, `saved_to`, and `size_bytes`
- Ran `ls data/raw/` and confirmed the PDF appeared on disk
- Uploaded a `.txt` file and confirmed a 400 response with `"Only .pdf files are accepted."`
- Tested via `curl -X POST http://localhost:8000/upload -F "file=@/path/to/file.pdf"` and confirmed the JSON response

### Notes to future me
- The filename is taken directly from `file.filename` — if two PDFs share the same name the second will overwrite the first; a deduplication strategy (e.g. UUID prefix) can be added later
- `RAW_DATA_DIR` is a hard-coded `Path` constant for now; it will eventually be read from `.env` via a config module
- `shutil.copyfileobj` streams the upload in chunks so large PDFs do not blow up memory
- Next step: read the saved PDF with `pypdf`, extract text page by page, and write a JSON file with one entry per page

---

## Step 4 — Extract text from a text PDF

### What I added
- `pipeline/extractor.py` — reads a PDF page by page using `pypdf` and returns a list of `{"page": N, "text": "..."}` dicts; also writes the result to `data/extracted/<stem>.json`
- `POST /extract/{filename}` endpoint in `app/main.py` — receives a filename, looks it up in `data/raw/`, calls the extractor, and returns page count plus output path

### Why this matters
Text extraction is the first real transformation in the RAG pipeline. Before this step the PDF is just an opaque binary file. After this step the text is in a structured, human-readable JSON format that every subsequent step (chunking, embedding, indexing) can consume. Storing it as JSON means you can inspect what the model will actually see without running any more code.

### Files changed
- `pipeline/extractor.py`: created — `extract_text_from_pdf(pdf_path)` opens the PDF with `PdfReader`, iterates pages with 1-based numbering, calls `page.extract_text()`, strips whitespace, builds the list, and writes `data/extracted/<stem>.json`
- `app/main.py`: added import of `extract_text_from_pdf`; added `POST /extract/{filename}` route with `.pdf` extension check and 404 guard for missing files

### How I tested
- Started FastAPI with `uvicorn app.main:app --reload --port 8000`
- Uploaded a real multi-page PDF via `POST /upload` using Swagger UI at `http://localhost:8000/docs`
- Called `POST /extract/{filename}` from Swagger UI (used the "Try it out" feature to avoid URL-encoding issues with spaces in the filename)
- Confirmed response showed correct `pages_extracted` count and `output_file` path
- Opened `data/extracted/<stem>.json` and verified the array contained one entry per page with readable text
- Tested the 404 path by trying to extract a filename that had not been uploaded yet
- Tested the 400 path by passing a non-`.pdf` filename

### Notes to future me
- `pypdf` only extracts the text layer baked into the PDF — scanned/image PDFs will return empty strings; OCR is a future step
- Spaces in PDF filenames require URL-encoding (`%20`) in curl; Swagger UI handles this automatically and is the easiest way to test endpoints with spaces in path parameters
- The JSON file on disk is the hand-off point to Step 5 — the chunker will read from `data/extracted/`
- `EXTRACTED_DIR` is hard-coded; it will eventually move to a config module alongside `RAW_DATA_DIR`
- Next step: split each page's text into overlapping chunks and save them as `data/chunks/<stem>.json`

---

## Step 5 — Chunk extracted text

### What I added
- `pipeline/chunker.py` — splits extracted page text into fixed-size, overlapping word-level chunks; each chunk carries its source page number and a global `chunk_index`; writes output to `data/chunks/<stem>.json`
- `POST /chunk/{filename}` endpoint in `app/main.py` — accepts a PDF filename, resolves the stem, calls `chunk_extracted_file`, and returns total chunk count and output path
- Also switched the PDF extraction library from `pypdf` to **PyMuPDF (`fitz`)** after discovering that `pypdf` merges words in character-spaced PDFs; PyMuPDF correctly reconstructs spaces and handles tables natively

### Why this matters
Embedding models and LLMs have token-length limits — a full PDF page can exceed them. Splitting into small, overlapping chunks means each unit fits inside the model's context window. The overlap (50 words by default) prevents a meaningful sentence from being cut cleanly at a chunk boundary. Attaching the page number to every chunk is what will make chunk-level citations possible later.

### Files changed
- `pipeline/chunker.py`: created — `_split_into_chunks(text, chunk_size, overlap)` slides a word-level window across the text; `chunk_extracted_file(stem)` loads `data/extracted/<stem>.json`, calls the splitter per page, accumulates a flat chunk list with a global `chunk_index`, and writes `data/chunks/<stem>.json`; constants `CHUNK_SIZE=200` and `CHUNK_OVERLAP=50` are at the top of the file for easy tuning
- `app/main.py`: added import of `chunk_extracted_file`; added `POST /chunk/{filename}` route with `.pdf` extension guard and `FileNotFoundError` → HTTP 404 conversion
- `pipeline/extractor.py`: replaced `pypdf` (`PdfReader` / `page.extract_text()`) with `pymupdf` (`fitz.open()` / `page.get_text("text")`) to fix merged-word output
- `pyproject.toml`: replaced `pypdf>=4.2.0` with `pymupdf>=1.24.0`

### How I tested
- Ran `POST /extract/test_file.pdf` via Swagger UI after switching to pymupdf; confirmed words in `data/extracted/test_file.json` were properly spaced
- Ran `POST /chunk/test_file.pdf` via Swagger UI; confirmed response showed `total_chunks: 1129` for a 544-page PDF (well above 1 chunk/page ratio, confirming chunking is working correctly)
- Inspected `data/chunks/test_file.json` and confirmed consecutive chunks share the last ~50 words, `page` numbers advance correctly, and no chunk exceeds ~200 words
- Ran extraction and chunking directly in Python via `.venv/bin/python3 -c "..."` — confirmed 544 pages extracted and 1129 chunks produced
- Tested the 404 error path by calling `/chunk/nonexistent.pdf`

### Notes to future me
- **PDF library comparison** — three libraries were evaluated during this step:
  - `pypdf`: simplest API, but merges words in character-spaced PDFs (no spaces reconstructed) — not usable for this document type
  - `pdfplumber`: better than `pypdf` for spacing, but table detection is heuristic and fragile with borderless or complex tables
  - `pymupdf (fitz)`: best overall — uses the C-based MuPDF engine, correctly reconstructs character-spaced text, preserves multi-column reading order, and has native table detection via `page.find_tables()` (v1.23+); AGPL license is acceptable for non-commercial use; **this is now the project standard**
- `CHUNK_SIZE=200` and `CHUNK_OVERLAP=50` are word-count-based; 200 words ≈ 250–300 tokens, safely within any local embedding model's limit; these can be tuned in `chunker.py` without touching other files
- `chunk_index` is a global counter across all pages, not per-page — this means every chunk has a unique ID which will be important when upserting into Qdrant
- Next step: call Ollama's local embedding model once per chunk and save the resulting vectors alongside chunk metadata

---

## Step 6 — Generate embeddings locally with Ollama

### What I added
- `pipeline/embedder.py` — reads `data/chunks/<stem>.json`, sends chunks to Ollama's `/api/embed` endpoint in batches of 32, and writes each chunk's vector + metadata to `data/embeddings/<stem>.json`
- `POST /embed/{filename}` endpoint in `app/main.py` — triggers the embedding run, returns chunk count, vector dimension, and output path; surfaces Ollama connectivity failures as HTTP 502
- `notebooks/pipeline_verification.ipynb` — full step-by-step verification notebook covering Steps 1–6 with `check()` assertions, curl equivalents, on-disk inspection cells, and a pipeline summary cell
- Updated `.env` and `.env.example` to use `mxbai-embed-large` (the model that was actually installed) instead of `nomic-embed-text`
- Also fixed a bug in `pipeline/chunker.py` discovered during verification: the per-page chunking strategy meant overlap was silently dropped at every page boundary; refactored to flatten all pages into a single word stream first, then slide the window across the whole document so overlap is preserved even across page breaks (chunks reduced from 1129 → 904, all more uniformly sized)

### Why this matters
Retrieval works by comparing a question vector against all chunk vectors and finding the nearest matches. This step produces those chunk vectors. Nothing is indexed yet — that is Step 7 — but after this step every chunk has a 1024-dimensional float vector that a vector DB can search.

### Files changed
- `pipeline/embedder.py`: created — `_embed_batch(texts)` calls `POST /api/embed` on Ollama with a list of texts and returns a list of vectors; `embed_chunks(stem)` loops in `BATCH_SIZE=32` batches, zips vectors back onto chunk dicts, and writes `data/embeddings/<stem>.json`; reads `OLLAMA_BASE_URL` and `OLLAMA_EMBED_MODEL` from `.env`
- `app/main.py`: added import of `embed_chunks`; added `POST /embed/{filename}` with `.pdf` check, `FileNotFoundError` → 404, generic `Exception` → 502 with Ollama hint; reports `vector_dimensions` in the response
- `pipeline/chunker.py`: refactored from per-page sliding window to a single document-wide word stream with per-word page tags; overlap now crosses page boundaries correctly; `_split_into_chunks` helper removed (no longer needed)
- `pyproject.toml`: replaced `pypdf>=4.2.0` with `pymupdf>=1.24.0` (carried over from Step 5 library switch)
- `.env.example`: updated `OLLAMA_EMBED_MODEL` from `nomic-embed-text` to `mxbai-embed-large`
- `notebooks/pipeline_verification.ipynb`: created — covers Steps 1–6 with labeled markdown headers, Python `httpx` calls, `check()` PASS/FAIL assertions, curl-equivalent comments, and a final artefact-state summary cell

### How I tested
- Ran `POST /embed/test_file.pdf` via Swagger UI; confirmed `total_chunks: 904`, `vector_dimensions: 1024`, output file at `data/embeddings/test_file.json`
- Ran the Step 6c notebook cell to inspect the embeddings file on disk; confirmed every chunk had a 1024-dim float vector with non-zero values
- Verified the chunker fix via Python: confirmed `overlap_preserved_across_page_boundary: True` at the first cross-page boundary (chunk 0 page 1 → chunk 1 page 3)
- Verified Ollama model list via `GET /api/tags`; confirmed `mxbai-embed-large:latest` was available

### Notes to future me
- `BATCH_SIZE=32` is a pragmatic default — larger batches are faster but use more RAM; tunable at the top of `embedder.py`
- The embedding run is slow (~2–5 min for 900+ chunks on CPU); results are cached in `data/embeddings/test_file.json` so you do not need to re-embed unless chunks change
- `mxbai-embed-large` produces 1024-dimensional vectors — the Qdrant collection created in Step 7 must match this dimension exactly
- The chunker page tag is the page of the **first word** in the chunk, not the last; a chunk may span two pages but only one page is cited; this is the standard convention and sufficient for Step 11 citations
- Next step: start Qdrant locally, create a collection with `vector_size=1024`, and upsert all chunks from `data/embeddings/test_file.json`

---

## Step 7 — Add Qdrant and index chunks

### What I added
- `pipeline/indexer.py` — connects to a local Qdrant instance, creates the `rag_chunks` collection if it doesn't exist (with `vector_size=1024`, `distance=Cosine`), and upserts all chunk vectors + metadata from `data/embeddings/<stem>.json` in batches of 100
- `POST /index/{filename}` endpoint in `app/main.py` — triggers the indexing run; returns `indexed_chunks` and `collection` name; surfaces `FileNotFoundError` as 404, vector-size mismatch as 409, and Qdrant connectivity errors as 502
- Qdrant started via Docker: `docker run -d --name qdrant -p 6333:6333 qdrant/qdrant`
- Updated `notebooks/pipeline_verification.ipynb` — added Step 7 cells: Qdrant health check, API index trigger, collection state assertion via REST, point payload spot-check, error case; also updated the pipeline summary cell to include Qdrant point count

### Why this matters
The embeddings JSON on disk is not searchable — it's just a flat array. Qdrant is the vector index that makes similarity search fast. Once chunks are upserted as Qdrant points, Step 8 can embed a question and retrieve the most relevant chunks in milliseconds without scanning all 904 vectors manually.

### Files changed
- `pipeline/indexer.py`: created — `_get_client()` returns a configured `QdrantClient`; `_ensure_collection()` creates the collection or validates the existing one's vector size; `index_embeddings(stem)` loads the embeddings JSON, builds `PointStruct` objects (id=chunk_index, vector=embedding, payload={text, page, source}), and upserts them in batches of 100
- `app/main.py`: added import of `index_embeddings`; added `POST /index/{filename}` with three error cases (404 / 409 / 502)
- `notebooks/pipeline_verification.ipynb`: added five Step 7 cells (health check, index API call, collection REST check, point payload spot-check, error case) and extended the pipeline summary cell to show Qdrant point count

### How I tested
- Started Qdrant with `docker run -d --name qdrant -p 6333:6333 qdrant/qdrant` and confirmed `healthz check passed`
- Ran `index_embeddings('test_file')` directly in Python — confirmed 904/904 chunks indexed and `collection points_count: 904, vector_size: 1024`
- Ran `POST /index/test_file.pdf` a second time via Swagger UI — confirmed it returned 904 again (idempotent upsert works)
- Fetched `GET http://localhost:6333/collections/rag_chunks/points/0` directly and confirmed payload keys `text`, `page`, `source` were present
- Tested `POST /index/nonexistent.pdf` — confirmed HTTP 404 with correct error message

### Notes to future me
- Qdrant data is stored inside the Docker container by default — it is lost if the container is removed; for persistence, add `-v $(pwd)/qdrant_storage:/qdrant/storage` to the Docker run command
- `chunk_index` is used as the Qdrant point `id` (integer) — this means re-running `/index` after re-embedding is safe (same ids, upsert overwrites); but if chunk count changes between runs (e.g. after re-chunking), old points with higher ids remain until the collection is deleted and recreated
- Cosine distance is the right choice for text embeddings — it measures directional similarity and is insensitive to vector magnitude
- The `source` field in the payload (= stem of the PDF filename) will let Step 8 filter results by source document when multiple PDFs are indexed
- Next step: embed an incoming question with Ollama and query Qdrant for the top-k nearest chunk payloads — no generation yet
