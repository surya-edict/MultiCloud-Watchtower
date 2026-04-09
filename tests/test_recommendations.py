from __future__ import annotations

import unittest
from datetime import datetime, timezone

from src.models.schemas import CostRecord
from src.recommendations.engine import build_recommendations


class RecommendationTests(unittest.TestCase):
    def test_generates_recommendation_for_low_utilization_high_cost(self) -> None:
        now = datetime.now(timezone.utc)
        records = [
            CostRecord(
                cloud="azure",
                service="Virtual Machines",
                account_id="demo",
                currency="USD",
                amount=400.0,
                period_start=now,
                period_end=now,
                utilization_pct=10.0,
                metadata={"resource_id": "vm-1"},
            )
        ]
        recommendations = build_recommendations(records, low_utilization_pct=20.0, high_cost_threshold=100.0)
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].resource_id, "vm-1")

    def test_skips_records_without_utilization(self) -> None:
        now = datetime.now(timezone.utc)
        records = [
            CostRecord("aws", "S3", "demo", "USD", 500.0, now, now, utilization_pct=None),
        ]
        recommendations = build_recommendations(records, low_utilization_pct=20.0, high_cost_threshold=100.0)
        self.assertEqual(recommendations, [])


if __name__ == "__main__":
    unittest.main()
