# RAG Pipeline — Architecture

**Last updated:** Step 10 — Generate answer from retrieved chunks

This diagram shows every component that has been built so far.
It is a living document — updated at each finalization step if the architecture changed.

---

## Full System Data Flow

```mermaid
flowchart TD
    subgraph USER["User"]
        U1["Browser\n(Streamlit UI\nlocalhost:8501)"]
    end

    subgraph API["FastAPI Backend — localhost:8000"]
        EP_UPLOAD["POST /upload"]
        EP_EXTRACT["POST /extract/{filename}"]
        EP_CHUNK["POST /chunk/{filename}"]
        EP_EMBED["POST /embed/{filename}"]
        EP_INDEX["POST /index/{filename}"]
        EP_RETRIEVE["GET /retrieve"]
        EP_GENERATE["POST /generate"]
    end

    subgraph PIPELINE["Pipeline Modules"]
        P_EXTRACT["extractor.py\nextract_text_from_pdf()"]
        P_CHUNK["chunker.py\nchunk_text()"]
        P_EMBED["embedder.py\nembed_chunks()"]
        P_INDEX["indexer.py\nindex_chunks()"]
        P_RETRIEVE["retriever.py\nretrieve()"]
        P_GENERATE["generator.py\ngenerate_answer()"]
    end

    subgraph STORAGE["Local Disk — data/"]
        D_RAW["data/raw/\n*.pdf"]
        D_EXTRACTED["data/extracted/\n*.json"]
        D_CHUNKS["data/chunks/\n*.json"]
        D_EMBEDDINGS["data/embeddings/\n*.json"]
    end

    subgraph OLLAMA["Ollama — localhost:11434"]
        O_EMBED["mxbai-embed-large\n(1024-dim embeddings)"]
        O_LLM["llama3.1\n(text generation)"]
    end

    subgraph QDRANT["Qdrant — localhost:6333"]
        Q_COL["collection: rag_chunks\n904 points · Cosine · 1024-dim"]
    end

    %% ── Ingestion path ────────────────────────────────────────────────────────
    U1 -->|"upload PDF"| EP_UPLOAD
    EP_UPLOAD --> D_RAW

    EP_EXTRACT --> P_EXTRACT
    P_EXTRACT -->|"reads"| D_RAW
    P_EXTRACT -->|"writes pages JSON"| D_EXTRACTED

    EP_CHUNK --> P_CHUNK
    P_CHUNK -->|"reads"| D_EXTRACTED
    P_CHUNK -->|"writes chunks JSON"| D_CHUNKS

    EP_EMBED --> P_EMBED
    P_EMBED -->|"reads"| D_CHUNKS
    P_EMBED -->|"POST /api/embed (batches of 32)"| O_EMBED
    O_EMBED -->|"1024-dim vectors"| P_EMBED
    P_EMBED -->|"writes embeddings JSON"| D_EMBEDDINGS

    EP_INDEX --> P_INDEX
    P_INDEX -->|"reads"| D_EMBEDDINGS
    P_INDEX -->|"upsert points"| Q_COL

    %% ── Query path ────────────────────────────────────────────────────────────
    U1 -->|"type question"| EP_RETRIEVE
    EP_RETRIEVE --> P_RETRIEVE
    P_RETRIEVE -->|"POST /api/embed (single query)"| O_EMBED
    P_RETRIEVE -->|"query_points top_k"| Q_COL
    Q_COL -->|"scored chunks"| P_RETRIEVE
    P_RETRIEVE -->|"ranked chunks list"| EP_RETRIEVE
    EP_RETRIEVE -->|"JSON results"| U1

    EP_GENERATE --> P_RETRIEVE
    EP_GENERATE --> P_GENERATE
    P_GENERATE -->|"POST /api/generate"| O_LLM
    O_LLM -->|"answer text"| P_GENERATE
    P_GENERATE -->|"answer + chunks"| EP_GENERATE
    EP_GENERATE -->|"JSON answer"| U1
```

---

## Component Summary

| Component | Technology | Role |
|-----------|-----------|------|
| Streamlit UI | `ui/app.py` | User-facing question input and chunk results display |
| FastAPI backend | `app/main.py` | REST API — orchestrates all pipeline steps |
| extractor.py | PyMuPDF (fitz) | Converts PDF pages to plain text JSON |
| chunker.py | Custom (200-word / 50-word overlap) | Splits page text into overlapping windows |
| embedder.py | Ollama `/api/embed` | Produces 1024-dim vectors per chunk |
| indexer.py | Qdrant client | Upserts vectors + metadata into Qdrant |
| retriever.py | Qdrant `query_points` | Embeds query, fetches top-k nearest chunks |
| generator.py | Ollama `/api/generate` | Builds grounding prompt, calls LLM, returns answer |
| Ollama | `mxbai-embed-large` + `llama3.1` | Local embedding model and local LLM |
| Qdrant | Docker `qdrant/qdrant` | Vector database, collection `rag_chunks` |
| Disk storage | `data/{raw,extracted,chunks,embeddings}/` | Intermediate JSON artefacts per step |

---

## Data Artefacts

```
data/
├── raw/              ← uploaded PDFs
├── extracted/        ← [{page: N, text: "..."}] per PDF
├── chunks/           ← [{chunk_index, page, text}] per PDF
└── embeddings/       ← [{chunk_index, page, text, embedding: [f×1024]}] per PDF
```

---

## What is NOT built yet (next steps)

- Chunk-level citations shown in the UI (Step 11)
- Soft refusal when evidence score is too low (Step 12)
- Conversation memory / multi-turn (future)
- Semantic cache (future)
- Hybrid retrieval / reranker (future)
