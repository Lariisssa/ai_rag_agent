ROUTING_SYSTEM = "You decide if a user’s question is best answered from the user’s uploaded PDFs or via web search."

DECISION_PROMPT = (
    "Task: Decide if the provided 3 pages collectively answer the question.\n"
    "Output strict JSON:\n"
    "{\n  \"answerable\": true,\n  \"rationale\": \"short reason\",\n  \"key_spans\": [{\"doc_title\":\"...\", \"page\": 12, \"quote\": \"...\" }],\n  \"missing_info\": \"what is missing if any\"\n}\n"
)

GROUNDED_SYNTHESIS_PROMPT = (
    "Provide a concise, direct answer grounded in the cited pages. If user asked for images, include any page images relevant (we have URLs). Use the format:\n"
    "Body (markdown allowed).\n"
    "Citations: (Doc: \"<title>\", p.<page_number>) inline where claims are made.\n"
    "If pages conflict, mention uncertainty briefly.\n"
    "If also using web, append a short ‘From the web:’ section with bullet points + linked titles."
)

REWRITE_QUERY_PROMPT = """Dada a seguinte conversa, reescreva a última pergunta do usuário para que seja uma pergunta independente que possa ser entendida sem o contexto anterior. Retorne apenas a pergunta reescrita, sem nenhum outro texto. Se a última pergunta já for independente, apenas a retorne como está.

Histórico da Conversa:
{history}

Pergunta Independente:"""
