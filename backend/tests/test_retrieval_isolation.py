import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.chatbot import KnowledgeDocumentChunk
from backend.app.core.database import async_sessionmaker
from backend.app.chatbot.rag.retriever import hybrid_retrieve

@pytest.fixture
async def db_session():
    async with async_sessionmaker() as session:
        yield session
        # Cleanup after test
        await session.execute(KnowledgeDocumentChunk.__table__.delete())
        await session.commit()

@pytest.mark.asyncio
async def test_retrieval_user_isolation(db_session: AsyncSession):
    # Create two users (ids 1 and 2) and corresponding document chunks
    chunk_user1 = KnowledgeDocumentChunk(
        doc_id="doc1",
        chunk_index=0,
        title="Title 1",
        section="Section A",
        content="Content specific to user one",
        doc_type="health_general",
        trust_level="official",
        source_url="",
        last_updated="2023-01-01",
        user_id=1,
        embedding_json="[0.1, 0.2, 0.3]",
        metadata_json="{}",
    )
    chunk_user2 = KnowledgeDocumentChunk(
        doc_id="doc2",
        chunk_index=0,
        title="Title 2",
        section="Section B",
        content="Content specific to user two",
        doc_type="health_general",
        trust_level="official",
        source_url="",
        last_updated="2023-01-01",
        user_id=2,
        embedding_json="[0.1, 0.2, 0.3]",
        metadata_json="{}",
    )
    db_session.add_all([chunk_user1, chunk_user2])
    await db_session.commit()

    state_user1 = {"routes": ["health_general"], "user_query": "query1", "user_id": 1}
    docs1 = await hybrid_retrieve("query1", db_session, user_id=state_user1["user_id"], doc_type_filter="health_general")
    # Shared public knowledge is available to authenticated users, but another
    # user's private document must never be returned.
    assert any(doc.doc_id == "doc1" for doc in docs1)
    assert all(doc.doc_id != "doc2" for doc in docs1)

    state_user2 = {"routes": ["health_general"], "user_query": "query2", "user_id": 2}
    docs2 = await hybrid_retrieve("query2", db_session, user_id=state_user2["user_id"], doc_type_filter="health_general")
    assert any(doc.doc_id == "doc2" for doc in docs2)
    assert all(doc.doc_id != "doc1" for doc in docs2)

@pytest.mark.asyncio
async def test_retrieval_missing_user_id_returns_all(db_session: AsyncSession):
    public_chunk = KnowledgeDocumentChunk(
        doc_id="public-doc",
        chunk_index=0,
        title="Public Title",
        section="Public Section",
        content="Public content accessible to all users",
        doc_type="health_general",
        trust_level="official",
        source_url="",
        last_updated="2023-01-01",
        user_id=None,
        embedding_json="[0.1, 0.2, 0.3]",
        metadata_json="{}",
    )
    db_session.add(public_chunk)
    await db_session.commit()

    state = {"routes": ["health_general"], "user_query": "any query"}
    docs = await hybrid_retrieve("any query", db_session, user_id=None, doc_type_filter="health_general")
    assert any(d.doc_id == "public-doc" for d in docs)
