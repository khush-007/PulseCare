import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select
from backend.app.core.database import AsyncSessionLocal, init_db
from backend.app.core.security import hash_password
from backend.app.models.user import User, UserRole
from backend.app.models.doctor import Doctor
from backend.app.models.appointment import Appointment, AppointmentStatus
from backend.app.models.service import MedicalService
from backend.app.models.medicine import Medicine


async def seed():
    print("[Seed] Initializing database tables...")
    await init_db()

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        res = await session.execute(select(User).where(User.email == "admin@pulsecare.com"))
        if res.scalars().first():
            print("[Seed] Database already seeded. Skipping.")
            return

        print("[Seed] Inserting Users and Doctors...")
        # Admin
        admin = User(
            email="admin@pulsecare.com",
            full_name="PulseCare System Administrator",
            hashed_password=hash_password("admin123"),
            role=UserRole.ADMIN,
            phone="1-800-PULSE-ADMIN",
            is_active=True,
        )
        session.add(admin)

        # Patients
        patient1 = User(
            email="john.doe@example.com",
            full_name="John Doe",
            hashed_password=hash_password("patient123"),
            role=UserRole.PATIENT,
            phone="555-0101",
            is_active=True,
        )
        patient2 = User(
            email="jane.smith@example.com",
            full_name="Jane Smith",
            hashed_password=hash_password("patient123"),
            role=UserRole.PATIENT,
            phone="555-0102",
            is_active=True,
        )
        session.add_all([patient1, patient2])
        await session.flush()

        # Doctor Users
        doc_sarah_user = User(
            email="dr.smith@pulsecare.com",
            full_name="Dr. Sarah Smith",
            hashed_password=hash_password("doctor123"),
            role=UserRole.DOCTOR,
            phone="555-0201",
            is_active=True,
        )
        doc_david_user = User(
            email="dr.chen@pulsecare.com",
            full_name="Dr. David Chen",
            hashed_password=hash_password("doctor123"),
            role=UserRole.DOCTOR,
            phone="555-0202",
            is_active=True,
        )
        doc_priya_user = User(
            email="dr.patel@pulsecare.com",
            full_name="Dr. Priya Patel",
            hashed_password=hash_password("doctor123"),
            role=UserRole.DOCTOR,
            phone="555-0203",
            is_active=True,
        )
        doc_elena_user = User(
            email="dr.garcia@pulsecare.com",
            full_name="Dr. Elena Garcia",
            hashed_password=hash_password("doctor123"),
            role=UserRole.DOCTOR,
            phone="555-0204",
            is_active=True,
        )
        doc_robert_user = User(
            email="dr.taylor@pulsecare.com",
            full_name="Dr. Robert Taylor",
            hashed_password=hash_password("doctor123"),
            role=UserRole.DOCTOR,
            phone="555-0205",
            is_active=True,
        )
        session.add_all([doc_sarah_user, doc_david_user, doc_priya_user, doc_elena_user, doc_robert_user])
        await session.flush()

        # Doctor Clinical Profiles
        doc_sarah = Doctor(
            user_id=doc_sarah_user.id,
            specialty="Cardiology",
            qualifications="MD, FACC - Harvard Medical School",
            bio="Board-certified cardiologist with 14 years experience specializing in coronary artery disease, heart failure, and preventive cardiology.",
            consultation_fee=150.0,
            available_days="Monday,Tuesday,Wednesday,Thursday,Friday",
            available_time_start="09:00",
            available_time_end="16:00",
            room_number="Suite 204 (Heart Center)",
            is_available=True,
        )
        doc_david = Doctor(
            user_id=doc_david_user.id,
            specialty="Neurology",
            qualifications="MD, PhD - Johns Hopkins University",
            bio="Senior neurologist focusing on headache disorders, epilepsy, stroke rehabilitation, and neuro-diagnostics.",
            consultation_fee=180.0,
            available_days="Monday,Tuesday,Wednesday,Thursday",
            available_time_start="10:00",
            available_time_end="17:00",
            room_number="Suite 305 (Neuroscience Wing)",
            is_available=True,
        )
        doc_priya = Doctor(
            user_id=doc_priya_user.id,
            specialty="Pediatrics",
            qualifications="MBBS, MD - Stanford Health Care",
            bio="Dedicated pediatrician with expertise in child development, immunizations, adolescent care, and pediatric asthma.",
            consultation_fee=120.0,
            available_days="Tuesday,Wednesday,Thursday,Friday,Saturday",
            available_time_start="08:30",
            available_time_end="15:30",
            room_number="Suite 108 (Children's Pavilion)",
            is_available=True,
        )
        doc_elena = Doctor(
            user_id=doc_elena_user.id,
            specialty="Dermatology",
            qualifications="MD - Columbia University College of Physicians and Surgeons",
            bio="Dermatologist specializing in medical dermatology, eczema, psoriasis, skin cancer screening, and acne management.",
            consultation_fee=130.0,
            available_days="Monday,Wednesday,Friday",
            available_time_start="09:00",
            available_time_end="17:00",
            room_number="Suite 210 (Dermatology Clinic)",
            is_available=True,
        )
        doc_robert = Doctor(
            user_id=doc_robert_user.id,
            specialty="Orthopedics",
            qualifications="MD, FAAOS - Mayo Clinic College of Medicine",
            bio="Orthopedic specialist treating sports injuries, joint replacement, spinal health, and osteoarthritis.",
            consultation_fee=160.0,
            available_days="Monday,Tuesday,Wednesday,Thursday",
            available_time_start="09:00",
            available_time_end="16:30",
            room_number="Suite 115 (Orthopedics & Sports Care)",
            is_available=True,
        )
        session.add_all([doc_sarah, doc_david, doc_priya, doc_elena, doc_robert])
        await session.flush()

        print("[Seed] Inserting Medical Services...")
        services = [
            MedicalService(
                name="Comprehensive Cardiac Evaluation",
                department="Cardiology",
                description="Electrocardiogram (ECG), blood pressure profiling, cholesterol review, and physician examination.",
                base_fee=250.0,
                duration_minutes=45,
                is_active=True,
            ),
            MedicalService(
                name="Neurological Screening & EEG",
                department="Neurology",
                description="Full neurological physical evaluation and EEG wave diagnostic monitoring.",
                base_fee=320.0,
                duration_minutes=60,
                is_active=True,
            ),
            MedicalService(
                name="Pediatric Well-Child Checkup",
                department="Pediatrics",
                description="Growth tracking, developmental milestones assessment, and routine vaccinations.",
                base_fee=120.0,
                duration_minutes=30,
                is_active=True,
            ),
            MedicalService(
                name="Full-Body Skin Cancer Screening",
                department="Dermatology",
                description="Dermoscopic examination of moles, lesions, and high-risk skin variations.",
                base_fee=160.0,
                duration_minutes=30,
                is_active=True,
            ),
            MedicalService(
                name="Orthopedic Joint Assessment & Digital X-Ray",
                department="Orthopedics",
                description="Mobility assessment, joint stability testing, and localized 2-view digital imaging.",
                base_fee=210.0,
                duration_minutes=45,
                is_active=True,
            ),
            MedicalService(
                name="Preventive Annual Wellness Exam",
                department="General Medicine",
                description="Comprehensive baseline physical, vital signs check, lab referrals, and lifestyle counseling.",
                base_fee=95.0,
                duration_minutes=30,
                is_active=True,
            ),
            MedicalService(
                name="Telehealth Virtual Consultation",
                department="General Medicine",
                description="Secure video consultation for acute non-emergency conditions, follow-ups, and prescription refills.",
                base_fee=75.0,
                duration_minutes=20,
                is_active=True,
            ),
        ]
        session.add_all(services)

        print("[Seed] Inserting Medicines Catalog...")
        medicines = [
            Medicine(
                name="Amoxicillin",
                generic_name="Amoxicillin Trihydrate",
                dosage_form="Capsule",
                standard_dosage="500 mg orally every 8 hours for 7-10 days",
                indications="Bacterial infections including ear infections, pneumonia, streptococcal pharyngitis, and skin infections.",
                contraindications="Hypersensitivity to penicillin or cephalosporin class antibiotics.",
                side_effects="Nausea, diarrhea, mild rash, headache.",
                requires_prescription=True,
                price=14.50,
            ),
            Medicine(
                name="Lisinopril",
                generic_name="Lisinopril",
                dosage_form="Tablet",
                standard_dosage="10 mg orally once daily in the morning",
                indications="Hypertension (high blood pressure) and heart failure management; post-myocardial infarction recovery.",
                contraindications="History of angioedema related to ACE inhibitors; pregnancy (fetal toxicity risk).",
                side_effects="Dry persistent cough, dizziness, elevated potassium levels, headache.",
                requires_prescription=True,
                price=12.00,
            ),
            Medicine(
                name="Metformin",
                generic_name="Metformin Hydrochloride",
                dosage_form="Tablet",
                standard_dosage="500 mg orally twice daily with meals",
                indications="Type 2 diabetes mellitus management alongside diet and exercise to lower blood glucose.",
                contraindications="Severe renal impairment (eGFR < 30 mL/min), acute metabolic acidosis, severe hypoxemia.",
                side_effects="Gastrointestinal upset, diarrhea, metallic taste, nausea.",
                requires_prescription=True,
                price=10.50,
            ),
            Medicine(
                name="Atorvastatin",
                generic_name="Atorvastatin Calcium",
                dosage_form="Tablet",
                standard_dosage="20 mg orally once daily in the evening",
                indications="Hypercholesterolemia (elevated LDL cholesterol) and reduction of cardiovascular disease risk.",
                contraindications="Active liver disease, unexplained persistent elevations in hepatic transaminases, pregnancy.",
                side_effects="Muscle aches (myalgia), joint pain, slight elevations in blood glucose, indigestion.",
                requires_prescription=True,
                price=18.00,
            ),
            Medicine(
                name="Ibuprofen",
                generic_name="Ibuprofen",
                dosage_form="Tablet",
                standard_dosage="200 mg to 400 mg orally every 4 to 6 hours as needed (maximum 1200 mg/day OTC)",
                indications="Mild to moderate pain, inflammation, headache, musculoskeletal pain, and fever reduction.",
                contraindications="Active peptic ulcer disease, severe heart failure, third trimester of pregnancy, NSAID allergy.",
                side_effects="Stomach irritation, heartburn, fluid retention, nausea.",
                requires_prescription=False,
                price=8.00,
            ),
            Medicine(
                name="Paracetamol",
                generic_name="Acetaminophen",
                dosage_form="Tablet",
                standard_dosage="500 mg to 1000 mg orally every 4 to 6 hours as needed (maximum 3000 mg/day)",
                indications="Mild to moderate pain relief and fever reduction; suitable for patients with gastrointestinal sensitivity.",
                contraindications="Severe hepatic impairment, active severe liver disease, chronic heavy alcohol consumption.",
                side_effects="Rare at recommended doses; risk of severe liver toxicity if daily limit is exceeded.",
                requires_prescription=False,
                price=6.50,
            ),
            Medicine(
                name="Albuterol Inhaler",
                generic_name="Albuterol Sulfate",
                dosage_form="Aerosol Inhaler (HFA)",
                standard_dosage="2 inhalations every 4 to 6 hours as needed for bronchospasm or 15 minutes before exercise",
                indications="Treatment and prevention of acute bronchospasm in patients with reversible obstructive airway disease / asthma.",
                contraindications="Hypersensitivity to albuterol or milk proteins (in dry powder formulations).",
                side_effects="Tremor, nervousness, palpitations, tachycardia, throat irritation.",
                requires_prescription=True,
                price=35.00,
            ),
            Medicine(
                name="Omeprazole",
                generic_name="Omeprazole",
                dosage_form="Delayed-Release Capsule",
                standard_dosage="20 mg orally once daily before breakfast for 14 to 28 days",
                indications="Gastroesophageal reflux disease (GERD), heartburn, erosive esophagitis, and duodenal ulcers.",
                contraindications="Known hypersensitivity to substituted benzimidazoles; co-administration with rilpivirine.",
                side_effects="Headache, abdominal pain, diarrhea, nausea, vitamin B12 deficiency on long-term therapy.",
                requires_prescription=False,
                price=15.00,
            ),
        ]
        session.add_all(medicines)

        print("[Seed] Inserting Sample Patient Appointments...")
        tomorrow_str = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
        next_week_str = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

        appts = [
            Appointment(
                patient_id=patient1.id,
                doctor_id=doc_sarah.id,
                appointment_date=tomorrow_str,
                appointment_time="10:00",
                status=AppointmentStatus.SCHEDULED,
                reason="Routine blood pressure checkup and follow-up on cardiovascular wellness.",
                notes="Patient requested morning slot. Bring previous lipid panel results.",
            ),
            Appointment(
                patient_id=patient1.id,
                doctor_id=doc_david.id,
                appointment_date=next_week_str,
                appointment_time="14:30",
                status=AppointmentStatus.SCHEDULED,
                reason="Consultation regarding mild recurring tension headaches.",
                notes="Recommended to keep a symptom diary before the session.",
            ),
            Appointment(
                patient_id=patient2.id,
                doctor_id=doc_elena.id,
                appointment_date=tomorrow_str,
                appointment_time="11:15",
                status=AppointmentStatus.SCHEDULED,
                reason="Annual skin spot check and rash assessment.",
                notes="Patient Jane Smith appointment.",
            ),
        ]
        session.add_all(appts)

        await session.commit()
        print("[Seed] Successfully seeded PulseCare database!")


if __name__ == "__main__":
    asyncio.run(seed())
