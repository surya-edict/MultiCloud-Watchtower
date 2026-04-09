from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.config.settings import load_settings, validate_required_settings


class ConfigTests(unittest.TestCase):
    def test_missing_live_credentials_returns_error(self) -> None:
        env = {
            "CLOUD_MODE": "live",
            "ALLOW_MOCK_FALLBACK": "false",
            "AWS_ENABLED": "true",
            "GCP_ENABLED": "true",
            "AZURE_ENABLED": "true",
            "GCP_BIGQUERY_TABLE": "",
            "AZURE_SUBSCRIPTION_ID": "",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = load_settings()
            error = validate_required_settings(settings)
        self.assertIsNotNone(error)
        self.assertIn("Missing required live integration settings", error)


if __name__ == "__main__":
    unittest.main()
