import os
import re
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from backend.app.models.chatbot import KnowledgeDocumentChunk
from backend.app.chatbot.rag.embeddings import get_embedding


class DocumentChunk:
    def __init__(
        self,
        doc_id: str,
        chunk_index: int,
        title: str,
        section: str,
        content: str,
        doc_type: str,
        trust_level: str,
        source_url: Optional[str] = None,
        last_updated: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.doc_id = doc_id
        self.chunk_index = chunk_index
        self.title = title
        self.section = section
        self.content = content
        self.doc_type = doc_type
        self.trust_level = trust_level
        self.source_url = source_url or ""
        self.last_updated = last_updated or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.metadata = metadata or {}


def parse_markdown_document(filepath: str) -> List[DocumentChunk]:
    """
    Parse a Markdown file using structure-aware semantic chunking.
    Extracts headers to build contextual chunks with parent metadata.
    """
    filename = os.path.basename(filepath)
    doc_id = os.path.splitext(filename)[0]
    
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # Determine document type and trust level based on file naming or frontmatter
    doc_type = "faq" if "faq" in doc_id.lower() else (
        "policy" if "policy" in doc_id.lower() else (
            "medical_guide" if "medical" in doc_id.lower() else "feature"
        )
    )
    trust_level = "verified_clinical" if doc_type == "medical_guide" else "official"

    # Extract main title (first #)
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    doc_title = title_match.group(1).strip() if title_match else doc_id.replace("_", " ").title()

    # Split document by section headers (## or ###)
    sections = re.split(r"\n(?=##+\s+)", text)
    chunks: List[DocumentChunk] = []
    chunk_index = 0

    for section_text in sections:
        section_text = section_text.strip()
        if not section_text:
            continue

        # Extract section header
        header_match = re.match(r"^##+\s+(.+)$", section_text, re.MULTILINE)
        section_name = header_match.group(1).strip() if header_match else "General"

        # Prepend contextual header to enforce grounding
        contextual_content = f"[{doc_title} > {section_name}]\n{section_text}"

        chunks.append(
            DocumentChunk(
                doc_id=doc_id,
                chunk_index=chunk_index,
                title=doc_title,
                section=section_name,
                content=contextual_content,
                doc_type=doc_type,
                trust_level=trust_level,
                source_url=f"/docs/{filename}",
                last_updated=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                metadata={"filename": filename, "section": section_name},
            )
        )
        chunk_index += 1

    return chunks


async def ingest_directory(
    directory_path: str,
    db: AsyncSession,
    reindex: bool = True,
) -> Dict[str, Any]:
    """
    Ingest all documentation files from a directory into the database.
    Computes vector embeddings and saves parent-child chunk records.
    """
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    all_chunks: List[DocumentChunk] = []
    doc_count = 0

    for root, _, files in os.walk(directory_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in [".md", ".txt"]:
                filepath = os.path.join(root, file)
                doc_chunks = parse_markdown_document(filepath)
                all_chunks.extend(doc_chunks)
                doc_count += 1

    if reindex:
        # Clear existing knowledge chunks
        await db.execute(delete(KnowledgeDocumentChunk))
        await db.commit()

    # Generate embeddings and persist chunks
    for chunk in all_chunks:
        # Embed chunk content
        emb = get_embedding(chunk.content)
        
        db_chunk = KnowledgeDocumentChunk(
            doc_id=chunk.doc_id,
            chunk_index=chunk.chunk_index,
            title=chunk.title,
            section=chunk.section,
            content=chunk.content,
            doc_type=chunk.doc_type,
            trust_level=chunk.trust_level,
            source_url=chunk.source_url,
            last_updated=chunk.last_updated,
            embedding_json=json.dumps(emb),
            metadata_json=json.dumps(chunk.metadata),
        )
        db.add(db_chunk)

    await db.commit()

    return {
        "status": "success",
        "documents_ingested": doc_count,
        "total_chunks": len(all_chunks),
        "message": f"Successfully ingested {len(all_chunks)} chunks from {doc_count} documents.",
    }
