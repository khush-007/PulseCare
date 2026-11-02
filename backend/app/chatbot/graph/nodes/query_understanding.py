import re
import time
from typing import Dict, Any, List
from backend.app.chatbot.graph.state import ChatbotState
from backend.app.chatbot.rag.query_transform import rewrite_query_with_history

SPECIALTIES = ["cardiology", "cardiologist", "neurology", "neurologist", "pediatrics", "pediatrician", "dermatology", "dermatologist", "orthopedics", "orthopedic", "general medicine", "family medicine"]
MEDICINES = ["amoxicillin", "lisinopril", "metformin", "atorvastatin", "ibuprofen", "paracetamol", "acetaminophen", "albuterol", "omeprazole"]
DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
NON_NAME_TERMS = {
    "what", "who", "tell", "about", "doctor", "dr", "consultation", "consult",
    "cardiac", "cardiology", "service", "services", "fee", "fees", "cost", "price",
    "available", "specialist", "profile", "clinic", "appointment", "her", "his",
    "their", "the", "is", "are", "for", "of", "how", "much",
}


def _doctor_name_from_query(query: str) -> str | None:
    
    explicit = re.search(
        r"\b(?:dr\.?|doctor)\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){0,2}?)(?=\s*(?:['’]s\b|[.,?!;:]|\s|$))",
        query,
        re.IGNORECASE,
    )

    if explicit:
        candidate = explicit.group(1).strip(" .,'’")
        name_words = []
        for word in candidate.split():
            if word.lower() in NON_NAME_TERMS:
                break
            name_words.append(word)
        candidate = re.sub(r"['’]s$", "", " ".join(name_words), flags=re.IGNORECASE)
        if candidate and not any(spec in candidate.lower() for spec in SPECIALTIES):
            return candidate.title()

    # Recognize a person-name-shaped fee query even without an honorific. This
    # prevents a misspelled/unknown doctor name from falling through to the
    # general services catalog and returning an unrelated service price.
    named_fee = re.search(
        r"\b([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){1,2})"
        r"(?:['’]s)?\s+(?:(?:consultation)\s+)?(?:fees?|costs?|prices?)\b",
        query,
        re.IGNORECASE,
    )
    if named_fee:
        candidate = named_fee.group(1).strip()
        words = candidate.lower().split()
        if not any(word in NON_NAME_TERMS for word in words) and not any(
            spec in candidate.lower() for spec in SPECIALTIES
        ):
            return candidate.title()

    return None


def _recent_doctor_context(history: List[Dict[str, str]], current_query: str) -> bool:
    prior_turns = history[-6:]
    if prior_turns and prior_turns[-1].get("role") == "user" and prior_turns[-1].get("content", "").strip().casefold() == current_query.strip().casefold():
        prior_turns = prior_turns[:-1]
    context = " ".join(turn.get("content", "") for turn in prior_turns)
    return bool(re.search(r"\b(?:dr\.?\s+[A-Za-z]+|doctor directory|verified specialists|doctor:)\b", context, re.IGNORECASE))




def _doctor_name_from_history(history: List[Dict[str, str]]) -> str | None:
    """Extract the full doctor name from recent conversation history."""
    for turn in reversed(history):
        content = turn.get("content", "")

        # Explicit doctor reference: Dr. Sarah Smith
        match = re.search(
            r"\bDr\.?\s+([A-Z][a-z'-]+(?:\s+[A-Z][a-z'-]+){0,2})",
            content,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        if turn.get("role") != "assistant":
            continue

        # Bold doctor name: **Sarah Smith**
        match = re.search(
            r"\*\*([A-Z][A-Za-z'-]+\s+[A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+)?)\*\*",
            content,
        )
        if match:
            return match.group(1).strip()

        # Plain-text profile: Physician Profile: Sarah Smith
        match = re.search(
            r"(?:Physician Profile|Doctor)\s*:\s*"
            r"([A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+){0,2})",
            content,
        )
        if match:
            return match.group(1).strip()

    return None

    """Extract a full doctor name from recent conversation history."""
    for turn in reversed(history):
        content = turn.get("content", "")

        # Explicit doctor reference, e.g. Dr. Sarah Smith
        match = re.search(
            r"\*\*([A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+){1,2})\*\*",
            content,
        )
        if match:
            return match.group(1).strip()

        # Doctor names displayed in assistant responses, e.g. **Sarah Smith**
        if turn.get("role") == "assistant":
            match = re.search(
                r"\*\*([A-Z][a-z]+(?:[-'][A-Za-z]+)?"
                r"\s+[A-Z][a-z]+(?:[-'][A-Za-z]+)?)\*\*",
                content,
            )
            if match:
                return match.group(1).strip()

            # Plain-text profile names, e.g. "Physician Profile: Sarah Smith"
            match = re.search(
                r"(?:Physician Profile|Doctor)\s*:\s*"
                r"([A-Z][a-z]+(?:[-'][A-Za-z]+)?"
                r"(?:\s+[A-Z][a-z]+(?:[-'][A-Za-z]+)?){0,2})",
                content,
            )
            if match:
                return match.group(1).strip()

    return None


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
    
    
    # Doctor Name Extraction
    doctor_name = _doctor_name_from_query(standalone)

    # Resolve pronoun-based follow-ups using the full name in conversation history.
    is_doctor_follow_up = bool(re.search(
        r"\b(?:he|she|his|her|they|their|him|them|unki|unke|unka|uski|uske|uska)\b|\baur\b",
        query,
        re.IGNORECASE,
    ))

    if is_doctor_follow_up and _recent_doctor_context(history, query):
        history_doctor = _doctor_name_from_history(history)
        if history_doctor:
            doctor_name = history_doctor

    # Recognize a bare doctor name only in an existing doctor conversation.
    if not doctor_name:
        bare_name = re.fullmatch(
            r"\s*([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){1,2})\s*[?.!]*\s*",
            query,
        )
        if bare_name and _recent_doctor_context(history, query):
            candidate = bare_name.group(1).strip()
            if not any(word.lower() in NON_NAME_TERMS for word in candidate.split()):
                doctor_name = candidate.title()

    if doctor_name:
        entities["doctor_name"] = doctor_name


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
