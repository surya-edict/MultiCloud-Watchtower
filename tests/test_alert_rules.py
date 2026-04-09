from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from src.alerts.rules import build_alert_events
from src.models.schemas import CostRecord
from src.storage.redis_cache import RedisAlertCache


class AlertRuleTests(unittest.TestCase):
    def test_builds_alert_when_cost_crosses_threshold(self) -> None:
        now = datetime.now(timezone.utc)
        records = [
            CostRecord("aws", "EC2", "demo", "USD", 100.0, now - timedelta(days=1), now - timedelta(days=1)),
            CostRecord("aws", "EC2", "demo", "USD", 600.0, now, now),
        ]
        alerts = build_alert_events(
            records=records,
            threshold=500.0,
            spike_percentage=20.0,
            cache=RedisAlertCache("redis://unused"),
            dedupe_hours=timedelta(hours=12),
        )
        self.assertEqual(len(alerts), 1)
        self.assertIn("Cost spike detected", alerts[0].title)

    def test_dedupes_repeat_alert(self) -> None:
        now = datetime.now(timezone.utc)
        record = CostRecord("aws", "EC2", "demo", "USD", 600.0, now, now)
        cache = RedisAlertCache("redis://unused")
        cache.set_alert(record.alert_key(), timedelta(hours=12))
        alerts = build_alert_events(
            records=[record],
            threshold=500.0,
            spike_percentage=20.0,
            cache=cache,
            dedupe_hours=timedelta(hours=12),
        )
        self.assertEqual(alerts, [])


if __name__ == "__main__":
    unittest.main()
