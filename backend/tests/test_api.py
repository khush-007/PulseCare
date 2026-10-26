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
