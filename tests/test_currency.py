from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from src.models.schemas import CostRecord
from src.service import currency
from src.service.currency import FALLBACK_RATES, normalize_currency


def _record(currency_code: str, amount: float, tax_amount: float = 0.0) -> CostRecord:
    now = datetime.now(timezone.utc)
    return CostRecord(
        cloud="aws",
        service="EC2",
        account_id="demo",
        currency=currency_code,
        amount=amount,
        period_start=now,
        period_end=now,
        tax_amount=tax_amount,
    )


class CurrencyNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        currency._cached_rates = None

    def tearDown(self) -> None:
        currency._cached_rates = None

    def test_leaves_base_currency_records_unchanged(self) -> None:
        record = _record("USD", 42.5, tax_amount=3.0)
        rates = {"USD": 1.0, "INR": 0.012, "EUR": 1.08}
        with patch("src.service.currency.get_exchange_rates", return_value=rates):
            result = normalize_currency([record], base_currency="USD")

        self.assertEqual(len(result), 1)
        self.assertIs(result[0], record)
        self.assertEqual(result[0].amount, 42.5)
        self.assertEqual(result[0].currency, "USD")

    def test_converts_foreign_amounts_and_taxes_to_usd(self) -> None:
        record = _record("INR", 1000.0, tax_amount=180.0)
        rates = {"USD": 1.0, "INR": 0.012, "EUR": 1.08}
        with patch("src.service.currency.get_exchange_rates", return_value=rates):
            result = normalize_currency([record], base_currency="USD")

        converted = result[0]
        self.assertEqual(converted.currency, "USD")
        self.assertEqual(converted.amount, 12.0)
        self.assertEqual(converted.tax_amount, 2.16)
        self.assertEqual(converted.metadata["original_currency"], "INR")
        self.assertEqual(converted.metadata["original_amount"], 1000.0)
        self.assertEqual(converted.metadata["conversion_rate"], 0.012)

    def test_falls_back_to_hardcoded_rates_when_api_fails(self) -> None:
        with patch("src.service.currency.requests.get", side_effect=RuntimeError("timeout")):
            rates = currency.get_exchange_rates()

        self.assertEqual(rates, FALLBACK_RATES)
        # Cached fallback should be reused without another HTTP call
        with patch("src.service.currency.requests.get") as mocked_get:
            cached = currency.get_exchange_rates()
        mocked_get.assert_not_called()
        self.assertEqual(cached, FALLBACK_RATES)


if __name__ == "__main__":
    unittest.main()
