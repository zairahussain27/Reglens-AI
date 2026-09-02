import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .api.routes import router
from .core.config import settings
from .database.db import ensure_db_dir, init_db

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("reglens.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing RegLens AI backend services...")
    ensure_db_dir()
    init_db()
    logger.info("RegLens AI backend initialized successfully.")
    yield
    logger.info("RegLens AI backend shutting down.")


app = FastAPI(
    title="RegLens AI API",
    description="Backend API for RegLens AI compliance analysis (FastAPI + Gemini + Qdrant)",
    version="2.0.0",
    lifespan=lifespan,
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

# CORS configuration
allowed_origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    friendly_messages = []

    for error in errors:
        field = error.get("loc", ("unknown",))[-1]
        msg = error.get("msg", "Invalid value")
        lower_msg = msg.lower()

        if "at least" in lower_msg or "shorter" in lower_msg:
            friendly_messages.append(
                f"{field}: This field is too short. Please provide more details."
            )
        elif "at most" in lower_msg or "longer" in lower_msg:
            friendly_messages.append(f"{field}: This field is too long. Please keep it brief.")
        elif "required" in lower_msg:
            friendly_messages.append(f"{field}: This field is required.")
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled API exception at %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# Include API routes
app.include_router(router)
