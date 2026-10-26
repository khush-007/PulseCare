import pytest
from backend.app.core.database import AsyncSessionLocal
from backend.app.chatbot.rag.retriever import hybrid_retrieve


@pytest.mark.asyncio
async def test_hybrid_retriever_faq_query():
    async with AsyncSessionLocal() as session:
        chunks = await hybrid_retrieve("What is the appointment cancellation policy?", session, top_k=3)
        assert len(chunks) > 0
        top = chunks[0]
        # Should match cancellation section
        assert "cancellation" in top.content.lower() or "policy" in top.content.lower()


@pytest.mark.asyncio
async def test_hybrid_retriever_insurance():
    async with AsyncSessionLocal() as session:
        chunks = await hybrid_retrieve("Does PulseCare accept Blue Cross or Medicare insurance?", session, top_k=3)
        assert len(chunks) > 0
        assert any("insurance" in c.content.lower() for c in chunks)


@pytest.mark.asyncio
async def test_hybrid_retriever_metadata_filter():
    async with AsyncSessionLocal() as session:
        chunks = await hybrid_retrieve("emergency", session, top_k=5, doc_type_filter="policy")
        for c in chunks:
            assert c.doc_type == "policy"
