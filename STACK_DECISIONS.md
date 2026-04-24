# Stack Decisions for Local, Learning-First Production RAG

This document narrows the original README into a **local-first**, **learning-first** setup.

---

## 1) Recommended defaults for your setup

### LLM provider
- **Ollama** for local inference
- Start with a model that is easy to run locally before trying larger models

### UI
- **Streamlit** is mandatory for v1
- Keep Streamlit separate from FastAPI so you can learn both layers independently

### Backend API
- **FastAPI**

### Vector database
- **Qdrant**

### Orchestration
- **Start custom orchestration first** for the first few features
- Introduce **LangGraph later**, only when you add branching/loops such as:
  - query routing
  - corrective retrieval loops
  - self-grading / CRAG
  - optional human-in-the-loop

### PDF
- Text PDF only for v1
- No OCR in v1

### Citations
- **Chunk-level citations** in v1

---

## 2) My recommendation on orchestration

### Recommendation: hybrid approach

Use **custom orchestration first**, then **LangGraph later**.

Why:
- For the first 4–6 learning steps, custom orchestration is easier to read and debug.
- LangGraph becomes valuable when the flow becomes stateful and conditional.
- LangGraph is explicitly designed for workflows/agents with persistence, streaming, debugging, and stateful multi-step execution. citeturn2search11turn2search12

### Suggested progression
1. **Phase A (custom orchestration)**
   - PDF ingest
   - chunking
   - embeddings
   - vector search
   - generate answer
   - Streamlit UI

2. **Phase B (still custom)**
   - conversation memory
   - semantic cache
   - hybrid retrieval
   - reranking

3. **Phase C (introduce LangGraph)**
   - intent routing
   - self-grading retrieval
   - decomposition and re-retrieval loops
   - advanced observability

This gives you the best balance of **learning clarity now** and **clean extensibility later**.

---

## 3) Local LLM options for Ollama

## 3.1 Best starter LLMs

### Option A — `qwen2.5:7b-instruct`
**Why choose it:** excellent quality/speed tradeoff for local RAG on a decent laptop/desktop.

### Option B — `llama3.1:8b-instruct`
**Why choose it:** strong general local baseline if your machine can handle it comfortably.

### Option C — `phi4-mini` or similar small instruct model
**Why choose it:** lower resource usage, faster iteration, useful for learning.

### My advice
Start with a **7B–8B instruct model** in Ollama for answer generation. If response quality is poor, increase model size later. Keep the model configurable in `.env`.

---

## 4) Embedding model options (local, open source)

Ollama supports local embedding generation through its embedding API, and `nomic-embed-text` is a documented embedding model in the Ollama library. citeturn2search27turn2search28

### Option 1 — `nomic-embed-text`
**Pros**
- Very popular in Ollama
- Small footprint
- Good for getting started
- Long context window in the Ollama model page description

**Cons**
- Not the strongest retrieval quality among larger open models

**Best for**
- First implementation
- CPU-friendly development
- Fast local iteration

### Option 2 — `mxbai-embed-large`
**Pros**
- Better retrieval quality than smaller default options in many practical comparisons
- Still manageable locally on many machines

**Cons**
- Larger and heavier than `nomic-embed-text`

**Best for**
- Better retrieval quality once the basics work

### Option 3 — `bge-m3`
**Pros**
- Good multilingual and retrieval-oriented reputation
- Useful if you later want multilingual search or more advanced retrieval behavior

**Cons**
- Heavier setup and not my first recommendation for your learning-first v1

### My advice
Use:

1. **`nomic-embed-text` for v1**
2. Then compare against **`mxbai-embed-large`** once the pipeline works

This keeps your first milestone simple while leaving an easy upgrade path. Ollama documents `nomic-embed-text` specifically for local embeddings, and Qdrant supports hybrid search patterns that can later combine dense and sparse retrieval. citeturn2search27turn2search21

---

## 5) Reranker options (local)

Rerankers are usually **cross-encoders** that score `(query, chunk)` pairs more precisely than the retriever, but they are slower than first-stage retrieval. BGE’s reranker docs explicitly describe this tradeoff. citeturn2search17

### Option 1 — `BAAI/bge-reranker-base`
**Pros**
- Good baseline
- Common, well-known cross-encoder style reranker
- Easier starting point

**Cons**
- Lower quality than larger rerankers in some cases

### Option 2 — `BAAI/bge-reranker-large`
**Pros**
- Better quality than base on many tasks

**Cons**
- Heavier and slower

### Option 3 — `bge-reranker-v2-m3`
**Pros**
- Useful if you want multilingual support

**Cons**
- More complexity than needed for your first English-first or simple v1 setup

### Option 4 — `Qwen3-Reranker-0.6B / 4B`
Ollama search results show Qwen3 reranker variants are available in the ecosystem, including smaller and larger model sizes. citeturn2search20

**Pros**
- Strong modern reranker family
- Multiple sizes available

**Cons**
- Local setup details can be slightly more involved depending on packaging/runtime

### My advice
For your learning-first build:

1. **Do not add reranking in step 1**
2. Add reranking only after retrieval is already working
3. Start with **`BAAI/bge-reranker-base`** if you use Hugging Face locally
4. If you specifically want Ollama-native reranker experimentation later, try **Qwen3-Reranker-0.6B** first

That gives you the smallest conceptual jump.

---

## 6) UI recommendation

Use **Streamlit** first.

Why:
- Streamlit has built-in chat UI primitives like `st.chat_message` and `st.chat_input`, making it easy to build a conversational test UI quickly. citeturn2search3
- It helps you learn and verify each backend feature visually without spending time on frontend engineering.
- It keeps iteration speed high.

### Recommended UI split
- **FastAPI** = backend RAG API
- **Streamlit** = frontend for upload, query, citations, debug view

### Minimum UI features for v1
- upload PDF
- ingest PDF
- ask question
- show answer
- show chunk citations
- show retrieved chunks in expandable debug panel

---

## 7) Retrieval recommendation

Start simple, then grow.

### v1 retrieval
- Dense retrieval only
- Qdrant vector store
- top-k retrieval
- chunk-level citations

### v2 retrieval
- Add sparse retrieval / BM25
- Fuse dense + sparse using RRF
- Qdrant’s hybrid search capabilities are explicitly designed for combining dense and sparse methods. citeturn2search21turn2search26

### v3 retrieval
- Add reranker
- Add grading / corrective retrieval loop

---

## 8) Recommended stack for your first working version

### v1 stack
- **LLM**: Ollama + `qwen2.5:7b-instruct` (or nearest available instruct variant locally)
- **Embeddings**: Ollama + `nomic-embed-text`
- **Vector DB**: Qdrant
- **API**: FastAPI
- **UI**: Streamlit
- **Orchestration**: custom Python services
- **PDF parsing**: pypdf / pymupdf text extraction
- **Chunking**: simple recursive/token-aware chunker
- **Citations**: chunk level

### v2 stack
- swap embeddings to `mxbai-embed-large`
- add BM25 sparse retrieval
- add reranker
- keep UI and backend unchanged

### v3 stack
- introduce LangGraph
- add intent router
- add self-grading + decomposition loop

---

## 9) Most important learning advice

Do **not** start with the full production RAG system.

Start with this exact sequence:
1. ingest one PDF
2. embed chunks
3. ask one question
4. retrieve top chunks
5. answer from chunks
6. show answer in Streamlit
7. add citations
8. only then add hybrid retrieval
9. only then add reranker
10. only then add routing / memory / cache / grading

That sequence keeps the system understandable.
