ROUTING_SYSTEM = "You decide if a user’s question is best answered from the user’s uploaded PDFs or via web search."

DECISION_PROMPT = (
    "Task: Decide if the provided 3 pages collectively answer the question.\n"
    "Output strict JSON:\n"
    "{\n  \"answerable\": true,\n  \"rationale\": \"short reason\",\n  \"key_spans\": [{\"doc_title\":\"...\", \"page\": 12, \"quote\": \"...\" }],\n  \"missing_info\": \"what is missing if any\"\n}\n"
)

GROUNDED_SYNTHESIS_PROMPT = (
    "You are an expert assistant that answers questions based ONLY on the provided sources.\n\n"
    "Instructions:\n"
    "1. Provide a direct, concise answer grounded EXCLUSIVELY in the cited sources\n"
    "2. Include inline citations [n] corresponding to source numbers\n"
    "3. Extract information EXACTLY as it appears in the source (preserve numbers, values, names, etc.)\n"
    "4. If sources conflict, acknowledge the discrepancy\n"
    "5. If the answer is not found in the sources, explicitly state 'Not found in the provided documents'\n"
    "6. If user asked for images and images are available, reference them\n"
    "7. Use markdown for formatting when appropriate\n\n"
    "Format: <answer with [n] citations>\n"
    "If web sources are also used, append: 'Web sources: <bullet list>'"
)

REWRITE_QUERY_PROMPT = """Dada a seguinte conversa, reescreva a última pergunta do usuário para que seja uma pergunta independente que possa ser entendida sem o contexto anterior. Retorne apenas a pergunta reescrita, sem nenhum outro texto. Se a última pergunta já for independente, apenas a retorne como está.

Histórico da Conversa:
{history}

Pergunta Independente:"""
