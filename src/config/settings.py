from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

"""
Configuration module for the Multi-Cloud Cost Optimization tool.
This module loads all environmental settings and secrets, validates them,
and exposes them as a strongly-typed, immutable Settings object.
"""

def _get_bool(name: str, default: bool) -> bool:
    """Helper to parse boolean values from environment variables."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    """Helper to parse float values from environment variables."""
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def _get_int(name: str, default: int) -> int:
    """Helper to parse integer values from environment variables."""
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    """
    Centralized configuration object containing all operational parameters,
    cloud credentials, database URIs, and algorithmic thresholds.
    """
    app_env: str
    log_level: str
    cloud_mode: str
    allow_mock_fallback: bool
    scheduler_hourly_interval_minutes: int
    scheduler_daily_at: str
    influxdb_url: str
    influxdb_token: str
    influxdb_org: str
    influxdb_bucket: str
    redis_url: str
    slack_webhook_url: str
    alert_cost_threshold: float
    alert_spike_percentage: float
    alert_dedupe_hours: int
    recommendation_low_utilization_pct: float
    recommendation_high_cost_threshold: float
    aws_enabled: bool
    aws_region: str
    gcp_enabled: bool
    gcp_project_id: str
    gcp_billing_account_id: str
    gcp_bigquery_table: str
    azure_enabled: bool
    azure_subscription_id: str
    azure_tenant_id: str
    
    # Global Tax & Compliance Settings
    global_tax_rate_pct: float
    apply_notional_cost: bool
    notional_cost_pct: float

    @property
    def alert_dedupe_ttl(self) -> timedelta:
        """Returns the deduplication duration as a timedelta object."""
        return timedelta(hours=self.alert_dedupe_hours)


def load_settings() -> Settings:
    """
    Constructs the Settings object by reading from the OS environment.
    Defaults are provided for local development convenience.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
        
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        cloud_mode=os.getenv("CLOUD_MODE", "live"),
        allow_mock_fallback=_get_bool("ALLOW_MOCK_FALLBACK", True),
        scheduler_hourly_interval_minutes=_get_int("SCHEDULER_HOURLY_INTERVAL_MINUTES", 60),
        scheduler_daily_at=os.getenv("SCHEDULER_DAILY_AT", "09:00"),
        influxdb_url=os.getenv("INFLUXDB_URL", "http://influxdb:8086"),
        influxdb_token=os.getenv("INFLUXDB_TOKEN", ""),
        influxdb_org=os.getenv("INFLUXDB_ORG", "devops-lab"),
        influxdb_bucket=os.getenv("INFLUXDB_BUCKET", "multicloud_cost"),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
        alert_cost_threshold=_get_float("ALERT_COST_THRESHOLD", 500.0),
        alert_spike_percentage=_get_float("ALERT_SPIKE_PERCENTAGE", 20.0),
        alert_dedupe_hours=_get_int("ALERT_DEDUPE_HOURS", 12),
        recommendation_low_utilization_pct=_get_float("RECOMMENDATION_LOW_UTILIZATION_PCT", 20.0),
        recommendation_high_cost_threshold=_get_float("RECOMMENDATION_HIGH_COST_THRESHOLD", 100.0),
        aws_enabled=_get_bool("AWS_ENABLED", True),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        gcp_enabled=_get_bool("GCP_ENABLED", True),
        gcp_project_id=os.getenv("GCP_PROJECT_ID", ""),
        gcp_billing_account_id=os.getenv("GCP_BILLING_ACCOUNT_ID", ""),
        gcp_bigquery_table=os.getenv("GCP_BIGQUERY_TABLE", ""),
        azure_enabled=_get_bool("AZURE_ENABLED", True),
        azure_subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID", ""),
        azure_tenant_id=os.getenv("AZURE_TENANT_ID", ""),
        global_tax_rate_pct=_get_float("GLOBAL_TAX_RATE_PCT", 0.0), # Default 0% tax for global compatibility
        apply_notional_cost=_get_bool("APPLY_NOTIONAL_COST", False), # Disabled by default globally
        notional_cost_pct=_get_float("NOTIONAL_COST_PCT", 1.0),
    )


def validate_required_settings(settings: Settings) -> Optional[str]:
    """
    Validates that all necessary credentials and configs are present when running in live mode.
    If 'allow_mock_fallback' is disabled, missing configurations will cause a hard failure
    to prevent unintended missing data points.
    
    Args:
        settings (Settings): The fully loaded settings object to validate.
        
    Returns:
        Optional[str]: An error message detailing missing variables, or None if valid.
    """
    if settings.cloud_mode == "live" and not settings.allow_mock_fallback:
        missing = []
        if settings.aws_enabled and not os.getenv("AWS_ACCESS_KEY_ID"):
            missing.append("AWS_ACCESS_KEY_ID")
        if settings.gcp_enabled and not settings.gcp_bigquery_table:
            missing.append("GCP_BIGQUERY_TABLE")
        if settings.azure_enabled and not settings.azure_subscription_id:
            missing.append("AZURE_SUBSCRIPTION_ID")
        if missing:
            return f"Missing required live integration settings: {', '.join(missing)}"
    return None
