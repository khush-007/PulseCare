import asyncio
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.user import User
from backend.app.chatbot.tools.schemas import (
    SearchDoctorsInput,
    DoctorProfileInput,
    DoctorAvailabilityInput,
    ListServicesInput,
    GetMyAppointmentsInput,
    LookupMedicineInput,
    HandoffToTriageInput,
    ProposeAppointmentBookingInput,
)
from backend.app.chatbot.tools.doctor_tools import (
    search_doctors,
    get_doctor_profile,
    get_doctor_availability,
)
from backend.app.chatbot.tools.service_tools import list_services
from backend.app.chatbot.tools.appointment_tools import (
    get_my_appointments,
    propose_appointment_booking,
)
from backend.app.chatbot.tools.medicine_tools import lookup_medicine
from backend.app.chatbot.tools.triage_tools import handoff_to_triage

logger = logging.getLogger("pulsecare.chatbot.tools")


async def execute_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    db: AsyncSession,
    current_user: Optional[User] = None,
    timeout_seconds: float = 6.0,
) -> Dict[str, Any]:
    """
    Safely execute a tool with strict Pydantic validation, timeouts,
    server-side authorization, and structured error handling.
    """
    logger.info(f"Executing tool: {tool_name}")
    try:
        if tool_name == "search_doctors":
            validated = SearchDoctorsInput(**tool_args)
            coro = search_doctors(
                db=db,
                specialty=validated.specialty,
                name=validated.name,
                day_of_week=validated.day_of_week,
            )
            return await asyncio.wait_for(coro, timeout=timeout_seconds)

        elif tool_name == "get_doctor_profile":
            validated = DoctorProfileInput(**tool_args)
            coro = get_doctor_profile(db=db, doctor_id=validated.doctor_id)
            return await asyncio.wait_for(coro, timeout=timeout_seconds)

        elif tool_name == "get_doctor_availability":
            validated = DoctorAvailabilityInput(**tool_args)
            coro = get_doctor_availability(
                db=db,
                doctor_id=validated.doctor_id,
                date_str=validated.date_str,
            )
            return await asyncio.wait_for(coro, timeout=timeout_seconds)

        elif tool_name == "list_services":
            validated = ListServicesInput(**tool_args)
            coro = list_services(db=db, department=validated.department)
            return await asyncio.wait_for(coro, timeout=timeout_seconds)

        elif tool_name == "get_my_appointments":
            # Strict authorization: identity taken ONLY from authenticated current_user
            coro = get_my_appointments(db=db, current_user=current_user)
            return await asyncio.wait_for(coro, timeout=timeout_seconds)

        elif tool_name == "lookup_medicine":
            validated = LookupMedicineInput(**tool_args)
            coro = lookup_medicine(db=db, name=validated.name)
            return await asyncio.wait_for(coro, timeout=timeout_seconds)

        elif tool_name == "handoff_to_triage":
            validated = HandoffToTriageInput(**tool_args)
            coro = handoff_to_triage(
                db=db,
                current_user=current_user,
                symptom_text=validated.symptom_text,
            )
            return await asyncio.wait_for(coro, timeout=timeout_seconds)

        elif tool_name == "propose_appointment_booking":
            validated = ProposeAppointmentBookingInput(**tool_args)
            coro = propose_appointment_booking(
                db=db,
                doctor_id=validated.doctor_id,
                preferred_date=validated.preferred_date,
                preferred_time=validated.preferred_time,
                reason=validated.reason,
            )
            return await asyncio.wait_for(coro, timeout=timeout_seconds)

        else:
            return {
                "status": "error",
                "message": f"Unknown tool: '{tool_name}'",
            }

    except asyncio.TimeoutError:
        logger.error(f"Timeout executing tool {tool_name}")
        return {
            "status": "error",
            "message": f"Tool '{tool_name}' timed out after {timeout_seconds} seconds.",
        }
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Could not complete {tool_name}: {str(e)}",
        }
