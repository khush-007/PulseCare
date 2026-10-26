import re
import time
from typing import Dict, Any
from backend.app.chatbot.graph.state import ChatbotState

# Critical emergency indicator patterns
EMERGENCY_REGEX_PATTERNS = [
    r"\b(chest\s+pain|crushing\s+(chest\s+)?pressure|heart\s+attack|angina)\b",
    r"\b(can'?t\s+breathe|difficulty\s+breathing|shortness\s+of\s+breath|gasping(\s+for\s+air)?|choking|suffocating)\b",
    r"\b(stroke|facial\s+droop\w*|face(\s+\w+)?\s+droop\w*|arm\s+weakness|slurr\w*\s+speech|speech(\s+\w+)?\s+slurr\w*|sudden\s+paralysis)\b",
    r"\b(severe\s+bleeding|uncontrolled\s+(severe\s+)?bleeding|coughing\s+(up\s+)?blood)\b",
    r"\b(unconscious|passed\s+out|blackout|seizure|convulsions)\b",
    r"\b(suicid(e|al)|kill\s+myself|end\s+my\s+life|want\s+to\s+die)\b",
    r"\b(overdose|swallowed\s+poison|ingested\s+bleach|poisoning)\b",
    r"\b(anaphylaxis|throat\s+swelling|severe\s+allergic\s+reaction)\b",
]


def emergency_detector_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 2: Emergency Detector
    Rule-based + high-priority detection of life-threatening symptoms.
    Instantly short-circuits the pipeline to deliver immediate emergency instructions.
    """
    start_time = time.time()
    query = state.get("sanitized_query") or state.get("user_query", "")
    query_lower = query.lower()

    is_emergency = False
    triggered_category = ""

    for pattern in EMERGENCY_REGEX_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            is_emergency = True
            triggered_category = match.group(0)
            break

    if is_emergency:
        is_crisis = (
            "suicid" in triggered_category
            or "kill myself" in triggered_category
            or "want to die" in triggered_category
            or "end my life" in triggered_category
        )

        if is_crisis:
            response = (
                "🚨 **URGENT CRISIS SUPPORT** 🚨\n\n"
                "If you or someone you know is struggling or in crisis, help is available right now:\n\n"
                "• **National Suicide & Crisis Lifeline**: Call or text **988** (available 24/7, free, confidential)\n"
                "• **Crisis Text Line**: Text **HOME** to **741741**\n"
                "• **Emergency Services**: Call **911** (US/Canada) or **112** (EU/UK) or your local emergency number immediately.\n\n"
                "You are not alone, and support is available at any time."
            )
        else:
            response = (
                "🚨 **MEDICAL EMERGENCY DETECTED** 🚨\n\n"
                "The symptoms you described may indicate a critical, life-threatening emergency:\n\n"
                "1. **Call Emergency Services Immediately**: Dial **112** (India/International), **911** (US/Canada), or **102/108** (India).\n"
                "2. **Seek Immediate Emergency Care**: Proceed directly to the nearest hospital Emergency Room. **Do not attempt to drive yourself.**\n"
                "3. **PulseCare Emergency Pavilion**: If you are near our facility, the Emergency Pavilion is open 24/7/365 for urgent care.\n\n"
                "The AI assistant cannot diagnose or manage emergency conditions. Please seek immediate human medical assistance."
            )

        return {
            "is_emergency": True,
            "emergency_response": response,
            "final_answer": response,
            "info_badge": "verified",
            "suggested_actions": ["Call 911 / Emergency Services", "Find Nearest Emergency Room", "Contact 988 Crisis Lifeline"],
            "latency_records": {**state.get("latency_records", {}), "emergency_detector": (time.time() - start_time) * 1000},
        }

    return {
        "is_emergency": False,
        "latency_records": {**state.get("latency_records", {}), "emergency_detector": (time.time() - start_time) * 1000},
    }
