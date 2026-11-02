import pytest
from sqlalchemy.dialects import sqlite

from backend.app.chatbot.memory.history import get_session_history


@pytest.mark.asyncio
async def test_history_limit_keeps_newest_messages_and_returns_chronological_order():
    newest_first = [
        type("Message", (), {"id": message_id, "content": content})()
        for message_id, content in ((32, "latest follow-up"), (31, "doctor profile"), (30, "doctor question"))
    ]

    class ScalarResult:
        def all(self):
            return newest_first

    class Result:
        def scalars(self):
            return ScalarResult()

    class FakeDatabase:
        statement = None

        async def execute(self, statement):
            self.statement = statement
            return Result()

    db = FakeDatabase()
    history = await get_session_history(db, session_id="session-1", limit=3)

    assert [message.content for message in history] == [
        "doctor question", "doctor profile", "latest follow-up",
    ]
    sql = str(db.statement.compile(
        dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
    )).lower()
    assert "order by chat_messages.created_at desc, chat_messages.id desc" in sql
    assert "limit 3" in sql
