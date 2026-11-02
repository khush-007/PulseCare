import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

from backend.app.chatbot.sources.contracts import EvidenceRecord, SourceRequest

_STOP_WORDS = {
    "the", "and", "for", "with", "what", "when", "where", "does", "how", "can",
    "could", "please", "about", "tell", "me", "you", "your", "is", "are", "or",
    "not", "healthy", "unhealthy", "health", "good", "bad", "safe", "harmful",
    "common", "cause", "causes", "benefit", "benefits", "why", "should", "would",
}


class MarkdownKnowledgeSource:
    def __init__(self, source_id: str, category: str, paths: Sequence[str], top_k: int = 5):
        if category not in {"application", "medical"}:
            raise ValueError("Markdown source category must be application or medical")
        self.source_id = source_id
        self.category = category
        self.paths = tuple(paths)
        self.top_k = top_k

    async def retrieve(self, request: SourceRequest) -> List[EvidenceRecord]:
        applicable = "website_help" in request.routes if self.category == "application" else bool(
            {"health_general", "medicine_info", "triage_handoff"}.intersection(request.routes)
        )
        if not applicable:
            return []
        terms = [
            term for term in re.findall(r"[\w]+", request.query.lower())
            if len(term) > 2 and term not in _STOP_WORDS
        ]
        finding_doctor = self.category == "application" and bool(re.search(
            r"\b(find|search|locate)\b.{0,50}\bdoctor|\bdoctor\b.{0,50}\b(find|search|locate)\b",
            request.query.lower(),
        ))
        ranked = []
        for configured_path in self.paths:
            path = Path(configured_path)
            if not path.is_absolute():
                path = Path(__file__).resolve().parents[4] / path
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else path.stem.replace("_", " ").title()
            headings = list(re.finditer(r"^#{1,3}\s+(.+)$", content, re.MULTILINE))
            sections = []
            if headings:
                for index, heading in enumerate(headings):
                    end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
                    section_text = content[heading.start():end].strip()
                    if heading.group(1).strip() == title and content[heading.end():end].strip():
                        sections.append(("General", content[heading.end():end].strip()))
                        continue
                    if heading.group(1).strip() == title:
                        continue
                    sections.append((heading.group(1).strip(), section_text))
            else:
                sections.append(("General", content))
            for section_name, section_text in sections:
                score = sum(section_text.lower().count(term) for term in terms)
                if finding_doctor and re.search(
                    r"\b(doctors page|locate a specialist|find a specialist)\b",
                    section_text,
                    re.IGNORECASE,
                ):
                    # Prefer the actual navigation instructions over doctor
                    # portal/profile material that happens to repeat "doctor".
                    score += 20
                if score:
                    ranked.append((score, path, title, section_name, section_text))
        ranked.sort(key=lambda item: (-item[0], item[1].name.lower(), item[3].lower()))
        now = datetime.now(timezone.utc).date().isoformat()
        result_limit = min(request.limit, self.top_k)
        if self.category == "application":
            result_limit = min(result_limit, 1)
        return [
            EvidenceRecord(
                source_id=self.source_id,
                record_id=f"{self.source_id}:{path.name}:{section_name}",
                title=title,
                section=section_name,
                content=section_text,
                category=self.category,
                trust_level="official" if self.category == "application" else "verified_clinical",
                source_url=f"/docs/{path.name}",
                last_updated=now,
                metadata={"evidence_kind": "document", "file_name": path.name},
            )
            for score, path, title, section_name, section_text in ranked[:result_limit]
        ]
