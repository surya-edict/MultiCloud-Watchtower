from __future__ import annotations

import logging
from typing import List

from src.alerts.rules import build_alert_events
from src.alerts.slack import send_slack_alert
from src.collectors.base import normalize_records
from src.service.currency import normalize_currency
from src.service.taxes import apply_taxes_and_compliance
from src.collectors.registry import get_registry
from src.config.settings import Settings
from src.models.schemas import CostRecord, Recommendation
from src.recommendations.engine import build_recommendations
from src.storage.influx import InfluxRepository
from src.storage.redis_cache import RedisAlertCache

"""
Core Orchestration Pipeline.
Coordinates data collection, processing, storage, and alerting in a unified sequence.
"""

LOGGER = logging.getLogger(__name__)


def collect_cost_records(settings: Settings) -> List[CostRecord]:
    """
    Iterates through the registered cloud providers to collect cost data.
    Aggregates data from AWS, GCP, and Azure concurrently if configured.
    Falls back to a Mock provider if live integration fails and fallback is enabled.
    
    Args:
        settings (Settings): The application configuration block.
        
    Returns:
        List[CostRecord]: A normalized, flattened array of cost records from all clouds.
    """
    registry = get_registry()
    mock_provider = registry.get("mock")
    if mock_provider is None:
        raise RuntimeError("Mock provider not registered.")

    # Short-circuit immediately if running in full mock mode
    if settings.cloud_mode == "mock":
        return normalize_records(mock_provider.fetch(settings))

    records: List[CostRecord] = []
    failures: List[str] = []

    # Execute configured live providers
    for provider in registry.ordered():
        if provider.key == "mock":
            continue
        if not provider.is_configured(settings):
            continue
        try:
            records.extend(provider.fetch(settings))
        except Exception as exc:
            failures.append(f"{provider.label}: {exc}")

    if records:
        return normalize_records(records)
        
    # Fallback to mock data to prevent dashboard outages, if allowed
    if settings.allow_mock_fallback:
        LOGGER.warning(
            "Live collectors unavailable, falling back to mock data: %s",
            "; ".join(failures) if failures else "no configured providers",
        )
        return normalize_records(mock_provider.fetch(settings))
        
    if failures:
        raise RuntimeError("; ".join(failures))
        
    raise RuntimeError("No cost records collected. Check cloud configuration.")


def run_sync(settings: Settings) -> tuple[List[CostRecord], List[Recommendation], int]:
    """
    Executes a complete end-to-end data synchronization lifecycle.
    1. Collects raw cost telemetry.
    2. Analyzes for underutilized rightsizing recommendations.
    3. Persists all metrics to InfluxDB.
    4. Evaluates anomalies and dispatches alerts via Slack.
    
    Args:
        settings (Settings): The configuration block controlling execution thresholds.
        
    Returns:
        tuple: (Ingested Records, Generated Recommendations, Total Sent Alerts)
    """
    # 1. Collection Phase
    raw_records = collect_cost_records(settings)
    
    # 1.1 Currency Normalization Phase
    # Converts all records to a base currency (e.g. USD) so they can be 
    # mathematically aggregated and displayed on a single unified dashboard.
    currency_normalized_records = normalize_currency(raw_records, base_currency="USD")
    
    # 1.2 Tax & Compliance Phase
    # Evaluates the records against financial rules (e.g., Notional cost, Standard Tax).
    cost_records = apply_taxes_and_compliance(currency_normalized_records, settings)
    
    # 2. Analysis Phase
    recommendations = build_recommendations(
        records=cost_records,
        low_utilization_pct=settings.recommendation_low_utilization_pct,
        high_cost_threshold=settings.recommendation_high_cost_threshold,
    )

    # 3. Storage Setup
    influx = InfluxRepository(
        url=settings.influxdb_url,
        token=settings.influxdb_token,
        org=settings.influxdb_org,
        bucket=settings.influxdb_bucket,
    )
    cache = RedisAlertCache(redis_url=settings.redis_url)

    # 4. Persistence Phase
    influx.write_cost_records(cost_records)
    influx.write_recommendations(recommendations)

    # 5. Alerting Phase
    alerts = build_alert_events(
        records=cost_records,
        threshold=settings.alert_cost_threshold,
        spike_percentage=settings.alert_spike_percentage,
        cache=cache,
        dedupe_hours=settings.alert_dedupe_ttl,
    )

    sent_alerts = 0
    for alert in alerts:
        if send_slack_alert(settings.slack_webhook_url, alert):
            sent_alerts += 1
            
    return cost_records, recommendations, sent_alerts
