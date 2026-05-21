import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from dotenv import load_dotenv
from groq import Groq

from .retriever import retrieve

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TIMEOUT_SECONDS = int(os.getenv("GROQ_TIMEOUT_SECONDS", "30"))
GROQ_WORKERS = int(os.getenv("GROQ_WORKERS", "4"))

_client = None
_executor = ThreadPoolExecutor(max_workers=GROQ_WORKERS)

SUPPORTED_INDUSTRIES = [
    "fintech",
    "digital payments",
    "lending",
    "nbfc",
    "msme",
    "manufacturing",
    "gst",
    "ecommerce",
    "e-commerce",
]


def service_message(title: str, body: str, action: str) -> str:
    return f"""
## {title}

{body}

**What to do:** {action}
        """


def get_groq_client() -> Groq:
    global _client
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT_SECONDS)
    return _client


def is_in_scope(business_profile: dict) -> bool:
    combined = (
        business_profile.get("industry", "")
        + business_profile.get("services", "")
        + business_profile.get("transaction_type", "")
    ).lower()
    return any(keyword in combined for keyword in SUPPORTED_INDUSTRIES)


def build_query(business_profile: dict) -> str:
    return f"""
    Business type: {business_profile['business_type']}
    Industry: {business_profile['industry']}
    Services offered: {business_profile['services']}
    Customer type: {business_profile['customer_type']}
    Transaction type: {business_profile['transaction_type']}
    Annual revenue: {business_profile['revenue']}
    """


def assess_retrieval_quality(results: list) -> bool:
    return len(results) >= 3


def extract_source_documents(results: list) -> list[str]:
    source_documents = []
    seen = set()

    for _, source in results:
        if not isinstance(source, str):
            continue
        source = source.strip()
        if source and source not in seen:
            source_documents.append(source)
            seen.add(source)

    return source_documents


def load_prompt_template() -> str:
    prompt_path = os.path.join(ROOT_DIR, "prompts", "compliance.txt")
    with open(prompt_path, "r", encoding="utf-8") as prompt_file:
        return prompt_file.read()


def call_groq_completion(filled_prompt: str):
    return get_groq_client().chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=2000,
        messages=[
            {
                "role": "system",
                "content": """You are RegLens AI, a strict regulatory compliance assistant for Indian FinTechs and MSMEs.

STRICT RULES:
1. Only use information from the regulatory context provided. Never use your own memory for legal facts.
2. If unsure about any regulation, explicitly flag it with UNCERTAIN.
3. Never present this as legal advice. Always recommend professional consultation for final decisions.
4. If a regulation is not clearly supported by the context, write INSUFFICIENT DATA - do not guess.
5. All sources in the context are verified official government documents from trusted domains (.gov.in, .nic.in, etc.).""",
            },
            {
                "role": "user",
                "content": filled_prompt,
            },
        ],
        temperature=0.1,
    )


def run_compliance_check(business_profile: dict) -> str:
    result_text, _ = run_compliance_check_with_sources(business_profile)
    return result_text


def run_compliance_check_with_sources(business_profile: dict) -> tuple[str, list[str]]:
    if not is_in_scope(business_profile):
        return service_message(
            "Out of Scope",
            "RegLens AI currently covers FinTech, Digital Payments, Lending, NBFC, MSME, E-Commerce, and GST registered businesses.",
            "Consult a qualified compliance professional for domain-specific regulatory guidance.",
        ), []

    query = build_query(business_profile)

    try:
        results = retrieve(query, n_results=8)
    except Exception:
        logger.exception("Unexpected retrieval failure")
        results = []

    source_documents = extract_source_documents(results)

    if not assess_retrieval_quality(results):
        return service_message(
            "Insufficient Regulatory Data",
            "RegLens AI could not retrieve enough relevant regulatory information for this business profile.",
            "Refresh the regulation index or consult a qualified compliance professional. Do not rely on AI guidance for this case.",
        ), source_documents

    regulatory_context = ""
    for chunk, source in results:
        if isinstance(source, str) and source.strip():
            regulatory_context += f"\n[Source: {source}]\n{chunk}\n"

    if not regulatory_context.strip():
        logger.warning("No regulatory context survived source filtering")
        return service_message(
            "Insufficient Regulatory Data",
            "RegLens AI retrieved records, but none could be safely converted into regulatory context.",
            "Refresh the regulation index or consult a qualified compliance professional.",
        ), source_documents

    try:
        prompt_template = load_prompt_template()
    except OSError:
        logger.exception("Compliance prompt template could not be loaded")
        return service_message(
            "Service Configuration Error",
            "RegLens AI could not load its compliance prompt template.",
            "Contact the system administrator or try again after deployment is repaired.",
        ), source_documents

    filled_prompt = prompt_template.replace("{business_profile}", query).replace(
        "{regulatory_context}",
        regulatory_context,
    )

    start_time = time.time()
    try:
        logger.info("Starting Groq API call with %s second timeout", GROQ_TIMEOUT_SECONDS)
        future = _executor.submit(call_groq_completion, filled_prompt)
        response = future.result(timeout=GROQ_TIMEOUT_SECONDS)
        elapsed_time = time.time() - start_time
        logger.info("Groq API call completed successfully in %.2f seconds", elapsed_time)

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned an empty response")
        return content, source_documents
    except FutureTimeout:
        elapsed_time = time.time() - start_time
        logger.error("Groq API call timed out after %.2f seconds", elapsed_time)
        return service_message(
            "Response Timeout",
            "RegLens AI did not receive a response from the model within the configured timeout.",
            "Please try again in a few moments or consult a qualified compliance professional.",
        ), source_documents
    except Exception:
        elapsed_time = time.time() - start_time
        logger.exception("Groq API error after %.2f seconds", elapsed_time)
        return service_message(
            "API Error",
            "RegLens AI encountered an error while processing your request.",
            "Please try again or consult a qualified compliance professional if the error persists.",
        ), source_documents
