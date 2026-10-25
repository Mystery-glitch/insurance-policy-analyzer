"""
Insurance Policy Analyzer — FastAPI Application
=================================================
Entry point for the API server.
"""

import logging

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.upload import router as upload_router
from app.api.routes.analyze import router as analyze_router
from app.api.routes.ask import router as ask_router

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Insurance Policy Analyzer",
    description=(
        "AI-powered API that accepts insurance policy PDFs (scanned, unscanned, "
        "or hybrid), extracts their text, and produces plain-English analysis "
        "including summaries, coverage highlights, exclusions, and risk alerts."
    ),
    version="0.1.0",
)

# ── CORS — allow all origins during development ───────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────
app.include_router(upload_router, prefix="/api/v1", tags=["PDF Upload"])
app.include_router(analyze_router, prefix="/api/v1", tags=["Policy Analysis"])
app.include_router(ask_router, prefix="/api/v1", tags=["Q&A"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_banner():
    """Print clean, clickable URLs on startup."""
    logger.info("=" * 55)
    logger.info("  🚀 InsureClear is running!")
    logger.info("  👉 On this Mac: http://localhost:8000")
    logger.info("  👉 On other devices: http://192.168.1.21:8000")
    logger.info("  👉 API Docs: http://localhost:8000/docs")
    logger.info("=" * 55)


# ── Serve Frontend SPA ────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

@app.get("/", include_in_schema=False)
async def serve_index():
    """Explicitly serve the index.html on root requests."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Frontend not found"}


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
