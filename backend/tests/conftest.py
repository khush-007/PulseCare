import asyncio
import pytest
from backend.app.core.database import init_db, AsyncSessionLocal
from backend.app.models.user import User, UserRole
from backend.app.core.security import hash_password
from backend.app.models.doctor import Doctor
from backend.app.models.service import MedicalService
from backend.app.models.medicine import Medicine
from backend.app.models.chatbot import KnowledgeDocumentChunk
import json
from backend.app.models.appointment import Appointment, AppointmentStatus
from backend.app.chatbot.rag.embeddings import get_embedding
from backend.app.core.config import settings

# Async fixture that creates tables and seeds deterministic test data.
# It runs once per test session and uses the test SQLite DB defined in settings.
@pytest.fixture(scope="session", autouse=True)
async def init_and_seed_db():
    """Initialize schema and populate required seed data for the test suite.
    The fixture is async so we can await DB operations without blocking.
    """
    # Ensure tables exist.
    await init_db()
    async with AsyncSessionLocal() as session:
        # Clean up any leftover data (order respects FK constraints)
        from sqlalchemy import delete
        await session.execute(delete(KnowledgeDocumentChunk))
        await session.execute(delete(Medicine))
        await session.execute(delete(Appointment))
        await session.execute(delete(MedicalService))
        await session.execute(delete(Doctor))
        await session.execute(delete(User))
        await session.flush()
        # --- Users ---------------------------------------------------
        john = User(
            email="john.doe@example.com",
            full_name="John Doe",
            hashed_password=hash_password("hashed"),
            role=UserRole.PATIENT,
            enable_memory=True,
        )
        jane = User(
            email="jane.smith@example.com",
            full_name="Jane Smith",
            hashed_password=hash_password("hashed"),
            role=UserRole.PATIENT,
            enable_memory=True,
        )
        dr_user = User(
            email="dr.sarah@example.com",
            full_name="Sarah Smith",
            hashed_password=hash_password("hashed"),
            role=UserRole.DOCTOR,
            enable_memory=False,
        )
        session.add_all([john, jane, dr_user])
        await session.flush()  # assign IDs
        # Disable external medicine API for deterministic tests
        settings.FEATURE_EXTERNAL_MEDICINE_API = False

        # --- Doctor profile ------------------------------------------
        doctor = Doctor(
            user_id=dr_user.id,
            specialty="Cardiology",
            qualifications="MD Cardiology",
            bio="Experienced cardiologist.",
            consultation_fee=150.0,
            is_available=True,
            available_days="Monday,Tuesday,Wednesday,Thursday,Friday",
            available_time_start="09:00",
            available_time_end="17:00",
        )
        session.add(doctor)
        await session.flush()  # assign doctor.id
        # --- Additional Doctor for Jane ---
        elena_user = User(
            email="elena.garcia@example.com",
            full_name="Elena Garcia",
            hashed_password="hashed",
            role=UserRole.DOCTOR,
            enable_memory=False,
        )
        session.add(elena_user)
        await session.flush()  # assign elena user id
        elena_doctor = Doctor(
            user_id=elena_user.id,
            specialty="General",
            qualifications="MD General",
            bio="General practitioner.",
            consultation_fee=120.0,
            is_available=True,
            available_days="Monday,Tuesday,Wednesday,Thursday,Friday",
            available_time_start="09:00",
            available_time_end="17:00",
        )
        session.add(elena_doctor)
        await session.flush()  # assign elena doctor id
        # --- Appointment for Jane with Elena ---
        jane_appointment = Appointment(
            patient_id=jane.id,
            doctor_id=elena_doctor.id,
            appointment_date="2026-11-02",
            appointment_time="11:00",
            status=AppointmentStatus.SCHEDULED,
            reason="General checkup",
            notes="General checkup",
        )
        session.add(jane_appointment)

        # --- Medical Service -----------------------------------------
        cardio_service = MedicalService(
            name="Cardiac Consultation",
            department="Cardiology",
            description="Standard cardiology appointment.",
            base_fee=250.0,
            duration_minutes=30,
        )
        session.add(cardio_service)
        # Seed an appointment for John Doe with Dr. Sarah Smith
# import moved to top earlier
        appointment = Appointment(
            patient_id=john.id,
            doctor_id=doctor.id,
            appointment_date="2026-11-01",
            appointment_time="10:00",
            status=AppointmentStatus.SCHEDULED,
            reason="Initial consultation",
            notes="Initial consultation",
        )
        session.add(appointment)

        # --- Medicine -----------------------------------------------
        amox = Medicine(
            name="Amoxicillin",
            generic_name="Amoxicillin",
            dosage_form="Tablet",
            standard_dosage="500 mg",
            indications="Bacterial infections",
            contraindications="Penicillin allergy",
            side_effects="Nausea, rash",
            requires_prescription=True,
            price=15.0,
        )
        session.add(amox)

        # --- Knowledge Document Chunks for RAG -----------------------
        embed_faq_cancel = get_embedding("The appointment cancellation policy allows you to cancel up to 24 hours in advance without penalty.")
        embed_faq_insurance = get_embedding("PulseCare accepts Blue Cross, Medicare, and most major insurers.")
        faq_cancel = KnowledgeDocumentChunk(
            doc_id="faq_001",
            chunk_index=0,
            title="Appointment Cancellation Policy",
            section="Policies",
            content="The appointment cancellation policy allows you to cancel up to 24 hours in advance without penalty.",
            doc_type="faq",
            trust_level="official",
            source_url="https://example.com/policy",
            last_updated="2026-01-01",
            embedding_json=json.dumps(embed_faq_cancel),
            metadata_json="{}",
        )
        faq_insurance = KnowledgeDocumentChunk(
            doc_id="faq_002",
            chunk_index=0,
            title="Insurance Acceptance",
            section="Policies",
            content="PulseCare accepts Blue Cross, Medicare, and most major insurers. Insurance coverage is extensive.",
            doc_type="faq",
            trust_level="official",
            source_url="https://example.com/insurance",
            last_updated="2026-01-01",
            embedding_json=json.dumps(embed_faq_insurance),
            metadata_json="{}",
        )
        session.add_all([faq_cancel, faq_insurance])
        # Add a policy document chunk for metadata filter tests
        policy_chunk = KnowledgeDocumentChunk(
            doc_id="policy_001",
            chunk_index=0,
            title="Cancellation and Insurance Policy",
            section="Policies",
            content="The appointment cancellation policy allows you to cancel up to 24 hours in advance without penalty. PulseCare accepts Blue Cross, Medicare, and most major insurers.",
            doc_type="policy",
            trust_level="official",
            source_url="https://example.com/policy",
            last_updated="2026-01-01",
            embedding_json=json.dumps(get_embedding("The appointment cancellation policy allows you to cancel up to 24 hours in advance without penalty. PulseCare accepts Blue Cross, Medicare, and most major insurers.")),
            metadata_json="{}",
        )
        session.add(policy_chunk)
        # Commit all seeded data within the async context before the session is closed
        await session.commit()
