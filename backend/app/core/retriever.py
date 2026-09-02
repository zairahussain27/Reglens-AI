import logging
from typing import Any
from qdrant_client import QdrantClient
from .config import settings
from .embeddings import generate_embedding

logger = logging.getLogger(__name__)

_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Lazy singleton loader for Qdrant client."""
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client

    if not settings.QDRANT_URL:
        raise RuntimeError("QDRANT_URL is not configured")

    try:
        kwargs: dict[str, Any] = {"url": settings.QDRANT_URL}
        if settings.QDRANT_API_KEY:
            kwargs["api_key"] = settings.QDRANT_API_KEY
        _qdrant_client = QdrantClient(**kwargs)
        return _qdrant_client
    except Exception as exc:
        logger.exception("Failed to initialize Qdrant client")
        raise RuntimeError(f"Qdrant client initialization failed: {exc}") from exc


def check_vector_store() -> dict:
    """Return health payload for Qdrant vector store."""
    try:
        client = get_qdrant_client()
        count_result = client.count(collection_name=settings.QDRANT_COLLECTION)
        vector_count = int(getattr(count_result, "count", 0))

        return {
            "status": "ok" if vector_count > 0 else "empty",
            "mode": "qdrant",
            "collection": settings.QDRANT_COLLECTION,
            "documents": vector_count,
            "detail": f"Qdrant collection '{settings.QDRANT_COLLECTION}' available with {vector_count} points",
        }
    except Exception as exc:
        logger.warning("Vector store health check failed: %s", exc)
        return {
            "status": "error",
            "mode": "qdrant",
            "collection": settings.QDRANT_COLLECTION,
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


def retrieve(query: str, n_results: int = 8) -> list[tuple[str, str, dict]]:
    """Retrieve top-N relevant regulation chunks from Qdrant Cloud.

    Returns:
        List of tuples: (chunk_text, source_document_name, full_metadata)
    """
    if not isinstance(query, str) or not query.strip():
        logger.warning("Empty query received for retrieval")
        return []

    try:
        query_vector = generate_embedding(query)
    except Exception as exc:
        logger.exception("Embedding generation failed for query: %s", exc)
        return []

    try:
        client = get_qdrant_client()
        query_response = client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=query_vector,
            limit=n_results,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:
        logger.exception("Qdrant retrieval query failed: %s", exc)
        return []

    results: list[tuple[str, str, dict]] = []
    for hit in getattr(query_response, "points", []):
        payload = _normalize_payload(getattr(hit, "payload", None))
        text = payload.get("text", "") or ""
        source = payload.get("source", payload.get("document_name", "unknown")) or "unknown"
        results.append((text, source, payload))

    return results
