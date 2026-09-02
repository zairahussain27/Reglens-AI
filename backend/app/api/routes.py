import json
import logging
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from ..core.compliance_engine import run_compliance_check_with_sources
from ..core.retriever import check_vector_store
from ..database.db import fetch_recent_requests, log_request, ping_database
from ..schemas.compliance import (
    BusinessProfile,
    ComplianceHistoryItem,
    ComplianceResponse,
    PDFExportRequest,
)
from ..services.pdf_generator import build_pdf_report

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.get("/health")
def health_check() -> JSONResponse:
    """Health check endpoint for database and Qdrant vector store."""
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
        if vector_status.get("status") == "error":
            payload["status"] = "degraded"
    except Exception as exc:
        payload["status"] = "unhealthy"
        payload["components"]["vector_store"] = {"status": "error", "detail": str(exc)}
        status_code = 503
        logger.exception("Vector store health check failed")

    return JSONResponse(status_code=status_code, content=payload)


@router.post("/api/compliance-check", response_model=ComplianceResponse)
def compliance_check(request: Request, profile: BusinessProfile) -> JSONResponse:
    """Execute regulatory compliance analysis for a given business profile."""
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


@router.get("/api/history", response_model=list[ComplianceHistoryItem])
def get_history(request: Request) -> list[ComplianceHistoryItem]:
    """Fetch recent compliance checks from audit logs."""
    try:
        return fetch_recent_requests(limit=50)
    except Exception:
        logger.exception("Audit history endpoint failed")
        raise HTTPException(status_code=503, detail="Audit history is unavailable.")


@router.post("/api/export-pdf")
def export_pdf(payload: PDFExportRequest) -> Response:
    """Generate a downloadable PDF compliance report."""
    try:
        pdf_bytes = build_pdf_report(
            business_profile=payload.business_profile,
            result_text=payload.result_text,
            risk_score=payload.risk_score,
            timeline=payload.timeline,
            source_documents=payload.source_documents,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=reglens_compliance_report.pdf"},
        )
    except Exception as exc:
        logger.exception("PDF report generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="PDF generation failed.")
