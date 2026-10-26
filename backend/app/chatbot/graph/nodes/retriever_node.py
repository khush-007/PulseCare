import time
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.chatbot.graph.state import ChatbotState
from backend.app.chatbot.rag.retriever import hybrid_retrieve


async def retriever_node(state: ChatbotState, db: AsyncSession) -> Dict[str, Any]:
    """
    Node 5: Advanced Hybrid Retriever
    Fetches grounded documentation chunks for website_help, health_general, or medicine_info.
    Uses dense vector search + BM25 keyword matching + RRF fusion + Cross-Encoder reranking.
    """
    start_time = time.time()
    routes = state.get("routes", [])
    query = state.get("standalone_query") or state.get("sanitized_query") or state.get("user_query", "")
    user_id = state.get("user_id")

    # Only retrieve if relevant routes are active
    needs_retrieval = any(r in routes for r in ["website_help", "health_general", "medicine_info"])
    if not needs_retrieval:
        return {
            "retrieved_docs": [],
            "latency_records": {**state.get("latency_records", {}), "retriever": (time.time() - start_time) * 1000},
        }

    # Determine doc_type filter based on active routes
    doc_type_filter = None
    if "website_help" in routes:
        doc_type_filter = "website_help"
    elif "health_general" in routes:
        doc_type_filter = "health_general"
    elif "medicine_info" in routes:
        doc_type_filter = "medicine_info"

    # Execute hybrid retrieval with per-user isolation and doc_type filtering
    chunks = await hybrid_retrieve(
        query=query,
        db=db,
        top_k=settings.RAG_TOP_K_RERANK,
        user_id=user_id,
        doc_type_filter=doc_type_filter,
    )

    doc_dicts = [
        {
            "doc_id": c.doc_id,
            "chunk_id": c.chunk_id,
            "title": c.title,
            "section": c.section,
            "content": c.content,
            "doc_type": c.doc_type,
            "trust_level": c.trust_level,
            "source_url": c.source_url,
            "last_updated": c.last_updated,
            "score": c.score,
        }
        for c in chunks
    ]

    return {
        "retrieved_docs": doc_dicts,
        "retrieval_retry_count": state.get("retrieval_retry_count", 0),
        "latency_records": {**state.get("latency_records", {}), "retriever": (time.time() - start_time) * 1000},
    }
