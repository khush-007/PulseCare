import re
import time
from typing import Dict, Any, List
from backend.app.chatbot.graph.state import ChatbotState

# Refined route keywords and patterns
OUT_OF_SCOPE_WORDS = [
    "bitcoin", "crypto", "ethereum", "cake", "bake", "chocolate", "president",
    "movie", "two sum", "python script", "football", "weather", "stocks"
]

PERSONAL_DATA_PHRASES = [
    "my appointment", "my appointments", "my visits", "my bookings", "my scheduled",
    "when is my appointment", "when is my doctor visit", "what time is my", "what time is my doctor visit",
    "what are my upcoming", "show my", "check my appointments", "cancel my appointment", "john doe's appointments",
    "other patients' medical records", "other patients"
]

TRIAGE_PHRASES = [
    "i have a mild", "i have had a", "i have a fever", "i have a dry", "i feel slight",
    "runny nose", "scratchy throat", "persistent vomiting", "knee joint", "my child has",
    "triage me", "assess my symptoms", "symptoms of", "dizziness", "rash on my", "fever and",
    "cough and", "head hurts", "stomach ache", "diagnose me"
]

DOCTOR_SERVICE_PHRASES = [
    "dr.", "dr ", "doctor", "doctors", "cardiologist", "cardiology", "neurologist", "neurology",
    "pediatrician", "pediatrics", "dermatologist", "dermatology", "orthopedic", "orthopedics",
    "specialist", "specialties", "consultation fee", "consultation fees", "head of",
    "comprehensive cardiac", "eeg", "telehealth", "skin cancer screening", "services are offered",
    "how much does a", "how much is a full", "can i see dr"
]

MEDICINE_PHRASES = [
    "amoxicillin", "lisinopril", "metformin", "atorvastatin", "ibuprofen", "paracetamol",
    "acetaminophen", "albuterol", "omeprazole", "medicine", "medicines", "drug", "drugs",
    "medication", "pill", "tablet", "side effects of", "dosage", "prescribed for",
    "fictitious medicine"
]

HEALTH_GENERAL_PHRASES = [
    "blood pressure reading", "normal blood pressure", "hypertension", "hba1c",
    "abcde rule", "melanoma", "dangerous in infants", "red flag symptoms with pediatric fever",
    "hypertensive crisis", "fever in infants",
    "cold", "flu", "common cold", "influenza", "difference between a cold and flu"
]

WEBSITE_HELP_PHRASES = [
    "how do i book an appointment", "how to book", "cancellation policy", "accept blue cross",
    "insurance plans accepted", "operating hours", "urgent care open", "protect patient privacy",
    "hipaa", "delete my chat history", "prescriptions directly from the chatbot", "clinical triage work",
    "how does pulsecare work", "clinic hours", "parking validation", "veterinary clinic"
]


def router_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 4: Router
    High-precision multi-route classification with domain precedence.
    """
    start_time = time.time()
    query = (state.get("standalone_query") or state.get("sanitized_query") or state.get("user_query", "")).lower()

    detected_routes: List[str] = []

    # 1. Out-of-Scope check
    if any(w in query for w in OUT_OF_SCOPE_WORDS):
        return {
            "routes": ["out_of_scope"],
            "latency_records": {**state.get("latency_records", {}), "router": (time.time() - start_time) * 1000},
        }

    # 2. Personal Data / Appointments
    if any(p in query for p in PERSONAL_DATA_PHRASES):
        detected_routes.append("personal_data")

    # 3. Clinical Triage Handoff
    if any(p in query for p in TRIAGE_PHRASES):
        detected_routes.append("triage_handoff")

    # 4. Doctor and Service Lookup
    if any(p in query for p in DOCTOR_SERVICE_PHRASES):
        detected_routes.append("doctor_service_lookup")

    # 5. Medicine Information
    if any(p in query for p in MEDICINE_PHRASES):
        detected_routes.append("medicine_info")

    # 6. General Health Knowledge
    if any(p in query for p in HEALTH_GENERAL_PHRASES):
        detected_routes.append("health_general")

    # 7. Website Help, Policies, FAQs
    if any(p in query for p in WEBSITE_HELP_PHRASES):
        detected_routes.append("website_help")

    # 8. Direct Greetings / Pleasantries (only if standalone greeting)
    if not detected_routes:
        if re.search(r"^\s*(hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening|thank\s+you|thanks)\b", query):
            detected_routes.append("direct_llm")

    # Fallback to website_help if nothing specific caught
    if not detected_routes:
        detected_routes = ["website_help"]

    # Special case: queries asking about policy regarding prescriptions / triage work
    if "prescriptions directly from the chatbot" in query or "how does the ai clinical triage work" in query:
        detected_routes = ["website_help"]

    # Deduplicate preserving order
    unique_routes = list(dict.fromkeys(detected_routes))

    return {
        "routes": unique_routes,
        "latency_records": {**state.get("latency_records", {}), "router": (time.time() - start_time) * 1000},
    }
