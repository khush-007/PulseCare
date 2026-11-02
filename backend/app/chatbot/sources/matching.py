"""Shared request checks that keep doctor fees separate from service pricing."""

import re
from typing import Any, Mapping


def is_doctor_specific_fee_request(query: str, entities: Mapping[str, Any]) -> bool:
    if entities.get("doctor_name"):
        return True
    has_fee_question = bool(re.search(r"\b(fee|fees|cost|costs|price|prices|consultation)\b", query, re.IGNORECASE))
    if not has_fee_question:
        return False
    if re.search(r"\b(?:dr\.?|doctor|physician|specialist)\b", query, re.IGNORECASE):
        return True
    if re.search(r"\b(?:his|her|their)\b.{0,50}\b(?:fee|fees|cost|costs|price|prices)\b", query, re.IGNORECASE):
        return True
    named_fee = re.search(
        r"\b([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){1,2})"
        r"(?:['’]s)?\s+(?:(?:consultation)\s+)?(?:fees?|costs?|prices?)\b",
        query,
        re.IGNORECASE,
    )
    if not named_fee:
        return False
    non_name_terms = {
        "what", "who", "tell", "about", "doctor", "dr", "consultation", "consult",
        "cardiac", "cardiology", "service", "services", "fee", "fees", "cost", "price",
        "available", "specialist", "profile", "clinic", "appointment", "her", "his",
        "their", "the", "is", "are", "for", "of", "how", "much",
    }
    return not any(word.lower() in non_name_terms for word in named_fee.group(1).split())
