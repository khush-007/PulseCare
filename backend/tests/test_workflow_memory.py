import pytest
import json
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal, init_db
from backend.app.models.user import User
from sqlalchemy.future import select
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

@pytest.mark.asyncio
async def test_workflow_loads_memories_for_user(john_token):
    # Ensure a memory exists for John
    headers = {"Authorization": f"Bearer {john_token}"}
    mem_res = client.post("/api/memory/", json={"key": "favorite_color", "value": "blue"}, headers=headers)
    assert mem_res.status_code == 201

    # Retrieve John user object
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "john.doe@example.com"))
        john_user: User = result.scalars().first()
        assert john_user is not None

        # Run the workflow
        final_state = await run_chatbot_workflow(
            user_query="What is my favorite color?",
            session_id="test-session",
            db=db,
            current_user=john_user,
            history=[],
        )
        # Verify the memory is present in the state
        user_memories = final_state.get("user_memories", [])
        assert any(m["key"] == "favorite_color" and m["value"] == "blue" for m in user_memories)

@pytest.mark.asyncio
async def test_workflow_no_memories_for_user_without_memory_enabled(dr_token):
    # Doctor user has memory disabled by default
    headers = {"Authorization": f"Bearer {dr_token}"}
    # Ensure no memories exist (should be none)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "dr.sarah@example.com"))
        dr_user: User = result.scalars().first()
        assert dr_user is not None
        # Run the workflow
        final_state = await run_chatbot_workflow(
            user_query="What is my favorite color?",
            session_id="test-session-2",
            db=db,
            current_user=dr_user,
            history=[],
        )
        user_memories = final_state.get("user_memories", [])
        # Should be empty list
        assert user_memories == []
