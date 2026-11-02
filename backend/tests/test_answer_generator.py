import pytest

from backend.app.chatbot.graph.nodes import answer_generator


@pytest.mark.asyncio
async def test_health_answer_receives_history_and_evidence_separately(monkeypatch):
    captured = {}

    async def generate(**kwargs):
        captured.update(kwargs)
        return "Blood pressure is the force of blood against artery walls."

    monkeypatch.setattr(answer_generator, "generate_completion", generate)
    result = await answer_generator.answer_generator_node({
        "user_query": "What does this reading mean?",
        "standalone_query": "What does this reading mean?",
        "routes": ["health_general"],
        "history": [
            {"role": "assistant", "content": "You mentioned a reading of 128/82."},
            {"role": "user", "content": "What does this reading mean?"},
        ],
        "retrieved_docs": [{"title": "Blood pressure guide", "section": "Readings", "content": "A reading has two numbers."}],
    })
    assert result["draft_answer"].startswith("Blood pressure")
    assert captured["system_prompt"]
    assert captured["conversation_history"] == [{"role": "assistant", "content": "You mentioned a reading of 128/82."}]
    assert "A reading has two numbers" in captured["evidence"]
    assert "A reading has two numbers" not in captured["prompt"]


@pytest.mark.asyncio
async def test_application_claim_without_records_says_unverified(monkeypatch):
    async def must_not_call(**_kwargs):
        pytest.fail("app-specific answer must not be generated without evidence")

    monkeypatch.setattr(answer_generator, "generate_completion", must_not_call)
    result = await answer_generator.answer_generator_node({
        "user_query": "What insurance does PulseCare accept?",
        "routes": ["website_help"],
        "retrieved_docs": [],
    })
    assert "could not verify" in result["draft_answer"]


@pytest.mark.asyncio
async def test_provider_error_is_safe_and_does_not_return_mock_answer(monkeypatch):
    from backend.app.chatbot.graph.nodes.safety_postprocessor import safety_postprocessor_node

    async def fail(**_kwargs):
        raise RuntimeError("private-provider-detail-secret-token")

    monkeypatch.setattr(answer_generator, "generate_completion", fail)
    result = await answer_generator.answer_generator_node({
        "user_query": "What is hypertension?",
        "routes": ["health_general"],
        "retrieved_docs": [],
    })
    assert "health-answer service is unavailable" in result["draft_answer"].lower()
    assert "private-provider-detail-secret-token" not in result["draft_answer"]
    assert result["generation_failed"] is True

    final = safety_postprocessor_node({
        "routes": ["health_general"],
        "retrieved_docs": [{
            "title": "Relevant health guide", "section": "Overview", "content": "verified text",
            "trust_level": "verified_clinical",
        }],
        **result,
    })
    assert final["info_badge"] == "general"
    assert final["citations"] == []
    assert "Medical Disclaimer" not in final["final_answer"]


@pytest.mark.asyncio
async def test_unknown_doctor_response_does_not_claim_a_service_fee():
    result = await answer_generator.answer_generator_node({
        "user_query": "What is Elena Garchia's fee?",
        "standalone_query": "What is Elena Garchia's fee?",
        "routes": ["doctor_service_lookup"],
        "extracted_entities": {"doctor_name": "Elena Garchia"},
        "retrieved_docs": [],
    })

    assert "Elena Garchia" in result["draft_answer"]
    assert "could not verify" in result["draft_answer"].lower()
    assert "$250" not in result["draft_answer"]
