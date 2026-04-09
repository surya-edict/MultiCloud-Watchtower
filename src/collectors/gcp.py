from __future__ import annotations

from typing import List

from src.collectors.base import default_time_window
from src.models.schemas import CostRecord

"""
GCP BigQuery Billing Export integration module.
Reads and aggregates raw billing data directly from a BigQuery dataset
using cost-optimized partition-pruning queries.
"""


def fetch_gcp_cost_data(project_id: str, billing_account_id: str, bigquery_table: str) -> List[CostRecord]:
    """
    Executes a SQL aggregation against the GCP Cloud Billing standard export table.
    Implements mandatory `_PARTITIONTIME` filters to prevent full-table scans
    and bounds the query size to 1GB to prevent Denial-of-Wallet attacks.
    
    Args:
        project_id (str): The GCP project hosting the BigQuery dataset.
        billing_account_id (str): The billing account ID for context mapping.
        bigquery_table (str): Fully qualified BigQuery table (e.g., 'proj.dataset.gcp_billing_export_v1_XXXXX').
        
    Returns:
        List[CostRecord]: A list of normalized GCP cost records.
    """
    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise RuntimeError("google-cloud-bigquery is required for GCP live collection") from exc

    start_time, end_time = default_time_window()
    
    # Initialize the BQ client utilizing the standard GCP credential chain
    client = bigquery.Client(project=project_id)
    
    # Prune data via _PARTITIONTIME to minimize the volume of bytes scanned
    query = f"""
        SELECT
          service.description AS service,
          COALESCE(location.location, 'global') AS region,
          SUM(cost) AS amount,
          currency
        FROM `{bigquery_table}`
        WHERE DATE(_PARTITIONTIME) BETWEEN DATE(@start_time) AND DATE(@end_time)
          AND usage_start_time >= @start_time
          AND usage_end_time <= @end_time
        GROUP BY service, region, currency
        ORDER BY amount DESC
    """
    
    # Set up parameterized constraints to prevent SQL injection and apply a 1GB byte limit
    config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
            bigquery.ScalarQueryParameter("end_time", "TIMESTAMP", end_time),
        ],
        maximum_bytes_billed=1073741824 # 1GB limit to prevent Denial of Wallet
    )
    
    # Blocking execution of the analytical query
    rows = client.query(query, job_config=config).result()

    records: List[CostRecord] = []
    for row in rows:
        records.append(
            CostRecord(
                cloud="gcp",
                service=row["service"],
                account_id=billing_account_id or project_id,
                currency=row["currency"],
                amount=float(row["amount"]),
                period_start=start_time,
                period_end=end_time,
                region=row["region"],
                metadata={"source": "bigquery-billing-export"},
            )
        )
        
    return records
