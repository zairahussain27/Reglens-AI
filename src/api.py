import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from .schemas import BusinessProfile, ComplianceResponse, ComplianceHistoryItem
from .compliance_engine import run_compliance_check
from .db import init_db, log_request, fetch_recent_requests

# Load environment variables
load_dotenv()

app = FastAPI(
    title="RegLens AI API",
    description="Backend API for RegLens AI compliance analysis",
    version="1.0.0",
)

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format validation errors with user-friendly messages"""
    errors = exc.errors()
    friendly_messages = []
    
    for error in errors:
        field = error.get('loc', ('unknown',))[-1]
        msg = error.get('msg', 'Invalid value')
        
        # Map validation errors to friendly messages
        if 'at least' in msg.lower() or 'shorter' in msg.lower():
            friendly_messages.append(f"⚠️ {field}: This field is too short. Please provide more details.")
        elif 'at most' in msg.lower() or 'longer' in msg.lower():
            friendly_messages.append(f"⚠️ {field}: This field is too long. Please keep it brief.")
        elif 'required' in msg.lower():
            friendly_messages.append(f"⚠️ {field}: This field is required.")
        elif 'currency' in msg.lower():
            friendly_messages.append(f"⚠️ {field}: Please enter valid revenue information (e.g., '₹1 Crore' or 'Under ₹1 Crore').")
        else:
            friendly_messages.append(f"⚠️ {field}: {msg}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation failed - please check your input",
            "errors": friendly_messages
        }
    )

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={"detail": "Rate limit exceeded. Too many requests."}
))

# Get allowed origins from environment, defaults to localhost for development
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/api/compliance-check", response_model=ComplianceResponse)
@limiter.limit("10/minute")
def compliance_check(request: Request, profile: BusinessProfile) -> JSONResponse:
    try:
        result = run_compliance_check(profile.dict())
        log_request(profile.dict(), status="success", result_text=result)
        return JSONResponse(status_code=200, content={"result": result})
    except Exception as exc:
        log_request(profile.dict(), status="error", result_text=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/history", response_model=list[ComplianceHistoryItem])
@limiter.limit("30/minute")
def get_history(request: Request) -> list[ComplianceHistoryItem]:
    history = fetch_recent_requests(limit=50)
    return history
