#!/usr/bin/env python3
"""Preflight checks for RegLens AI deployments."""

from __future__ import annotations

import os
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "Dockerfile.backend",
    "Dockerfile.frontend",
    "docker-compose.yml",
    "requirements-backend.txt",
    "requirements-frontend.txt",
    "src/api.py",
    "src/app.py",
    "prompts/compliance.txt",
    "k8s/configmap.yaml",
    "k8s/secret.example.yaml",
    "k8s/ingest-job.yaml",
    "k8s/backend-deployment.yaml",
    "k8s/frontend-deployment.yaml",
    "k8s/backend-service.yaml",
    "k8s/frontend-service.yaml",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    sys.exit(1)


def check_files() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        fail("Missing required deployment files: " + ", ".join(missing))


def check_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        print("WARN: .env is missing. Create it from .env.example before Docker Compose deployment.")
        return

    env_text = env_file.read_text(encoding="utf-8", errors="replace")
    if "GROQ_API_KEY=" not in env_text:
        fail(".env does not define GROQ_API_KEY")
    if "gsk_your_api_key_here" in env_text or "YOUR_GROQ_API_KEY" in env_text:
        fail(".env still contains a placeholder GROQ_API_KEY")


def check_regulations() -> None:
    regulations_dir = ROOT / "regulations"
    if not regulations_dir.exists():
        fail("regulations/ directory is missing")

    pdfs = list(regulations_dir.glob("*.pdf"))
    if not pdfs:
        fail("regulations/ contains no PDF files to ingest")

    print(f"OK: found {len(pdfs)} bundled regulation PDF(s)")


def check_gitignore() -> None:
    gitignore = ROOT / ".gitignore"
    if not gitignore.exists():
        print("WARN: .gitignore is missing")
        return

    ignored = gitignore.read_text(encoding="utf-8", errors="replace")
    for pattern in [".env", "venv", "__pycache__"]:
        if pattern not in ignored:
            print(f"WARN: .gitignore does not include {pattern}")


def main() -> int:
    os.chdir(ROOT)
    check_files()
    check_env()
    check_regulations()
    check_gitignore()
    print("OK: deployment preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
