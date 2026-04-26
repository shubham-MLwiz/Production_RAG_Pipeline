import httpx
import streamlit as st

# The backend base URL. Later this will come from an env variable.
BACKEND_URL = "http://localhost:8000"

# How many chunks to retrieve from the backend.
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


# ── Page layout ──────────────────────────────────────────────────────────────

st.title("RAG Pipeline")

# Show backend status at the top so it is always visible.
if check_backend_health():
    st.success("Backend is running")
else:
    st.error("Backend is not reachable — start the FastAPI server first")

st.divider()

# ── Question input + search button ───────────────────────────────────────────

question = st.text_input("Ask a question about your document", key="question")
search_clicked = st.button("Search", type="primary")

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
                    # The full text is visible in the notebook / API.
                    preview = chunk["text"][:300]
                    if len(chunk["text"]) > 300:
                        preview += "…"
                    st.write(preview)
        else:
            st.info("No chunks returned. Try a different question or check that the document has been indexed.")
else:
    st.caption("Type a question above and click **Search** to see the most relevant passages from your document.")
