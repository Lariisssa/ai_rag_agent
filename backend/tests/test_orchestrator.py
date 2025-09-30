
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock

# Mock the schema and llm_client before other imports
from app.schemas import ChatMessage
from app.services.orchestrator import rewrite_query_with_history

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.mark.parametrize(
    "history, mock_llm_response, expected_query",
    [
        # Case 1: Simple follow-up question
        (
            [
                ChatMessage(role="user", content="Qual o valor da segunda rodada de investimentos?"),
                ChatMessage(role="assistant", content="O valor é de R$ 10.000."),
                ChatMessage(role="user", content="e quando ela vai ocorrer?"),
            ],
            "Quando a segunda rodada de investimentos de R$ 10.000 vai ocorrer?",
            "Quando a segunda rodada de investimentos de R$ 10.000 vai ocorrer?",
        ),
        # Case 2: Question is already standalone
        (
            [
                ChatMessage(role="user", content="Qual a capital da França?"),
                ChatMessage(role="assistant", content="Paris."),
                ChatMessage(role="user", content="Qual a população de Paris?"),
            ],
            "Qual a população de Paris?",
            "Qual a população de Paris?",
        ),
        # Case 3: History is too short to need rewriting
        (
            [
                ChatMessage(role="user", content="Olá!"),
            ],
            "", # LLM should not be called
            "Olá!",
        ),
    ],
)
async def test_rewrite_query_with_history(history, mock_llm_response, expected_query):
    """
    Tests the rewrite_query_with_history function with various scenarios.
    """
    # We patch the llm_client used inside the orchestrator module
    with patch("app.services.orchestrator.llm_client", new_callable=MagicMock) as mock_llm_client:
        # Configure the mock's async chat method
        mock_llm_client.chat.return_value = mock_llm_response

        # Call the function
        rewritten_query = await rewrite_query_with_history(history)

        # Assertions
        assert rewritten_query == expected_query

        # Check if LLM was called when expected
        if len(history) > 1:
            mock_llm_client.chat.assert_called_once()
        else:
            mock_llm_client.chat.assert_not_called()

