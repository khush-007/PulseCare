import time
from typing import Dict, Any, Optional
import urllib.request
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.app.core.config import settings
from backend.app.models.medicine import Medicine

# In-memory TTL cache for external medicine lookups
_medicine_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


async def lookup_medicine(
    db: AsyncSession,
    name: str,
) -> Dict[str, Any]:
    """
    Look up clinical medication information:
    1. Primary: Internal PulseCare Medicine Catalog
    2. Secondary: Cached external OpenFDA API lookup
    """
    clean_name = name.strip()
    
    # 1. Search internal database
    result = await db.execute(
        select(Medicine).where(
            (Medicine.name.ilike(f"%{clean_name}%")) | 
            (Medicine.generic_name.ilike(f"%{clean_name}%"))
        )
    )
    med = result.scalars().first()
    
    if med:
        return {
            "status": "found_internal",
            "source": "PulseCare Pharmacy Formulary",
            "medicine_name": med.name,
            "generic_name": med.generic_name,
            "dosage_form": med.dosage_form,
            "standard_dosage": med.standard_dosage,
            "indications": med.indications,
            "contraindications": med.contraindications,
            "common_side_effects": med.side_effects,
            "requires_prescription": med.requires_prescription,
            "estimated_price": f"${med.price:.2f}",
            "disclaimer": "Informational only. Do not change or initiate dosages without physician instruction.",
        }

    # 2. Check external cache
    cache_key = clean_name.lower()
    now = time.time()
    if cache_key in _medicine_cache:
        entry = _medicine_cache[cache_key]
        if now - entry["timestamp"] < CACHE_TTL_SECONDS:
            return entry["data"]

    # 3. Fallback: Query openFDA Drug Labeling API if enabled
    if settings.FEATURE_EXTERNAL_MEDICINE_API:
        try:
            url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{urllib.parse.quote(clean_name)}+openfda.brand_name:{urllib.parse.quote(clean_name)}&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "PulseCareHealthcareBot/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    results = data.get("results", [])
                    if results:
                        item = results[0]
                        fda_indications = item.get("indications_and_usage", ["Consult medication guide."])[0][:300]
                        fda_warnings = item.get("warnings", ["Consult healthcare provider."])[0][:300]
                        fda_adverse = item.get("adverse_reactions", ["Consult package insert."])[0][:300]
                        
                        out = {
                            "status": "found_external",
                            "source": "US FDA Drug Information Directory",
                            "medicine_name": clean_name.title(),
                            "generic_name": clean_name.title(),
                            "indications": fda_indications,
                            "warnings": fda_warnings,
                            "common_side_effects": fda_adverse,
                            "disclaimer": "Retrieved from FDA open database. Always consult a PulseCare clinician or pharmacist.",
                        }
                        _medicine_cache[cache_key] = {"data": out, "timestamp": now}
                        return out
        except Exception:
            pass  # Fall through to not_found

    return {
        "status": "not_found",
        "message": f"Medicine '{clean_name}' was not found in the PulseCare formulary or verified databases. Please verify spelling or consult a PulseCare doctor or pharmacist.",
    }
