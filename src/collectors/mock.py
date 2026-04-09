from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from src.collectors.base import default_time_window
from src.models.schemas import CostRecord

"""
A mock data generator for testing and local development.
Provides deterministic, cross-cloud sample records without requiring actual
cloud credentials or incurring any API charges.
"""


def fetch_mock_cost_data(reference_time: datetime | None = None) -> List[CostRecord]:
    """
    Generates static, hardcoded mock cost records simulating AWS, GCP, and Azure responses.
    
    Args:
        reference_time (datetime | None): Optional anchor point for generating
            the time window. Defaults to the current UTC time.
            
    Returns:
        List[CostRecord]: A pre-defined set of synthetic cost records across various services.
    """
    start_time, end_time = default_time_window()
    now = reference_time or datetime.now(timezone.utc)
    
    # Align the period start to the beginning of the day for consistent mock display
    period_start = start_time.replace(hour=0)
    period_end = end_time

    return [
        CostRecord(
            cloud="aws",
            service="EC2",
            account_id="prod-aws-01",
            currency="USD",
            amount=142.50, # Optimized down from 600+
            period_start=period_start,
            period_end=period_end,
            region="us-east-1",
            utilization_pct=82.0, # High utilization = Good!
            metadata={"resource_id": "i-prod-web-01", "generated_at": now.isoformat()},
        ),
        CostRecord(
            cloud="aws",
            service="S3",
            account_id="prod-aws-01",
            currency="USD",
            amount=45.20,
            period_start=period_start,
            period_end=period_end,
            region="us-east-1",
            utilization_pct=None,
            metadata={"resource_id": "s3-prod-assets", "generated_at": now.isoformat()},
        ),
        CostRecord(
            cloud="gcp",
            service="Compute Engine",
            account_id="prod-gcp-02",
            currency="EUR", 
            amount=85.00, # Optimized
            period_start=period_start,
            period_end=period_end,
            region="europe-west1",
            utilization_pct=76.5, # Efficient
            metadata={"resource_id": "gce-prod-app-01", "generated_at": now.isoformat()},
        ),
        CostRecord(
            cloud="gcp",
            service="BigQuery",
            account_id="prod-gcp-02",
            currency="USD",
            amount=112.40,
            period_start=period_start,
            period_end=period_end,
            region="us",
            utilization_pct=None,
            metadata={"resource_id": "bq-analytics-warehouse", "generated_at": now.isoformat()},
        ),
        CostRecord(
            cloud="azure",
            service="Virtual Machines",
            account_id="prod-azure-03",
            currency="INR", 
            amount=12500.00, # ~150 USD, optimized
            period_start=period_start,
            period_end=period_end,
            region="centralindia",
            utilization_pct=91.0, # Very efficient
            metadata={"resource_id": "/subscriptions/prod/vm-db-master", "generated_at": now.isoformat()},
        ),
        CostRecord(
            cloud="azure",
            service="Storage",
            account_id="prod-azure-03",
            currency="USD",
            amount=32.10,
            period_start=period_start,
            period_end=period_end,
            region="eastus",
            utilization_pct=None,
            metadata={"resource_id": "/subscriptions/prod/st-backups-01", "generated_at": now.isoformat()},
        ),
        # Adding a specific low-utilization resource to trigger a POSITIVE recommendation (Savings)
        CostRecord(
            cloud="aws",
            service="RDS",
            account_id="prod-aws-01",
            currency="USD",
            amount=450.00,
            period_start=period_start,
            period_end=period_end,
            region="us-west-2",
            utilization_pct=5.0, # Low utilization but high cost = Huge savings potential
            metadata={"resource_id": "db-unused-dev", "generated_at": now.isoformat()},
        ),
    ]
