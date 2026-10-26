import re
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.deps import get_optional_current_user
from backend.app.models.user import User
from backend.app.models.triage import TriageAssessment, TriageSeverity
from backend.app.schemas.clinical import TriageRequest, TriageResponse

router = APIRouter(prefix="/triage", tags=["AI Triage Workflow"])

# Rule-based emergency indicators for the clinical triage engine
EMERGENCY_PATTERNS = [
    r"\b(chest pain|heart attack|crushing pressure|angina)\b",
    r"\b(difficulty breathing|can't breathe|shortness of breath|suffocating)\b",
    r"\b(stroke|facial droop|arm weakness|slurred speech)\b",
    r"\b(severe bleeding|uncontrolled bleeding|coughing blood)\b",
    r"\b(unconscious|passed out|loss of consciousness|seizure|convulsing)\b",
    r"\b(suicidal|kill myself|end my life|overdose)\b",
    r"\b(anaphylaxis|throat swelling|severe allergic reaction)\b",
]


@router.post("/assess", response_model=TriageResponse)
async def assess_symptoms(
    req: TriageRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Existing PulseCare Clinical Triage Workflow:
    Evaluates patient symptoms into Clinical Severity levels:
    - Emergency (Life-threatening, immediate 911 / ER)
    - Urgent (Requires prompt attention within hours)
    - Non-Urgent (Routine clinic consultation)
    - Self-Care (Mild symptoms manageable at home)
    """
    symptoms_lower = req.symptoms.lower()
    
    # 1. Emergency Check
    is_emergency = False
    for pat in EMERGENCY_PATTERNS:
        if re.search(pat, symptoms_lower):
            is_emergency = True
            break
            
    if is_emergency:
        severity = TriageSeverity.EMERGENCY
        action = (
            "CRITICAL MEDICAL EMERGENCY DETECTED: Call emergency services (911 in US/Canada, 112 in EU, 102/108 in India) "
            "immediately or proceed to the nearest Emergency Room. Do not drive yourself."
        )
        specialty = "Emergency Medicine"
        score = 9.8
        contacts = ["Emergency Services: 911", "Hospital ER Direct: 1-800-PULSE-911", "Crisis Lifeline: 988"]
    else:
        # Check for urgent symptoms
        urgent_keywords = ["high fever", "severe abdominal pain", "persistent vomiting", "deep wound", "fracture", "burn"]
        has_urgent = any(k in symptoms_lower for k in urgent_keywords)
        
        if has_urgent or (req.duration_days and req.duration_days >= 7):
            severity = TriageSeverity.URGENT
            action = "Urgent consultation recommended within 12-24 hours. Consider Urgent Care or same-day appointment."
            score = 6.5
            contacts = ["PulseCare Urgent Line: 1-800-PULSE-URGENT"]
        else:
            # Routine vs self-care
            if "mild" in symptoms_lower or "slight" in symptoms_lower or (req.duration_days and req.duration_days <= 2):
                severity = TriageSeverity.SELF_CARE
                action = "Mild symptoms detected. Rest, stay hydrated, and monitor condition. If symptoms worsen, schedule a consultation."
                score = 2.0
                contacts = ["PulseCare Health Advisory: 1-800-PULSE-CARE"]
            else:
                severity = TriageSeverity.NON_URGENT
                action = "Schedule a routine consultation with a specialist or general practitioner at PulseCare."
                score = 4.0
                contacts = ["PulseCare Appointments: 1-800-PULSE-CARE"]

        # Specialty inference
        if any(w in symptoms_lower for w in ["heart", "palpitation", "bp", "blood pressure"]):
            specialty = "Cardiology"
        elif any(w in symptoms_lower for w in ["skin", "rash", "acne", "itching"]):
            specialty = "Dermatology"
        elif any(w in symptoms_lower for w in ["headache", "migraine", "dizziness", "numbness"]):
            specialty = "Neurology"
        elif any(w in symptoms_lower for w in ["bone", "joint", "back pain", "knee"]):
            specialty = "Orthopedics"
        elif any(w in symptoms_lower for w in ["child", "pediatric", "infant", "baby"]):
            specialty = "Pediatrics"
        else:
            specialty = "General Medicine"

    # Persist triage assessment record
    triage_rec = TriageAssessment(
        patient_id=current_user.id if current_user else None,
        symptoms_text=req.symptoms,
        severity_level=severity.value,
        recommended_action=action,
        recommended_specialty=specialty,
        triage_score=score,
    )
    db.add(triage_rec)
    await db.commit()
    await db.refresh(triage_rec)
    
    return TriageResponse(
        severity_level=severity.value,
        is_emergency=is_emergency,
        recommended_action=action,
        recommended_specialty=specialty,
        emergency_contacts=contacts,
        triage_score=score,
    )
