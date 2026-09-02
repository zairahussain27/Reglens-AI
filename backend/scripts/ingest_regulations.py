#!/usr/bin/env python3
"""One-time & re-runnable PDF ingestion script for RegLens AI.

Extracts text from the 11 statutory PDFs in regulations/,
chunks them, computes 384d dense embeddings via all-MiniLM-L6-v2,
and uploads them with full metadata to Qdrant Cloud.
"""

import os
import sys
import uuid
import logging
from pathlib import Path
from typing import List, Dict

import pypdf
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

sys.path.insert(0, str(BACKEND_DIR))
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest")


def clean_text(text: str) -> str:
    """Normalize extracted PDF text."""
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split clean text into overlapping word chunks."""
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if len(chunk.strip()) > 30:  # Ignore trivial chunks
            chunks.append(chunk)
    return chunks


def extract_pdf_chunks(pdf_path: Path) -> List[Dict]:
    """Extract page-wise chunks from a PDF file."""
    reader = pypdf.PdfReader(str(pdf_path))
    doc_name = pdf_path.name
    all_chunks = []
    chunk_counter = 0

    for page_idx, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
            clean_page = clean_text(page_text)
            if not clean_page:
                continue

            page_chunks = chunk_text(clean_page, chunk_size=500, overlap=50)
            for p_chunk in page_chunks:
                chunk_counter += 1
                all_chunks.append(
                    {
                        "document_name": doc_name,
                        "source": doc_name,
                        "page_number": page_idx,
                        "chunk_id": chunk_counter,
                        "text": p_chunk,
                    }
                )
        except Exception as exc:
            logger.warning("Error extracting page %d of %s: %s", page_idx, doc_name, exc)

    return all_chunks


def run_ingestion() -> None:
    regulations_dir = Path(settings.REGULATIONS_DIR)
    if not regulations_dir.exists():
        logger.error("Regulations directory not found: %s", regulations_dir)
        sys.exit(1)

    pdf_files = sorted(list(regulations_dir.glob("*.pdf")))
    if not pdf_files:
        logger.error("No PDF files found in %s", regulations_dir)
        sys.exit(1)

    logger.info("Found %d regulatory PDFs in %s", len(pdf_files), regulations_dir)

    # 1. Extract all chunks
    all_records: List[Dict] = []
    for pdf_file in pdf_files:
        logger.info("Extracting: %s (%d bytes)", pdf_file.name, pdf_file.stat().st_size)
        chunks = extract_pdf_chunks(pdf_file)
        logger.info("  -> Extracted %d chunks from %s", len(chunks), pdf_file.name)
        all_records.extend(chunks)

    total_chunks = len(all_records)
    logger.info("Total chunks across all documents: %d", total_chunks)

    # 2. Compute embeddings
    logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL_NAME)
    embed_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)

    texts = [record["text"] for record in all_records]
    logger.info("Computing dense 384d embeddings for %d chunks...", len(texts))
    embeddings = embed_model.encode(texts, show_progress_bar=True, batch_size=64)

    # 3. Connect to Qdrant Cloud
    if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
        logger.error("QDRANT_URL and QDRANT_API_KEY must be configured in environment.")
        sys.exit(1)

    logger.info("Connecting to Qdrant Cloud at %s...", settings.QDRANT_URL)
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

    collection_name = settings.QDRANT_COLLECTION
    logger.info("Recreating collection '%s' with dimension %d (Cosine)...", collection_name, settings.VECTOR_DIMENSION)

    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=qmodels.VectorParams(
            size=settings.VECTOR_DIMENSION,
            distance=qmodels.Distance.COSINE,
        ),
    )

    # 4. Upload points in batches
    logger.info("Uploading %d points to Qdrant collection '%s'...", total_chunks, collection_name)
    points = []
    batch_size = 20

    for idx, (record, vector) in enumerate(zip(all_records, embeddings)):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{record['document_name']}_{record['page_number']}_{record['chunk_id']}"))
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vector.tolist(),
                payload=record,
            )
        )

        if len(points) >= batch_size:
            client.upsert(collection_name=collection_name, points=points)
            logger.info("  Uploaded %d / %d points...", idx + 1, total_chunks)
            points = []

    if points:
        client.upsert(collection_name=collection_name, points=points)
        logger.info("  Uploaded final batch (%d points).", len(points))

    # 5. Verify count
    count_res = client.count(collection_name=collection_name)
    logger.info("✅ Ingestion successfully completed! Qdrant collection '%s' count: %d", collection_name, count_res.count)


if __name__ == "__main__":
    run_ingestion()
