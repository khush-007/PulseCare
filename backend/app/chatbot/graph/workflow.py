import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
from sqlalchemy.future import select
from backend.app.models.user_memory import UserMemory
from backend.app.models.user import User
from backend.app.chatbot.graph.state import ChatbotState
from backend.app.chatbot.graph.nodes.input_guard import input_guard_node
from backend.app.chatbot.graph.nodes.emergency_detector import emergency_detector_node
from backend.app.chatbot.graph.nodes.query_understanding import query_understanding_node
from backend.app.chatbot.graph.nodes.router import router_node
from backend.app.chatbot.graph.nodes.retriever_node import retriever_node
from backend.app.chatbot.graph.nodes.tool_executor_node import tool_executor_node
from backend.app.chatbot.graph.nodes.document_grader import document_grader_node
from backend.app.chatbot.graph.nodes.answer_generator import answer_generator_node
from backend.app.chatbot.graph.nodes.grounding_verifier import grounding_verifier_node
from backend.app.chatbot.graph.nodes.safety_postprocessor import safety_postprocessor_node

logger = logging.getLogger("pulsecare.chatbot.graph")


# --- Node Wrappers that inject Configurable Runtime Dependencies ---

def wrapped_input_guard(state: ChatbotState, config: RunnableConfig) -> Dict[str, Any]:
    return input_guard_node(state)


def wrapped_emergency_detector(state: ChatbotState, config: RunnableConfig) -> Dict[str, Any]:
    return emergency_detector_node(state)


def wrapped_query_understanding(state: ChatbotState, config: RunnableConfig) -> Dict[str, Any]:
    return query_understanding_node(state)


def wrapped_router(state: ChatbotState, config: RunnableConfig) -> Dict[str, Any]:
    return router_node(state)


async def wrapped_retriever(state: ChatbotState, config: RunnableConfig) -> Dict[str, Any]:
    db: AsyncSession = config.get("configurable", {}).get("db")
    return await retriever_node(state, db)


def wrapped_document_grader(state: ChatbotState, config: RunnableConfig) -> Dict[str, Any]:
    return document_grader_node(state)


async def wrapped_tool_executor(state: ChatbotState, config: RunnableConfig) -> Dict[str, Any]:
    db: AsyncSession = config.get("configurable", {}).get("db")
    current_user: Optional[User] = config.get("configurable", {}).get("current_user")
    return await tool_executor_node(state, db, current_user)


async def wrapped_answer_generator(state: ChatbotState, config: RunnableConfig) -> Dict[str, Any]:
    return await answer_generator_node(state)


def wrapped_grounding_verifier(state: ChatbotState, config: RunnableConfig) -> Dict[str, Any]:
    return grounding_verifier_node(state)


def wrapped_safety_postprocessor(state: ChatbotState, config: RunnableConfig) -> Dict[str, Any]:
    return safety_postprocessor_node(state)


# --- Conditional Branching Evaluators ---

def check_guard_condition(state: ChatbotState) -> str:
    if state.get("guard_triggered"):
        return "safety_postprocessor"
    return "emergency_detector"


def check_emergency_condition(state: ChatbotState) -> str:
    if state.get("is_emergency"):
        return "safety_postprocessor"
    return "query_understanding"


def check_router_condition(state: ChatbotState) -> str:
    routes = state.get("routes", [])
    if any(r in routes for r in ["direct_llm", "out_of_scope"]) and len(routes) == 1:
        return "answer_generator"
    return "retriever"


def check_grader_condition(state: ChatbotState) -> str:
    if not state.get("documents_relevant", True) and state.get("retrieval_retry_count", 0) <= 2:
        return "retriever"
    return "tool_executor"


def build_chatbot_graph() -> Any:
    """
    Constructs and compiles the 10-node LangGraph StateMachine:
    1. input_guard
    2. emergency_detector
    3. query_understanding
    4. router
    5. retriever
    6. document_grader
    7. tool_executor
    8. answer_generator
    9. grounding_verifier
    10. safety_postprocessor
    """
    workflow = StateGraph(ChatbotState)

    # Add Nodes
    workflow.add_node("input_guard", wrapped_input_guard)
    workflow.add_node("emergency_detector", wrapped_emergency_detector)
    workflow.add_node("query_understanding", wrapped_query_understanding)
    workflow.add_node("router", wrapped_router)
    workflow.add_node("retriever", wrapped_retriever)
    workflow.add_node("document_grader", wrapped_document_grader)
    workflow.add_node("tool_executor", wrapped_tool_executor)
    workflow.add_node("answer_generator", wrapped_answer_generator)
    workflow.add_node("grounding_verifier", wrapped_grounding_verifier)
    workflow.add_node("safety_postprocessor", wrapped_safety_postprocessor)

    # Edge: START -> input_guard
    workflow.add_edge(START, "input_guard")

    # Conditional: input_guard
    workflow.add_conditional_edges(
        "input_guard",
        check_guard_condition,
        {
            "safety_postprocessor": "safety_postprocessor",
            "emergency_detector": "emergency_detector",
        },
    )

    # Conditional: emergency_detector
    workflow.add_conditional_edges(
        "emergency_detector",
        check_emergency_condition,
        {
            "safety_postprocessor": "safety_postprocessor",
            "query_understanding": "query_understanding",
        },
    )

    # Edge: query_understanding -> router
    workflow.add_edge("query_understanding", "router")

    # Conditional: router
    workflow.add_conditional_edges(
        "router",
        check_router_condition,
        {
            "answer_generator": "answer_generator",
            "retriever": "retriever",
        },
    )

    # Edge: retriever -> document_grader
    workflow.add_edge("retriever", "document_grader")

    # Conditional: document_grader (CRAG loop)
    workflow.add_conditional_edges(
        "document_grader",
        check_grader_condition,
        {
            "retriever": "retriever",
            "tool_executor": "tool_executor",
        },
    )

    # Edge: tool_executor -> answer_generator
    workflow.add_edge("tool_executor", "answer_generator")

    # Edge: answer_generator -> grounding_verifier
    workflow.add_edge("answer_generator", "grounding_verifier")

    # Edge: grounding_verifier -> safety_postprocessor
    workflow.add_edge("grounding_verifier", "safety_postprocessor")

    # Edge: safety_postprocessor -> END
    workflow.add_edge("safety_postprocessor", END)

    compiled = workflow.compile()
    return compiled


# Pre-compiled singleton graph instance
chatbot_app = build_chatbot_graph()


async def run_chatbot_workflow(
    user_query: str,
    session_id: str,
    db: AsyncSession,
    current_user: Optional[User] = None,
    history: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Executes the full LangGraph state machine.
    """
    role = current_user.role.value if current_user else "guest"
    user_id = current_user.id if current_user else None
    # Load long‑term memories if enabled
    user_memories = []
    if current_user and getattr(current_user, "enable_memory", True):
        result = await db.execute(
            select(UserMemory).where(UserMemory.user_id == current_user.id)
        )
        mems = result.scalars().all()
        user_memories = [{"key": m.key, "value": m.value} for m in mems]

    initial_state: ChatbotState = {
        "user_query": user_query,
        "session_id": session_id,
        "user_id": user_id,
        "user_role": role,
        "history": history or [],
        "retrieval_retry_count": 0,
        "latency_records": {},
        "errors": [],
        "user_memories": user_memories,
    }
    
    config: RunnableConfig = {
        "configurable": {
            "db": db,
            "current_user": current_user,
        }
    }
    
    final_state = await chatbot_app.ainvoke(initial_state, config=config)
    return final_state
