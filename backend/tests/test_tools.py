import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.user import User
from backend.app.chatbot.tools.doctor_tools import search_doctors, get_doctor_profile
from backend.app.chatbot.tools.appointment_tools import get_my_appointments, propose_appointment_booking
from backend.app.chatbot.tools.medicine_tools import lookup_medicine
from backend.app.chatbot.tools.triage_tools import handoff_to_triage
from backend.app.chatbot.tools.service_tools import list_services


@pytest.mark.asyncio
async def test_search_doctors_live_db():
    async with AsyncSessionLocal() as session:
        res = await search_doctors(session, specialty="Cardiology")
        assert res["status"] == "success"
        assert res["count"] >= 1
        doc = res["doctors"][0]
        assert "Sarah Smith" in doc["name"]
        assert doc["specialty"] == "Cardiology"


@pytest.mark.asyncio
async def test_get_doctor_profile():
    async with AsyncSessionLocal() as session:
        res = await get_doctor_profile(session, doctor_id=1)
        assert res["status"] == "success"
        assert "Sarah Smith" in res["name"]
        assert "$150.00" in res["consultation_fee"]


@pytest.mark.asyncio
async def test_list_services():
    async with AsyncSessionLocal() as session:
        res = await list_services(session, department="Cardiology")
        assert res["status"] == "success"
        assert len(res["services"]) >= 1
        assert "Cardiac" in res["services"][0]["name"]


@pytest.mark.asyncio
async def test_get_my_appointments_unauthenticated():
    async with AsyncSessionLocal() as session:
        res = await get_my_appointments(session, current_user=None)
        assert res["status"] == "unauthorized"
        assert "logged in" in res["message"]


@pytest.mark.asyncio
async def test_get_my_appointments_authenticated_john_doe():
    async with AsyncSessionLocal() as session:
        # Load user John Doe (id=2 in seed data)
        from sqlalchemy.future import select
        res_u = await session.execute(select(User).where(User.email == "john.doe@example.com"))
        john = res_u.scalars().first()
        assert john is not None

        res = await get_my_appointments(session, current_user=john)
        assert res["status"] == "success"
        assert res["patient_name"] == "John Doe"
        assert res["count"] >= 1
        # John's appointment is with Dr. Sarah Smith
        assert any("Sarah Smith" in a["doctor"] for a in res["appointments"])


@pytest.mark.asyncio
async def test_cross_user_data_isolation():
    async with AsyncSessionLocal() as session:
        from sqlalchemy.future import select
        res_jane = await session.execute(select(User).where(User.email == "jane.smith@example.com"))
        jane = res_jane.scalars().first()
        assert jane is not None

        res = await get_my_appointments(session, current_user=jane)
        assert res["status"] == "success"
        assert res["patient_name"] == "Jane Smith"
        # Jane cannot see John Doe's appointments!
        assert not any("Sarah Smith" in a["doctor"] for a in res["appointments"])
        assert any("Elena Garcia" in a["doctor"] for a in res["appointments"])


@pytest.mark.asyncio
async def test_lookup_medicine_internal_db():
    async with AsyncSessionLocal() as session:
        res = await lookup_medicine(session, name="Amoxicillin")
        assert res["status"] == "found_internal"
        assert res["medicine_name"] == "Amoxicillin"
        assert "Bacterial" in res["indications"]
        assert res["requires_prescription"] is True


@pytest.mark.asyncio
async def test_handoff_to_triage():
    async with AsyncSessionLocal() as session:
        res = await handoff_to_triage(session, current_user=None, symptom_text="Mild fever and slight sore throat for 1 day")
        assert res["status"] == "triage_assessed"
        assert res["severity_level"] in ["self_care", "non_urgent"]
        assert "PulseCare" in res["handoff_note"]


@pytest.mark.asyncio
async def test_propose_booking_non_destructive():
    async with AsyncSessionLocal() as session:
        res = await propose_appointment_booking(session, doctor_id=1, preferred_date="2026-10-30")
        assert res["status"] == "proposal"
        assert res["requires_confirmation"] is True
        assert "/portal/appointments/book" in res["booking_url"]
