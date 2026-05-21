import json
import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .compliance_engine import run_compliance_check_with_sources
from .db import fetch_recent_requests, init_db, log_request, ping_database
from .retriever import check_vector_store
from .schemas import BusinessProfile, ComplianceHistoryItem, ComplianceResponse

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RegLens AI API",
    description="Backend API for RegLens AI compliance analysis",
    version="1.0.0",
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Unhandled request failure %s %s after %.1fms",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "%s %s -> %s in %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    friendly_messages = []

    for error in errors:
        field = error.get("loc", ("unknown",))[-1]
        msg = error.get("msg", "Invalid value")
        lower_msg = msg.lower()

        if "at least" in lower_msg or "shorter" in lower_msg:
            friendly_messages.append(f"{field}: This field is too short. Please provide more details.")
        elif "at most" in lower_msg or "longer" in lower_msg:
            friendly_messages.append(f"{field}: This field is too long. Please keep it brief.")
        elif "required" in lower_msg:
            friendly_messages.append(f"{field}: This field is required.")
        elif "currency" in lower_msg:
            friendly_messages.append(f"{field}: Please enter valid revenue information, such as '1 Crore' or 'Under 1 Crore'.")
        else:
            friendly_messages.append(f"{field}: {msg}")

    logger.warning("Request validation failed at %s: %s", request.url.path, friendly_messages)
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation failed - please check your input",
            "errors": friendly_messages,
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    logger.warning("Rate limit exceeded for %s", get_remote_address(request))
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Too many requests."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled API exception at %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8501")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    try:
        # Validate environment and required paths before initializing services
        validate_environment()
        init_db()
    except Exception:
        logger.exception("Startup initialization failed")
        raise


def validate_environment() -> None:
    """Basic environment validation performed on startup.

    - Ensures required directories exist and are writable
    - Enforces presence of critical secrets in production
    """
    env = os.getenv("ENVIRONMENT", "development").lower()

    # Ensure data directories exist when using local paths
    db_url = os.getenv("DATABASE_URL")
    chroma_path = os.getenv("CHROMA_DB_PATH")

    # Resolve and create chroma db path if necessary
    if chroma_path:
        try:
            if not os.path.isabs(chroma_path):
                chroma_path = os.path.abspath(chroma_path)
            os.makedirs(chroma_path, exist_ok=True)
        except Exception:
            logger.exception("Could not create CHROMA_DB_PATH at %s", chroma_path)
            if env == "production":
                raise

    # Ensure database directory exists for sqlite file paths
    if db_url and db_url.startswith("sqlite") and "memory" not in db_url:
        try:
            # Strip sqlite:/// prefix
            path = db_url.removeprefix("sqlite:///")
            if not os.path.isabs(path):
                path = os.path.abspath(os.path.join(os.getcwd(), path))
            db_dir = os.path.dirname(path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        except Exception:
            logger.exception("Could not create database directory for %s", db_url)
            if env == "production":
                raise

    # Enforce GROQ API key presence in production
    groq_key = os.getenv("GROQ_API_KEY")
    if env == "production" and not groq_key:
        logger.error("GROQ_API_KEY is required in production environment")
        raise RuntimeError("Missing GROQ_API_KEY in production environment")


def profile_to_dict(profile: BusinessProfile) -> dict:
    if hasattr(profile, "model_dump"):
        return profile.model_dump()
    return profile.dict()


def safe_log_request(
    profile_data: dict,
    status: str,
    result_text: str,
    source_documents: str | None = None,
) -> None:
    try:
        log_request(
            profile_data,
            status=status,
            result_text=result_text,
            source_documents=source_documents,
        )
    except Exception:
        logger.exception("Failed to write audit log for %s request", status)


@app.get("/health")
def health_check() -> JSONResponse:
    status_code = 200
    payload = {
        "status": "healthy",
        "components": {},
    }

    try:
        payload["components"]["database"] = ping_database()
    except Exception as exc:
        payload["status"] = "unhealthy"
        payload["components"]["database"] = {"status": "error", "detail": str(exc)}
        status_code = 503
        logger.exception("Database health check failed")

    try:
        vector_status = check_vector_store()
        payload["components"]["vector_store"] = vector_status
        if vector_status.get("documents", 0) == 0:
            payload["status"] = "degraded"
            if os.getenv("REQUIRE_VECTOR_STORE_READY", "false").lower() == "true":
                status_code = 503
    except Exception as exc:
        payload["status"] = "unhealthy"
        payload["components"]["vector_store"] = {"status": "error", "detail": str(exc)}
        status_code = 503
        logger.exception("Vector store health check failed")

    return JSONResponse(status_code=status_code, content=payload)


@app.post("/api/compliance-check", response_model=ComplianceResponse)
@limiter.limit("10/minute")
def compliance_check(request: Request, profile: BusinessProfile) -> JSONResponse:
    profile_data = profile_to_dict(profile)

    try:
        logger.info("Compliance check requested for industry=%s", profile_data.get("industry"))
        result, source_documents = run_compliance_check_with_sources(profile_data)
        safe_log_request(
            profile_data,
            status="success",
            result_text=result,
            source_documents=json.dumps(source_documents),
        )
        return JSONResponse(
            status_code=200,
            content={"result": result, "source_documents": source_documents},
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning("Compliance validation error: %s", exc)
        safe_log_request(profile_data, status="error", result_text=str(exc))
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Compliance check failed unexpectedly")
        safe_log_request(profile_data, status="error", result_text=str(exc))
        raise HTTPException(
            status_code=500,
            detail="Compliance analysis failed. Please try again later.",
        )


@app.get("/api/history", response_model=list[ComplianceHistoryItem])
@limiter.limit("30/minute")
def get_history(request: Request) -> list[ComplianceHistoryItem]:
    try:
        return fetch_recent_requests(limit=50)
    except Exception:
        logger.exception("Audit history endpoint failed")
        raise HTTPException(status_code=503, detail="Audit history is unavailable.")
