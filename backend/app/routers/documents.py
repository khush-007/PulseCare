import uuid
import os
import json
from datetime import datetime, timezone
from typing import List

# pdfplumber is imported lazily inside _parse_pdf
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.chatbot import KnowledgeDocumentChunk
from backend.app.chatbot.rag.embeddings import get_embedding

router = APIRouter(prefix="/documents", tags=["User Documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def _validate_upload(file: UploadFile):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    return True

async def _save_upload(file: UploadFile, user: User) -> str:
    """Save uploaded PDF to a user‑specific directory and return its absolute path."""
    user_dir = os.path.abspath(os.path.join(settings.DOCUMENTS_ROOT, str(user.id)))
    os.makedirs(user_dir, exist_ok=True)
    dest_path = os.path.join(user_dir, f"{uuid.uuid4()}_{file.filename}")
    size = 0
    with open(dest_path, "wb") as out_file:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                out_file.close()
                os.remove(dest_path)
                raise HTTPException(status_code=413, detail="File size exceeds 10 MB limit.")
            out_file.write(chunk)
    return dest_path

def _parse_pdf(filepath: str, doc_id: str) -> List[KnowledgeDocumentChunk]:
    """Parse a PDF into one `KnowledgeDocumentChunk` per page (including page citations)."""
    # Import pdfplumber lazily to avoid module import errors when the dependency is optional.
    try:
        import pdfplumber
    except ImportError as e:
        raise HTTPException(status_code=500, detail="PDF processing is unavailable because 'pdfplumber' is not installed.")
    chunks: List[KnowledgeDocumentChunk] = []
    with pdfplumber.open(filepath) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            title = os.path.splitext(os.path.basename(filepath))[0]
            section = f"Page {page_number}"
            embedding = get_embedding(text)
            chunk = KnowledgeDocumentChunk(
                doc_id=doc_id,
                chunk_index=page_number - 1,
                title=title,
                section=section,
                content=text,
                doc_type="pdf",
                trust_level="official",
                source_url=f"/documents/{doc_id}",
                last_updated=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                user_id=None,  # will be set below per user
                embedding_json=json.dumps(embedding),
                metadata_json=json.dumps({"filename": os.path.basename(filepath), "page": page_number}),
            )
            chunks.append(chunk)
    return chunks

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF, extract pages, embed and store per‑user chunks."""
    _validate_upload(file)
    saved_path = await _save_upload(file, current_user)
    doc_id = str(uuid.uuid4())
    chunks = _parse_pdf(saved_path, doc_id)
    for chunk in chunks:
        chunk.user_id = current_user.id
        db.add(chunk)
    await db.commit()
    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "pages": len(chunks),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/", response_model=List[dict])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KnowledgeDocumentChunk.doc_id, KnowledgeDocumentChunk.source_url).where(KnowledgeDocumentChunk.user_id == current_user.id)
    result = await db.execute(stmt)
    rows = result.all()
    docs = []
    seen = set()
    for row in rows:
        doc_id = row[0]
        if doc_id in seen:
            continue
        seen.add(doc_id)
        docs.append({"doc_id": doc_id, "source_url": row[1]})
    return docs

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KnowledgeDocumentChunk).where(KnowledgeDocumentChunk.doc_id == doc_id, KnowledgeDocumentChunk.user_id == current_user.id)
    result = await db.execute(stmt)
    chunks = result.scalars().all()
    if not chunks:
        raise HTTPException(status_code=404, detail="Document not found.")
    await db.execute(delete(KnowledgeDocumentChunk).where(KnowledgeDocumentChunk.doc_id == doc_id, KnowledgeDocumentChunk.user_id == current_user.id))
    await db.commit()
    # attempt to delete stored file(s)
    user_dir = os.path.abspath(os.path.join(settings.DOCUMENTS_ROOT, str(current_user.id)))
    if os.path.isdir(user_dir):
        for fname in os.listdir(user_dir):
            if doc_id in fname:
                try:
                    os.remove(os.path.join(user_dir, fname))
                except Exception:
                    pass
    return {"status": "deleted", "doc_id": doc_id}
