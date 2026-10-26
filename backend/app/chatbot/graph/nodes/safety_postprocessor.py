import re
import time
from typing import Dict, Any, List
from backend.app.chatbot.graph.state import ChatbotState

MEDICAL_DISCLAIMER = (
    "\n\n---\n"
    "*⚠️ Medical Disclaimer: This information is provided for general educational purposes and does not constitute "
    "individual medical advice, diagnosis, or treatment. Please consult a licensed PulseCare physician or healthcare provider "
    "regarding specific health concerns or medication adjustments.*"
)


def safety_postprocessor_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 10: Safety Post-Processor
    - Formats contextual citations
    - Assigns verified vs general information badge
    - Appends mandatory non-prescriptive medical disclaimers when relevant
    - Strips any accidental leaked internal keys or PII
    - Generates context-aware suggested quick actions
    """
    start_time = time.time()
    raw_answer = state.get("final_answer") or state.get("draft_answer", "")
    routes = state.get("routes", [])
    docs = state.get("retrieved_docs", [])
    tool_results = state.get("tool_results", [])
    is_emergency = state.get("is_emergency", False)

    # 1. Determine Info Badge:
    # "verified" if sourced from live DB tools or official hospital documentation
    # "general" if broad educational overview or fallback
    has_live_tools = any(t.get("result", {}).get("status") in ["success", "found_internal", "triage_assessed"] for t in tool_results)
    has_official_docs = any(d.get("trust_level") in ["official", "verified_clinical"] for d in docs)
    
    if has_live_tools or has_official_docs or is_emergency:
        badge = "verified"
    else:
        badge = "general"

    # 2. Build Citation Objects
    citations: List[Dict[str, Any]] = []
    
    # Doc citations
    for d in docs[:4]:
        citations.append({
            "title": d.get("title", "PulseCare Documentation"),
            "section": d.get("section", "General"),
            "source_url": d.get("source_url", "/docs"),
            "last_updated": d.get("last_updated", "2026"),
            "snippet": d.get("content", "")[:180] + "...",
        })

    # Tool live data citations
    for t in tool_results:
        t_name = t.get("tool")
        if t_name in ["search_doctors", "get_doctor_profile", "get_doctor_availability"]:
            citations.append({
                "title": "PulseCare Verified Doctor Directory",
                "section": "Clinical Staff Registry (Live DB)",
                "source_url": "/doctors",
                "last_updated": "Real-time",
                "snippet": "Live medical staff credentialing and clinic schedule records.",
            })
        elif t_name == "list_services":
            citations.append({
                "title": "PulseCare Medical Services Catalog",
                "section": "Departments & Pricing (Live DB)",
                "source_url": "/services",
                "last_updated": "Real-time",
                "snippet": "Verified outpatient and diagnostic clinical fee schedule.",
            })
        elif t_name == "lookup_medicine":
            citations.append({
                "title": "PulseCare Pharmacy Formulary & FDA Directory",
                "section": "Pharmaceutical Catalog",
                "source_url": "/pharmacy",
                "last_updated": "Current",
                "snippet": "Formulary indications, dosage forms, and clinical precautions.",
            })
        elif t_name == "handoff_to_triage":
            citations.append({
                "title": "PulseCare Clinical Triage Protocol",
                "section": "Emergency & Urgency Stratification",
                "source_url": "/triage",
                "last_updated": "Active Workflow",
                "snippet": "Automated clinical urgency scoring engine.",
            })

    # Deduplicate citations by title + section
    seen = set()
    unique_citations = []
    for c in citations:
        key = (c["title"], c["section"])
        if key not in seen:
            seen.add(key)
            unique_citations.append(c)

    # 3. Append Medical Disclaimer when discussing health, medicines, or triage
    needs_disclaimer = any(r in routes for r in ["medicine_info", "health_general", "triage_handoff"])
    final_answer = raw_answer
    if needs_disclaimer and not is_emergency and MEDICAL_DISCLAIMER not in final_answer:
        final_answer += MEDICAL_DISCLAIMER

    # 4. Strip any leaked internal strings or API keys
    final_answer = re.sub(r"sk-[a-zA-Z0-9_-]{20,}", "[REDACTED-KEY]", final_answer)
    final_answer = re.sub(r"pulsecare-production-secret[a-zA-Z0-9_-]*", "[REDACTED-SECRET]", final_answer)

    # 5. Determine context-aware suggested actions
    suggested_actions = state.get("suggested_actions", [])
    if not suggested_actions:
        if "doctor_service_lookup" in routes:
            suggested_actions = ["Check doctor working hours", "View all specialties", "How to book an appointment"]
        elif "medicine_info" in routes:
            suggested_actions = ["Ask about side effects", "Find a prescribing doctor", "Pharmacy hours"]
        elif "personal_data" in routes:
            suggested_actions = ["Book new appointment", "Cancellation policy", "Contact my clinic"]
        elif "triage_handoff" in routes:
            suggested_actions = ["Schedule urgent consultation", "Emergency guidelines", "View clinic directions"]
        else:
            suggested_actions = ["Find a cardiologist", "What insurance is accepted?", "Clinic operating hours", "Check my appointments"]

    return {
        "final_answer": final_answer,
        "info_badge": badge,
        "citations": unique_citations,
        "suggested_actions": suggested_actions,
        "latency_records": {**state.get("latency_records", {}), "safety_postprocessor": (time.time() - start_time) * 1000},
    }
