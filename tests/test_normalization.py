from __future__ import annotations

import unittest
from datetime import datetime, timezone

from src.collectors.base import normalize_records
from src.collectors.mock import fetch_mock_cost_data
from src.models.schemas import CostRecord


class NormalizationTests(unittest.TestCase):
    def test_mock_records_are_generated(self) -> None:
        records = fetch_mock_cost_data()
        self.assertGreaterEqual(len(records), 6)
        self.assertEqual({record.cloud for record in records}, {"aws", "gcp", "azure"})

    def test_normalize_records_orders_by_cloud_account_service(self) -> None:
        now = datetime.now(timezone.utc)
        records = [
            CostRecord("gcp", "Compute Engine", "b", "USD", 10, now, now),
            CostRecord("aws", "EC2", "a", "USD", 10, now, now),
            CostRecord("azure", "Virtual Machines", "c", "USD", 10, now, now),
        ]
        normalized = normalize_records(records)
        ordered_clouds = [record.cloud for record in normalized]
        self.assertEqual(ordered_clouds, ["aws", "azure", "gcp"])


if __name__ == "__main__":
    unittest.main()
