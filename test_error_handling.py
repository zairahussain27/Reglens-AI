import unittest
from unittest.mock import patch

from src import compliance_engine
from src.retriever import retrieve


VALID_PROFILE = {
    "business_type": "Private Limited Company",
    "industry": "FinTech",
    "services": "Digital payment processing for small merchants",
    "customer_type": "B2B",
    "transaction_type": "Digital payments",
    "revenue": "1 Crore annual",
}


class ErrorHandlingTests(unittest.TestCase):
    def test_retriever_rejects_empty_query_without_loading_model(self):
        with patch("src.retriever.get_embedding_model") as get_embedding_model:
            self.assertEqual(retrieve("   "), [])
            get_embedding_model.assert_not_called()

    def test_retrieval_failure_returns_guardrail_message(self):
        with patch("src.compliance_engine.retrieve", side_effect=RuntimeError("boom")):
            result, sources = compliance_engine.run_compliance_check_with_sources(VALID_PROFILE)

        self.assertIn("Insufficient Regulatory Data", result)
        self.assertEqual(sources, [])

    def test_missing_groq_key_returns_controlled_error(self):
        chunks = [
            ("Register before collecting payment fees.", "local"),
            ("Keep payment records for audits.", "local"),
            ("Review compliance obligations monthly.", "local"),
        ]

        with patch("src.compliance_engine.GROQ_API_KEY", None), patch(
            "src.compliance_engine.retrieve",
            return_value=chunks,
        ), patch(
            "src.compliance_engine.load_prompt_template",
            return_value="{business_profile}\n{regulatory_context}",
        ):
            result, sources = compliance_engine.run_compliance_check_with_sources(VALID_PROFILE)

        self.assertIn("API Error", result)
        self.assertNotIn("GROQ_API_KEY", result)
        self.assertEqual(sources, ["local"])


if __name__ == "__main__":
    unittest.main()
