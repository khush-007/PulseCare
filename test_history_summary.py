
import asyncio
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

from backend.app.chatbot.memory.history import _summarize_older_turns


async def main():
    messages = [
        SimpleNamespace(
            role="user",
            content="I have had a headache for three days.",
        ),
        SimpleNamespace(
            role="assistant",
            content="When does it get worse?",
        ),
        SimpleNamespace(
            role="user",
            content="It gets worse at night. I also feel dizzy.",
        ),
    ]

    # Test 1: LLM summarization
    with patch(
        "backend.app.chatbot.memory.history.generate_completion",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = (
            "The user reports a three-day headache, "
            "worse at night, and occasional dizziness."
        )

        summary = await _summarize_older_turns(messages)

        assert "three-day headache" in summary
        assert "dizziness" in summary
        mock_llm.assert_awaited_once()

        print("PASS: LLM summary returned correctly.")
        print(summary)

    # Test 2: Fallback if the LLM fails
    with patch(
        "backend.app.chatbot.memory.history.generate_completion",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.side_effect = RuntimeError("Simulated provider failure")

        fallback = await _summarize_older_turns(messages)

        assert "Earlier conversation excerpts" in fallback
        assert "headache" in fallback

        print("\nPASS: Fallback works when the LLM fails.")
        print(fallback)


if __name__ == "__main__":
    asyncio.run(main())

