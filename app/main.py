from fastapi import FastAPI

# Create the FastAPI application instance.
# The `title` appears in the auto-generated docs at /docs.
app = FastAPI(title="RAG Pipeline API")


@app.get("/health/live")
def health_live():
    """Return a simple liveness signal."""
    return {"status": "ok"}
