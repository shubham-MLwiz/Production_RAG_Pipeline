import httpx
import streamlit as st

# The backend base URL. Later this will come from an env variable.
BACKEND_URL = "http://localhost:8000"

# How many chunks to retrieve / pass to the LLM.
TOP_K = 5


def check_backend_health() -> bool:
    """Return True if the FastAPI backend is reachable and healthy."""
    try:
        response = httpx.get(f"{BACKEND_URL}/health/live", timeout=3)
        return response.status_code == 200
    except httpx.RequestError:
        return False


def retrieve_chunks(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Call GET /retrieve on the backend and return the results list.
    Raises RuntimeError if the backend returns an error.
    """
    response = httpx.get(
        f"{BACKEND_URL}/retrieve",
        params={"question": query, "top_k": top_k},
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Backend returned {response.status_code}: "
            f"{response.json().get('detail', 'unknown error')}"
        )
    return response.json()["results"]


def call_generate(query: str, top_k: int = TOP_K) -> dict:
    """
    Call POST /generate on the backend and return the full response dict.
    Response contains: question, answer, chunks_used, citations, chunks.
    Raises RuntimeError if the backend returns an error.
    """
    response = httpx.post(
        f"{BACKEND_URL}/generate",
        json={"question": query, "top_k": top_k},
        timeout=180,  # LLM generation can take up to 2 minutes on CPU
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Backend returned {response.status_code}: "
            f"{response.json().get('detail', 'unknown error')}"
        )
    return response.json()


# ── Page layout ──────────────────────────────────────────────────────────────

st.title("RAG Pipeline")

# Show backend status at the top so it is always visible.
if check_backend_health():
    st.success("Backend is running")
else:
    st.error("Backend is not reachable — start the FastAPI server first")

st.divider()

# ── Question input + action buttons ─────────────────────────────────────────

question = st.text_input("Ask a question about your document", key="question")

col_search, col_generate = st.columns([1, 1])
with col_search:
    search_clicked = st.button("Search Chunks", type="secondary", use_container_width=True)
with col_generate:
    generate_clicked = st.button("Generate Answer", type="primary", use_container_width=True)

st.divider()

# ── Results area ─────────────────────────────────────────────────────────────

if search_clicked:
    question_text = question.strip()

    if not question_text:
        st.warning("Please type a question before searching.")
    else:
        with st.spinner("Searching for relevant chunks..."):
            try:
                results = retrieve_chunks(question_text)
            except RuntimeError as exc:
                st.error(str(exc))
                results = []

        if results:
            st.subheader(f"Top {len(results)} retrieved chunks")
            for i, chunk in enumerate(results, start=1):
                # Each chunk is shown as an expandable card.
                # The header shows rank, score, and location at a glance.
                header = (
                    f"#{i}  ·  score {chunk['score']:.4f}"
                    f"  ·  page {chunk['page']}"
                    f"  ·  {chunk['source']}"
                )
                with st.expander(header, expanded=(i == 1)):
                    st.markdown(f"**chunk index:** {chunk['chunk_index']}")
                    # Show the first 300 chars so the card stays readable.
                    preview = chunk["text"][:300]
                    if len(chunk["text"]) > 300:
                        preview += "…"
                    st.write(preview)
        else:
            st.info("No chunks returned. Try a different question or check that the document has been indexed.")

elif generate_clicked:
    question_text = question.strip()

    if not question_text:
        st.warning("Please type a question before generating.")
    else:
        with st.spinner("Generating answer — this may take up to 2 minutes on CPU…"):
            try:
                result = call_generate(question_text)
            except RuntimeError as exc:
                st.error(str(exc))
                result = None

        if result:
            st.subheader("Answer")
            st.info(result["answer"])

            # Show citations so the user knows which pages grounded the answer.
            # ref numbers match the [N] markers in the LLM's own answer text.
            # Each citation is collapsed by default — click to read the full chunk text.
            st.subheader("Sources")

            # Build a lookup from chunk_index → {text, score} so we can show
            # both in each expander without an extra API call.
            chunk_data_by_index = {
                c["chunk_index"]: {"text": c["text"], "score": c["score"]}
                for c in result["chunks"]
            }

            for cite in result["citations"]:
                data  = chunk_data_by_index.get(cite["chunk_index"], {})
                score = data.get("score")
                score_str = f"{score:.4f}" if score is not None else "n/a"
                label = (
                    f"[{cite['ref']}]  score {score_str}"
                    f"  ·  page {cite['page']}"
                    f"  ·  chunk {cite['chunk_index']}"
                    f"  ·  {cite['source']}"
                )
                with st.expander(label, expanded=False):
                    st.write(data.get("text", ""))

else:
    st.caption(
        "Type a question above. "
        "Use **Search Chunks** to see matching passages, "
        "or **Generate Answer** to get an LLM-generated response with citations."
    )
