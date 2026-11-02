import pytest
import json
from backend.app.chatbot.graph.nodes.router import router_node
from backend.app.chatbot.graph.state import ChatbotState


@pytest.mark.asyncio
async def test_route_doctor_lookup(monkeypatch):
    async def classify(*_args, **_kwargs): return json.dumps({"intents": ["doctor_service_lookup"]})
    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    state: ChatbotState = {"standalone_query": "Is there a cardiologist available on Monday?"}
    res = await router_node(state)
    assert "doctor_service_lookup" in res["routes"]


@pytest.mark.asyncio
async def test_route_personal_data(monkeypatch):
    async def classify(*_args, **_kwargs): return json.dumps({"intents": ["patient_records"]})
    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    state: ChatbotState = {"standalone_query": "When is my appointment scheduled?"}
    res = await router_node(state)
    assert "personal_data" in res["routes"]


@pytest.mark.asyncio
async def test_route_medicine_info(monkeypatch):
    async def classify(*_args, **_kwargs): return json.dumps({"intents": ["medicine_info"]})
    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    state: ChatbotState = {"standalone_query": "What are the common side effects of Lisinopril?"}
    res = await router_node(state)
    assert "medicine_info" in res["routes"]


@pytest.mark.asyncio
async def test_route_triage_handoff(monkeypatch):
    async def classify(*_args, **_kwargs): return json.dumps({"intents": ["triage"]})
    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    state: ChatbotState = {"standalone_query": "I have a fever and my head hurts, can you triage me?"}
    res = await router_node(state)
    assert "triage_handoff" in res["routes"]


@pytest.mark.asyncio
async def test_route_website_help(monkeypatch):
    async def classify(*_args, **_kwargs): return json.dumps({"intents": ["application_help"]})
    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    state: ChatbotState = {"standalone_query": "What is the appointment cancellation policy?"}
    res = await router_node(state)
    assert "website_help" in res["routes"]


@pytest.mark.asyncio
async def test_route_direct_llm():
    state: ChatbotState = {"standalone_query": "Hello there! Good morning."}
    res = await router_node(state)
    assert "direct_llm" in res["routes"]


@pytest.mark.asyncio
async def test_route_out_of_scope(monkeypatch):
    async def classify(*_args, **_kwargs): return json.dumps({"intents": ["out_of_scope"]})
    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    state: ChatbotState = {"standalone_query": "Who is going to win the football match tonight?"}
    res = await router_node(state)
    assert "out_of_scope" in res["routes"]


@pytest.mark.asyncio
async def test_multi_route_query(monkeypatch):
    async def classify(*_args, **_kwargs): return json.dumps({"intents": ["doctor_service_lookup", "medicine_info"]})
    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    state: ChatbotState = {
        "standalone_query": "Is Dr. Sarah Smith available tomorrow and what are the side effects of Metformin?"
    }
    res = await router_node(state)
    assert "doctor_service_lookup" in res["routes"]
    assert "medicine_info" in res["routes"]


@pytest.mark.asyncio
async def test_informal_hinglish_routes_using_mock_classifier(monkeypatch):
    from backend.app.chatbot.graph import llm
    monkeypatch.setattr(llm.settings, "LLM_PROVIDER", "mock")
    state: ChatbotState = {"standalone_query": "Mujhe bukhar aur sar dard hai, kya karun?"}
    result = await router_node(state)
    assert result["routes"] == ["triage_handoff"]


@pytest.mark.asyncio
async def test_follow_up_uses_recent_history(monkeypatch):
    async def classify(prompt, **_kwargs):
        assert "Dr. Sarah Smith" in prompt
        return json.dumps({"intents": ["follow_up", "doctor_service_lookup"]})
    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    result = await router_node({
        "standalone_query": "Aur unki fee?",
        "history": [{"role": "assistant", "content": "Dr. Sarah Smith is a cardiologist."}],
    })
    assert "doctor_service_lookup" in result["routes"]


def test_hinglish_follow_up_resolves_prior_verified_doctor():
    from backend.app.chatbot.graph.nodes.query_understanding import query_understanding_node

    result = query_understanding_node({
        "sanitized_query": "Aur unki fee?",
        "history": [{
            "role": "assistant",
            "content": "• **Sarah Smith** — Cardiology\n  **Consultation Fee**: $150.00",
        }],
    })
    assert "Sarah Smith" in result["standalone_query"]
    assert result["extracted_entities"]["doctor_name"] == "Sarah Smith"


def test_english_doctor_fee_follow_up_resolves_named_doctor_from_history():
    from backend.app.chatbot.graph.nodes.query_understanding import query_understanding_node

    result = query_understanding_node({
        "sanitized_query": "What is her consultation fee?",
        "history": [
            {"role": "user", "content": "Tell me about Dr. Sarah Smith."},
            {"role": "assistant", "content": "### Sarah Smith\nDoctor: Sarah Smith; Specialty: Cardiology; Consultation fee: $150.00"},
            {"role": "user", "content": "What is her consultation fee?"},
        ],
    })

    assert result["extracted_entities"]["doctor_name"] == "Sarah Smith"


def test_bare_name_after_doctor_lookup_is_not_a_request_for_all_doctors():
    from backend.app.chatbot.graph.nodes.query_understanding import query_understanding_node

    result = query_understanding_node({
        "sanitized_query": "priya patel",
        "history": [
            {"role": "user", "content": "Tell me about Dr. David Chen."},
            {"role": "assistant", "content": "I could not verify a matching doctor."},
            {"role": "user", "content": "priya patel"},
        ],
    })

    assert result["extracted_entities"]["doctor_name"] == "Priya Patel"


def test_misspelled_name_fee_query_stays_doctor_specific():
    from backend.app.chatbot.graph.nodes.query_understanding import query_understanding_node

    result = query_understanding_node({"sanitized_query": "elena garchia fees?", "history": []})

    assert result["extracted_entities"]["doctor_name"] == "Elena Garchia"


@pytest.mark.asyncio
async def test_extracted_doctor_entity_overrides_generic_or_out_of_scope_classification(monkeypatch):
    async def classify(*_args, **_kwargs):
        return json.dumps({"intents": ["out_of_scope"]})

    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    result = await router_node({
        "standalone_query": "priya patel",
        "extracted_entities": {"doctor_name": "Priya Patel"},
    })

    assert result["routes"] == ["doctor_service_lookup"]


@pytest.mark.asyncio
async def test_invalid_intent_schema_falls_back_safely(monkeypatch):
    async def classify(*_args, **_kwargs): return '{"intents":["make_me_a_web_app"]}'
    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    result = await router_node({"standalone_query": "Write a Python script to sort files"})
    assert result["routes"] == ["out_of_scope"]


@pytest.mark.asyncio
async def test_provider_failure_falls_back_without_exposing_error(monkeypatch):
    async def fail(*_args, **_kwargs): raise RuntimeError("secret-token-value")
    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", fail)
    result = await router_node({"standalone_query": "What is normal blood pressure?"})
    assert "health_general" in result["routes"]
    assert "secret-token-value" not in str(result)


@pytest.mark.asyncio
async def test_find_doctor_on_pulsecare_is_application_help_not_directory_lookup(monkeypatch):
    async def classify(*_args, **_kwargs):
        return json.dumps({"intents": ["doctor_service_lookup", "application_help"]})

    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    result = await router_node({"standalone_query": "How can I find a doctor on PulseCare?"})
    assert result["routes"] == ["website_help"]


@pytest.mark.asyncio
async def test_informal_sugar_health_question_overrides_false_out_of_scope(monkeypatch):
    async def classify(*_args, **_kwargs):
        return json.dumps({"intents": ["out_of_scope"]})

    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    result = await router_node({"standalone_query": "sugar is healthy or not?"})

    assert result["routes"] == ["health_general"]


@pytest.mark.asyncio
async def test_informal_sugar_health_question_routes_when_classifier_fails(monkeypatch):
    async def fail(*_args, **_kwargs):
        raise RuntimeError("provider detail must remain private")

    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", fail)
    result = await router_node({"standalone_query": "sugar is healthy or not?"})

    assert result["routes"] == ["health_general"]
    assert "provider detail" not in str(result)


@pytest.mark.asyncio
async def test_general_headache_causes_question_is_education_not_triage(monkeypatch):
    async def classify(*_args, **_kwargs):
        return json.dumps({"intents": ["triage"]})

    monkeypatch.setattr("backend.app.chatbot.graph.nodes.router.generate_completion", classify)
    result = await router_node({"standalone_query": "What are common causes of a headache?"})

    assert result["routes"] == ["health_general"]
