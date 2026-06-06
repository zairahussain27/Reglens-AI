import logging
import os
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
#from sentence_transformers import SentenceTransformer

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

logger = logging.getLogger(__name__)

VECTOR_COLLECTION_NAME = "regulations"
VECTOR_STORE_MODE = "qdrant"
VECTOR_STORE_DETAIL = "Using Qdrant Cloud for semantic retrieval."
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

_qdrant_client: QdrantClient | None = None
#_embedding_model: SentenceTransformer | None = None

#def get_embedding_model() -> SentenceTransformer:
#    global _embedding_model
#    if _embedding_model is not None:
#        return _embedding_model
#
#    if not EMBEDDING_MODEL_NAME:
#        raise RuntimeError("EMBEDDING_MODEL_NAME is not configured")
#
#    try:
#        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
#        return _embedding_model
#    except Exception as exc:
#        logger.exception(
#            "Failed to initialize embedding model %s",
#            EMBEDDING_MODEL_NAME,
#        )
#        raise RuntimeError("Embedding model initialization failed") from exc
#
#
def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client

    if not QDRANT_URL:
        raise RuntimeError("QDRANT_URL is not configured")

    if not QDRANT_API_KEY:
        raise RuntimeError("QDRANT_API_KEY is not configured")

    try:
        _qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        return _qdrant_client
    except Exception as exc:
        logger.exception("Failed to initialize Qdrant client")
        raise RuntimeError("Qdrant client initialization failed") from exc


def check_vector_store() -> dict:
    """Return a small health payload for the retriever dependencies."""
    try:
        client = get_qdrant_client()
        count_result = client.count(collection_name=VECTOR_COLLECTION_NAME)
        vector_count = int(getattr(count_result, "count", 0))

        return {
            "status": "ok" if vector_count else "empty",
            "mode": VECTOR_STORE_MODE,
            "documents": vector_count,
            "detail": f"Qdrant collection '{VECTOR_COLLECTION_NAME}' available",
        }
    except Exception as exc:
        logger.exception("Vector store health check failed")
        return {
            "status": "error",
            "mode": VECTOR_STORE_MODE,
            "documents": 0,
            "detail": str(exc),
        }


def _normalize_payload(payload: Any) -> dict:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "to_dict"):
        try:
            return payload.to_dict()
        except Exception:
            pass
    try:
        return dict(payload)
    except Exception:
        return {}


def retrieve(query: str, n_results: int = 8) -> list[tuple[str, str]]:
#    if not isinstance(query, str) or not query.strip():
#        logger.warning("Empty query received for retrieval")
        return []
#
#    try:
#        model = get_embedding_model()
#        embedding = model.encode(query).tolist()
#    except Exception:
#        logger.exception("Embedding generation failed for query")
#        return []
#
#    try:
#        client = get_qdrant_client()
#        hits = client.query_points(
#            collection_name=VECTOR_COLLECTION_NAME,
#            query=embedding,
#            limit=n_results,
#            with_payload=True,
#            with_vectors=False,
#        )
#    except Exception:
#        logger.exception("Qdrant retrieval failed")
#        return []
#
#    results: list[tuple[str, str]] = []
#    for hit in hits:
#        payload = _normalize_payload(getattr(hit, "payload", None))
#        text = payload.get("text", "") or ""
#        source = payload.get("source", "unknown") or "unknown"
#        results.append((text, source))
#
#    return results