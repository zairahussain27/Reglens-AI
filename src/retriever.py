import logging
import os
import re
from urllib.parse import urlparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGULATIONS_DIR = os.path.join(ROOT_DIR, "regulations")
logger = logging.getLogger(__name__)

# Whitelist of trusted government domains (same as ingest.py)
TRUSTED_DOMAINS = [
    'rbi.org.in',
    'gst.gov.in',
    'msme.gov.in',
    'sebi.gov.in',
    'mca.gov.in',
    'fema.gov.in',
    'gov.in',
    'nic.in',
]

def is_trusted_domain(url):
    """Check if URL is from an exact trusted domain or a real subdomain."""
    parsed = urlparse(url)
    domain = (parsed.hostname or "").lower().rstrip(".")
    return any(
        domain == trusted or domain.endswith(f".{trusted}")
        for trusted in TRUSTED_DOMAINS
    )

VECTOR_STORE_MODE = "local_keyword"
VECTOR_STORE_DETAIL = "Using bundled regulation context with keyword retrieval; ChromaDB is disabled."

STOP_WORDS = {
    "a", "an", "and", "annual", "are", "as", "at", "based", "be", "business",
    "by", "company", "crore", "customer", "for", "from", "in", "industry", "is",
    "limited", "of", "on", "or", "private", "revenue", "services", "the", "this",
    "to", "transaction", "type", "with",
}

SOURCE_HINTS = {
    "01_RBI_KYC.pdf": {"kyc", "identity", "payment", "lending", "nbfc"},
    "02_RBI_Payment_Aggregators.pdf": {"payment", "aggregator", "gateway", "merchant", "digital", "fintech"},
    "03_RBI_PPI_Master_Directions.pdf": {"ppi", "prepaid", "wallet", "payment", "digital", "fintech"},
    "04_RBI_Digital_Lending.pdf": {"lending", "loan", "credit", "borrower"},
    "05_RBI_NBFC_Master_Direction.pdf": {"nbfc", "lending", "loan", "credit", "finance"},
    "06_RBI_Fair_Practices_NBFC.pdf": {"nbfc", "fair", "practice", "lending", "loan", "borrower"},
    "07_CGST_Rules_2017.pdf": {"gst", "cgst", "tax", "invoice", "ecommerce", "e-commerce", "manufacturing"},
    "08_MSME_Udyam_Registration.pdf": {"msme", "udyam", "manufacturing", "enterprise", "registration"},
    "10_IncomeTax_TDS_Section194.pdf": {"income", "tax", "tds", "section", "deduction"},
    "11_FEMA_Basic_Compliance.pdf": {"fema", "foreign", "exchange", "cross-border", "international"},
    "12_MCA_Company_Filing.pdf": {"mca", "filing", "roc", "director"},
}

QUERY_EXPANSIONS = {
    "fintech": {"rbi", "kyc", "payment"},
    "payments": {"payment", "aggregator", "merchant", "ppi", "kyc"},
    "payment": {"aggregator", "merchant", "ppi", "kyc"},
    "gateway": {"payment", "aggregator", "merchant"},
    "lending": {"loan", "borrower", "credit", "nbfc", "rbi"},
    "loan": {"lending", "borrower", "credit", "nbfc"},
    "nbfc": {"lending", "borrower", "fair", "practice", "rbi"},
    "msme": {"udyam", "enterprise", "registration"},
    "manufacturing": {"msme", "udyam", "gst", "tax"},
    "ecommerce": {"gst", "cgst", "invoice", "tax"},
    "e-commerce": {"gst", "cgst", "invoice", "tax"},
    "gst": {"cgst", "invoice", "tax", "registration"},
    "private": {"company", "mca", "filing", "roc"},
}

LOCAL_REGULATION_CHUNKS = [
    (
        "RBI KYC Master Direction requires regulated entities to perform customer due diligence, verify customer identity, identify beneficial owners where applicable, classify customers by risk, monitor transactions on an ongoing basis, maintain KYC records, and report suspicious transactions through the required compliance process.",
        "01_RBI_KYC.pdf",
    ),
    (
        "RBI Payment Aggregator guidance applies to entities that aggregate online payments for merchants. Key obligations include RBI authorization where applicable, merchant onboarding and due diligence, escrow or nodal account controls, settlement discipline, information security controls, customer grievance handling, transaction monitoring, and compliance reporting.",
        "02_RBI_Payment_Aggregators.pdf",
    ),
    (
        "RBI PPI Master Directions apply to prepaid payment instruments such as wallets, stored value accounts, cards, and similar payment products. Obligations include authorization, KYC or minimum-detail requirements based on PPI type, limits and loading controls, customer disclosures, grievance redressal, interoperability where applicable, and security monitoring.",
        "03_RBI_PPI_Master_Directions.pdf",
    ),
    (
        "RBI Digital Lending Guidelines apply when digital platforms, lending service providers, or apps are used for loan origination, servicing, collection, or borrower interaction. Obligations include clear Key Fact Statements, explicit borrower consent, direct disbursal and repayment through regulated accounts, privacy controls, disclosure of charges, cooling-off rights where applicable, and grievance redressal.",
        "04_RBI_Digital_Lending.pdf",
    ),
    (
        "RBI NBFC Master Directions apply to non-banking financial companies and lending businesses that require NBFC registration or operate under an RBI-regulated lending model. Obligations include registration checks, prudential norms, fair lending practices, customer disclosures, asset classification, reporting, governance, and board-approved policies.",
        "05_RBI_NBFC_Master_Direction.pdf",
    ),
    (
        "RBI Fair Practices guidance for NBFCs requires transparent loan terms, fair borrower communication, non-coercive recovery practices, grievance redressal, disclosure of interest and charges, and board-approved fair practices policies.",
        "06_RBI_Fair_Practices_NBFC.pdf",
    ),
    (
        "CGST Rules apply to businesses making taxable supplies or collecting GST. Common obligations include GST registration when turnover or business model requires it, correct tax invoices, return filing, input tax credit documentation, e-way bill or e-invoicing compliance where applicable, and preservation of GST records.",
        "07_CGST_Rules_2017.pdf",
    ),
    (
        "MSME Udyam registration guidance applies to micro, small, and medium enterprises that want formal MSME recognition. Businesses should verify classification, register or update Udyam details, maintain investment and turnover information, and use the registration for eligible schemes or benefits.",
        "08_MSME_Udyam_Registration.pdf",
    ),
    (
        "Income Tax TDS provisions may apply when a business makes specified payments such as contractor, professional, rent, commission, salary, interest, or other covered payments. Obligations include deducting TDS when thresholds and sections apply, depositing TDS on time, filing TDS returns, and issuing certificates.",
        "10_IncomeTax_TDS_Section194.pdf",
    ),
    (
        "FEMA compliance applies to foreign exchange transactions, cross-border payments, foreign investment, overseas remittances, imports, exports, and other international dealings. Businesses should check authorized dealer bank routing, reporting obligations, documentation, and applicable RBI/FEMA limits.",
        "11_FEMA_Basic_Compliance.pdf",
    ),
    (
        "MCA company filing obligations apply to companies such as Private Limited Companies and LLPs. Obligations can include maintaining statutory registers, board and shareholder records, annual financial statements, annual returns, director KYC or disclosures, ROC forms, and event-based filings.",
        "12_MCA_Company_Filing.pdf",
    ),
]

def get_embedding_model():
    """Compatibility hook for callers from the old vector retrieval path."""
    raise RuntimeError(VECTOR_STORE_DETAIL)


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())
        if token not in STOP_WORDS
    ]


def build_query_terms(query: str) -> set[str]:
    terms = set(tokenize(query))
    for term in list(terms):
        terms.update(QUERY_EXPANSIONS.get(term, set()))
    return terms


def list_regulation_pdfs() -> list[str]:
    pdf_names = {
        source
        for _, source in LOCAL_REGULATION_CHUNKS
    }
    if os.path.isdir(REGULATIONS_DIR):
        pdf_names.update(
            filename
            for filename in os.listdir(REGULATIONS_DIR)
            if filename.lower().endswith(".pdf")
        )
    return sorted(pdf_names)


def select_candidate_pdfs(query_terms: set[str], limit: int = 3) -> list[str]:
    scored = []
    for filename in list_regulation_pdfs():
        hints = SOURCE_HINTS.get(filename, set())
        score = len(query_terms & hints)
        if score:
            scored.append((score, filename))

    if not scored:
        return list_regulation_pdfs()[:limit]

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [filename for _, filename in scored[:limit]]


def score_chunk(chunk: str, source: str, query_terms: set[str]) -> int:
    chunk_terms = set(tokenize(chunk))
    score = len(query_terms & chunk_terms) * 4
    source_terms = set(tokenize(source.replace("_", " ")))
    score += len(query_terms & source_terms) * 2
    return score

def check_vector_store() -> dict:
    """Return a small health payload for the retriever dependencies."""
    pdf_count = len(list_regulation_pdfs())
    return {
        "status": "ok" if pdf_count else "empty",
        "mode": VECTOR_STORE_MODE,
        "documents": pdf_count,
        "detail": VECTOR_STORE_DETAIL,
    }

def retrieve(query, n_results=5):
    if not isinstance(query, str) or not query.strip():
        logger.warning("Retriever received an empty or invalid query")
        return []
    try:
        n_results = max(1, min(int(n_results), 20))
    except (TypeError, ValueError):
        logger.warning("Invalid n_results=%r; falling back to 5", n_results)
        n_results = 5

    query_terms = build_query_terms(query)
    candidate_pdfs = select_candidate_pdfs(query_terms)
    chunks = [
        (chunk, source)
        for chunk, source in LOCAL_REGULATION_CHUNKS
        if source in candidate_pdfs
    ]

    ranked = [
        (score_chunk(chunk, source, query_terms), chunk, source)
        for chunk, source in chunks
    ]
    ranked = [item for item in ranked if item[0] > 0]
    ranked.sort(key=lambda item: item[0], reverse=True)

    if len(ranked) < min(n_results, 3):
        logger.warning("Local keyword retrieval found only %s scored chunks", len(ranked))

    return [(chunk, source) for _, chunk, source in ranked[:n_results]]
