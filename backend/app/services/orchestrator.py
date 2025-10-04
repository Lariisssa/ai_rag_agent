from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from .llm import llm_client
from .ranking import ann_search_pages
from ..prompts import DECISION_PROMPT, GROUNDED_SYNTHESIS_PROMPT, REWRITE_QUERY_PROMPT
from ..schemas import ChatMessage as Message
from ..agents.reranker import semantic_reranker
import structlog
import re

log = structlog.get_logger(__name__)

def build_multimodal_content(text: str, images: List[Dict[str, Any]]) -> Any:
    """
    Build multimodal content for GPT-4o.
    If images are present, returns a list with text + image_url parts.
    Otherwise, returns simple text string.
    """
    if not images:
        return text

    # Build multimodal content array
    content_parts = [{"type": "text", "text": text}]

    # Add up to 5 images (GPT-4o limit per message)
    import base64
    from ..config import settings
    import os

    for img in images[:5]:
        try:
            # Read image file and convert to base64
            file_path = os.path.join(settings.media_root, os.path.basename(img['file_url']))
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Use data URL format (works with OpenAI API)
            data_url = f"data:image/jpeg;base64,{image_data}"
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": data_url, "detail": "auto"}
            })
        except Exception as e:
            log.warning("failed_to_load_image", file_url=img.get('file_url'), error=str(e))
            continue

    return content_parts

async def rewrite_query_with_history(messages: List[Message]) -> str:
    """
    Uses an LLM to rewrite the user's last question to be self-contained,
    using the conversation history as context.
    """
    if not messages:
        return ""

    # Keep the history concise, e.g., last 5 messages
    history = messages[-5:]
    last_user_message = next((m.content for m in reversed(history) if m.role == 'user'), "")

    if len(history) <= 1:
        return last_user_message

    # Format history for the prompt
    formatted_history = "\n".join([f"{m.role}: {m.content}" for m in history])

    prompt = REWRITE_QUERY_PROMPT.format(history=formatted_history)

    log.info("rewrite_query_prompt", prompt=prompt)
    try:
        rewritten_query = await llm_client.chat('gpt-5', [
            {"role": "user", "content": prompt}
        ], temperature=0.0)
        
        # Clean up the response, LLM might add quotes
        rewritten_query = rewritten_query.strip().strip('\"')

        log.info("rewrite_query_result", original=last_user_message, rewritten=rewritten_query)
        # As a safeguard, if the rewritten query is empty, fall back to the original.
        if not rewritten_query:
             return last_user_message
        return rewritten_query
    except Exception as e:
        log.warning("rewrite_query_failed", error=str(e))
        return last_user_message # Fallback to the original query on error

async def route_decision(query: str, doc_ids: Optional[List[str]], force_web: bool) -> Dict[str, Any]:
    if force_web:
        return {"use_docs": False, "use_web": True, "doc_ids": doc_ids or [], "reason": "force_web"}
    # Heuristic bias to docs if any provided
    use_docs = bool(doc_ids)
    return {"use_docs": use_docs, "use_web": not use_docs, "doc_ids": doc_ids or [], "reason": "heuristic"}

async def fetch_pages_basic(db: AsyncSession, doc_ids: Optional[List[str]], limit: int = 12) -> List[Dict[str, Any]]:
    # Fallback when no embeddings: grab first pages
    params: Dict[str, Any] = {"limit": limit}
    where = "1=1"
    if doc_ids:
        # Let asyncpg adapt Python list to uuid[] for ANY(:doc_ids)
        where += " AND dp.document_id = ANY(:doc_ids)"
        params["doc_ids"] = doc_ids
    sql = text(
        """
        SELECT dp.id, dp.document_id, dp.page_number, coalesce(dp.content,'') AS content, d.title
        FROM document_pages dp
        JOIN documents d ON d.id = dp.document_id
        WHERE {where}
        ORDER BY dp.page_number ASC
        LIMIT :limit
        """.format(where=where)
    )
    res = await db.execute(sql, params)
    rows = res.mappings().all()
    log.info("fetch_pages_basic_result", limit=limit, doc_ids=doc_ids or [], count=len(rows))
    out: List[Dict[str, Any]] = []
    for r in rows:
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
            "similarity": 0.0,
            "images": images,
        })
    return out

async def decision_on_candidates(query: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Compose prompt context
    snippets = "\n\n".join([f"Doc: {c['title']} p.{c['page_number']}\n{(c['content'] or '')[:1500]}" for c in candidates])
    user = f"Question: {query}\n\nPages:\n{snippets}\n\n{DECISION_PROMPT}"
    log.info("decision_prompt", user=user)
    try:
        resp = await llm_client.chat('gpt-5', [{"role":"user","content": user}], temperature=0.0)
        log.info("decision_response_raw", resp=resp)
        # Best-effort parse JSON
        import json
        data = json.loads(resp)
    except Exception:
        data = {"answerable": True, "rationale": "fallback", "key_spans": [], "missing_info": ""}
    log.info("decision_parsed", data=data)
    return data

async def synthesize_answer(query: str, used: List[Dict[str, Any]], web_items: Optional[List[Dict[str, Any]]] = None) -> str:
    # Prefer concise, grounded synthesis with bracket citations [n].
    # Build compact, deduped context with numbered sources and query-focused excerpts.
    if not used and not web_items:
        return "Não encontrei trechos relevantes para responder com base nos documentos fornecidos."

    # Prepare numbered sources for citations
    import re
    numbered: List[Dict[str, Any]] = []
    lines: List[str] = []

    # Generic focus: currency-like patterns + tokens from the user's query
    # Examples covered: "R$ 500.000,00", "R$ 2 milhões", "500 mil", "2 mi", "1,5 milhão"
    currency_re = re.compile(
        r"(R\$\s?\d[\d\.,]*\s*(mil|milh(?:ã|a)o(?:es)?|mi|m|bilh(?:ã|a)o(?:es)?|bi)?)|("
        r"\b\d+[\.,]\d{3}[\.,]\d{2}\b)|("  # numbers like 1.234,56
        r"\b\d+(?:[\.,]\d+)?\s*(mil|milh(?:ã|a)o(?:es)?|mi|m|bilh(?:ã|a)o(?:es)?|bi)\b)",
        re.IGNORECASE,
    )

    def make_excerpt(text: str, window: int = 500, max_len: int = 1800) -> str:
        t = (text or "").strip()
        if not t:
            return ""
        t_low = t.lower()
        hits = []
        # currency/number hits
        for m in currency_re.finditer(t):
            hits.append(m.start())
        # Also check query terms tokens
        for token in re.findall(r"\w+", query.lower()):
            if len(token) < 3:
                continue
            i = t_low.find(token)
            if i != -1:
                hits.append(i)
        if not hits:
            return t[:max_len]
        hits = sorted(set(hits))[:6]
        chunks = []
        for pos in hits:
            start = max(0, pos - window)
            end = min(len(t), pos + window)
            chunk = t[start:end]
            # add ellipses when cutting
            prefix = "…" if start > 0 else ""
            suffix = "…" if end < len(t) else ""
            chunks.append(prefix + chunk + suffix)
            if sum(len(c) for c in chunks) >= max_len:
                break
        excerpt = " \n…\n ".join(chunks)
        return excerpt[: max_len]

    raw_sources: List[Dict[str, Any]] = []
    for idx, c in enumerate(used, start=1):
        content = c.get("content") or ""
        excerpt = make_excerpt(content)
        title = c.get("title") or ""
        page = c.get("page_number")
        numbered.append({"n": idx, **c})
        lines.append(f"[{idx}] {title} (p.{page}):\n{excerpt}")
        raw_sources.append({"n": idx, "title": title, "page": page, "content": content})
    context = "\n\n".join(lines)

    # Removed query-specific numeric candidate hints to keep prompts pure RAG.

    sys = (
        "Você é um assistente que responde SOMENTE com base nos trechos e imagens fornecidos. "
        "Responda em português, de forma direta e concisa. "
        "IMPORTANTE: Se imagens foram fornecidas junto com os trechos, você DEVE analisá-las para responder a pergunta. "
        "Extraia informações EXATAMENTE como aparecem (números, valores, nomes, logos, gráficos). "
        "Use citações em colchetes [n] correspondendo às fontes listadas. "
        "Se a informação não estiver nos trechos OU nas imagens, diga que não foi encontrado."
    )
    user = (
        f"Pergunta: {query}\n\n"
        + f"Fontes textuais (use [n] nas citações):\n{context}\n\n"
        + "Escreva a resposta final de forma objetiva, incluindo informação das imagens se disponíveis."
    )
    log.info(
        "synth_prompts",
        system=sys,
        user=user,
        candidates_count=0,
        context_chars=len(context),
    )

    try:
        # Check if query is asking for visual/image content
        visual_keywords = ['logo', 'imagem', 'figura', 'gráfico', 'grafico', 'foto', 'desenho', 'ilustração', 'ilustracao', 'visual', 'aparência', 'aparencia']
        is_visual_query = any(keyword in query.lower() for keyword in visual_keywords)

        # Collect all images from used sources for multimodal synthesis (only if visual query)
        all_images = []
        if is_visual_query:
            for c in used:
                if c.get("images"):
                    all_images.extend(c["images"])

        # Build multimodal user content if images are available
        user_content = build_multimodal_content(user, all_images)

        answer = await llm_client.chat('gpt-5', [
            {"role": "system", "content": sys},
            {"role": "user", "content": user_content},
        ], temperature=0.0)

        # Append images as markdown ONLY if it's a visual query and model likely referenced them
        if all_images and is_visual_query:
            answer += "\n\n**Imagens relevantes:**\n\n"
            for img in all_images:
                answer += f"![Imagem da fonte]({img['file_url']})\n\n"

        log.info("synth_answer", answer=answer, images_sent=len(all_images), is_visual_query=is_visual_query)
    except Exception:
        # Fallback to a simple draft if LLM fails
        body = []
        for c in used:
            body.append(f"(Doc: \"{c['title']}\", p.{c['page_number']}) {((c['content'] or '')[:300]).strip()}")
        answer = f"Answer (draft) to: {query}\n\n" + "\n\n".join(body)
        if web_items:
            answer += "\n\nFrom the web:\n" + "\n".join([f"- [{w['title']}]({w['url']}) — {w['snippet']}" for w in web_items])
        log.info("synth_answer_fallback", answer=answer)
    return answer

async def synthesize_answer_structured(query: str, used: List[Dict[str, Any]], web_items: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Ask the LLM to return a strict JSON control object:
    {"code":1, "text":"..."} -> answer found using provided sources
    {"code":2} -> not found in these sources; try next batch
    {"code":3} -> not found in docs; consider web
    """
    import re, json
    # Build numbered sources and concise excerpts (reuse logic similar to synthesize_answer)
    def make_excerpt(text: str, window: int = 400, max_len: int = 1400) -> str:
        t = (text or "").strip()
        if not t:
            return ""
        # simple centered slice around first query token hit
        t_low = t.lower()
        pos = -1
        for token in re.findall(r"\w+", query.lower()):
            if len(token) < 3:
                continue
            pos = t_low.find(token)
            if pos != -1:
                break
        if pos == -1:
            return t[:max_len]
        start = max(0, pos - window)
        end = min(len(t), pos + window)
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(t) else ""
        return (prefix + t[start:end] + suffix)[:max_len]

    lines: List[str] = []
    for idx, c in enumerate(used, start=1):
        content = c.get("content") or ""
        excerpt = make_excerpt(content)
        title = c.get("title") or ""
        page = c.get("page_number")
        lines.append(f"[{idx}] {title} (p.{page}):\n{excerpt}")
    context = "\n\n".join(lines)

    sys = (
        "Você é um assistente que responde SOMENTE com base nos trechos fornecidos. "
        "Responda em português, de forma direta e concisa. "
        "USE APENAS as fontes fornecidas. Sempre que possível, inclua citações [n]. "
        "Retorne APENAS um JSON mínimo, sem markdown, exatamente em um destes formatos: "
        "{\"code\":1,\"text\":\"RESPOSTA AQUI\"} ou {\"code\":2} ou {\"code\":3}. "
        "code=1 significa que você encontrou a resposta com base nas fontes. "
        "code=2 significa que não encontrou a resposta nestes trechos e precisa de mais páginas. "
        "code=3 significa que não encontrou nos documentos e talvez precise buscar na web."
    )
    user = (
        f"Pergunta: {query}\n\n"
        + (f"Fontes (use [n] nas citações):\n{context}\n\n" if used else "")
        + ("Use também os itens da web, se fornecidos.\n\n" if web_items else "")
        + "Responda APENAS com um JSON em uma única linha, sem comentários, sem explicações."
    )
    try:
        answer = await llm_client.chat('gpt-5', [
            {"role": "system", "content": sys},
            {"role": "user", "content": user},
        ], temperature=0.0)
        log.info("synth_structured_answer_raw", answer=answer)
        data = json.loads(answer)
        # normalize
        code = int(data.get("code", 2))
        text = data.get("text") if code == 1 else None
        return {"code": code, "text": text}
    except Exception as e:
        log.warning("synth_structured_parse_fail", error=str(e))
        return {"code": 2}

async def orchestrate_chat(db: AsyncSession, messages: List[Message], doc_ids: Optional[List[str]], force_web: bool) -> Tuple[List[str], Dict[str, Any]]:
    # Returns token chunks and final envelope

    # Rewrite query with conversation history for better context
    query = await rewrite_query_with_history(messages)
    log.info("orchestrate_chat_query", original_messages_count=len(messages), rewritten_query=query)

    routing = await route_decision(query, doc_ids, force_web)
    sources: List[Dict[str, Any]] = []
    web_items: List[Dict[str, Any]] = []

    if routing["use_docs"]:
        # Try embeddings route first; if empty or wrong dim, fallback to basic fetch
        try:
            qvec = (await llm_client.embed([query]))[0]
            if isinstance(qvec, list) and len(qvec) == 3072:
                candidates = await ann_search_pages(db, qvec, doc_ids=doc_ids, limit=30)
            else:
                candidates = await fetch_pages_basic(db, doc_ids, limit=30)
        except Exception:
            candidates = await fetch_pages_basic(db, doc_ids, limit=30)

        # Deduplicate by (document_id, page_number) and keep top by similarity then lower page number
        seen = set()
        deduped: List[Dict[str, Any]] = []
        for c in candidates:
            key = (c.get("document_id"), c.get("page_number"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(c)
        deduped.sort(key=lambda x: (-(x.get("similarity", 0.0)), x.get("page_number", 0)))

        # Apply semantic re-ranking for better relevance
        log.info("applying_semantic_reranking", candidate_count=len(deduped))
        deduped = await semantic_reranker.rerank(query, deduped, top_k=15)

        # Pre-populate sources with the best candidates *before* the structured decision loop.
        # This ensures that if the loop fails to get a code:1, we still have the top documents for final synthesis.
        max_pages = 15
        batch_size = 3
        pool = deduped[:max_pages]
        sources = pool  # Use the top candidates as the default source list

        accepted_answer: Optional[str] = None
        for i in range(0, len(pool), batch_size):
            batch = pool[i:i+batch_size]
            if not batch:
                break
            log.info("batch_try", index=i//batch_size, size=len(batch))
            decision = await synthesize_answer_structured(query, batch, None)
            log.info("batch_structured_decision", index=i//batch_size, decision=decision)
            code = int(decision.get("code", 2))
            if code == 1 and decision.get("text"):
                # If LLM accepts a batch, override sources to be just that batch
                sources = batch
                accepted_answer = str(decision["text"])
                break
            if code == 3:
                # Early exit to web, but `sources` still holds the top candidates
                break
        if sources:
            log.info(
                "retrieval_sources",
                count=len(sources),
                items=[{"doc_id": s.get("document_id"), "title": s.get("title"), "page": s.get("page_number"), "similarity": s.get("similarity")} for s in sources],
            )

    if routing.get("use_web"):
        from .web_search import get_provider
        provider = await get_provider()
        web_items = await provider.search(query)

    # Synthesis
    if routing["use_docs"] and sources:
        # If we already accepted a batch answer during the doc loop, reuse it
        answer_text = accepted_answer if 'accepted_answer' in locals() and accepted_answer is not None else await synthesize_answer(query, sources, None)
    elif routing.get("use_web") and not sources:
        # Use web-only synthesis when no doc batch succeeded
        answer_text = await synthesize_answer(query, [], web_items if web_items else None)
    else:
        answer_text = "Não encontrei trechos relevantes para responder com base nos documentos fornecidos."
    tokens = answer_text.split()
    # Final envelope
    citations = []
    for s in sources:
        citations.append({
            "kind": "doc",
            "doc_id": s.get("document_id", ""),
            "title": s.get("title", ""),
            "page": s.get("page_number", 0),
        })
    for w in web_items:
        citations.append({
            "kind": "web",
            "url": w.get("url", ""),
            "title": w.get("title", ""),
        })
    final_env = {
        "citations": citations,
        "sources": {
            "type": "doc" if sources else "web",
            "items": [
                {
                    "doc_id": s["document_id"],
                    "title": s["title"],
                    "page": s["page_number"],
                    "similarity": s.get("similarity", 0.0),
                    "snippet": (s.get("content") or "")[:200],
                    "images": s.get("images", []),
                } for s in sources
            ] if sources else web_items
        }
    }
    return tokens, final_env
