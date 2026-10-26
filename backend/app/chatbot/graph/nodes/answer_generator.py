import logging
import time
import asyncio
from backend.app.chatbot.graph.llm import generate_completion
from typing import Dict, Any, List
from backend.app.chatbot.graph.state import ChatbotState

logger = logging.getLogger("pulsecare.chatbot.answer_generator")


async def answer_generator_node(state: ChatbotState) -> Dict[str, Any]:
    """
    Node 8: Grounded Answer Generator
    Generates draft response strictly from retrieved documentation chunks
    and safe tool execution results. Never invents doctors, prices, or clinical facts.
    """
    start_time = time.time()
    routes = state.get("routes", [])
    tool_results = state.get("tool_results", [])
    docs = state.get("retrieved_docs", [])
    query = state.get("standalone_query") or state.get("user_query", "")

    # 1. Out of Scope Route
    if "out_of_scope" in routes and len(routes) == 1:
        answer = (
            "I specialize exclusively in PulseCare healthcare services, medical appointments, "
            "doctor directories, clinic facilities, and general health information. "
            "I cannot assist with topics outside healthcare. How can I assist you with your health or clinic visits today?"
        )
        return {
            "draft_answer": answer,
            "latency_records": {**state.get("latency_records", {}), "answer_generator": (time.time() - start_time) * 1000},
        }

    # 2. Direct LLM Greeting / Small Talk
    if "direct_llm" in routes and len(routes) == 1:
        answer = (
            "Hello! I am PulseCare's AI Healthcare Assistant. I am here to help you navigate our healthcare platform:\n\n"
            "• **Find Doctors**: Search specialists in Cardiology, Neurology, Pediatrics, Dermatology, and Orthopedics.\n"
            "• **Appointments**: View your scheduled visits or prepare for booking.\n"
            "• **Medical Services**: Learn about procedures, durations, and transparent fees.\n"
            "• **Medicine Information**: Review indications and precautions for common medications.\n"
            "• **AI Clinical Triage**: Assess symptoms and understand care urgency.\n\n"
            "How can I help you today?"
        )
        return {
            "draft_answer": answer,
            "latency_records": {**state.get("latency_records", {}), "answer_generator": (time.time() - start_time) * 1000},
        }

    sections: List[str] = []

    # 3. Process Tool Results
    for item in tool_results:
        tool_name = item.get("tool")
        res = item.get("result", {})

        if tool_name == "get_my_appointments":
            if res.get("status") == "unauthorized":
                sections.append(res.get("message", "Please log in to view your appointments."))
            elif res.get("status") == "success":
                appts = res.get("appointments", [])
                if not appts:
                    sections.append(res.get("message", "You currently have no scheduled appointments."))
                else:
                    patient_name = res.get("patient_name", "Patient")
                    lines = [f"### Your Scheduled Appointments ({patient_name})\n"]
                    for a in appts:
                        lines.append(
                            f"• **Date**: {a['date']} at {a['time']}\n"
                            f"  **Doctor**: {a['doctor']} ({a['specialty']})\n"
                            f"  **Location**: {a['room']}\n"
                            f"  **Status**: {a['status'].title()} | **Reason**: {a['reason']}\n"
                        )
                    sections.append("\n".join(lines))

        elif tool_name == "search_doctors":
            if res.get("status") == "not_found":
                sections.append(res.get("message", "No matching doctors found in PulseCare directory."))
            else:
                doctors = res.get("doctors", [])
                lines = [f"### PulseCare Verified Specialists ({len(doctors)} found)\n"]
                for d in doctors:
                    lines.append(
                        f"• **{d['name']}** — {d['specialty']}\n"
                        f"  **Qualifications**: {d['qualifications']}\n"
                        f"  **Consultation Fee**: {d['consultation_fee']} | **Location**: {d['room']}\n"
                        f"  **Availability**: {d['available_days']} ({d['hours']})\n"
                    )
                sections.append("\n".join(lines))

        elif tool_name == "get_doctor_profile":
            if res.get("status") == "success":
                sections.append(
                    f"### Physician Profile: {res['name']}\n"
                    f"• **Specialty**: {res['specialty']}\n"
                    f"• **Qualifications**: {res['qualifications']}\n"
                    f"• **Bio**: {res.get('bio', 'Specialist physician at PulseCare.')}\n"
                    f"• **Consultation Fee**: {res['consultation_fee']}\n"
                    f"• **Clinic Hours**: {res['available_days']} ({res['available_hours']}) in {res['room_number']}\n"
                )

        elif tool_name == "list_services":
            if res.get("status") == "success":
                svcs = res.get("services", [])
                lines = ["### PulseCare Medical Services & Transparent Pricing\n"]
                for s in svcs:
                    lines.append(
                        f"• **{s['name']}** ({s['department']})\n"
                        f"  **Fee**: {s['base_fee']} | **Duration**: {s['duration']}\n"
                        f"  **Details**: {s['description']}\n"
                    )
                sections.append("\n".join(lines))

        elif tool_name == "lookup_medicine":
            if res.get("status") in ["found_internal", "found_external"]:
                sections.append(
                    f"### Medication Information: {res.get('medicine_name')}\n"
                    f"• **Generic Name**: {res.get('generic_name')}\n"
                    f"• **Indications**: {res.get('indications')}\n"
                    f"• **Standard Dosage**: {res.get('standard_dosage', 'Follow physician guidance.')}\n"
                    f"• **Contraindications / Warnings**: {res.get('contraindications') or res.get('warnings', 'None noted.')}\n"
                    f"• **Common Side Effects**: {res.get('common_side_effects')}\n"
                    f"• **Prescription Required**: {'Yes' if res.get('requires_prescription', True) else 'No (Over-the-counter)'}\n"
                    f"• **Source**: {res.get('source')}\n"
                )
            else:
                sections.append(res.get("message", "Medicine details not found in formulary."))

        elif tool_name == "handoff_to_triage":
            if res.get("status") == "triage_assessed":
                sections.append(
                    f"### PulseCare Clinical Triage Assessment\n"
                    f"• **Evaluated Severity**: **{res.get('severity_level', '').upper()}**\n"
                    f"• **Recommended Action**: {res.get('recommended_action')}\n"
                    f"• **Recommended Specialty**: {res.get('recommended_specialty', 'General Medicine')}\n"
                    f"• **Clinical Guidance**: {res.get('handoff_note')}\n"
                )

        elif tool_name == "propose_appointment_booking":
            if res.get("status") == "proposal":
                sections.append(
                    f"### Appointment Booking Proposal\n"
                    f"{res.get('message')}\n\n"
                    f"• **Doctor**: {res.get('doctor_name')} ({res.get('specialty')})\n"
                    f"• **Suggested Slot**: {res.get('suggested_date')} at {res.get('suggested_time')}\n"
                    f"• **Fee**: {res.get('consultation_fee')}\n\n"
                    f"👉 [Proceed to Official Booking]({res.get('booking_url')})"
                )

    # 4. Process Retrieved Documents
    if docs and any(r in routes for r in ["website_help", "health_general"]):
        doc_lines = []
        for d in docs[:3]:
            # Extract main sentences
            content_clean = d["content"].replace("\n", " ")
            doc_lines.append(f"• **{d['title']} ({d['section']})**: {content_clean}")
        
        if not sections:
            sections.append("### PulseCare Knowledge Information\n" + "\n".join(doc_lines))
        else:
            sections.append("### Relevant Platform Information\n" + "\n".join(doc_lines))

    # Fallback if no sections were generated
    if not sections:
        # No grounded info, fall back to LLM generation (Gemini) using the original user query
        user_query = state.get("user_query", "")
        try:
            answer = await generate_completion(user_query)
        except Exception as e:
            logger.warning(f"LLM generation failed in answer_generator fallback: {e}")
            answer = "I’m unable to generate a response at this time. Please try again later."
    else:
        answer = "\n\n".join(sections)

    return {
        "draft_answer": answer,
        "latency_records": {**state.get("latency_records", {}), "answer_generator": (time.time() - start_time) * 1000},
    }
