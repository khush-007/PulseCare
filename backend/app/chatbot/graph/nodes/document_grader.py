import time
from typing import Dict, Any
from backend.app.core.config import settings
from backend.app.chatbot.graph.state import ChatbotState


def document_grader_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 7: Document Grader (Corrective RAG / CRAG)
    Grades retrieved chunks for relevance.
    If relevance is insufficient, triggers query reformulation and retrieval retry (up to 2 loops).
    """
    start_time = time.time()
    docs = state.get("retrieved_docs", [])
    retry_count = state.get("retrieval_retry_count", 0)
    query = state.get("standalone_query") or state.get("user_query", "")

    # If no retrieval was needed, skip
    routes = state.get("routes", [])
    needs_docs = any(r in routes for r in ["website_help", "health_general"])
    if not needs_docs:
        return {
            "documents_relevant": True,
            "latency_records": {**state.get("latency_records", {}), "document_grader": (time.time() - start_time) * 1000},
        }

    # Evaluate relevance
    is_relevant = False
    if docs:
        top_score = docs[0].get("score", 0.0)
        # Check if score exceeds threshold or if keywords appear in content
        q_tokens = [w.lower() for w in query.split() if len(w) > 3]
        matched_tokens = any(
            any(tok in d.get("content", "").lower() for tok in q_tokens)
            for d in docs
        )
        if top_score >= settings.RAG_RELEVANCE_THRESHOLD or matched_tokens:
            is_relevant = True

    # If not relevant and under retry limit, reformulate query
    if not is_relevant and retry_count < 2:
        reformed_query = f"PulseCare healthcare guide {query} policies features"
        return {
            "documents_relevant": False,
            "standalone_query": reformed_query,
            "retrieval_retry_count": retry_count + 1,
            "latency_records": {**state.get("latency_records", {}), "document_grader": (time.time() - start_time) * 1000},
        }

    return {
        "documents_relevant": True,
        "latency_records": {**state.get("latency_records", {}), "document_grader": (time.time() - start_time) * 1000},
    }
