import logging
from sentence_transformers import SentenceTransformer
from .config import settings

logger = logging.getLogger(__name__)

_model_instance: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Lazy singleton loader for the sentence-transformers embedding model."""
    global _model_instance
    if _model_instance is not None:
        return _model_instance

    model_name = settings.EMBEDDING_MODEL_NAME
    logger.info("Loading embedding model: %s", model_name)
    try:
        _model_instance = SentenceTransformer(model_name)
        return _model_instance
    except Exception as exc:
        logger.exception("Failed to initialize embedding model: %s", model_name)
        raise RuntimeError(f"Embedding model initialization failed: {exc}") from exc


def generate_embedding(text: str) -> list[float]:
    """Generate 384-dimensional dense vector for a given text."""
    if not text or not text.strip():
        return [0.0] * settings.VECTOR_DIMENSION
    model = get_embedding_model()
    return model.encode(text).tolist()
