from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.health_status import build_health_status


class HealthStatusTest(unittest.TestCase):
    def test_reports_configuration_without_returning_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            secret = "never-return-this-value"
            status = build_health_status(
                Path(temporary),
                "1.0",
                {"LLM_PROVIDER": "google", "GOOGLE_API_KEY": secret},
            )

        self.assertEqual(status["provider"]["state"], "configured")
        self.assertEqual(status["vector_store"]["state"], "empty")
        self.assertNotIn(secret, repr(status))

    def test_openai_compatible_provider_requires_key_and_base_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing_url = build_health_status(
                Path(temporary),
                "1.0",
                {"LLM_PROVIDER": "openai_compatible", "OPENAI_API_KEY": "hidden"},
            )
            configured = build_health_status(
                Path(temporary),
                "1.0",
                {
                    "LLM_PROVIDER": "openai_compatible",
                    "OPENAI_API_KEY": "hidden",
                    "OPENAI_BASE_URL": "https://provider.example/v1",
                },
            )

        self.assertEqual(missing_url["provider"]["state"], "missing")
        self.assertEqual(configured["provider"]["state"], "configured")


if __name__ == "__main__":
    unittest.main()
