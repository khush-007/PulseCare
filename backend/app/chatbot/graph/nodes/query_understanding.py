import re
import time
from typing import Dict, Any, List
from backend.app.chatbot.graph.state import ChatbotState
from backend.app.chatbot.rag.query_transform import rewrite_query_with_history

DOCTOR_NAMES = ["sarah smith", "smith", "david chen", "chen", "priya patel", "patel", "elena garcia", "garcia", "robert taylor", "taylor"]
SPECIALTIES = ["cardiology", "cardiologist", "neurology", "neurologist", "pediatrics", "pediatrician", "dermatology", "dermatologist", "orthopedics", "orthopedic", "general medicine", "family medicine"]
MEDICINES = ["amoxicillin", "lisinopril", "metformin", "atorvastatin", "ibuprofen", "paracetamol", "acetaminophen", "albuterol", "omeprazole"]
DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def query_understanding_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 3: Query Understanding
    - Resolves conversational follow-ups and pronouns using sliding history.
    - Extracts structured domain entities (doctor, specialty, medicine, date).
    - Produces a standalone, disambiguated query.
    """
    start_time = time.time()
    query = state.get("sanitized_query") or state.get("user_query", "")
    history = state.get("history", [])

    # 1. Rewrite query with conversational history
    standalone = rewrite_query_with_history(query, history)

    # 2. Extract clinical domain entities
    entities: Dict[str, Any] = {}
    q_lower = standalone.lower()

    # Doctor Name Extraction: First check generic pattern (Dr. <Name> or Doctor <Name>)
    doc_match = re.search(r"\b(?:dr\.?|doctor)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b", standalone, re.IGNORECASE)
    if doc_match:
        cand_name = doc_match.group(1).strip()
        # Exclude common nouns and specialty names
        skip_words = ["visit", "appointment", "schedule", "profile", "fee", "hours", "office", "clinic"]
        if (not any(spec in cand_name.lower() for spec in SPECIALTIES) and 
            not any(cand_name.lower().startswith(sw) for sw in skip_words)):
            entities["doctor_name"] = cand_name.title()

    if "doctor_name" not in entities:
        for doc in DOCTOR_NAMES:
            if f"dr. {doc}" in q_lower or f"doctor {doc}" in q_lower or f"dr {doc}" in q_lower or doc in q_lower:
                entities["doctor_name"] = doc.title()
                break

    # Specialty Extraction
    for spec in SPECIALTIES:
        if spec in q_lower:
            # Map agent names to clinical specialty
            if "cardio" in spec:
                entities["specialty"] = "Cardiology"
            elif "neuro" in spec:
                entities["specialty"] = "Neurology"
            elif "pediatric" in spec:
                entities["specialty"] = "Pediatrics"
            elif "dermat" in spec:
                entities["specialty"] = "Dermatology"
            elif "ortho" in spec:
                entities["specialty"] = "Orthopedics"
            else:
                entities["specialty"] = "General Medicine"
            break

    # Medicine Extraction
    for med in MEDICINES:
        if med in q_lower:
            entities["medicine_name"] = med.title()
            break

    # Day of week
    for day in DAYS_OF_WEEK:
        if day in q_lower:
            entities["day_of_week"] = day.title()
            break

    # Date pattern (YYYY-MM-DD)
    date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", standalone)
    if date_match:
        entities["date"] = date_match.group(0)

    return {
        "standalone_query": standalone,
        "extracted_entities": entities,
        "latency_records": {**state.get("latency_records", {}), "query_understanding": (time.time() - start_time) * 1000},
    }
