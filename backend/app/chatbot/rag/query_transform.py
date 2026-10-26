import re
from typing import List, Optional
from backend.app.core.config import settings


def rewrite_query_with_history(query: str, history: List[dict]) -> str:
    """
    Resolve coreferences, pronouns (e.g. 'he', 'she', 'that doctor', 'this medicine')
    and conversational context to produce a standalone query.
    """
    if not history:
        return query.strip()

    # Get the last 2-3 assistant and user messages
    recent_turns = history[-4:]
    context_text = " ".join([t.get("content", "") for t in recent_turns])

    # Check for pronoun or contextual follow-up indicators
    follow_up_cues = [" he ", " she ", " his ", " her ", " they ", " that ", " this ", " it ", " their "]
    has_cue = any(cue in f" {query.lower()} " for cue in follow_up_cues)
    
    # Extract entities from recent context if follow-up detected
    if has_cue:
        # Check if recent context mentioned a doctor
        doc_match = re.search(r"\b(Dr\.\s+[A-Za-z]+(?:\s+[A-Za-z]+)?)\b", context_text)
        med_match = re.search(r"\b(Amoxicillin|Lisinopril|Metformin|Atorvastatin|Ibuprofen|Paracetamol|Albuterol|Omeprazole)\b", context_text, re.IGNORECASE)
        spec_match = re.search(r"\b(Cardiology|Neurology|Pediatrics|Dermatology|Orthopedics)\b", context_text, re.IGNORECASE)
        
        rewritten = query
        if doc_match and any(p in query.lower() for p in ["he", "she", "his", "her", "that doctor"]):
            rewritten = f"{query} [regarding {doc_match.group(1)}]"
        elif med_match and any(p in query.lower() for p in ["it", "this medicine", "that drug", "dosage"]):
            rewritten = f"{query} [regarding {med_match.group(1)}]"
        elif spec_match and any(p in query.lower() for p in ["they", "there", "department"]):
            rewritten = f"{query} [department: {spec_match.group(1)}]"
            
        return rewritten.strip()

    return query.strip()


def expand_queries(query: str) -> List[str]:
    """
    Generate query expansions and synonyms to improve retrieval recall.
    """
    queries = [query]
    q_lower = query.lower()
    
    # Domain expansions
    if "book" in q_lower or "schedule" in q_lower or "appointment" in q_lower:
        queries.append(f"how to book appointment in PulseCare portal {query}")
    if "doctor" in q_lower or "specialist" in q_lower:
        queries.append(f"PulseCare doctor directory available specialties {query}")
    if "cost" in q_lower or "fee" in q_lower or "price" in q_lower:
        queries.append(f"consultation fee medical services pricing {query}")
    if "cancel" in q_lower or "reschedule" in q_lower:
        queries.append(f"cancellation policy refund 24 hours notice {query}")
    if "insurance" in q_lower or "coverage" in q_lower:
        queries.append(f"insurance plans accepted Blue Cross Medicare {query}")
    if "triage" in q_lower or "symptom" in q_lower:
        queries.append(f"PulseCare AI clinical triage severity assessment {query}")

    return list(dict.fromkeys(queries))  # Deduplicate preserving order
