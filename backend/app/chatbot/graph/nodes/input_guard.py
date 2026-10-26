import re
import time
from typing import Dict, Any
from backend.app.core.config import settings
from backend.app.chatbot.graph.state import ChatbotState

# Prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"reveal\s+(the\s+)?(system\s+prompt|developer\s+instructions)",
    r"system\s*prompt",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"\bdan\b",
    r"dan\s+mode",
    r"jailbreak",
    r"bypass\s+safety",
    r"disregard\s+all\s+(guidelines|instructions)",
    r"act\s+as\s+an\s+unrestricted",
    r"unrestricted\s+ai",
    r"what\s+is\s+your\s+secret\s+key",
    r"what\s+is\s+your\s+api\s+token",
]

# PII Patterns for redaction
EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
PHONE_PATTERN = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"


def input_guard_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 1: Input Guard
    - Checks length limits
    - Detects prompt injection / jailbreak attempts
    - Masks PII to protect patient privacy
    """
    start_time = time.time()
    raw_query = state.get("user_query", "").strip()

    # 1. Length Check
    if len(raw_query) > settings.CHAT_MAX_INPUT_LENGTH:
        return {
            "guard_triggered": True,
            "guard_response": (
                f"Your message exceeds the maximum allowed length of {settings.CHAT_MAX_INPUT_LENGTH} characters. "
                "Please shorten your question."
            ),
            "final_answer": (
                f"Your message exceeds the maximum allowed length of {settings.CHAT_MAX_INPUT_LENGTH} characters. "
                "Please shorten your question."
            ),
            "info_badge": "general",
            "latency_records": {**state.get("latency_records", {}), "input_guard": (time.time() - start_time) * 1000},
        }

    # 2. Prompt Injection Detection
    query_lower = raw_query.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query_lower):
            return {
                "guard_triggered": True,
                "guard_response": (
                    "I am PulseCare's healthcare assistant. I cannot modify my system instructions, "
                    "reveal system prompts, or bypass safety policies. How can I assist you with healthcare services or appointments?"
                ),
                "final_answer": (
                    "I am PulseCare's healthcare assistant. I cannot modify my system instructions, "
                    "reveal system prompts, or bypass safety policies. How can I assist you with healthcare services or appointments?"
                ),
                "info_badge": "general",
                "latency_records": {**state.get("latency_records", {}), "input_guard": (time.time() - start_time) * 1000},
            }

    # 3. PII Masking
    sanitized = raw_query
    # Mask SSN / ID
    sanitized = re.sub(SSN_PATTERN, "[REDACTED-SSN]", sanitized)
    # Mask Phone
    sanitized = re.sub(PHONE_PATTERN, "[REDACTED-PHONE]", sanitized)

    return {
        "sanitized_query": sanitized,
        "guard_triggered": False,
        "latency_records": {**state.get("latency_records", {}), "input_guard": (time.time() - start_time) * 1000},
    }
