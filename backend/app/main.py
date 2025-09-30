from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .logging_setup import setup_logging
from .routes import documents, chat

setup_logging(settings.log_level)
app = FastAPI(title="RAG PDF/Web QA MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve media files in dev
app.mount("/media", StaticFiles(directory=settings.media_root), name="media")

@app.get("/api/healthz")
async def healthz():
    return {"ok": True}

app.include_router(documents.router)
app.include_router(chat.router)
