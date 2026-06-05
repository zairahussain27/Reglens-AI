import logging
import os
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Whitelist of trusted government domains (India-specific)
TRUSTED_DOMAINS = [
    "rbi.org.in",
    "gst.gov.in",
    "msme.gov.in",
    "sebi.gov.in",
    "mca.gov.in",
    "fema.gov.in",
    "gov.in",
    "nic.in",
]

VECTOR_STORE_DISABLED_REASON = "Qdrant ingestion is disabled for this deployment."


def is_trusted_domain(url):
    """Check if URL is from an exact trusted domain or a real subdomain."""
    parsed = urlparse(url)
    domain = (parsed.hostname or "").lower().rstrip(".")
    return any(
        domain == trusted or domain.endswith(f".{trusted}")
        for trusted in TRUSTED_DOMAINS
    )


def is_trusted_pdf_url(url):
    """Only accept HTTPS PDF URLs from trusted government domains."""
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and is_trusted_domain(url)
        and parsed.path.lower().endswith(".pdf")
    )


def looks_like_pdf(content):
    """Verify that downloaded bytes look like a real PDF."""
    return content.lstrip()[:4] == b"%PDF"


def safe_pdf_filename(url):
    """Derive a local filename from a trusted PDF URL."""
    filename = os.path.basename(urlparse(url).path)
    if not filename or not filename.lower().endswith(".pdf"):
        raise ValueError("URL must point to a PDF file")
    return filename


def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


def ingest_pdf_from_url(pdf_url):
    """Report that URL ingestion is unavailable while Qdrant ingestion is disabled."""
    if not is_trusted_pdf_url(pdf_url):
        print(f"Rejected: {pdf_url} - Only HTTPS PDF URLs from trusted government domains are allowed")
    else:
        print(f"Skipped: {pdf_url} - {VECTOR_STORE_DISABLED_REASON}")
    return False


def remove_existing_source(filename, source_url=None):
    """Report disabled cleanup for callers that still invoke the old ingest API."""
    logger.warning(VECTOR_STORE_DISABLED_REASON)
    return {"by_filename": False, "by_url": False, "errors": [VECTOR_STORE_DISABLED_REASON]}


def ingest_pdf(pdf_path, source_url=None):
    raise RuntimeError(VECTOR_STORE_DISABLED_REASON)


def ingest_all(folder_path=None):
    raise RuntimeError(VECTOR_STORE_DISABLED_REASON)


def ingest_all_from_urls(pdf_urls):
    """Preserve the old update API while making Qdrant ingestion a no-op."""
    total = len(pdf_urls)
    for index, pdf_url in enumerate(pdf_urls, start=1):
        print(f"\n[{index}/{total}] Checking source: {pdf_url}")
        ingest_pdf_from_url(pdf_url)

    print(f"\nUpdate skipped: {VECTOR_STORE_DISABLED_REASON}")
    return {
        "total": total,
        "successful": 0,
        "rejected_or_failed": total,
    }


if __name__ == "__main__":
    logger.warning(VECTOR_STORE_DISABLED_REASON)
    print(VECTOR_STORE_DISABLED_REASON)
