from __future__ import annotations

from typing import Iterable, List

from src.models.schemas import CostRecord, Recommendation

"""
Data access layer for InfluxDB.
Handles translating internal domain schemas (CostRecord, Recommendation)
into time-series measurements and executing high-performance batch writes.
"""


class InfluxRepository:
    """
    Repository pattern implementation for InfluxDB time-series storage.
    Provides batch ingestion interfaces for analytical telemetry data.
    """

    def __init__(self, url: str, token: str, org: str, bucket: str) -> None:
        """
        Initializes the InfluxDB repository.
        
        Args:
            url (str): The HTTP endpoint for the InfluxDB host.
            token (str): API authentication token with write permissions.
            org (str): The target organization workspace.
            bucket (str): The destination bucket for telemetry.
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket

    def _client(self):
        """
        Lazy-loads the InfluxDBClient to avoid hard-crashing at startup 
        if the library is missing but the fallback/mock paths are utilized.
        """
        try:
            from influxdb_client import InfluxDBClient
        except ImportError as exc:
            raise RuntimeError("influxdb-client is required for InfluxDB integration") from exc
        return InfluxDBClient(url=self.url, token=self.token, org=self.org)

    def write_cost_records(self, records: Iterable[CostRecord]) -> None:
        """
        Transforms CostRecord objects into 'cloud_cost' measurements and writes them.
        Optimized by constructing the payload array in memory before opening the
        socket connection to minimize the window of potential network timeouts.
        
        Args:
            records (Iterable[CostRecord]): The cost telemetry to be persisted.
        """
        items = list(records)
        if not items or not self.token:
            return
        points: List[dict] = []
        for record in items:
            points.append(
                {
                    "measurement": "cloud_cost",
                    "tags": {
                        "cloud": record.cloud,
                        "service": record.service,
                        "account_id": record.account_id,
                        "region": record.region,
                        "currency": record.currency,
                    },
                    "fields": {
                        "amount": float(record.amount),
                        "tax_amount": float(record.tax_amount),
                        "utilization_pct": float(record.utilization_pct) if record.utilization_pct is not None else -1.0,
                    },
                    "time": record.period_end.isoformat(),
                }
            )
        with self._client() as client:
            write_api = client.write_api()
            try:
                write_api.write(bucket=self.bucket, org=self.org, record=points)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error(f"Failed to write cost records to InfluxDB: {exc}")

    def write_recommendations(self, recommendations: Iterable[Recommendation]) -> None:
        """
        Transforms Recommendation objects into 'rightsizing_recommendation' measurements
        and commits them to the time-series database.
        
        Args:
            recommendations (Iterable[Recommendation]): Identified rightsizing opportunities.
        """
        items = list(recommendations)
        if not items or not self.token:
            return
        points: List[dict] = []
        for recommendation in items:
            points.append(
                {
                    "measurement": "rightsizing_recommendation",
                    "tags": {
                        "cloud": recommendation.cloud,
                        "service": recommendation.service,
                        "resource_id": recommendation.resource_id,
                        "severity": recommendation.severity,
                    },
                    "fields": {
                        "estimated_monthly_savings": float(recommendation.estimated_monthly_savings),
                        "title": recommendation.title,
                        "description": recommendation.description,
                    },
                    "time": recommendation.created_at.isoformat(),
                }
            )
        with self._client() as client:
            write_api = client.write_api()
            try:
                write_api.write(bucket=self.bucket, org=self.org, record=points)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error(f"Failed to write recommendations to InfluxDB: {exc}")
