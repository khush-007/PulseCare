import asyncio
import re
from typing import List

from backend.app.chatbot.sources.contracts import EvidenceRecord, SourceRequest
from backend.app.chatbot.sources.matching import is_doctor_specific_fee_request


class PostgresToolKnowledgeSource:
    """Public clinic data adapter backed by existing parameterized ORM tools."""

    source_id = "pulsecare-postgres-public"

    async def retrieve(self, request: SourceRequest) -> List[EvidenceRecord]:
        if "doctor_service_lookup" not in request.routes or request.db is None:
            return []
        from backend.app.chatbot.tools.doctor_tools import search_doctors
        from backend.app.chatbot.tools.service_tools import list_services

        query = request.query.lower()
        entities = request.entities
        doctor_fee_question = is_doctor_specific_fee_request(query, entities)
        if doctor_fee_question and not entities.get("doctor_name"):
            # We know the requested fact is doctor-specific, but do not have a
            # reliable doctor entity to query. Returning no evidence is safer
            # than listing every doctor or substituting a service fee.
            return []
        wants_services = not doctor_fee_question and bool(re.search(
            r"\b(services?|screening|eeg)\b", query
        ))
        wants_doctors = bool(entities.get("doctor_name") or entities.get("specialty")) or bool(re.search(
            r"\b(doctor|dr\.?|physician|specialist|cardiologist|neurologist|pediatrician)\b", query
        ))
        output: List[EvidenceRecord] = []
        if wants_doctors:
            result = await asyncio.wait_for(search_doctors(
                db=request.db,
                specialty=entities.get("specialty"),
                name=entities.get("doctor_name"),
                day_of_week=entities.get("day_of_week"),
            ), timeout=6.0)
            for item in result.get("doctors", []):
                content = "; ".join(
                    f"{label}: {item[key]}" for key, label in (
                        ("name", "Doctor"), ("specialty", "Specialty"),
                        ("qualifications", "Qualifications"), ("consultation_fee", "Consultation fee"),
                        ("available_days", "Available days"), ("hours", "Hours"), ("room", "Location"),
                    ) if item.get(key)
                )
                output.append(EvidenceRecord(
                    source_id=self.source_id,
                    record_id=f"doctor:{item['doctor_id']}",
                    title=item.get("name", "PulseCare doctor"),
                    section="Doctor directory",
                    content=content,
                    category="doctor_service_lookup",
                    source_url="/doctors",
                    metadata={"evidence_kind": "structured_record", "record_type": "doctor", "fields": item},
                ))
        if wants_services:
            result = await asyncio.wait_for(
                list_services(db=request.db, department=entities.get("specialty")),
                timeout=6.0,
            )
            for item in result.get("services", []):
                content = "; ".join(
                    f"{label}: {item[key]}" for key, label in (
                        ("name", "Service"), ("department", "Department"), ("base_fee", "Fee"),
                        ("duration", "Duration"), ("description", "Details"),
                    ) if item.get(key)
                )
                output.append(EvidenceRecord(
                    source_id=self.source_id,
                    record_id=f"service:{item['service_id']}",
                    title=item.get("name", "PulseCare service"),
                    section="Medical services catalog",
                    content=content,
                    category="doctor_service_lookup",
                    source_url="/services",
                    metadata={"evidence_kind": "structured_record", "record_type": "service", "fields": item},
                ))
        return output
