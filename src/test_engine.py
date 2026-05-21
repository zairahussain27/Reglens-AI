"""Manual smoke script for the compliance engine.

Run with:
    python -m src.test_engine
"""

from src.compliance_engine import run_compliance_check


TEST_PROFILE = {
    "business_type": "Private Limited Company",
    "industry": "FinTech - Digital Payments",
    "services": "Online payment gateway, wallet services, UPI transactions",
    "customer_type": "Retail Consumers (B2C)",
    "transaction_type": "Digital Payments / UPI",
    "revenue": "Under Rs 1 Crore",
}


def main() -> None:
    print("Running RegLens AI compliance check...\n")
    result = run_compliance_check(TEST_PROFILE)
    print(result)


if __name__ == "__main__":
    main()
