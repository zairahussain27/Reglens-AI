import pdfplumber
import chromadb
from sentence_transformers import SentenceTransformer
import os
import requests
import logging
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Whitelist of trusted government domains (India-specific)
TRUSTED_DOMAINS = [
    'rbi.org.in',
    'gst.gov.in',
    'msme.gov.in',
    'sebi.gov.in',
    'mca.gov.in',
    'fema.gov.in',
    'gov.in',  # General .gov.in for other ministries
    'nic.in',  # National Informatics Centre
]

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

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize ChromaDB
chroma_db_path = os.getenv("CHROMA_DB_PATH", os.path.join(ROOT_DIR, "chroma_db"))
if not os.path.isabs(chroma_db_path):
    chroma_db_path = os.path.abspath(os.path.join(ROOT_DIR, chroma_db_path))

client = chromadb.PersistentClient(path=chroma_db_path)
collection = client.get_or_create_collection(name="regulations")

def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def ingest_pdf_from_url(pdf_url):
    """Download and ingest PDF from a trusted government URL"""
    if not is_trusted_pdf_url(pdf_url):
        print(f"Rejected: {pdf_url} - Only HTTPS PDF URLs from trusted government domains are allowed")
        return False
    
    filename = safe_pdf_filename(pdf_url)
    print(f"Downloading: {pdf_url}")
    
    temp_path = None
    try:
        response = requests.get(pdf_url, timeout=30, allow_redirects=True)
        response.raise_for_status()

        final_url = response.url
        if not is_trusted_pdf_url(final_url):
            print(f"Rejected: {pdf_url} redirected to untrusted or non-PDF URL: {final_url}")
            return False

        if not looks_like_pdf(response.content):
            print(f"Rejected: {pdf_url} - Downloaded content is not a valid PDF")
            return False
        
        # Save temporarily
        temp_path = os.path.join(ROOT_DIR, "temp", filename)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        # Process the PDF
        ingest_pdf(temp_path, source_url=final_url)
        return True
        
    except Exception as e:
        print(f"Failed to download {pdf_url}: {str(e)}")
        return False
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

def remove_existing_source(filename, source_url=None):
    """Remove old chunks for a source so updates are repeatable.
    
    Properly logs and handles errors during deletion to ensure visibility into failures.
    """
    deletion_status = {"by_filename": False, "by_url": False, "errors": []}
    
    # Attempt to delete by filename
    if filename:
        try:
            logger.info(f"Attempting to delete existing chunks for file: {filename}")
            collection.delete(where={"source": filename})
            deletion_status["by_filename"] = True
            logger.info(f"✅ Successfully deleted chunks for file: {filename}")
        except Exception as e:
            error_msg = f"⚠️ Failed to delete chunks by filename '{filename}': {type(e).__name__}: {str(e)}"
            logger.warning(error_msg)
            deletion_status["errors"].append(error_msg)
    
    # Attempt to delete by source URL if provided
    if source_url:
        try:
            logger.info(f"Attempting to delete existing chunks for URL: {source_url}")
            collection.delete(where={"source_url": source_url})
            deletion_status["by_url"] = True
            logger.info(f"✅ Successfully deleted chunks for URL: {source_url}")
        except Exception as e:
            error_msg = f"⚠️ Failed to delete chunks by URL '{source_url}': {type(e).__name__}: {str(e)}"
            logger.warning(error_msg)
            deletion_status["errors"].append(error_msg)
    
    return deletion_status

def ingest_pdf(pdf_path, source_url=None):
    filename = os.path.basename(pdf_path)
    print(f"Processing: {filename}")
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + " "
    
    chunks = chunk_text(full_text)
    if not chunks:
        raise ValueError(f"No extractable text found in {filename}")

    # Remove old chunks for this source (with proper error logging)
    deletion_status = remove_existing_source(filename, source_url=source_url)
    if deletion_status["errors"]:
        logger.warning(f"Deletion had {len(deletion_status['errors'])} error(s) during cleanup.")
    
    for i, chunk in enumerate(chunks):
        embedding = model.encode(chunk).tolist()
        metadata = {"source": filename}
        if source_url:
            metadata["source_url"] = source_url
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{filename}_chunk_{i}"],
            metadatas=[metadata]
        )
    
    print(f"✅ Done: {filename} — {len(chunks)} chunks stored from {source_url or 'local file'}")

def ingest_all(folder_path=None):
    if folder_path is None:
        folder_path = os.path.join(ROOT_DIR, "regulations")

    files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
    for file in files:
        ingest_pdf(os.path.join(folder_path, file))
    print("\n✅ All PDFs ingested successfully.")

def ingest_all_from_urls(pdf_urls):
    """Download and ingest a list of trusted government PDF URLs."""
    total = len(pdf_urls)
    successful = 0
    rejected_or_failed = 0

    for index, pdf_url in enumerate(pdf_urls, start=1):
        print(f"\n[{index}/{total}] Checking source: {pdf_url}")
        if ingest_pdf_from_url(pdf_url):
            successful += 1
        else:
            rejected_or_failed += 1

    print(
        f"\nUpdate summary: {successful} ingested, "
        f"{rejected_or_failed} rejected or failed, {total} total."
    )
    return {
        "total": total,
        "successful": successful,
        "rejected_or_failed": rejected_or_failed,
    }

if __name__ == "__main__":
    ingest_all()
