import re
from typing import Optional, Dict, List
from pydantic import BaseModel, field_validator


def sanitize_string(value: str) -> str:
    """Remove potentially malicious characters and patterns from strings."""
    if not isinstance(value, str):
        return value

    # Remove newlines, carriage returns, tabs
    value = value.replace("\n", " ").replace("\r", " ").replace("\t", " ")

    # Remove multiple consecutive spaces
    value = re.sub(r"\s+", " ", value)

    # Remove common injection characters
    dangerous_chars = [";", "||", "&&", "`", "$", "{", "}", "(", ")", "[", "]"]
    for char in dangerous_chars:
        value = value.replace(char, " ")

    # Remove URLs and email addresses
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "", value)

    return value.strip()


class BusinessProfile(BaseModel):
    business_type: str
    industry: str
    services: str
    customer_type: str
    transaction_type: str
    revenue: str

    @field_validator("business_type")
    @classmethod
    def validate_business_type(cls, v: str) -> str:
        v = sanitize_string(v)
        if not v or len(v) < 1:
            raise ValueError("Business type is required")
        if len(v) > 100:
            raise ValueError("Business type must not exceed 100 characters")
        return v

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, v: str) -> str:
        v = sanitize_string(v)
        if not v or len(v) < 1:
            raise ValueError("Industry is required")
        if len(v) > 100:
            raise ValueError("Industry must not exceed 100 characters")
        return v

    @field_validator("services")
    @classmethod
    def validate_services(cls, v: str) -> str:
        v = sanitize_string(v)
        if not v or len(v) < 5:
            raise ValueError("Services must be at least 5 characters")
        if len(v) > 2000:
            raise ValueError("Services must not exceed 2000 characters")
        return v

    @field_validator("customer_type")
    @classmethod
    def validate_customer_type(cls, v: str) -> str:
        v = sanitize_string(v)
        if not v or len(v) < 1:
            raise ValueError("Customer type is required")
        if len(v) > 100:
            raise ValueError("Customer type must not exceed 100 characters")
        return v

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: str) -> str:
        v = sanitize_string(v)
        if not v or len(v) < 1:
            raise ValueError("Transaction type is required")
        if len(v) > 100:
            raise ValueError("Transaction type must not exceed 100 characters")
        return v

    @field_validator("revenue")
    @classmethod
    def validate_revenue(cls, v: str) -> str:
        v = sanitize_string(v)
        if not v or len(v) < 1:
            raise ValueError("Revenue information is required")
        if len(v) > 100:
            raise ValueError("Revenue must not exceed 100 characters")
        if not re.search(r"\d+|crore|lakh|year|annual|under|above", v.lower()):
            raise ValueError("Revenue must contain valid currency or amount details")
        return v


class ComplianceResponse(BaseModel):
    result: str
    source_documents: list[str] = []


class ComplianceHistoryItem(BaseModel):
    id: int
    timestamp: str
    business_type: str
    industry: str
    services: str
    customer_type: str
    transaction_type: str
    revenue: str
    status: str
    result_text: str
    source_documents: Optional[str] = None


class PDFExportRequest(BaseModel):
    business_profile: Dict[str, str]
    result_text: str
    risk_score: int = 50
    timeline: Dict[str, List[str]] = {}
    source_documents: List[str] = []
