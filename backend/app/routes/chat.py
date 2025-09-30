from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import AsyncSessionLocal
from ..schemas import ChatRequest
from ..services.orchestrator import orchestrate_chat, rewrite_query_with_history
import json

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat")
async def chat(req: ChatRequest):
    async def event_stream():
        # Create a dedicated DB session for the duration of the stream
        async with AsyncSessionLocal() as db:
            # Rewrite query with history before passing to orchestrator
            rewritten_query = await rewrite_query_with_history(req.messages)
            tokens, env = await orchestrate_chat(db, query=rewritten_query, doc_ids=req.document_ids, force_web=bool(req.force_web))
            # Stream tokens one by one
            for t in tokens:
                yield f"data: {t} \n\n"
            # Final envelope as JSON
            yield f"data: {json.dumps(env)}\n\n"
            yield "event: end\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
