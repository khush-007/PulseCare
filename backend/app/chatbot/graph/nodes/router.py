import json
import re
import time
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.chatbot.graph.llm import generate_completion
from backend.app.chatbot.graph.state import ChatbotState

Intent = Literal[
    "general_health", "doctor_service_lookup", "application_help", "follow_up",
    "triage", "emergency", "out_of_scope", "patient_records", "medicine_info",
]


class IntentClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intents: List[Intent] = Field(min_length=1, max_length=5)


INTENT_SYSTEM_PROMPT = """Classify the latest message for the PulseCare healthcare assistant.
Use recent conversation only to resolve a follow-up. Choose one or more intents from:
general_health, doctor_service_lookup, application_help, follow_up, triage,
emergency, out_of_scope, patient_records, medicine_info.
Medical symptoms that request assessment are triage unless emergency signs are present.
Questions asking for general definitions, causes, or explanations of health topics are
general_health; triage is for a user reporting symptoms or requesting an assessment.
Questions asking whether something is healthy, unhealthy, safe, harmful, or beneficial
for health are general_health, including informal wording such as 'is sugar healthy or not?'.
Do not mark a clearly health-related question out of scope just because it is informal.
Return only a JSON object: {\"intents\":[...]} using the allowed labels. Do not answer."""


def _is_app_doctor_navigation_request(query: str) -> bool:
    q = query.lower()
    has_app_context = any(term in q for term in ("pulsecare", "on the app", "in the app", "portal", "website"))
    navigation_phrase = bool(re.search(
        r"\b(how\s+(?:can|do)\s+i\s+find|where\s+can\s+i\s+find|how\s+to\s+find)\b.*\bdoctor", q
    ))
    hinglish_navigation = bool(re.search(
        r"\bdoctor\b.*\b(kaise|kahan)\b.*\b(app|pulsecare|portal)\b|"
        r"\b(app|pulsecare|portal)\b.*\bdoctor\b.*\b(kaise|kahan)\b", q
    ))
    return has_app_context and (navigation_phrase or hinglish_navigation) and not re.search(
        r"\b(?:fee|cost|price|consultation)\b", q
    )


def _is_clear_general_health_question(query: str) -> bool:
    """Recognize plainly phrased health-education questions the classifier may miss."""
    q = query.lower().strip()
    return bool(re.search(
        r"\b(?:is|are|was|were|does|do|can|should|what|which|why)\b"
        r".{0,100}\b(?:healthy|unhealthy|safe|harmful|sehat|swasth|health benefits?|good for (?:your |my )?health|bad for (?:your |my )?health)\b",
        q,
    )) or bool(re.search(r"\bkya\b.{0,60}\b(?:sehat|swasth|healthy|safe)\b", q))


def _is_general_health_education_question(query: str) -> bool:
    """Distinguish educational questions about symptoms from a personal triage request."""
    q = query.lower().strip()
    asks_for_education = bool(re.search(
        r"^\s*(?:what\s+(?:is|are)|what\s+causes|common\s+causes\s+of|"
        r"explain|define|how\s+does|why\s+(?:do|does|is|are))\b",
        q,
    ))
    health_topic = bool(re.search(
        r"\b(headache|migraine|fever|cough|rash|cold|flu|blood pressure|"
        r"blood sugar|diabetes|sugar|nutrition|sleep|hypertension|symptom|health)\b",
        q,
    ))
    return asks_for_education and health_topic


def _conservative_fallback(query: str, history: List[Dict[str, str]]) -> List[str]:
    q = query.lower()
    routes: List[str] = []
    if re.search(r"\b(my|mera|meri|mere)\b.*\b(appointment|booking|visit|appt)\b|\bappointment\s+(hai|kab)\b", q):
        routes.append("personal_data")
    if re.search(r"\b(chest pain|can't breathe|cannot breathe|stroke|overdose|suicid|severe bleeding)\b", q):
        routes.append("triage_handoff")
    elif re.search(r"\b(fever|pain|cough|rash|symptom|dard|bukhar|khansi|chakkar|headache|sick|ill)\b", q):
        routes.append("triage_handoff")
    if re.search(r"\b(doctor|dr\.?|cardiolog|neurolog|pediatric|dermatolog|orthop|specialist|fee|cost|service|doctor|doctor|doc)\b", q):
        routes.append("doctor_service_lookup")
    if re.search(r"\b(medicine|medication|drug|tablet|pill|dosage|side effects|amoxicillin|metformin|ibuprofen|paracetamol)\b", q):
        routes.append("medicine_info")
    if re.search(r"\b(pulsecare|app|website|book|cancel|insurance|clinic|how to use|feature|policy|support|chat history)\b", q):
        routes.append("website_help")
    if re.search(r"\b(health|blood pressure|diabetes|cold|flu|nutrition|sleep|hba1c|hypertension)\b", q):
        routes.append("health_general")
    if _is_clear_general_health_question(q):
        routes.append("health_general")
    if _is_general_health_education_question(q):
        routes = [route for route in routes if route != "triage_handoff"]
        routes.append("health_general")
    if not routes and re.search(r"\b(he|she|it|they|that|this|aur|uska|iska|yeh|woh)\b", q) and history:
        routes.extend(["follow_up", "health_general"])
    if not routes and re.search(r"\b(hi|hello|hey|namaste|namaskar|thanks|thank you)\b", q):
        routes.append("direct_llm")
    if not routes:
        routes.append("out_of_scope")
    return list(dict.fromkeys(routes))


async def router_node(state: ChatbotState) -> Dict[str, Any]:
    """Schema-validated intent classification; deterministic safety remains authoritative."""
    start_time = time.time()
    query = (state.get("standalone_query") or state.get("sanitized_query") or state.get("user_query", "")).strip()
    history = state.get("history", [])[-6:]
    if re.fullmatch(r"\s*(hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening|namaste|thanks|thank\s+you)[\w\s!.,?]*", query, re.IGNORECASE):
        return {
            "routes": ["direct_llm"],
            "intent_classification": ["application_help"],
            "latency_records": {**state.get("latency_records", {}), "router": (time.time() - start_time) * 1000},
        }
    prompt = json.dumps({"message": query, "recent_history": history}, ensure_ascii=False)
    try:
        raw = await generate_completion(prompt, system_prompt=INTENT_SYSTEM_PROMPT, temperature=0)
        classification = IntentClassification.model_validate_json(raw)
        labels = classification.intents
        routes = []
        for label in labels:
            if label == "application_help": routes.append("website_help")
            elif label == "general_health": routes.append("health_general")
            elif label in {"triage", "emergency"}: routes.append("triage_handoff")
            elif label == "patient_records": routes.append("personal_data")
            else: routes.append(label)
        if "follow_up" in routes:
            routes.remove("follow_up")
            # Keep follow-up intent metadata while routing via its classified topic.
            if not any(r in routes for r in ("health_general", "doctor_service_lookup", "website_help", "medicine_info", "personal_data", "triage_handoff")):
                routes.extend(_conservative_fallback(query, history))
        routes = list(dict.fromkeys(routes))
        if "out_of_scope" in routes and len(routes) > 1:
            routes = ["out_of_scope"]
        if not routes:
            routes = ["out_of_scope"]
    except (ValidationError, ValueError, TypeError):
        routes = _conservative_fallback(query, history)
    except Exception:
        # Provider failure is visible in the node error and uses a conservative local classifier.
        routes = _conservative_fallback(query, history)

    # Rule-based emergency detector runs earlier; this check is defense in depth.
    if re.search(r"\b(chest\s+pain|can't\s+breathe|stroke|overdose|suicid|severe\s+bleeding)\b", query.lower()):
        routes = ["triage_handoff"]
    elif _is_app_doctor_navigation_request(query):
        # Finding where the directory lives is app help; it is not a request to
        # claim that a particular doctor exists or return a directory record.
        routes = ["website_help"]
        labels = ["application_help"]
    elif _is_general_health_education_question(query):
        # Asking about common causes is education, not a report of symptoms.
        # The emergency detector earlier in the graph remains authoritative.
        routes = ["health_general"]
        labels = ["general_health"]
    elif _is_clear_general_health_question(query):
        # A clear health-education question remains in scope even if the LLM
        # classifier incorrectly labels it out_of_scope.
        routes = ["health_general"]
        labels = ["general_health"]
    elif state.get("extracted_entities", {}).get("doctor_name"):
        # Entity extraction is authoritative for public directory lookup. A
        # provider classification must not turn a doctor name into a generic
        # service search or an out-of-scope refusal.
        routes = ["doctor_service_lookup"]
        labels = ["doctor_service_lookup"]

    return {
        "routes": routes,
        "intent_classification": labels if 'labels' in locals() else routes,
        "latency_records": {**state.get("latency_records", {}), "router": (time.time() - start_time) * 1000},
    }
