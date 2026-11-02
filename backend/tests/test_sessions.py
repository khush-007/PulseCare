import pytest
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def get_token(email: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

@pytest.fixture(scope="function")
def john_token():
    return get_token("john.doe@example.com", "hashed")

@pytest.fixture(scope="function")
def jane_token():
    return get_token("jane.smith@example.com", "hashed")

def test_create_and_rename_session(john_token, jane_token):
    # John creates a session
    headers = {"Authorization": f"Bearer {john_token}"}
    res = client.post("/api/chatbot/sessions", json={"title": "John's Session"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    session_id = data["id"]
    assert data["title"] == "John's Session"

    # John renames his session
    rename_res = client.patch(f"/api/chatbot/sessions/{session_id}", json="John's Renamed Session", headers=headers)
    assert rename_res.status_code == 200
    assert rename_res.json()["title"] == "John's Renamed Session"

    # Jane attempts to rename John's session – should be forbidden
    jane_headers = {"Authorization": f"Bearer {jane_token}"}
    bad_rename = client.patch(f"/api/chatbot/sessions/{session_id}", json="Hack", headers=jane_headers)
    assert bad_rename.status_code == 404

def test_message_persistence_and_deletion(john_token):
    headers = {"Authorization": f"Bearer {john_token}"}
    # Create a session
    res = client.post("/api/chatbot/sessions", json={"title": "Temp Session"}, headers=headers)
    sid = res.json()["id"]

    # Send a message within the session
    msg_res = client.post("/api/chatbot/message", json={"message": "Hello", "session_id": sid}, headers=headers)
    assert msg_res.status_code == 200
    assert msg_res.json()["session_id"] == sid
    msg_id = msg_res.json()["message_id"]

    # Retrieve messages for the session
    msgs = client.get(f"/api/chatbot/sessions/{sid}/messages", headers=headers)
    assert msgs.status_code == 200
    msgs_json = msgs.json()
    assert any(m["id"] == msg_id for m in msgs_json)

    # Delete the session history
    del_res = client.delete(f"/api/chatbot/sessions/{sid}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Ensure messages are gone (or session unavailable)
    empty = client.get(f"/api/chatbot/sessions/{sid}/messages", headers=headers)
    # After deletion, the endpoint may return 404 or empty list
    assert empty.status_code == 404 or empty.json() == []


def test_other_user_cannot_reuse_or_read_session(john_token, jane_token):
    john_headers = {"Authorization": f"Bearer {john_token}"}
    jane_headers = {"Authorization": f"Bearer {jane_token}"}
    created = client.post(
        "/api/chatbot/sessions",
        json={"title": "Private Session"},
        headers=john_headers,
    )
    session_id = created.json()["id"]

    sent = client.post(
        "/api/chatbot/message",
        json={"message": "session ownership test", "session_id": session_id},
        headers=john_headers,
    )
    assert sent.status_code == 200

    assert client.post(
        "/api/chatbot/message",
        json={"message": "cross-account attempt", "session_id": session_id},
        headers=jane_headers,
    ).status_code == 404
    assert client.post(
        "/api/chatbot/stream",
        json={"message": "cross-account attempt", "session_id": session_id},
        headers=jane_headers,
    ).status_code == 404
    assert client.get(
        f"/api/chatbot/sessions/{session_id}/messages", headers=jane_headers
    ).status_code == 404
    assert client.patch(
        f"/api/chatbot/sessions/{session_id}",
        json="Not the owner",
        headers=jane_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/chatbot/sessions/{session_id}", headers=jane_headers
    ).status_code == 404

    owner_messages = client.get(
        f"/api/chatbot/sessions/{session_id}/messages", headers=john_headers
    )
    assert owner_messages.status_code == 200
    assert any(m["content"] == "session ownership test" for m in owner_messages.json())


def test_guest_session_cannot_be_claimed_by_authenticated_user(jane_token):
    guest_message = client.post(
        "/api/chatbot/message",
        json={"message": "guest session ownership test"},
    )
    assert guest_message.status_code == 200
    session_id = guest_message.json()["session_id"]
    jane_headers = {"Authorization": f"Bearer {jane_token}"}

    assert client.post(
        "/api/chatbot/message",
        json={"message": "claim guest session", "session_id": session_id},
        headers=jane_headers,
    ).status_code == 404
    assert client.get(
        f"/api/chatbot/sessions/{session_id}/messages", headers=jane_headers
    ).status_code == 404
    assert client.patch(
        f"/api/chatbot/sessions/{session_id}",
        json="Claimed",
        headers=jane_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/chatbot/sessions/{session_id}", headers=jane_headers
    ).status_code == 404

    guest_messages = client.get(f"/api/chatbot/sessions/{session_id}/messages")
    assert guest_messages.status_code == 200
    assert any(
        m["content"] == "guest session ownership test"
        for m in guest_messages.json()
    )


def test_unknown_client_chosen_session_id_is_not_created():
    response = client.post(
        "/api/chatbot/message",
        json={"message": "new session", "session_id": "client-chosen-id"},
    )

    assert response.status_code == 404
