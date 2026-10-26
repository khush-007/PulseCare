from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.user import User
from backend.app.schemas.clinical import TriageRequest
from backend.app.routers.triage import assess_symptoms


async def handoff_to_triage(
    db: AsyncSession,
    current_user: Optional[User],
    symptom_text: str,
) -> Dict[str, Any]:
    """
    Hands off symptom descriptions directly to the EXISTING PulseCare clinical triage engine.
    STRICT COMPLIANCE: Does NOT re-implement triage logic; delegates to the established workflow.
    """
    req = TriageRequest(
        symptoms=symptom_text,
        duration_days=1,
    )
    triage_result = await assess_symptoms(req=req, current_user=current_user, db=db)
    
    return {
        "status": "triage_assessed",
        "severity_level": triage_result.severity_level,
        "is_emergency": triage_result.is_emergency,
        "recommended_action": triage_result.recommended_action,
        "recommended_specialty": triage_result.recommended_specialty,
        "emergency_contacts": triage_result.emergency_contacts,
        "triage_score": triage_result.triage_score,
        "handoff_note": "Evaluated by PulseCare Clinical Triage Workflow.",
    }
