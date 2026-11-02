import json
import logging
from dataclasses import dataclass, field
from typing import Any, List, Sequence

from backend.app.chatbot.sources.contracts import EvidenceRecord, KnowledgeSource, SourceRequest
from backend.app.chatbot.sources.csv_source import CsvKnowledgeSource
from backend.app.chatbot.sources.markdown_source import MarkdownKnowledgeSource
from backend.app.chatbot.sources.postgres_source import PostgresToolKnowledgeSource

logger = logging.getLogger("pulsecare.chatbot.sources")


@dataclass
class SourceResults:
    records: List[EvidenceRecord] = field(default_factory=list)
    failed_sources: List[str] = field(default_factory=list)


class SourceRegistry:
    def __init__(self, sources: Sequence[KnowledgeSource] = ()):
        self._sources = list(sources)

    def register(self, source: KnowledgeSource) -> None:
        if any(s.source_id == source.source_id for s in self._sources):
            raise ValueError(f"Duplicate knowledge source id: {source.source_id}")
        self._sources.append(source)

    async def retrieve(self, request: SourceRequest) -> SourceResults:
        result = SourceResults()
        for source in self._sources:
            try:
                result.records.extend(await source.retrieve(request))
            except Exception as exc:
                # Provider/file/database details can contain sensitive values; log only safe identifiers.
                logger.warning("Knowledge source '%s' unavailable (%s).", source.source_id, type(exc).__name__)
                result.failed_sources.append(source.source_id)
        return result


def build_source_registry(config: Any) -> SourceRegistry:
    registry = SourceRegistry()
    registry.register(PostgresToolKnowledgeSource())

    try:
        csv_configs = json.loads(config.CHATBOT_CSV_SOURCES_JSON or "[]")
        if not isinstance(csv_configs, list):
            raise ValueError("CSV source configuration must be a list")
    except (ValueError, TypeError):
        logger.warning("CSV knowledge source configuration is invalid; optional CSV sources are disabled.")
        csv_configs = []
    for item in csv_configs:
        try:
            registry.register(CsvKnowledgeSource.from_config(item))
        except (TypeError, ValueError, KeyError):
            logger.warning("A CSV knowledge source configuration is invalid and was skipped.")

    for source_id, category, paths_json in (
        ("pulsecare-application-files", "application", config.PULSECARE_KNOWLEDGE_FILES_JSON),
        ("pulsecare-medical-files", "medical", config.MEDICAL_KNOWLEDGE_FILES_JSON),
    ):
        try:
            paths = json.loads(paths_json or "[]")
            if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
                raise ValueError("File paths must be a list of strings")
            registry.register(MarkdownKnowledgeSource(source_id, category, paths))
        except (ValueError, TypeError):
            logger.warning("Knowledge file configuration for '%s' is invalid; source disabled.", source_id)
    return registry
