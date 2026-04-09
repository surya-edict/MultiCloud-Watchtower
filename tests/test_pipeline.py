from __future__ import annotations

import unittest
from unittest.mock import patch

from src.config.settings import load_settings
from src.service.pipeline import run_sync


class PipelineTests(unittest.TestCase):
    def test_run_sync_works_in_mock_mode(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "CLOUD_MODE": "mock",
                "INFLUXDB_TOKEN": "",
                "SLACK_WEBHOOK_URL": "",
            },
            clear=False,
        ):
            settings = load_settings()
            records, recommendations, sent_alerts = run_sync(settings)

        self.assertGreater(len(records), 0)
        self.assertGreater(len(recommendations), 0)
        self.assertEqual(sent_alerts, 0)


if __name__ == "__main__":
    unittest.main()
