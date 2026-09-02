import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from google import genai
from google.genai import types
from .config import settings
from .retriever import retrieve

logger = logging.getLogger(__name__)

_genai_client: genai.Client | None = None
_executor = ThreadPoolExecutor(max_workers=4)

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
    "technology",
    "saas",
]

SYSTEM_PROMPT = """You are RegLens AI, a strict regulatory compliance assistant for Indian FinTechs and MSMEs.

STRICT RULES YOU MUST FOLLOW:
1. Only use information from the regulatory context provided. Never use your own memory or training data for legal facts.
2. If unsure about any regulation, explicitly flag it with UNCERTAIN.
3. Never present this as legal advice. Always recommend professional consultation for final decisions.
4. If a regulation is not clearly supported by the context, write INSUFFICIENT DATA - do not guess.
5. All sources in the context are verified official government documents (.rbi.org.in, .gst.gov.in, .msme.gov.in, etc.)."""


def service_message(title: str, body: str, action: str) -> str:
    return f"""## {title}

{body}

**What to do:** {action}"""


def get_genai_client() -> genai.Client:
    """Lazy singleton loader for Google GenAI Client."""
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    _genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _genai_client


def is_in_scope(business_profile: dict) -> bool:
    combined = (
        business_profile.get("industry", "")
        + " "
        + business_profile.get("services", "")
        + " "
        + business_profile.get("transaction_type", "")
    ).lower()
    return any(keyword in combined for keyword in SUPPORTED_INDUSTRIES)


def build_query(business_profile: dict) -> str:
    return f"""Business type: {business_profile.get('business_type', '')}
Industry: {business_profile.get('industry', '')}
Services offered: {business_profile.get('services', '')}
Customer type: {business_profile.get('customer_type', '')}
Transaction type: {business_profile.get('transaction_type', '')}
Annual revenue: {business_profile.get('revenue', '')}"""


def assess_retrieval_quality(results: list) -> bool:
    return len(results) >= 3


def extract_source_documents(results: list) -> list[str]:
    source_documents = []
    seen = set()

    for item in results:
        # Results can be (text, source, payload) or (text, source)
        source = item[1] if len(item) > 1 else "unknown"
        if not isinstance(source, str):
            continue
        source = source.strip()
        if source and source != "unknown" and source not in seen:
            source_documents.append(source)
            seen.add(source)

    return source_documents


def load_prompt_template() -> str:
    prompt_path = settings.PROMPT_PATH
    if not os.path.exists(prompt_path):
        # Fallback inline template if file is missing
        return """BUSINESS PROFILE:
{business_profile}

REGULATORY CONTEXT:
{regulatory_context}

Provide a structured regulatory compliance report following standard RegLens AI format."""
    with open(prompt_path, "r", encoding="utf-8") as prompt_file:
        return prompt_file.read()


def _call_gemini_api(filled_prompt: str) -> str:
    client = get_genai_client()
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.1,
        max_output_tokens=2500,
    )
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=filled_prompt,
        config=config,
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty response")
    return response.text


def run_compliance_check_with_sources(business_profile: dict) -> tuple[str, list[str]]:
    """Primary compliance evaluation method.

    Returns:
        tuple of (analysis_markdown_string, list_of_source_documents)
    """
    if not is_in_scope(business_profile):
        return (
            service_message(
                "Out of Scope",
                "RegLens AI currently covers FinTech, Digital Payments, Lending, NBFC, MSME, E-Commerce, and GST registered businesses.",
                "Consult a qualified compliance professional for domain-specific regulatory guidance.",
            ),
            [],
        )

    query = build_query(business_profile)

    try:
        results = retrieve(query, n_results=8)
    except Exception:
        logger.exception("Unexpected retrieval failure")
        results = []

    source_documents = extract_source_documents(results)

    if not assess_retrieval_quality(results):
        return (
            service_message(
                "Insufficient Regulatory Data",
                "RegLens AI could not retrieve enough relevant regulatory information for this business profile.",
                "Refresh the regulation vector index or consult a qualified compliance professional. Do not rely on AI guidance for this case.",
            ),
            source_documents,
        )

    regulatory_context = ""
    for item in results:
        chunk = item[0]
        source = item[1] if len(item) > 1 else "official regulation"
        if isinstance(source, str) and source.strip():
            regulatory_context += f"\n[Source: {source}]\n{chunk}\n"

    if not regulatory_context.strip():
        logger.warning("No regulatory context survived source filtering")
        return (
            service_message(
                "Insufficient Regulatory Data",
                "RegLens AI retrieved records, but none could be safely converted into regulatory context.",
                "Refresh the regulation index or consult a qualified compliance professional.",
            ),
            source_documents,
        )

    prompt_template = load_prompt_template()
    filled_prompt = prompt_template.replace("{business_profile}", query).replace(
        "{regulatory_context}", regulatory_context
    )

    start_time = time.time()
    try:
        logger.info("Starting Gemini API call using model: %s", settings.GEMINI_MODEL)
        future = _executor.submit(_call_gemini_api, filled_prompt)
        content = future.result(timeout=settings.GEMINI_TIMEOUT_SECONDS)
        elapsed_time = time.time() - start_time
        logger.info("Gemini API call completed in %.2f seconds", elapsed_time)
        return content, source_documents
    except FutureTimeout:
        elapsed_time = time.time() - start_time
        logger.error("Gemini API call timed out after %.2f seconds", elapsed_time)
        return (
            service_message(
                "Response Timeout",
                "RegLens AI did not receive a response from the model within the configured timeout.",
                "Please try again in a few moments or consult a qualified compliance professional.",
            ),
            source_documents,
        )
    except Exception as exc:
        elapsed_time = time.time() - start_time
        logger.exception("Gemini API error after %.2f seconds: %s", elapsed_time, exc)
        return (
            service_message(
                "API Error",
                "RegLens AI encountered an error while processing your request.",
                "Please verify your GEMINI_API_KEY configuration or consult a qualified compliance professional.",
            ),
            source_documents,
        )


def run_compliance_check(business_profile: dict) -> str:
    result_text, _ = run_compliance_check_with_sources(business_profile)
    return result_text
