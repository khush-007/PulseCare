import hashlib
import math
from typing import List
from backend.app.core.config import settings

# Global cache for sentence transformer model if loaded
_local_model = None


def _get_mock_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Generate a deterministic, normalized pseudo-embedding vector for text.
    Uses SHA-256 character hashes with token frequency weighting so that
    semantically identical or overlapping words produce higher cosine similarity.
    """
    words = text.lower().split()
    vec = [0.0] * dim
    if not words:
        return vec
        
    for word in words:
        h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        # Distribute hash influence across multiple dimensions
        idx1 = h % dim
        idx2 = (h >> 16) % dim
        idx3 = (h >> 32) % dim
        vec[idx1] += 1.0
        vec[idx2] += 0.5
        vec[idx3] += 0.25

    # L2 Normalization
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def get_embedding(text: str) -> List[float]:
    """Compute dense embedding vector for a single text string."""
    provider = settings.EMBEDDING_PROVIDER.lower()
    dim = settings.EMBEDDING_DIMENSION
    
    if provider == "mock":
        return _get_mock_embedding(text, dim)
        
    elif provider in ["huggingface", "sentence-transformers"]:
        global _local_model
        if _local_model is None:
            from sentence_transformers import SentenceTransformer
            _local_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        emb = _local_model.encode(text, normalize_embeddings=True)
        return emb.tolist()
        
    elif provider == "gemini" and settings.LLM_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=settings.LLM_API_KEY)
            resp = client.models.embed_content(
                model=settings.EMBEDDING_MODEL,
                contents=text,
            )
            return resp.embedding.values
        except Exception:
            return _get_mock_embedding(text, dim)
            
    else:
        return _get_mock_embedding(text, dim)


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Compute embeddings for a batch of strings."""
    return [get_embedding(t) for t in texts]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two normalized vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    return float(dot)
