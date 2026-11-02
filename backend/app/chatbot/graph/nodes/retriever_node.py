import time
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.models.user import User
from backend.app.chatbot.graph.state import ChatbotState
from backend.app.chatbot.sources.contracts import SourceRequest
from backend.app.chatbot.sources.registry import build_source_registry

source_registry = build_source_registry(settings)


async def retriever_node(
    state: ChatbotState,
    db: AsyncSession,
    current_user: Optional[User] = None,
) -> Dict[str, Any]:
    """
    Node 5: Configured Knowledge Source Retrieval
    Queries configured knowledge sources through the shared source contract.
    """
    start_time = time.time()
    routes = state.get("routes", [])
    query = state.get("standalone_query") or state.get("sanitized_query") or state.get("user_query", "")
    user_id = state.get("user_id")

    needs_retrieval = any(r in routes for r in [
        "website_help", "health_general", "medicine_info", "doctor_service_lookup",
    ])
    if not needs_retrieval:
        return {
            "retrieved_docs": [],
            "latency_records": {**state.get("latency_records", {}), "retriever": (time.time() - start_time) * 1000},
        }

    result = await source_registry.retrieve(SourceRequest(
        query=query,
        routes=routes,
        entities=state.get("extracted_entities", {}),
        db=db,
        current_user=current_user,
        user_id=user_id,
        limit=settings.RAG_TOP_K_RERANK,
    ))
    doc_dicts = [record.to_dict() for record in result.records]
    return {
        "retrieved_docs": doc_dicts,
        "source_failures": result.failed_sources,
        "retrieval_retry_count": state.get("retrieval_retry_count", 0),
        "latency_records": {**state.get("latency_records", {}), "retriever": (time.time() - start_time) * 1000},
    }
