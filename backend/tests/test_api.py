import pytest
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_api_chatbot_message_greeting():
    res = client.post("/api/chatbot/message", json={"message": "Hello!"})
    assert res.status_code == 200
    data = res.json()
    assert "Hello!" in data["content"] or "PulseCare" in data["content"]
    assert data["session_id"] is not None
    assert data["is_emergency"] is False


def test_api_chatbot_stream():
    res = client.post("/api/chatbot/stream", json={"message": "What is the cancellation policy?"})
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    text = res.text
    assert "event: metadata" in text
    assert "event: token" in text
    assert "event: done" in text


def test_chat_api_answers_informal_health_questions_and_resolves_doctor_fee_follow_up(monkeypatch):
    import json
    from backend.app.chatbot.graph.nodes import answer_generator, router

    async def classify(*_args, **_kwargs):
        return json.dumps({"intents": ["out_of_scope"]})

    generation_calls = []

    async def generate(**kwargs):
        generation_calls.append(kwargs)
        return "Synthetic health education answer for this test."

    monkeypatch.setattr(router, "generate_completion", classify)
    monkeypatch.setattr(answer_generator, "generate_completion", generate)

    def stream_answer(response):
        parts = []
        metadata = {}
        for block in response.text.split("\n\n"):
            lines = block.splitlines()
            event = next((line[7:] for line in lines if line.startswith("event: ")), None)
            data = next((line[6:] for line in lines if line.startswith("data: ")), None)
            if event == "token" and data:
                parts.append(json.loads(data).get("token", ""))
            elif event == "metadata" and data:
                metadata = json.loads(data)
        return "".join(parts), metadata

    sugar = client.post("/api/chatbot/stream", json={"message": "sugar is healthy or not?"})
    assert sugar.status_code == 200
    assert len(generation_calls) == 1
    sugar_answer, sugar_metadata = stream_answer(sugar)
    assert "Synthetic health education answer" in sugar_answer
    assert sugar_metadata["route"] == "health_general"

    headache = client.post("/api/chatbot/stream", json={"message": "What are common causes of a headache?"})
    assert headache.status_code == 200
    headache_answer, headache_metadata = stream_answer(headache)
    assert "Synthetic health education answer" in headache_answer
    assert headache_metadata["route"] == "health_general"
    assert "SELF_CARE" not in headache_answer


def test_chat_api_keeps_doctor_fee_follow_up_on_the_doctor_record(monkeypatch):
    import json
    from backend.app.chatbot.graph.nodes import router

    async def classify(prompt, **_kwargs):
        message = json.loads(prompt)["message"].lower()
        if "find a doctor" in message:
            return json.dumps({"intents": ["doctor_service_lookup", "application_help"]})
        return json.dumps({"intents": ["doctor_service_lookup"]})

    monkeypatch.setattr(router, "generate_completion", classify)
    help_response = client.post("/api/chatbot/message", json={"message": "How can I find a doctor on PulseCare?"})
    session_id = help_response.json()["session_id"]
    profile = client.post(
        "/api/chatbot/message",
        json={"message": "Tell me about Dr. Sarah Smith.", "session_id": session_id},
    )
    follow_up = client.post(
        "/api/chatbot/message",
        json={"message": "What is her consultation fee?", "session_id": session_id},
    )

    assert help_response.status_code == profile.status_code == follow_up.status_code == 200
    assert "Doctors page" in help_response.json()["content"]
    assert "Doctor Portal Features" not in help_response.json()["content"]
    assert "Telehealth" not in help_response.json()["content"]
    assert "$150.00" in profile.json()["content"]
    assert "$150.00" in follow_up.json()["content"]
    assert "$250" not in follow_up.json()["content"]


def test_api_chatbot_feedback():
    # First get a valid message_id
    msg_res = client.post("/api/chatbot/message", json={"message": "Find Dr. Sarah Smith"})
    mid = msg_res.json()["message_id"]

    fb_res = client.post(
        "/api/chatbot/feedback",
        json={"message_id": mid, "rating": "thumbs_up", "comment": "Great doctor details!"},
    )
    assert fb_res.status_code == 201
    assert fb_res.json()["status"] == "success"


def test_api_chatbot_clear_session():
    msg_res = client.post("/api/chatbot/message", json={"message": "Temporary session message"})
    sid = msg_res.json()["session_id"]

    del_res = client.delete(f"/api/chatbot/sessions/{sid}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"
