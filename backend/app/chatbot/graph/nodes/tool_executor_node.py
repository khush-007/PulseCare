import time
import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.user import User
from backend.app.chatbot.graph.state import ChatbotState
from backend.app.chatbot.tools.registry import execute_tool


async def tool_executor_node(
    state: ChatbotState,
    db: AsyncSession,
    current_user: Optional[User],
) -> Dict[str, Any]:
    """
    Node 6: Safe Tool Executor
    Determines tool invocations from classified routes and entities,
    then executes tools strictly with parameterized queries and authorization enforcement.
    """
    start_time = time.time()
    routes = state.get("routes", [])
    entities = state.get("extracted_entities", {})
    query = (state.get("standalone_query") or state.get("sanitized_query") or state.get("user_query", "")).lower()

    planned_calls: List[Dict[str, Any]] = []

    # 1. Personal Data Route (My Appointments)
    if "personal_data" in routes:
        planned_calls.append({
            "tool": "get_my_appointments",
            "args": {},
        })

    # Public doctor/service retrieval runs through the configured source registry.
    # Personal records and clinical triage remain on their guarded tool paths.
    # Medicine Info Route
    if "medicine_info" in routes:
        med_name = entities.get("medicine_name")
        if not med_name:
            # Try to grab last word or candidate medicine name
            words = query.split()
            for w in words:
                if len(w) > 4 and w not in ["medicine", "about", "information", "what", "does", "take", "side", "effects"]:
                    med_name = w
                    break
        if med_name:
            planned_calls.append({
                "tool": "lookup_medicine",
                "args": {"name": med_name},
            })

    # 4. Triage Handoff Route
    if "triage_handoff" in routes:
        symptom_text = state.get("standalone_query") or state.get("user_query", "")
        planned_calls.append({
            "tool": "handoff_to_triage",
            "args": {"symptom_text": symptom_text},
        })

    # Execute all scheduled tool calls
    tool_results: List[Dict[str, Any]] = []
    for call in planned_calls:
        res = await execute_tool(
            tool_name=call["tool"],
            tool_args=call["args"],
            db=db,
            current_user=current_user,
        )
        tool_results.append({
            "tool": call["tool"],
            "input": call["args"],
            "result": res,
        })

    return {
        "tool_calls": planned_calls,
        "tool_results": tool_results,
        "latency_records": {**state.get("latency_records", {}), "tool_executor": (time.time() - start_time) * 1000},
    }
