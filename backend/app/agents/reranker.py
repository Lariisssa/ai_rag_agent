"""Agente de re-ranking semântico usando LLM"""
from __future__ import annotations
from typing import List, Dict, Any
import structlog
from ..services.llm import llm_client

log = structlog.get_logger(__name__)

class SemanticReranker:
    """Re-rankeia chunks usando relevância semântica profunda via LLM"""

    async def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Re-rankeia chunks usando LLM para avaliar relevância semântica
        """
        if not chunks:
            return []

        # Limita chunks para análise (custo de API)
        chunks_to_analyze = chunks[:min(20, len(chunks))]

        # Pede ao LLM para ranquear
        ranked_indices = await self._llm_rank(query, chunks_to_analyze)

        if not ranked_indices:
            # Fallback para ordem original
            return chunks[:top_k]

        # Reorganiza chunks conforme ranking
        reranked = []
        for idx in ranked_indices[:top_k]:
            if 0 <= idx < len(chunks_to_analyze):
                reranked.append(chunks_to_analyze[idx])

        log.info("semantic_rerank",
                 original_count=len(chunks),
                 analyzed=len(chunks_to_analyze),
                 returned=len(reranked))

        return reranked

    async def _llm_rank(self, query: str, chunks: List[Dict[str, Any]]) -> List[int]:
        """Usa LLM para ranquear chunks por relevância"""

        # Monta lista compacta de chunks
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            title = chunk.get('title', '')
            page = chunk.get('page_number', 0)
            # Pega primeiras 300 chars do conteúdo
            content_preview = (chunk.get('content', '') or '')[:300]
            chunk_summaries.append(f"[{i}] {title} p.{page}: {content_preview}...")

        chunks_text = "\n\n".join(chunk_summaries)

        system_prompt = """Você é um especialista em ranquear trechos de documentos por relevância semântica.

Dada uma pergunta e uma lista de trechos numerados [0], [1], [2]..., retorne APENAS uma lista JSON com os índices dos trechos ordenados do MAIS relevante para o MENOS relevante.

IMPORTANTE:
- Considere relevância semântica, não apenas keywords
- Priorize trechos que respondem diretamente a pergunta
- Se a pergunta é sobre valores específicos, priorize trechos com números
- Retorne APENAS o JSON, sem explicações

Formato: [2, 0, 5, 1, ...]"""

        user_prompt = f"""Pergunta: {query}

Trechos para ranquear:
{chunks_text}

Retorne os índices ordenados por relevância (mais relevante primeiro):"""

        try:
            response = await llm_client.chat('gpt-5-mini', [  # Usa mini para economizar
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.0)

            log.info("rerank_llm_response", response=response)

            # Parse JSON
            import json
            # Limpa markdown se presente
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            response = response.strip()

            indices = json.loads(response)

            if isinstance(indices, list) and all(isinstance(x, int) for x in indices):
                return indices

            return []

        except Exception as e:
            log.error("rerank_failed", error=str(e))
            return []

semantic_reranker = SemanticReranker()
