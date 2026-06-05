"""Deprecated migration utility.

This script previously migrated data from a local ChromaDB store into Qdrant.
The application now uses Qdrant Cloud directly for semantic retrieval, and the
legacy ChromaDB migration workflow is no longer supported.
"""

import logging

logger = logging.getLogger(__name__)
logger.warning("src/migrate_to_qdrant.py is deprecated and no longer supported.")
print("Deprecated migration utility: please use a current Qdrant ingestion workflow.")