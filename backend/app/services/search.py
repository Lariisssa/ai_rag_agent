from __future__ import annotations
from typing import List, Dict, Any

# Placeholder ranking service; will be replaced with pgvector ANN queries.

async def rank_pages(query_embedding: list[float], pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Trivial similarity placeholder
    ranked = sorted(pages, key=lambda p: (p.get('page_number', 0)))
    return ranked[:6]


def two_round_decision(pages: List[Dict[str, Any]]):
    # Return first 3 then next 3
    first = pages[:3]
    second = pages[3:6]
    return first, second
