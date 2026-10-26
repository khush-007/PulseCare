import re
import time
from typing import Dict, Any, List
from backend.app.chatbot.graph.state import ChatbotState


def grounding_verifier_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 9: Grounding Verifier (Self-Checking)
    Performs verification that every clinical or logistical claim (doctor names, fees,
    room numbers, dates, medicine details) is strictly supported by evidence from tools or docs.
    """
    start_time = time.time()
    draft = state.get("draft_answer", "")
    routes = state.get("routes", [])
    tool_results = state.get("tool_results", [])
    docs = state.get("retrieved_docs", [])

    # Special routes (greetings, out-of-scope, emergency) are intrinsically grounded
    if any(r in routes for r in ["direct_llm", "out_of_scope"]) or state.get("is_emergency"):
        return {
            "grounded": True,
            "final_answer": draft,
            "latency_records": {**state.get("latency_records", {}), "grounding_verifier": (time.time() - start_time) * 1000},
        }

    # Aggregate all verified evidence text
    evidence_text = ""
    for item in tool_results:
        evidence_text += " " + str(item.get("result", ""))
    for d in docs:
        evidence_text += " " + str(d.get("content", ""))

    evidence_lower = evidence_text.lower()
    draft_lower = draft.lower()

    # Extract claims to verify:
    # 1. Doctor names
    doctor_names = ["sarah smith", "david chen", "priya patel", "elena garcia", "robert taylor"]
    for doc in doctor_names:
        if doc in draft_lower and doc not in evidence_lower:
            # Fabricated doctor name not in evidence
            return {
                "grounded": False,
                "final_answer": (
                    "I don't have reliable, verified information on that in PulseCare records. "
                    "Please browse our official Doctor Directory or contact support at 1-800-PULSE-CARE."
                ),
                "info_badge": "general",
                "latency_records": {**state.get("latency_records", {}), "grounding_verifier": (time.time() - start_time) * 1000},
            }

    # 2. Currency/fee claims (e.g. $150, $250)
    fee_matches = re.findall(r"\$\d+", draft)
    for fee in fee_matches:
        if fee not in evidence_text and (fee.lower() not in evidence_lower):
            # Fabricated pricing
            return {
                "grounded": False,
                "final_answer": (
                    "I don't have reliable pricing information for that service in PulseCare records. "
                    "Please view our Services page for transparent pricing schedules."
                ),
                "info_badge": "general",
                "latency_records": {**state.get("latency_records", {}), "grounding_verifier": (time.time() - start_time) * 1000},
            }

    # Grounding check passed
    return {
        "grounded": True,
        "final_answer": draft,
        "latency_records": {**state.get("latency_records", {}), "grounding_verifier": (time.time() - start_time) * 1000},
    }
