from typing import List, Dict, Any, Optional, TypedDict


class ChatbotState(TypedDict, total=False):
    # User Long‑term memory (key‑value pairs)
    user_memories: List[Dict[str, Any]]
    # User Context
    user_query: str
    session_id: str
    user_id: Optional[int]
    user_role: str  # "guest", "patient", "doctor", "admin"
    history: List[Dict[str, str]]

    # Step 1: Input Guard
    sanitized_query: str
    guard_triggered: bool
    guard_response: Optional[str]

    # Step 2: Emergency Detector
    is_emergency: bool
    emergency_response: Optional[str]

    # Step 3: Query Understanding
    standalone_query: str
    extracted_entities: Dict[str, Any]

    # Step 4: Router
    routes: List[str]  # e.g. ["doctor_service_lookup", "medicine_info"]

    # Step 5: Retrieval
    retrieved_docs: List[Dict[str, Any]]
    retrieval_retry_count: int

    # Step 6: Tool Execution
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]

    # Step 7: Document Grader (CRAG)
    documents_relevant: bool

    # Step 8: Answer Generation
    draft_answer: str

    # Step 9: Grounding Verifier
    grounded: bool

    # Step 10: Safety Post-Processor
    final_answer: str
    info_badge: str  # "verified" or "general"
    citations: List[Dict[str, Any]]
    suggested_actions: List[str]

    # Telemetry
    latency_records: Dict[str, float]
    errors: List[str]
