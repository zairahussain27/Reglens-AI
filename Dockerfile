FROM python:3.11-slim

# Default image: backend API. The Streamlit UI is built from Dockerfile.frontend.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-backend.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements-backend.txt

COPY src ./src
COPY prompts ./prompts
COPY regulations ./regulations

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

ENV ALLOWED_ORIGINS=http://localhost:8501,http://frontend:8501 \
    DATABASE_URL=sqlite:////app/data/reglens.db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
