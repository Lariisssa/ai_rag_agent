from __future__ import annotations
import io
import os
import uuid
from typing import List, Tuple
from fastapi import UploadFile
import fitz  # PyMuPDF
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..config import settings
from .llm import llm_client
import structlog

log = structlog.get_logger()

# Notes:
# - We store images as JPG files under MEDIA_ROOT with UUID filenames.
# - We extract per-page text; if empty, we still create the page row, but skip embedding.
# - Embeddings are deferred (stubbed) to keep pipeline fast; hook left below.

async def ensure_media_dirs() -> None:
    os.makedirs(settings.media_root, exist_ok=True)

async def save_image_jpg(pix: fitz.Pixmap) -> Tuple[str, dict]:
    # Convert to RGB if needed
    if pix.n > 3:  # has alpha
        pix = fitz.Pixmap(fitz.csRGB, pix)

    # PyMuPDF API: tobytes() for format, then use PIL for quality control
    from PIL import Image
    import io

    # Get raw bytes in PPM format (lossless)
    img_bytes = pix.tobytes("ppm")
    # Use PIL to save as JPEG with quality
    img = Image.open(io.BytesIO(img_bytes))

    name = f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(settings.media_root, name)
    img.save(path, "JPEG", quality=85)

    # Return file url path mounted at /media
    return f"/media/{name}", {"width": pix.width, "height": pix.height}

async def ingest_pdf(db: AsyncSession, file: UploadFile) -> dict:
    await ensure_media_dirs()
    # Read file into memory (25MB cap should be enforced by request size elsewhere)
    data = await file.read()
    title = file.filename or "untitled.pdf"
    log.info("ingest_start", filename=title, size=len(data))
    try:
        doc = fitz.open(stream=io.BytesIO(data), filetype="pdf")
    except Exception as e:
        log.error("pdf_open_error", filename=title, error=str(e))
        raise

    # Insert document row
    res = await db.execute(text("""
        INSERT INTO documents (title, page_count) VALUES (:title, :page_count)
        RETURNING id
    """), {"title": title, "page_count": doc.page_count})
    doc_id = res.scalar_one()
    log.info("doc_inserted", document_id=str(doc_id), page_count=doc.page_count)

    # Iterate pages (collect for embeddings)
    page_rows: List[tuple[str, str | None]] = []  # (page_id, text)
    for pno in range(doc.page_count):
        page = doc.load_page(pno)
        text_content = page.get_text("text") or None
        # Insert page row first (embedding NULL for now)
        res = await db.execute(text("""
            INSERT INTO document_pages (document_id, page_number, content)
            VALUES (:doc_id, :page_number, :content)
            RETURNING id
        """), {"doc_id": doc_id, "page_number": pno + 1, "content": text_content})
        page_id = res.scalar_one()
        page_rows.append((str(page_id), text_content))
        if (pno + 1) % 25 == 0 or pno == 0:
            log.info("page_inserted", page_number=pno + 1, page_id=str(page_id))

        # Extract images
        try:
            for img in page.get_images(full=True):
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                except Exception as e:
                    log.warning("image_pixmap_error", page_number=pno + 1, error=str(e))
                    continue
                try:
                    file_url, dims = await save_image_jpg(pix)
                except Exception as e:
                    log.error("image_write_error", page_number=pno + 1, error=str(e))
                    continue
                import json
                await db.execute(text("""
                    INSERT INTO document_page_images (document_page_id, position, file_url, dimensions)
                    VALUES (:page_id, :position, :file_url, CAST(:dimensions AS jsonb))
                """), {"page_id": page_id, "position": None, "file_url": file_url, "dimensions": json.dumps(dims)})
        except Exception as e:
            log.error("image_extract_error", page_number=pno + 1, error=str(e))

    # Generate embeddings in batch (skip empty texts). If API key missing, this will produce small vectors; we only write if dim==3072
    texts: List[str] = []
    ids: List[str] = []
    for pid, t in page_rows:
        if t and t.strip():
            ids.append(pid)
            texts.append(t[:6000])  # guard tokenization, simple cut
    if texts:
        try:
            embs = await llm_client.embed(texts)
            # Persist embeddings; accept shorter dims by zero-padding up to 3072.
            for pid, vec in zip(ids, embs):
                if not isinstance(vec, list):
                    log.warning("embed_vec_invalid", page_id=pid, type=str(type(vec)))
                    continue
                dim = len(vec)
                if dim == 0:
                    log.warning("embed_vec_empty", page_id=pid)
                    continue
                if dim < 3072:
                    log.info("embed_vec_pad", page_id=pid, dim=dim, target=3072)
                    vec = vec + [0.0] * (3072 - dim)
                elif dim > 3072:
                    log.info("embed_vec_truncate", page_id=pid, dim=dim, target=3072)
                    vec = vec[:3072]
                # Now exactly 3072; send as string parameter and cast to vector
                vec_str = "[" + ",".join(str(float(x)) for x in vec) + "]"
                try:
                    await db.execute(text(
                        "UPDATE document_pages SET embedding = CAST(:vec AS vector) WHERE id = :pid"
                    ), {"pid": pid, "vec": vec_str})
                except Exception as e:
                    log.warning("embed_write_failed", page_id=pid, error=str(e))
        except Exception as e:
            # On failure, continue without embeddings
            log.warning("embed_failed", count=len(texts), error=str(e))

    await db.commit()
    log.info("ingest_complete", document_id=str(doc_id))
    return {"id": str(doc_id), "title": title, "page_count": doc.page_count}
