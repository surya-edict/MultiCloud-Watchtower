from __future__ import annotations

import logging
import requests
from typing import Dict, List, Optional
from src.models.schemas import CostRecord

"""
Currency Normalization Service.
Responsible for converting disparate cloud billing currencies (INR, EUR, etc.)
into a unified base currency (default USD) for accurate dashboard aggregation.
"""

LOGGER = logging.getLogger(__name__)

# Fallback exchange rates for offline/demo purposes
FALLBACK_RATES: Dict[str, float] = {
    "USD": 1.0,
    "INR": 0.012,  # 1 INR = 0.012 USD (Approx)
    "EUR": 1.08,   # 1 EUR = 1.08 USD (Approx)
    "GBP": 1.27,   # 1 GBP = 1.27 USD (Approx)
}

# In-memory cache to avoid hitting the API multiple times per pipeline run
_cached_rates: Optional[Dict[str, float]] = None

def get_exchange_rates() -> Dict[str, float]:
    """
    Fetches live daily exchange rates from a public, no-auth API.
    Converts rates to a USD-base multiplier (e.g., 1 INR = 0.012 USD).
    Falls back to hardcoded rates if the API request fails.
    """
    global _cached_rates
    if _cached_rates is not None:
        return _cached_rates

    try:
        # Using a free open endpoint that provides daily updated rates (base USD)
        response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        api_rates = data.get("rates", {})
        if not api_rates:
            raise ValueError("No rates found in API response")
            
        computed_rates = {"USD": 1.0}
        for currency, rate in api_rates.items():
            if rate > 0:
                # The API gives us how much 1 USD is in foreign currency (e.g., 83 INR)
                # We need the inverse: how much 1 foreign currency is in USD (e.g., 0.012)
                computed_rates[currency] = 1.0 / rate
                
        _cached_rates = computed_rates
        LOGGER.info("Successfully fetched live exchange rates.")
        return _cached_rates
        
    except Exception as e:
        LOGGER.warning(f"Failed to fetch live exchange rates: {e}. Falling back to hardcoded demo rates.")
        _cached_rates = FALLBACK_RATES
        return _cached_rates

def normalize_currency(records: List[CostRecord], base_currency: str = "USD") -> List[CostRecord]:
    """
    Normalizes a list of cost records to a single base currency.
    If a record is already in the base currency, it remains unchanged.
    Otherwise, the amount is converted using live exchange rates.
    
    Args:
        records (List[CostRecord]): The raw records with mixed currencies.
        base_currency (str): The target currency for normalization (default: 'USD').
        
    Returns:
        List[CostRecord]: A new list of records where all amounts are in base_currency.
    """
    normalized: List[CostRecord] = []
    
    # Fetch live rates dynamically
    rates = get_exchange_rates()
    
    # Get the rate for the base currency relative to USD (our internal pivot)
    base_rate = rates.get(base_currency, 1.0)
    
    for record in records:
        if record.currency == base_currency:
            normalized.append(record)
            continue
            
        # 1. Convert source currency to USD
        source_rate_to_usd = rates.get(record.currency, 1.0)
        amount_in_usd = record.amount * source_rate_to_usd
        
        # 2. Convert USD to target base currency
        normalized_amount = amount_in_usd / base_rate
        normalized_tax = (record.tax_amount * source_rate_to_usd) / base_rate
        
        # Create a new record with the normalized amount
        normalized.append(
            CostRecord(
                cloud=record.cloud,
                service=record.service,
                account_id=record.account_id,
                currency=base_currency, # Updated to base
                amount=round(normalized_amount, 4),
                tax_amount=round(normalized_tax, 4),
                period_start=record.period_start,
                period_end=record.period_end,
                region=record.region,
                utilization_pct=record.utilization_pct,
                metadata={
                    **record.metadata,
                    "original_amount": record.amount,
                    "original_currency": record.currency,
                    "conversion_rate": round(source_rate_to_usd / base_rate, 4),
                    "rates_source": "live_api" if rates is not FALLBACK_RATES else "fallback"
                }
            )
        )
        
    return normalized
