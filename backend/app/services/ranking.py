from __future__ import annotations
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

log = structlog.get_logger(__name__)

# Helper: run ANN search using pgvector cosine distance (<=>)

async def ann_search_pages(
    db: AsyncSession,
    query_embedding: List[float],
    doc_ids: Optional[List[str]] = None,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    vec_str = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
    params: Dict[str, Any] = {"limit": limit, "qvec": vec_str}
    where = "dp.embedding IS NOT NULL"
    if doc_ids:
        where += " AND dp.document_id = ANY(:doc_ids)"
        params["doc_ids"] = doc_ids
    log.info("ann_search_params", limit=limit, has_doc_filter=bool(doc_ids))
    sql = text(
        f"""
        SELECT dp.id, dp.document_id, dp.page_number, coalesce(dp.content,'') AS content,
               d.title,
               (dp.embedding <=> CAST(:qvec AS vector)) AS distance
        FROM document_pages dp
        JOIN documents d ON d.id = dp.document_id
        WHERE {where}
        ORDER BY dp.embedding <=> CAST(:qvec AS vector), dp.page_number ASC
        LIMIT :limit
    """
    )
    res = await db.execute(sql, params)
    rows = res.mappings().all()
    out: List[Dict[str, Any]] = []
    log.info("ann_search_pages", count=len(rows))
    for r in rows:
        # WARNING: logs entire content as requested by user
        log.info("ann_row", doc_id=str(r["document_id"]), page=int(r["page_number"]), title=r["title"], content=r["content"])

        # Fetch images for this page
        page_id = r["id"]
        img_res = await db.execute(text(
            "SELECT id, file_url, position, dimensions FROM document_page_images WHERE document_page_id = :pid ORDER BY created_at ASC"
        ), {"pid": page_id})
        images = [
            {
                "id": str(img["id"]),
                "file_url": img["file_url"],
                "position": img["position"],
                "dimensions": img["dimensions"],
            }
            for img in img_res.mappings().all()
        ]

        out.append({
            "id": str(r["id"]),
            "document_id": str(r["document_id"]),
            "page_number": int(r["page_number"]),
            "content": r["content"],
            "title": r["title"],
            "similarity": 1.0 - float(r["distance"]) if r["distance"] is not None else 0.0,
            "images": images,
        })
    return out
