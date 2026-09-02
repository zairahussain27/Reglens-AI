import os
import requests
from typing import Tuple, List, Dict, Any, Optional

DEFAULT_BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")


def get_backend_url() -> str:
    return os.getenv("BACKEND_API_URL", DEFAULT_BACKEND_URL).rstrip("/")


def check_backend_health(api_url: Optional[str] = None) -> Tuple[bool, dict]:
    url = (api_url or get_backend_url()).rstrip("/") + "/health"
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200, response.json()
    except Exception as exc:
        return False, {"status": "unreachable", "detail": str(exc)}


def submit_compliance_check(
    business_profile: dict,
    api_url: Optional[str] = None,
) -> Tuple[bool, dict]:
    url = (api_url or get_backend_url()).rstrip("/") + "/api/compliance-check"
    try:
        response = requests.post(url, json=business_profile, timeout=120)
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 422:
            return False, {"error_type": "validation", "detail": response.json()}
        else:
            return False, {
                "error_type": "server",
                "status_code": response.status_code,
                "detail": response.text,
            }
    except requests.exceptions.Timeout:
        return False, {
            "error_type": "timeout",
            "detail": "Server took too long to respond. Please try again.",
        }
    except Exception as exc:
        return False, {"error_type": "connection", "detail": str(exc)}


def fetch_audit_history(api_url: Optional[str] = None) -> Tuple[List[dict], Optional[str]]:
    url = (api_url or get_backend_url()).rstrip("/") + "/api/history"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except Exception as exc:
        return [], str(exc)


def request_pdf_export(payload: dict, api_url: Optional[str] = None) -> Tuple[bool, bytes | str]:
    url = (api_url or get_backend_url()).rstrip("/") + "/api/export-pdf"
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return True, response.content
        return False, f"Server returned status {response.status_code}"
    except Exception as exc:
        return False, str(exc)
