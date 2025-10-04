
import os
import pytest
import httpx
import json
from typing import List, Dict, Any

from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

# Golden Dataset based on plano_negocios.pdf
golden_dataset = [
    {
        "input": "Qual é o investimento inicial disponível para o negócio?",
        "expected_output": "O capital inicial disponível é de R$ 15.000.",
    },
    {
        "input": "Qual é a margem de lucro desejada sobre o preço de venda?",
        "expected_output": "A margem de lucro desejada é de 30% sobre o preço de venda.",
    },
    {
        "input": "Quanto é preciso vender por mês para atingir o ponto de equilíbrio?",
        "expected_output": "Para atingir o ponto de equilíbrio, a padaria precisa vender aproximadamente 362 produtos por mês, o que corresponde a uma receita de cerca de R$ 5.428,57.",
    },
    {
        "input": "Qual o custo estimado para um forno de convecção?",
        "expected_output": "O preço estimado para um forno de convecção ou turbo varia de R$ 3.000 a R$ 8.000.",
    },
    {
        "input": "Uma rodada de investimento futura é mencionada? Qual o valor?",
        "expected_output": "Sim, uma rodada de investimento futura de R$ 10.000 em 3 meses é mencionada como uma possibilidade para expandir o negócio.",
    },
    {
        "input": "Quais são os custos fixos mensais totais?",
        "expected_output": "O total de custos fixos mensais é de R$ 3.800, sendo R$ 800 de aluguel e R$ 3.000 de salários para duas pessoas.",
    },
    {
        "input": "Quantos funcionários são necessários e qual o custo total de salários?",
        "expected_output": "São necessários 2 funcionários (incluindo o proprietário) com um custo total de salários de R$ 3.000 por mês.",
    },
    {
        "input": "Qual o valor do aluguel mensal?",
        "expected_output": "O aluguel mensal é de R$ 800.",
    },
    {
        "input": "Qual é o preço de venda médio de cada produto?",
        "expected_output": "O preço médio de venda de cada produto é de R$ 15.",
    },
    {
        "input": "Qual o custo variável por unidade?",
        "expected_output": "O custo variável por unidade é de R$ 10,50.",
    },
]

async def get_rag_response(query: str, document_id: str) -> Dict[str, Any]:
    """Calls the local RAG API and parses the SSE response."""
    full_response_text = ""
    retrieval_context = []
    final_env = {}

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "POST",
                "http://localhost:8080/api/chat",
                json={
                    "messages": [{"role": "user", "content": query}],
                    "document_ids": [document_id],
                },
                timeout=120,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[len("data:") :].strip()
                        try:
                            # Try to parse as JSON
                            parsed_data = json.loads(data_str)
                            # Check if it's the final envelope object, not just any JSON (like a number)
                            if isinstance(parsed_data, dict) and ("citations" in parsed_data or "sources" in parsed_data):
                                final_env = parsed_data
                                # Extract retrieval context from the 'sources' field
                                if "sources" in final_env and "items" in final_env["sources"]:
                                    retrieval_context = [str(item.get("content", "")) for item in final_env["sources"]["items"]]
                            else:
                                # It's a valid JSON but not the envelope (e.g., a number), treat as a token
                                full_response_text += data_str + " "
                        except json.JSONDecodeError:
                            # It's a plain text token
                            full_response_text += data_str + " "
        except httpx.RequestError as e:
            pytest.fail(f"API request failed: {e}. Ensure the backend server is running.")

    return {
        "actual_output": full_response_text.strip(),
        "retrieval_context": retrieval_context,
    }

# You need to upload the PDF first and get its ID.
# For this test, we'll assume it's the first document uploaded.
# In a real scenario, you might fetch this ID from an API endpoint.
# NOTE: The user must replace this with the actual document ID after uploading the PDF.
DOCUMENT_ID_TO_TEST = os.getenv("EVAL_DOCUMENT_ID", "d5e8b5e9-92b5-45f1-9459-80309451a328") # Placeholder

@pytest.mark.parametrize("test_case_data", golden_dataset)
async def test_rag_evaluation(test_case_data: dict):
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY environment variable not set. Skipping DeepEval tests.")

    # Get response from our RAG application
    rag_response = await get_rag_response(test_case_data["input"], DOCUMENT_ID_TO_TEST)

    # Create the test case for DeepEval
    test_case = LLMTestCase(
        input=test_case_data["input"],
        actual_output=rag_response["actual_output"],
        expected_output=test_case_data["expected_output"],
        retrieval_context=rag_response["retrieval_context"],
    )

    # Define the metrics for evaluation
    metrics = [
        AnswerRelevancyMetric(threshold=0.7),
        FaithfulnessMetric(threshold=0.7),
    ]

    # Run the evaluation
    assert_test(test_case, metrics)
