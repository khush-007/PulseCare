# PulseCare knowledge source setup

The chatbot uses one source contract (`SourceRequest` in, `EvidenceRecord` out) and a registry that continues when an optional source is missing or fails. Source errors are logged with a source id and error type only; file paths, database exception text, and credentials are not sent to the user.

## CSV data

Set `CHATBOT_CSV_SOURCES_JSON` to a JSON list of source registrations. Each registration supplies a unique `source_id`, local `path`, and `field_mapping` from stable internal field names to the exact headers in the supplied CSV. The adapter does not assume or create CSV headers. CSV sources are restricted to public doctor/service information and are searched only for doctor/service intents.

Configuration shape (replace both placeholders with values from the supplied file):

```json
[{"source_id":"<unique-source-id>","path":"<local-file-path>","field_mapping":{"<canonical-field>":"<exact-header-from-file>"}}]
```

When the real files arrive, the remaining setup is to map their actual headers, choose the source path, and confirm the mapped fields are public clinic information. For named doctor lookups, map the canonical `doctor_name` field; a doctor-specific fee should map to `consultation_fee`. Service rows should use `service_name` and `fee`, so they cannot satisfy a named doctor's fee request. Missing files return no results; a mismatched configured header is isolated as a source failure. No sample records or real clinic values are included here.

## PostgreSQL data

Set the existing `DATABASE_URL` (and `SYNC_DATABASE_URL` where existing scripts require it). The registered public-clinic adapter calls the existing `search_doctors` and `list_services` tools, which use SQLAlchemy ORM queries. It does not execute SQL supplied by the model. Doctor, service, and fee results are normalized as evidence records. Patient appointments remain on their authenticated tool path and are not part of this public source.

When PostgreSQL is available, verify the configured connection and the existing model/table compatibility. No schema migration or data import is needed for this adapter; if the real database uses a different schema, an explicit repository/model mapping will still be required.

## Application and medical knowledge

`PULSECARE_KNOWLEDGE_FILES_JSON` lists Markdown/text files for PulseCare application help. `MEDICAL_KNOWLEDGE_FILES_JSON` lists general medical education documents. These sources are separate and can be updated independently. The defaults point to the maintained files under `knowledge_base/`; missing files are optional and do not stop chat processing.

Only retrieved application documents support PulseCare policy or feature claims. General health education can use the configured LLM with relevant medical documents and the medical safety prompt. No website crawling or live availability source is used.

## Adding a source

Implement `retrieve(SourceRequest) -> list[EvidenceRecord]`, give the source a unique id, and register it in `build_source_registry`. If configuration can fully describe the source (as for CSV and Markdown files), no chatbot routing or answer-generation changes are needed. Sources requiring authentication or a new schema/repository mapping need that setup in their adapter.
