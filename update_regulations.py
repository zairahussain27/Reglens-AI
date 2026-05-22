#!/usr/bin/env python3
"""
Update script to fetch latest government regulations
Run this periodically to keep the knowledge base current
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingest import ingest_all_from_urls
from government_sources import GOVERNMENT_SOURCES

def update_regulations():
    """Fetch and ingest latest regulations from government sources"""
    print("🔄 Updating RegLens AI knowledge base from official government sources...")
    print(f"Found {len(GOVERNMENT_SOURCES)} official URLs to check")

    summary = ingest_all_from_urls(GOVERNMENT_SOURCES)

    if summary["rejected_or_failed"]:
        print(
            "Update finished with "
            f"{summary['rejected_or_failed']} rejected or failed source(s). "
            "Only trusted HTTPS government PDFs were ingested."
        )
    else:
        print("Update complete. Knowledge base refreshed with trusted government PDFs.")


if __name__ == "__main__":
    update_regulations()
