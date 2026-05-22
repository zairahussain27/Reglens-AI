#!/usr/bin/env python3
"""PDF report generation smoke test."""

from src.app import build_pdf_report


TEST_BUSINESS_PROFILE = {
    "business_type": "Private Limited Company",
    "industry": "FinTech - Digital Payments",
    "services": "Online payment gateway with UPI integration",
    "customer_type": "Retail Consumers (B2C)",
    "transaction_type": "Digital Payments / UPI",
    "revenue": "Rs 1 Crore - Rs 5 Crore",
}

TEST_RESULT = """
## Compliance Analysis

Your business falls under RBI regulations for payment aggregators.

### Applicable Regulations:
1. RBI Payment Aggregators Guidelines 2020
2. KYC Master Directions 2016

### Risk Assessment: Medium (45%)
"""

TEST_TIMELINE = {
    "Immediate": ["Register with RBI as Payment Aggregator", "Implement KYC procedures"],
    "Monthly": ["Submit transaction reports", "Conduct internal audits"],
    "Quarterly": ["File regulatory returns", "Update compliance documentation"],
}


def test_build_pdf_report_returns_pdf_bytes():
    pdf_bytes = build_pdf_report(TEST_BUSINESS_PROFILE, TEST_RESULT, 45, TEST_TIMELINE)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


if __name__ == "__main__":
    pdf = build_pdf_report(TEST_BUSINESS_PROFILE, TEST_RESULT, 45, TEST_TIMELINE)
    with open("test_report.pdf", "wb") as report_file:
        report_file.write(pdf)
    print(f"PDF saved as test_report.pdf ({len(pdf)} bytes)")
