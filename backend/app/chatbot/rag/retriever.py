import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.app.core.config import settings
from backend.app.models.chatbot import KnowledgeDocumentChunk
from backend.app.chatbot.rag.embeddings import get_embedding, cosine_similarity
from backend.app.chatbot.rag.query_transform import expand_queries
from types import SimpleNamespace

# Optional cross-encoder model cache
_cross_encoder_model = None


class RetrievedChunk:
    def __init__(
        self,
        chunk_id: int,
        doc_id: str,
        title: str,
        section: str,
        content: str,
        doc_type: str,
        trust_level: str,
        source_url: str,
        last_updated: str,
        score: float,
        metadata: Dict[str, Any],
    ):
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.title = title
        self.section = section
        self.content = content
        self.doc_type = doc_type
        self.trust_level = trust_level
        self.source_url = source_url
        self.last_updated = last_updated
        self.score = score
        self.metadata = metadata

    def to_citation(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "section": self.section,
            "source_url": self.source_url,
            "last_updated": self.last_updated,
            "snippet": self.content[:200] + "..." if len(self.content) > 200 else self.content,
        }


def _bm25_sparse_score(query_tokens: List[str], text: str) -> float:
    """Compute sparse keyword match score."""
    text_lower = text.lower()
    score = 0.0
    for tok in query_tokens:
        count = text_lower.count(tok)
        if count > 0:
            score += 1.0 + (count * 0.2)
    return score


def _rerank_candidates(
    query: str,
    candidates: List[RetrievedChunk],
    top_k: int = 5,
) -> List[RetrievedChunk]:
    """
    Rerank candidates using a cross-encoder or fine-grained hybrid scorer.
    """
    if not candidates:
        return []

    provider = settings.RERANKER_PROVIDER.lower()
    if provider == "cross-encoder":
        global _cross_encoder_model
        try:
            if _cross_encoder_model is None:
                from sentence_transformers import CrossEncoder
                _cross_encoder_model = CrossEncoder(settings.RERANKER_MODEL)
            pairs = [[query, c.content] for c in candidates]
            scores = _cross_encoder_model.predict(pairs)
            for c, sc in zip(candidates, scores):
                c.score = float(sc)
            candidates.sort(key=lambda x: x.score, reverse=True)
            return candidates[:top_k]
        except Exception:
            pass  # Fall back to fine-grained ranker

    # Fallback fine-grained ranker: RRF score + Exact phrase bonus + Title bonus
    q_lower = query.lower()
    for c in candidates:
        content_lower = c.content.lower()
        title_lower = c.title.lower()
        section_lower = c.section.lower()
        
        bonus = 0.0
        # Exact keyword in title or section
        for word in q_lower.split():
            if len(word) > 3 and word in title_lower:
                bonus += 0.15
            if len(word) > 3 and word in section_lower:
                bonus += 0.20
        # Whole query phrase occurrence
        if len(q_lower) > 5 and q_lower in content_lower:
            bonus += 0.35
            
        c.score = c.score + bonus

    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates[:top_k]


async def hybrid_retrieve(
    query: str,
    db: AsyncSession,
    top_k: int = 5,
    doc_type_filter: Optional[str] = None,
    min_trust_level: Optional[str] = None,
    user_id: Optional[int] = None,
) -> List[RetrievedChunk]:
    """
    Advanced Hybrid RAG Retrieval:
    1. Dense Vector Search with multiple expanded queries
    2. Sparse BM25-style keyword matching
    3. Reciprocal Rank Fusion (RRF)
    4. Cross-Encoder / Semantic Reranker (top 20-30 -> top 4-6)
    5. Metadata and trust level filtering
    """
    # 1. Expand queries for high recall
    expanded_queries = expand_queries(query)
    query_embeddings = [get_embedding(q) for q in expanded_queries]
    query_tokens = [tok for q in expanded_queries for tok in re.findall(r"\w+", q.lower()) if len(tok) > 2]

    # Fetch knowledge chunks from database
    stmt = select(KnowledgeDocumentChunk)
    if doc_type_filter:
        stmt = stmt.where(KnowledgeDocumentChunk.doc_type == doc_type_filter)
    if user_id is not None:
        stmt = stmt.where(KnowledgeDocumentChunk.user_id == user_id)
    # TODO: min_trust_level filtering can be added similarly
    
    result = await db.execute(stmt)
    chunks = result.scalars().all()
    if not chunks:
        # Auto‑ingest knowledge base documents on first use
        from backend.app.chatbot.rag.ingestion import ingest_directory
        import os
        kb_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../knowledge_base"))
        # Populate the DB without wiping any existing data (reindex=False)
        await ingest_directory(kb_dir, db, reindex=False)
        # Re‑run the query after ingestion
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        if not chunks:
            return []

    # 2. Score chunks across Dense and Sparse channels
    dense_scores: Dict[int, float] = {}
    sparse_scores: Dict[int, float] = {}
    chunk_map: Dict[int, KnowledgeDocumentChunk] = {}

    for ch in chunks:
        chunk_map[ch.id] = ch
        emb = json.loads(ch.embedding_json)
        
        # Max cosine similarity across expanded query variants
        best_dense = max(cosine_similarity(q_emb, emb) for q_emb in query_embeddings)
        dense_scores[ch.id] = best_dense
        
        # Sparse keyword score
        sparse_scores[ch.id] = _bm25_sparse_score(query_tokens, ch.content)

    # 3. Compute RRF (Reciprocal Rank Fusion)
    # Rank by dense
    dense_ranked = sorted(dense_scores.keys(), key=lambda cid: dense_scores[cid], reverse=True)
    dense_ranks = {cid: rank + 1 for rank, cid in enumerate(dense_ranked)}

    # Rank by sparse
    sparse_ranked = sorted(sparse_scores.keys(), key=lambda cid: sparse_scores[cid], reverse=True)
    sparse_ranks = {cid: rank + 1 for rank, cid in enumerate(sparse_ranked)}

    # RRF formula: sum(1 / (60 + r))
    k_rrf = 60
    candidates: List[RetrievedChunk] = []
    
    for cid, ch in chunk_map.items():
        r_dense = dense_ranks[cid]
        r_sparse = sparse_ranks[cid]
        rrf_score = (1.0 / (k_rrf + r_dense)) + (1.0 / (k_rrf + r_sparse))
        
        # Boost verified clinical documentation
        if ch.trust_level == "verified_clinical":
            rrf_score *= 1.05

        meta = json.loads(ch.metadata_json) if ch.metadata_json else {}
        candidates.append(
            RetrievedChunk(
                chunk_id=ch.id,
                doc_id=ch.doc_id,
                title=ch.title,
                section=ch.section,
                content=ch.content,
                doc_type=ch.doc_type,
                trust_level=ch.trust_level,
                source_url=ch.source_url or "",
                last_updated=ch.last_updated,
                score=rrf_score,
                metadata=meta,
            )
        )

    # Sort initial candidate pool (top 20-30)
    candidates.sort(key=lambda x: x.score, reverse=True)
    top_candidates = candidates[: settings.RAG_TOP_K_RETRIEVAL]

    # 4. Cross-Encoder / Semantic Reranking to select final top_k
    final_chunks = _rerank_candidates(query, top_candidates, top_k=top_k)
    return final_chunks
