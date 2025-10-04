from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import AsyncSessionLocal
from ..schemas import ChatRequest
from ..services.orchestrator import orchestrate_chat
import json

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat")
async def chat(req: ChatRequest):
    async def event_stream():
        # Create a dedicated DB session for the duration of the stream
        async with AsyncSessionLocal() as db:
            # Pass full message history to orchestrator for context-aware query rewriting
            tokens, env = await orchestrate_chat(db, messages=req.messages, doc_ids=req.document_ids, force_web=bool(req.force_web))
            # Stream tokens one by one
            for t in tokens:
                yield f"data: {t} \n\n"
            # Final envelope as JSON
            yield f"data: {json.dumps(env)}\n\n"
            yield "event: end\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
