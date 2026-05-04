import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .schemas import BusinessProfile, ComplianceResponse, ComplianceHistoryItem
from .compliance_engine import run_compliance_check
from .db import init_db, log_request, fetch_recent_requests

app = FastAPI(
    title="RegLens AI API",
    description="Backend API for RegLens AI compliance analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/api/compliance-check", response_model=ComplianceResponse)
def compliance_check(profile: BusinessProfile) -> JSONResponse:
    try:
        result = run_compliance_check(profile.dict())
        log_request(profile.dict(), status="success", result_text=result)
        return JSONResponse(status_code=200, content={"result": result})
    except Exception as exc:
        log_request(profile.dict(), status="error", result_text=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/history", response_model=list[ComplianceHistoryItem])
def get_history() -> list[ComplianceHistoryItem]:
    history = fetch_recent_requests(limit=50)
    return history
