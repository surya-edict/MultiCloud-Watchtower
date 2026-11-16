from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from src.config.settings import load_settings
from src.models.schemas import CostRecord
from src.service.taxes import apply_taxes_and_compliance


def _record(service: str, amount: float) -> CostRecord:
    now = datetime.now(timezone.utc)
    return CostRecord(
        cloud="aws",
        service=service,
        account_id="demo",
        currency="USD",
        amount=amount,
        period_start=now,
        period_end=now,
    )


def _settings(**env: str):
    defaults = {
        "GLOBAL_TAX_RATE_PCT": "18.0",
        "APPLY_NOTIONAL_COST": "true",
        "NOTIONAL_COST_PCT": "1.0",
    }
    defaults.update(env)
    with patch.dict(os.environ, defaults, clear=False):
        return load_settings()


class TaxEngineTests(unittest.TestCase):
    def test_applies_standard_tax_to_compute_services(self) -> None:
        settings = _settings()
        records = [
            _record("EC2", 100.0),
            _record("Compute Engine", 50.0),
            _record("Virtual Machines", 200.0),
        ]
        result = apply_taxes_and_compliance(records, settings)

        self.assertEqual(result[0].tax_amount, 18.0)
        self.assertEqual(result[1].tax_amount, 9.0)
        self.assertEqual(result[2].tax_amount, 36.0)
        self.assertEqual(result[0].metadata["tax_rule"], "Standard Tax (18.0%)")
        # Pre-tax amounts stay unchanged
        self.assertEqual(result[0].amount, 100.0)

    def test_applies_notional_cost_to_storage_when_enabled(self) -> None:
        settings = _settings(APPLY_NOTIONAL_COST="true", NOTIONAL_COST_PCT="1.0")
        result = apply_taxes_and_compliance([_record("Storage", 200.0)], settings)

        self.assertEqual(result[0].tax_amount, 2.0)
        self.assertEqual(result[0].metadata["tax_rule"], "Notional Cost (1.0%)")

    def test_skips_storage_notional_cost_when_disabled(self) -> None:
        settings = _settings(APPLY_NOTIONAL_COST="false")
        result = apply_taxes_and_compliance([_record("Storage", 200.0)], settings)

        self.assertEqual(result[0].tax_amount, 0.0)
        self.assertEqual(result[0].metadata["tax_rule"], "None")

    def test_leaves_unlisted_services_untaxed(self) -> None:
        settings = _settings()
        result = apply_taxes_and_compliance([_record("Lambda", 80.0)], settings)

        self.assertEqual(result[0].tax_amount, 0.0)
        self.assertFalse(result[0].metadata["tax_applied"])


if __name__ == "__main__":
    unittest.main()
