from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence


@dataclass(frozen=True)
class SourceRequest:
    query: str
    routes: Sequence[str]
    entities: Dict[str, Any] = field(default_factory=dict)
    db: Any = None
    current_user: Any = None
    user_id: Optional[int] = None
    limit: int = 5


@dataclass(frozen=True)
class EvidenceRecord:
    source_id: str
    record_id: str
    title: str
    section: str
    content: str
    category: str
    trust_level: str = "official"
    source_url: Optional[str] = None
    last_updated: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.record_id,
            "chunk_id": None,
            "title": self.title,
            "section": self.section,
            "content": self.content,
            "doc_type": self.category,
            "trust_level": self.trust_level,
            "source_url": self.source_url or "",
            "last_updated": self.last_updated or "",
            "score": 1.0,
            "source_id": self.source_id,
            "record_id": self.record_id,
            "metadata": self.metadata,
        }


class KnowledgeSource(Protocol):
    source_id: str

    async def retrieve(self, request: SourceRequest) -> List[EvidenceRecord]: ...
