import chromadb
from sentence_transformers import SentenceTransformer
import logging
import os
from urllib.parse import urlparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger = logging.getLogger(__name__)

# Whitelist of trusted government domains (same as ingest.py)
TRUSTED_DOMAINS = [
    'rbi.org.in',
    'gst.gov.in',
    'msme.gov.in',
    'sebi.gov.in',
    'mca.gov.in',
    'fema.gov.in',
    'gov.in',
    'nic.in',
]

def is_trusted_domain(url):
    """Check if URL is from an exact trusted domain or a real subdomain."""
    parsed = urlparse(url)
    domain = (parsed.hostname or "").lower().rstrip(".")
    return any(
        domain == trusted or domain.endswith(f".{trusted}")
        for trusted in TRUSTED_DOMAINS
    )

chroma_db_path = os.getenv("CHROMA_DB_PATH", os.path.join(ROOT_DIR, "chroma_db"))
if not os.path.isabs(chroma_db_path):
    chroma_db_path = os.path.abspath(os.path.join(ROOT_DIR, chroma_db_path))

_model = None
_client = None
_collection = None


def get_embedding_model():
    """Load the embedding model lazily so API startup can still report health."""
    global _model
    if _model is None:
        logger.info("Loading sentence-transformers embedding model")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_collection():
    """Initialize ChromaDB lazily and reuse the collection between requests."""
    global _client, _collection
    if _collection is None:
        logger.info("Opening ChromaDB collection at %s", chroma_db_path)
        _client = chromadb.PersistentClient(path=chroma_db_path)
        _collection = _client.get_or_create_collection(name="regulations")
    return _collection


def check_vector_store() -> dict:
    """Return a small health payload for the retriever dependencies."""
    collection = get_collection()
    return {
        "status": "ok",
        "path": chroma_db_path,
        "documents": collection.count(),
    }

def retrieve(query, n_results=5):
    if not isinstance(query, str) or not query.strip():
        logger.warning("Retriever received an empty or invalid query")
        return []

    try:
        n_results = max(1, min(int(n_results), 20))
    except (TypeError, ValueError):
        logger.warning("Invalid n_results=%r; falling back to 5", n_results)
        n_results = 5

    try:
        embedding = get_embedding_model().encode(query).tolist()
    except Exception:
        logger.exception("Embedding model failed while encoding query")
        return []

    try:
        results = get_collection().query(
            query_embeddings=[embedding],
            n_results=n_results,
        )
    except Exception:
        logger.exception("ChromaDB query failed")
        return []

    try:
        documents = results.get("documents") or []
        metadatas = results.get("metadatas") or []
        chunks = documents[0] if documents else []
        chunk_metadatas = metadatas[0] if metadatas else []
    except (AttributeError, IndexError, TypeError):
        logger.exception("Unexpected ChromaDB response structure")
        return []

    if not chunks:
        logger.warning("ChromaDB returned no chunks for the query")
        return []

    filtered_results = []
    for index, (chunk, metadata) in enumerate(zip(chunks, chunk_metadatas)):
        try:
            if not isinstance(chunk, str) or not chunk.strip():
                continue

            metadata = metadata or {}
            if not isinstance(metadata, dict):
                logger.debug("Skipping chunk %s with invalid metadata", index)
                continue

            source_url = metadata.get("source_url")
            if source_url and is_trusted_domain(source_url):
                filtered_results.append((chunk, source_url))
            elif not source_url:
                filtered_results.append((chunk, metadata.get("source", "local")))
            else:
                logger.debug("Skipping untrusted source URL: %s", source_url)
        except Exception:
            logger.exception("Failed to process retrieved chunk %s", index)

    if not filtered_results:
        logger.warning("All retrieved chunks were empty or filtered out")

    return filtered_results
