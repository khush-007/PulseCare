import csv
from types import SimpleNamespace

import pytest

from backend.app.chatbot.sources.contracts import EvidenceRecord, SourceRequest
from backend.app.chatbot.sources.csv_source import CsvKnowledgeSource, CsvSchemaError
from backend.app.chatbot.sources.markdown_source import MarkdownKnowledgeSource
from backend.app.chatbot.sources.postgres_source import PostgresToolKnowledgeSource
from backend.app.chatbot.sources.registry import SourceRegistry
from backend.app.chatbot.sources.registry import build_source_registry


def _request(query, routes, **kwargs):
    return SourceRequest(query=query, routes=routes, **kwargs)


@pytest.mark.asyncio
async def test_csv_mapping_search_and_evidence_metadata(tmp_path):
    path = tmp_path / "synthetic.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["actual_name", "area", "fee_value"])
        writer.writeheader()
        writer.writerow({"actual_name": "Synthetic Doctor", "area": "Cardiology", "fee_value": "$12"})
        writer.writerow({"actual_name": "Other Person", "area": "Pediatrics", "fee_value": "$9"})
    source = CsvKnowledgeSource.from_config({
        "source_id": "test-csv",
        "path": str(path),
        "field_mapping": {"doctor_name": "actual_name", "specialty": "area", "fee": "fee_value"},
    })
    records = await source.retrieve(_request("Cardiology fee", ["doctor_service_lookup"]))
    assert len(records) == 1
    assert records[0].metadata["fields"]["doctor_name"] == "Synthetic Doctor"
    assert "fee: $12" in records[0].content.lower()
    assert records[0].source_id == "test-csv"


@pytest.mark.asyncio
async def test_csv_service_row_cannot_satisfy_named_doctor_fee(tmp_path):
    path = tmp_path / "doctor-services.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["doctor", "service", "price"])
        writer.writeheader()
        writer.writerow({"doctor": "", "service": "Cardiac Consultation", "price": "$250.00"})
    source = CsvKnowledgeSource.from_config({
        "source_id": "test-csv",
        "path": str(path),
        "field_mapping": {
            "doctor_name": "doctor", "service_name": "service", "fee": "price",
        },
    })

    records = await source.retrieve(_request(
        "Elena Garchia fees?", ["doctor_service_lookup"],
        entities={"doctor_name": "Elena Garchia"},
    ))

    assert records == []


@pytest.mark.asyncio
async def test_csv_missing_and_empty_sources_are_optional(tmp_path):
    missing = CsvKnowledgeSource("missing", str(tmp_path / "not-ready.csv"), {"name": "real header"})
    assert await missing.retrieve(_request("doctor", ["doctor_service_lookup"])) == []
    empty_path = tmp_path / "empty.csv"
    empty_path.write_text("", encoding="utf-8")
    empty = CsvKnowledgeSource("empty", str(empty_path), {"name": "real header"})
    assert await empty.retrieve(_request("doctor", ["doctor_service_lookup"])) == []


@pytest.mark.asyncio
async def test_csv_invalid_mapping_isolated_by_registry(tmp_path):
    path = tmp_path / "headers.csv"
    path.write_text("one,two\na,b\n", encoding="utf-8")
    source = CsvKnowledgeSource("bad-csv", str(path), {"name": "missing-header"})
    with pytest.raises(CsvSchemaError):
        await source.retrieve(_request("a", ["doctor_service_lookup"]))
    result = await SourceRegistry([source]).retrieve(_request("a", ["doctor_service_lookup"]))
    assert result.records == []
    assert result.failed_sources == ["bad-csv"]


def test_csv_registration_rejects_patient_data_fields():
    with pytest.raises(ValueError, match="patient or credential"):
        CsvKnowledgeSource.from_config({
            "source_id": "private-csv",
            "path": "not-opened.csv",
            "field_mapping": {"patient_name": "a real supplied header"},
        })


@pytest.mark.asyncio
async def test_markdown_application_and_medical_sources_are_separate(tmp_path):
    app_file = tmp_path / "app.md"
    app_file.write_text("# App Help\nUse the PulseCare portal to manage appointments.", encoding="utf-8")
    medical_file = tmp_path / "medical.md"
    medical_file.write_text("# Health Guide\nBlood pressure has two readings.", encoding="utf-8")
    app_source = MarkdownKnowledgeSource("app-docs", "application", [str(app_file)])
    med_source = MarkdownKnowledgeSource("health-docs", "medical", [str(medical_file)])
    app_results = await app_source.retrieve(_request("manage appointments", ["website_help"]))
    assert len(app_results) == 1 and app_results[0].category == "application"
    assert await med_source.retrieve(_request("manage appointments", ["website_help"])) == []
    med_results = await med_source.retrieve(_request("blood pressure", ["health_general"]))
    assert len(med_results) == 1 and med_results[0].category == "medical"


@pytest.mark.asyncio
async def test_registry_combines_sources_and_isolates_failures():
    class GoodSource:
        source_id = "good"
        async def retrieve(self, request):
            return [EvidenceRecord("good", "r1", "title", "section", "evidence", "application")]

    class BrokenSource:
        source_id = "broken"
        async def retrieve(self, request):
            raise RuntimeError("do not expose this detail")

    result = await SourceRegistry([GoodSource(), BrokenSource()]).retrieve(_request("question", ["website_help"]))
    assert [record.record_id for record in result.records] == ["r1"]
    assert result.failed_sources == ["broken"]
    assert "do not expose" not in str(result)


@pytest.mark.asyncio
async def test_postgres_adapter_reuses_existing_tool_results(monkeypatch):
    from backend.app.chatbot.tools import doctor_tools, service_tools

    async def fake_doctors(**_kwargs):
        return {"status": "success", "doctors": [{
            "doctor_id": 17, "name": "Synthetic Doctor", "specialty": "Cardiology",
            "qualifications": "Verified", "consultation_fee": "$10.00",
            "available_days": "Monday", "hours": "09:00 - 12:00", "room": "A1",
        }]}

    async def fake_services(**_kwargs):
        return {"status": "success", "services": []}

    monkeypatch.setattr(doctor_tools, "search_doctors", fake_doctors)
    monkeypatch.setattr(service_tools, "list_services", fake_services)
    result = await PostgresToolKnowledgeSource().retrieve(_request(
        "Cardiology doctor", ["doctor_service_lookup"], db=object(), entities={"specialty": "Cardiology"},
    ))
    assert len(result) == 1
    assert result[0].metadata["fields"]["doctor_id"] == 17
    assert "$10.00" in result[0].content


@pytest.mark.asyncio
async def test_doctor_fee_query_returns_only_matching_doctor_record(monkeypatch):
    from backend.app.chatbot.tools import doctor_tools, service_tools

    async def fake_doctors(**kwargs):
        assert kwargs["name"] == "Sarah Smith"
        return {"status": "success", "doctors": [{
            "doctor_id": 17, "name": "Sarah Smith", "specialty": "Cardiology",
            "qualifications": "MD", "consultation_fee": "$150.00",
            "available_days": "Monday", "hours": "09:00 - 12:00", "room": "A1",
        }]}

    async def services_must_not_answer_doctor_fee(**_kwargs):
        pytest.fail("A service fee must not satisfy a doctor-fee query")

    monkeypatch.setattr(doctor_tools, "search_doctors", fake_doctors)
    monkeypatch.setattr(service_tools, "list_services", services_must_not_answer_doctor_fee)
    result = await PostgresToolKnowledgeSource().retrieve(_request(
        "What is her consultation fee? [regarding Dr. Sarah Smith]",
        ["doctor_service_lookup"], db=object(), entities={"doctor_name": "Sarah Smith"},
    ))

    assert len(result) == 1
    assert result[0].metadata["record_type"] == "doctor"
    assert "$150.00" in result[0].content


@pytest.mark.asyncio
async def test_unresolved_doctor_fee_does_not_fall_back_to_services(monkeypatch):
    from backend.app.chatbot.tools import doctor_tools, service_tools

    async def doctors_must_not_be_listed_without_a_referent(**_kwargs):
        pytest.fail("An unresolved possessive fee query must not list all doctors")

    async def services_must_not_answer_doctor_fee(**_kwargs):
        pytest.fail("An unresolved doctor fee must not be replaced with a service fee")

    monkeypatch.setattr(doctor_tools, "search_doctors", doctors_must_not_be_listed_without_a_referent)
    monkeypatch.setattr(service_tools, "list_services", services_must_not_answer_doctor_fee)
    result = await PostgresToolKnowledgeSource().retrieve(_request(
        "What is her consultation fee?", ["doctor_service_lookup"],
        db=object(), entities={},
    ))

    assert result == []


@pytest.mark.asyncio
async def test_unknown_or_misspelled_doctor_never_gets_service_fee(monkeypatch):
    from backend.app.chatbot.tools import doctor_tools, service_tools

    async def doctors_not_found(**kwargs):
        assert kwargs["name"] == "Elena Garchia"
        return {"status": "not_found", "doctors": []}

    async def services_must_not_answer_doctor_fee(**_kwargs):
        pytest.fail("A similarly themed service fee is not a doctor fee")

    monkeypatch.setattr(doctor_tools, "search_doctors", doctors_not_found)
    monkeypatch.setattr(service_tools, "list_services", services_must_not_answer_doctor_fee)
    result = await PostgresToolKnowledgeSource().retrieve(_request(
        "elena garchia fees?", ["doctor_service_lookup"], db=object(),
        entities={"doctor_name": "Elena Garchia"},
    ))

    assert result == []


@pytest.mark.asyncio
async def test_multiple_sources_can_return_evidence_without_csv_or_database():
    class StaticSource:
        source_id = "configured"
        async def retrieve(self, request):
            return [EvidenceRecord("configured", "guide-1", "Verified guide", "FAQ", "Verified answer text", "application")]

    result = await SourceRegistry([StaticSource()]).retrieve(_request("help", ["website_help"]))
    assert result.records[0].to_dict()["content"] == "Verified answer text"
    assert not result.failed_sources


def test_registry_configuration_starts_without_optional_csv_files():
    config = SimpleNamespace(
        CHATBOT_CSV_SOURCES_JSON="[]",
        PULSECARE_KNOWLEDGE_FILES_JSON="[]",
        MEDICAL_KNOWLEDGE_FILES_JSON="[]",
    )
    registry = build_source_registry(config)
    assert {source.source_id for source in registry._sources} == {
        "pulsecare-postgres-public", "pulsecare-application-files", "pulsecare-medical-files",
    }


@pytest.mark.asyncio
async def test_postgres_and_csv_records_are_source_agnostic_to_answer_generator(monkeypatch):
    from backend.app.chatbot.graph.nodes import answer_generator

    async def must_not_call(**_kwargs):
        pytest.fail("structured clinic evidence should be rendered directly")

    monkeypatch.setattr(answer_generator, "generate_completion", must_not_call)
    record = EvidenceRecord(
        source_id="configured-source", record_id="record-1", title="Synthetic Doctor",
        section="Doctor directory", content="Doctor: Synthetic Doctor; Fee: $18.00",
        category="doctor_service_lookup", metadata={"evidence_kind": "structured_record"},
    )
    result = await answer_generator.answer_generator_node({
        "user_query": "What is this doctor's fee?",
        "routes": ["doctor_service_lookup"],
        "retrieved_docs": [record.to_dict()],
    })
    assert "Synthetic Doctor" in result["draft_answer"]
    assert "$18.00" in result["draft_answer"]


@pytest.mark.asyncio
async def test_find_doctor_application_help_returns_only_navigation_section():
    from backend.app.core.config import settings

    result = await build_source_registry(settings).retrieve(_request(
        "How can I find a doctor on PulseCare?", ["website_help"], limit=5,
    ))
    application_records = [record for record in result.records if record.category == "application"]

    assert len(application_records) == 1
    assert "Doctors page" in application_records[0].content
    assert "Doctor Portal Features" not in application_records[0].content
    assert "Telehealth" not in application_records[0].content


@pytest.mark.asyncio
async def test_generic_healthy_word_does_not_retrieve_unrelated_sugar_evidence():
    from backend.app.core.config import settings

    result = await build_source_registry(settings).retrieve(_request(
        "Is sugar healthy or not?", ["health_general"], limit=5,
    ))

    assert result.records == []
