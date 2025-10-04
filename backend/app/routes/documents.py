from __future__ import annotations
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..db import get_db
import structlog
from ..schemas import UploadResponse, DocumentOut
from ..services.ingestion import ingest_pdf

logger = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["documents"])

@router.get("/documents")
async def list_documents(limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db)):
    res = await db.execute(text(
        "SELECT id, title, page_count, created_at FROM documents ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    ), {"limit": limit, "offset": offset})
    rows = res.mappings().all()
    items = [
        {"id": str(r["id"]), "title": r["title"], "page_count": int(r["page_count"]), "created_at": r["created_at"].isoformat() if r["created_at"] else None}
        for r in rows
    ]
    return {"items": items, "limit": limit, "offset": offset}

@router.post("/documents", response_model=UploadResponse)
async def upload_documents(files: list[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    docs: list[DocumentOut] = []
    for f in files:
        # Accept common types; some browsers send application/octet-stream or omit
        if f.content_type not in ("application/pdf", "application/x-pdf", "application/octet-stream", ""):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {f.content_type}")
        try:
            # Size enforcement should be handled by server/client limits; UploadFile doesn't expose size reliably.
            meta = await ingest_pdf(db, f)
            docs.append(DocumentOut(id=meta["id"], title=meta["title"], page_count=meta["page_count"]))
        except Exception as e:
            logger.error("ingestion_failed", filename=f.filename, error=str(e))
            raise HTTPException(status_code=500, detail=f"Ingestion failed for {f.filename}: {e}")
    return UploadResponse(documents=docs)

@router.get("/documents/{doc_id}")
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(text("SELECT id, title, page_count FROM documents WHERE id = :id"), {"id": doc_id})
    row = res.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"id": str(row["id"]), "title": row["title"], "page_count": int(row["page_count"]) }

@router.get("/documents/{doc_id}/pages")
async def list_pages(doc_id: str, limit: int = 20, offset: int = 0, db: AsyncSession = Depends(get_db)):
    res = await db.execute(text(
        """
        SELECT dp.id, dp.page_number, left(coalesce(dp.content,''), 2000) AS content
        FROM document_pages dp
        WHERE dp.document_id = :doc_id
        ORDER BY dp.page_number ASC
        LIMIT :limit OFFSET :offset
        """
    ), {"doc_id": doc_id, "limit": limit, "offset": offset})
    pages = res.mappings().all()
    items = []
    for p in pages:
        img_res = await db.execute(text(
            "SELECT id, file_url, position, dimensions FROM document_page_images WHERE document_page_id = :pid ORDER BY created_at ASC"
        ), {"pid": p["id"]})
        imgs = [
            {
                "id": str(i["id"]),
                "file_url": i["file_url"],
                "position": i["position"],
                "dimensions": i["dimensions"],
            }
            for i in img_res.mappings().all()
        ]
        items.append({
            "id": str(p["id"]),
            "document_id": doc_id,
            "page_number": int(p["page_number"]),
            "content": p["content"],
            "images": imgs,
        })
    return {"items": items, "limit": limit, "offset": offset}

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Delete document and all its pages, embeddings, and images"""
    # Check if document exists
    res = await db.execute(text("SELECT id FROM documents WHERE id = :id"), {"id": doc_id})
    if not res.first():
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete in correct order (foreign keys):
    # 1. Images
    await db.execute(text(
        """
        DELETE FROM document_page_images
        WHERE document_page_id IN (
            SELECT id FROM document_pages WHERE document_id = :doc_id
        )
        """
    ), {"doc_id": doc_id})

    # 2. Pages (includes embeddings via CASCADE)
    await db.execute(text("DELETE FROM document_pages WHERE document_id = :doc_id"), {"doc_id": doc_id})

    # 3. Document itself
    await db.execute(text("DELETE FROM documents WHERE id = :id"), {"id": doc_id})

    await db.commit()
    logger.info("document_deleted", doc_id=doc_id)

    return {"ok": True, "deleted_id": doc_id}
