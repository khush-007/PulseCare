import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping

from backend.app.chatbot.sources.contracts import EvidenceRecord, SourceRequest
from backend.app.chatbot.sources.matching import is_doctor_specific_fee_request


class CsvSchemaError(ValueError):
    """The configured mapping does not match a CSV header."""


@dataclass
class CsvKnowledgeSource:
    source_id: str
    path: str
    field_mapping: Mapping[str, str]
    category: str = "doctor_service_lookup"
    title: str = "Configured PulseCare CSV records"
    top_k: int = 5

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "CsvKnowledgeSource":
        source_id = config.get("source_id")
        path = config.get("path")
        mapping = config.get("field_mapping")
        category = config.get("category", "doctor_service_lookup")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id is required")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("path is required")
        if not isinstance(mapping, dict) or not mapping or not all(
            isinstance(k, str) and isinstance(v, str) and v for k, v in mapping.items()
        ):
            raise ValueError("field_mapping must map canonical fields to CSV headers")
        sensitive_field = re.compile(r"patient|appointment|medical_record|health_record|email|phone|address|birth|ssn|token|password", re.IGNORECASE)
        if any(sensitive_field.search(key) for key in mapping):
            raise ValueError("CSV source mappings cannot include patient or credential fields")
        if category != "doctor_service_lookup":
            raise ValueError("CSV sources are limited to public doctor/service information")
        return cls(source_id.strip(), path, mapping, category)

    async def retrieve(self, request: SourceRequest) -> List[EvidenceRecord]:
        if self.category not in request.routes:
            return []
        source_path = Path(self.path)
        if not source_path.is_absolute():
            source_path = Path(__file__).resolve().parents[4] / source_path
        if not source_path.is_file():
            return []  # Optional sources can be configured before data arrives.
        if source_path.stat().st_size > 10 * 1024 * 1024:
            raise CsvSchemaError("configured CSV exceeds the supported size limit")

        with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            if not headers:
                return []  # Empty file with no header is an available empty source.
            missing_headers = sorted(set(self.field_mapping.values()) - set(headers))
            if missing_headers:
                # Do not include actual headers/paths in errors or user-facing output.
                raise CsvSchemaError("configured CSV mapping does not match file headers")
            rows = []
            for row_number, row in enumerate(reader):
                if row_number >= 50000:
                    raise CsvSchemaError("configured CSV exceeds the supported row limit")
                rows.append(row)

        terms = [term for term in re.findall(r"[\w]+", request.query.lower()) if len(term) > 2]
        matches = []
        doctor_fee_question = is_doctor_specific_fee_request(request.query, request.entities)
        if doctor_fee_question and not request.entities.get("doctor_name"):
            return []
        for index, row in enumerate(rows):
            values = {
                canonical: (row.get(column) or "").strip()
                for canonical, column in self.field_mapping.items()
            }
            requested_doctor = request.entities.get("doctor_name")
            if doctor_fee_question:
                # A fee or service row cannot stand in for the named doctor's
                # own record. CSV mappings must explicitly identify doctor_name.
                doctor_name = values.get("doctor_name", "")
                if not doctor_name or requested_doctor.lower() not in doctor_name.lower():
                    continue
            searchable = " ".join(values.values()).lower()
            score = sum(term in searchable for term in terms)
            if score:
                matches.append((score, index, values))
        matches.sort(key=lambda item: (-item[0], item[1]))

        records = []
        for score, index, values in matches[: min(request.limit, self.top_k)]:
            facts = [f"{name.replace('_', ' ').title()}: {value}" for name, value in values.items() if value]
            if not facts:
                continue
            records.append(EvidenceRecord(
                source_id=self.source_id,
                record_id=f"{self.source_id}:{index + 1}",
                title=self.title,
                section="Configured structured record",
                content="; ".join(facts),
                category=self.category,
                metadata={"evidence_kind": "structured_record", "fields": values, "match_score": score},
            ))
        return records
