from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from .config import settings
from .logging_setup import setup_logging
from .routes import documents, chat
from .middleware import RateLimitMiddleware, ErrorHandlerMiddleware, RequestLoggingMiddleware

setup_logging(settings.log_level)
app = FastAPI(
    title="RAG PDF/Web QA MVP",
    description="A production-ready RAG system for answering questions from PDFs and web search",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    """Test database connection on startup"""
    from .db import engine
    import structlog
    log = structlog.get_logger()

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        log.info("database_connection_ok")
    except Exception as e:
        log.warning("database_connection_failed_on_startup", error=str(e))
        # Don't raise - allow app to start and retry connections lazily

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    from .db import engine
    await engine.dispose()

# Add custom middlewares (order matters - first added = outermost layer)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_window=settings.rate_limit_per_5min,
    window_seconds=300,
)

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
