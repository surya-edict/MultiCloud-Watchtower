from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.collectors.registry import ProviderRegistry, ProviderSpec
from src.config.settings import load_settings
from src.models.schemas import CostRecord
from src.service.pipeline import collect_cost_records


class CollectCostRecordsTests(unittest.TestCase):
    def test_falls_back_to_mock_when_live_collectors_fail(self) -> None:
        registry = ProviderRegistry()

        def failing_fetch(_: object) -> list[CostRecord]:
            raise RuntimeError("boom")

        def mock_fetch(_: object) -> list[CostRecord]:
            now = datetime.now(timezone.utc)
            return [
                CostRecord(
                    cloud="mock",
                    service="demo",
                    account_id="demo",
                    currency="USD",
                    amount=1.0,
                    period_start=now - timedelta(hours=1),
                    period_end=now,
                    region="global",
                )
            ]

        registry.register(
            ProviderSpec(
                key="aws",
                label="AWS",
                is_configured=lambda _: True,
                fetch=failing_fetch,
            )
        )
        registry.register(
            ProviderSpec(
                key="mock",
                label="Mock",
                is_configured=lambda _: True,
                fetch=mock_fetch,
            )
        )

        with patch.dict(
            "os.environ",
            {
                "CLOUD_MODE": "live",
                "ALLOW_MOCK_FALLBACK": "true",
            },
            clear=False,
        ):
            settings = load_settings()

        with patch("src.service.pipeline.get_registry", return_value=registry):
            with self.assertLogs("src.service.pipeline", level="WARNING") as logs:
                records = collect_cost_records(settings)

        self.assertEqual(len(records), 1)
        self.assertIn("falling back to mock data", logs.output[0].lower())
        self.assertIn("AWS: boom", logs.output[0])

    def test_raises_aggregated_failures_when_fallback_disabled(self) -> None:
        registry = ProviderRegistry()

        def failing_fetch(_: object) -> list[CostRecord]:
            raise RuntimeError("boom")

        def mock_fetch(_: object) -> list[CostRecord]:
            return []

        registry.register(
            ProviderSpec(
                key="aws",
                label="AWS",
                is_configured=lambda _: True,
                fetch=failing_fetch,
            )
        )
        registry.register(
            ProviderSpec(
                key="mock",
                label="Mock",
                is_configured=lambda _: True,
                fetch=mock_fetch,
            )
        )

        with patch.dict(
            "os.environ",
            {
                "CLOUD_MODE": "live",
                "ALLOW_MOCK_FALLBACK": "false",
            },
            clear=False,
        ):
            settings = load_settings()

        with patch("src.service.pipeline.get_registry", return_value=registry):
            with self.assertRaises(RuntimeError) as ctx:
                collect_cost_records(settings)

        self.assertEqual(str(ctx.exception), "AWS: boom")


if __name__ == "__main__":
    unittest.main()

