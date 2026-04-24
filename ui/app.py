import httpx
import streamlit as st

# The backend base URL. Later this will come from an env variable.
BACKEND_URL = "http://localhost:8000"


def check_backend_health() -> bool:
    """Return True if the FastAPI backend is reachable and healthy."""
    try:
        response = httpx.get(f"{BACKEND_URL}/health/live", timeout=3)
        return response.status_code == 200
    except httpx.RequestError:
        return False


# ── Page layout ──────────────────────────────────────────────────────────────

st.title("RAG Pipeline")

# Show backend status at the top so it is always visible.
if check_backend_health():
    st.success("Backend is running")
else:
    st.error("Backend is not reachable — start the FastAPI server first")

st.divider()

# Question input — we will wire this up in Step 9.
st.text_input("Ask a question about your document", key="question", disabled=False)

# Placeholder for the answer area — will be filled in later steps.
st.caption("Answers will appear here once retrieval and generation are connected.")
