from __future__ import annotations

from typing import List

from src.collectors.base import default_time_window
from src.models.schemas import CostRecord

"""
Azure Cost Management API integration module.
Authenticates using the DefaultAzureCredential chain to pull resource costs
and aggregates them by ServiceName and ResourceLocation.
"""


def fetch_azure_cost_data(subscription_id: str) -> List[CostRecord]:
    """
    Fetches raw cost data for an Azure subscription.
    Uses 'Monthly' granularity to reduce control plane load and rate limiting
    from the Cost Management synchronous API.
    
    Args:
        subscription_id (str): The Azure subscription ID UUID to query against.
        
    Returns:
        List[CostRecord]: A list of normalized Azure cost records.
    """
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.costmanagement import CostManagementClient
    except ImportError as exc:
        raise RuntimeError("azure-identity and azure-mgmt-costmanagement are required for Azure live collection") from exc

    start_time, end_time = default_time_window()
    
    # Leverages environment variables or managed identity for secure authentication
    credential = DefaultAzureCredential()
    client = CostManagementClient(credential=credential)
    scope = f"/subscriptions/{subscription_id}"
    
    query = {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": start_time.isoformat(), "to": end_time.isoformat()},
        "dataset": {
            "granularity": "Monthly",
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "grouping": [
                {"type": "Dimension", "name": "ServiceName"},
                {"type": "Dimension", "name": "ResourceLocation"},
            ],
        },
    }
    
    # Executes the synchronous cost usage query
    response = client.query.usage(scope=scope, parameters=query)

    records: List[CostRecord] = []
    
    # Map dynamic column indexes since Azure returns a custom schema format
    columns = [column.name for column in response.columns]
    index_map = {name: idx for idx, name in enumerate(columns)}
    
    for row in response.rows:
        try:
            service_name = row[index_map.get("ServiceName", 0)]
            region = row[index_map.get("ResourceLocation", 1)] or "global"
            if "Cost" not in index_map:
                continue
            amount = float(row[index_map["Cost"]])
        except (ValueError, TypeError, IndexError):
            continue
            
        records.append(
            CostRecord(
                cloud="azure",
                service=str(service_name),
                account_id=subscription_id,
                currency="USD",
                amount=amount,
                period_start=start_time,
                period_end=end_time,
                region=str(region),
                metadata={"source": "azure-cost-management"},
            )
        )
        
    return records
