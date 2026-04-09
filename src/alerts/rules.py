from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable, List

from src.models.schemas import AlertEvent, CostRecord
from src.storage.redis_cache import RedisAlertCache

"""
Alert Rules Engine.
Analyzes cost telemetry to detect financial anomalies, such as extreme cost spikes
or threshold breaches, and constructs actionable alert events.
"""


def build_alert_events(
    records: Iterable[CostRecord],
    threshold: float,
    spike_percentage: float,
    cache: RedisAlertCache,
    dedupe_hours,
) -> List[AlertEvent]:
    """
    Evaluates raw cost records against configured financial thresholds.
    Groups records by cloud, account, and service to establish a historical baseline,
    then compares the most recent data point against this baseline.
    
    Args:
        records (Iterable[CostRecord]): The cost records to evaluate.
        threshold (float): Absolute dollar value threshold that triggers an alert.
        spike_percentage (float): Relative percentage increase that triggers an alert.
        cache (RedisAlertCache): Distributed cache used to prevent duplicate alerts.
        dedupe_hours (int): Time-to-live for the deduplication lock.
        
    Returns:
        List[AlertEvent]: A list of generated anomalies ready for notification routing.
    """
    grouped: dict[tuple[str, str, str], list[CostRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.cloud, record.account_id, record.service)].append(record)

    alerts: List[AlertEvent] = []
    for (cloud, account_id, service), group in grouped.items():
        group_len = len(group)
        
        # O(K) linear scan replaces O(K log K) full array sort to find the latest record
        current = max(group, key=lambda item: item.period_end)
        
        spike_ratio = 0.0
        if group_len > 1:
            # O(K) summation over the existing contiguous block.
            # We subtract current.amount mathematically to avoid an O(K) memory slice allocation.
            total_amount = sum(item.amount for item in group)
            previous_amount = (total_amount - current.amount) / (group_len - 1)
            
            if previous_amount > 0:
                spike_ratio = ((current.amount - previous_amount) / previous_amount) * 100
            elif current.amount > 0:
                # Going from $0 to >$0 is treated as a 100% spike to ensure visibility
                spike_ratio = 100.0

        dedupe_key = current.alert_key()
        
        # Check the distributed lock to prevent alert fatigue
        if cache.has_alert(dedupe_key):
            continue

        # Short-circuit evaluation: most restrictive checks trigger first
        if current.amount >= threshold or spike_ratio >= spike_percentage:
            body = (
                f"*Cloud:* {cloud}\n"
                f"*Service:* {service}\n"
                f"*Account:* {account_id}\n"
                f"*Current cost:* ${current.amount:.2f}\n"
                f"*Spike:* {spike_ratio:.2f}%"
            )
            alerts.append(
                AlertEvent(
                    channel="slack",
                    title=f"Cost spike detected for {cloud}/{service}",
                    body=body,
                    dedupe_key=dedupe_key,
                    records=group,
                    created_at=datetime.now(timezone.utc),
                )
            )
            # Secure the deduplication lock
            cache.set_alert(dedupe_key, dedupe_hours)
            
    return alerts
