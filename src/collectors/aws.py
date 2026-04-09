from __future__ import annotations

from typing import List

from src.collectors.base import default_time_window
from src.models.schemas import CostRecord

"""
AWS Cost Explorer integration module.
Responsible for authenticating with AWS and retrieving cost telemetry
optimized for minimal API execution costs.
"""


def fetch_aws_cost_data(region_name: str, account_id: str = "aws-default") -> List[CostRecord]:
    """
    Fetches raw cost data from the AWS Cost Explorer API for the last 24 hours.
    Uses MONTHLY granularity combined with pagination to reduce API payload sizes
    and overall AWS API charges while maintaining data fidelity.
    
    Args:
        region_name (str): The AWS region to target (e.g., us-east-1).
        account_id (str): A static or dynamic account identifier for mapping.
        
    Returns:
        List[CostRecord]: A list of normalized AWS cost records.
    """
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required for AWS live collection") from exc

    start_time, end_time = default_time_window()
    client = boto3.client("ce", region_name=region_name)
    kwargs = {
        "TimePeriod": {
            "Start": start_time.date().isoformat(),
            "End": end_time.date().isoformat(),
        },
        "Granularity": "MONTHLY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
    }

    records: List[CostRecord] = []
    
    # Loop to handle AWS API pagination via NextPageToken
    while True:
        response = client.get_cost_and_usage(**kwargs)
        for day in response.get("ResultsByTime", []):
            for group in day.get("Groups", []):
                try:
                    metrics = group.get("Metrics", {}).get("UnblendedCost", {})
                    if not metrics or "Amount" not in metrics:
                        continue
                    amount = float(metrics["Amount"])
                    currency = metrics.get("Unit", "USD")
                except (KeyError, ValueError, TypeError):
                    continue
                
                # Extract the service name, defaulting to 'Unknown' if mapping fails
                service_name = group.get("Keys", ["Unknown"])[0]
                records.append(
                    CostRecord(
                        cloud="aws",
                        service=service_name,
                        account_id=account_id,
                        currency=currency,
                        amount=amount,
                        period_start=start_time,
                        period_end=end_time,
                        region=region_name,
                        metadata={"source": "cost-explorer"},
                    )
                )
        
        if "NextPageToken" in response:
            kwargs["NextPageToken"] = response["NextPageToken"]
        else:
            break
            
    return records
