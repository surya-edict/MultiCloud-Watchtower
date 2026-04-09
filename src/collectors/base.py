from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, List

from src.models.schemas import CostRecord

"""
Base utilities for cost collectors.
Contains shared functions for time-window generation and data normalization
to ensure consistency across different cloud provider outputs.
"""


def default_time_window() -> tuple[datetime, datetime]:
    """
    Generates a standard 24-hour time window for cost collection.
    Rounds the end time to the nearest hour to avoid partial-hour data gaps.
    
    Returns:
        tuple[datetime, datetime]: A tuple containing (start_time, end_time).
    """
    end_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(hours=24)
    return start_time, end_time


def normalize_records(records: Iterable[CostRecord]) -> List[CostRecord]:
    """
    Sorts and normalizes an iterable of CostRecord objects.
    Enforces a strict ordering by cloud, account, service, and time
    to ensure deterministic downstream processing (e.g., for alert deduplication).
    
    Args:
        records (Iterable[CostRecord]): The raw cost records.
        
    Returns:
        List[CostRecord]: A sorted list of cost records.
    """
    return sorted(
        records,
        key=lambda record: (
            record.cloud,
            record.account_id,
            record.service,
            record.period_start,
        ),
    )
