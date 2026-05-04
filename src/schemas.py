from pydantic import BaseModel
from typing import Optional


class BusinessProfile(BaseModel):
    business_type: str
    industry: str
    services: str
    customer_type: str
    transaction_type: str
    revenue: str


class ComplianceResponse(BaseModel):
    result: str


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
