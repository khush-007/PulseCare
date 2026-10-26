import pytest
import json
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal, init_db
from backend.app.models.user import User
from backend.app.models.user_memory import UserMemory
from backend.app.chatbot.graph.workflow import run_chatbot_workflow

client = TestClient(app)

def get_token(email: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

@pytest.fixture(scope="function")
def john_token():
    return get_token("john.doe@example.com", "hashed")

@pytest.fixture(scope="function")
def dr_token():
    return get_token("dr.sarah@example.com", "hashed")

def test_memory_crud_and_isolation(john_token, dr_token):
    # John sets a memory
    headers = {"Authorization": f"Bearer {john_token}"}
    set_res = client.post("/api/memory/", json={"key": "favorite_color", "value": "blue"}, headers=headers)
    assert set_res.status_code == 201

    # Retrieve John's memory
    get_res = client.get("/api/memory/favorite_color", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json() == "blue"

    # Update memory
    upd_res = client.post("/api/memory/", json={"key": "favorite_color", "value": "green"}, headers=headers)
    assert upd_res.status_code == 201
    get_res2 = client.get("/api/memory/favorite_color", headers=headers)
    assert get_res2.json() == "green"

    # Delete memory
    del_res = client.delete("/api/memory/favorite_color", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Ensure not found after deletion
    not_found = client.get("/api/memory/favorite_color", headers=headers)
    assert not_found.status_code == 404

    # Dr. Sarah should not see John's memory (isolation)
    dr_headers = {"Authorization": f"Bearer {dr_token}"}
    dr_get = client.get("/api/memory/favorite_color", headers=dr_headers)
    assert dr_get.status_code == 404
