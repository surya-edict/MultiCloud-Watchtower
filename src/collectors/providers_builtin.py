from __future__ import annotations

from typing import List

from src.collectors.registry import ProviderRegistry, ProviderSpec
from src.config.settings import Settings
from src.models.schemas import CostRecord

"""
Built-in Cloud Providers wiring.
This module binds the actual collector functions to the ProviderSpec
interface and registers them into the global ProviderRegistry.
"""


def register_builtin_providers(registry: ProviderRegistry) -> None:
    """
    Registers AWS, GCP, Azure, and Mock providers into the provided registry.
    Lazy-loads the actual API integration modules (e.g., src.collectors.aws)
    so that if a provider isn't enabled, its heavyweight dependencies
    (like boto3 or google-cloud-bigquery) aren't needlessly imported.
    
    Args:
        registry (ProviderRegistry): The registry instance to populate.
    """
    # Lazy imports to defer dependency loading
    from src.collectors.aws import fetch_aws_cost_data
    from src.collectors.azure import fetch_azure_cost_data
    from src.collectors.gcp import fetch_gcp_cost_data
    from src.collectors.mock import fetch_mock_cost_data

    # Wrapper functions adapt the Settings object to specific kwargs
    def fetch_aws(settings: Settings) -> List[CostRecord]:
        return fetch_aws_cost_data(region_name=settings.aws_region)

    def fetch_gcp(settings: Settings) -> List[CostRecord]:
        return fetch_gcp_cost_data(
            project_id=settings.gcp_project_id,
            billing_account_id=settings.gcp_billing_account_id,
            bigquery_table=settings.gcp_bigquery_table,
        )

    def fetch_azure(settings: Settings) -> List[CostRecord]:
        return fetch_azure_cost_data(subscription_id=settings.azure_subscription_id)

    def fetch_mock(_: Settings) -> List[CostRecord]:
        return fetch_mock_cost_data()

    # AWS Registration
    registry.register(
        ProviderSpec(
            key="aws",
            label="AWS",
            is_configured=lambda settings: bool(settings.aws_enabled),
            fetch=fetch_aws,
        )
    )
    
    # GCP Registration
    registry.register(
        ProviderSpec(
            key="gcp",
            label="GCP",
            is_configured=lambda settings: bool(settings.gcp_enabled and settings.gcp_bigquery_table),
            fetch=fetch_gcp,
        )
    )
    
    # Azure Registration
    registry.register(
        ProviderSpec(
            key="azure",
            label="Azure",
            is_configured=lambda settings: bool(settings.azure_enabled and settings.azure_subscription_id),
            fetch=fetch_azure,
        )
    )
    
    # Mock Data Registration (used for testing or fallback scenarios)
    registry.register(
        ProviderSpec(
            key="mock",
            label="Mock",
            is_configured=lambda _: True,
            fetch=fetch_mock,
        )
    )

