from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from src.models.schemas import CostRecord, Recommendation

"""
Rightsizing and Recommendation Engine.
Analyzes ingested cost data against resource utilization thresholds
to generate actionable, cost-saving recommendations.
"""


def build_recommendations(
    records: Iterable[CostRecord],
    low_utilization_pct: float,
    high_cost_threshold: float,
) -> List[Recommendation]:
    """
    Scans a stream of CostRecords to identify underutilized resources.
    Uses O(1) deduplication to prevent generating duplicate recommendations
    for the same resource within a single execution cycle.
    
    Args:
        records (Iterable[CostRecord]): The input telemetry to analyze.
        low_utilization_pct (float): Maximum utilization percentage to be considered 'underutilized'.
        high_cost_threshold (float): Minimum cost threshold for a resource to warrant a recommendation.
        
    Returns:
        List[Recommendation]: A list of targeted rightsizing opportunities.
    """
    recommendations: List[Recommendation] = []
    seen_resources: set[str] = set()

    for record in records:
        # Early exit via short-circuiting to bypass expensive string allocations
        if record.utilization_pct is None:
            continue
        if record.utilization_pct > low_utilization_pct:
            continue
        if record.amount < high_cost_threshold:
            continue

        resource_id = str(record.metadata.get("resource_id", f"{record.account_id}:{record.service}"))
        
        # O(1) temporal deduplication short-circuit
        if resource_id in seen_resources:
            continue
        seen_resources.add(resource_id)

        # Estimate savings conservatively at 25% of current run-rate
        recommendations.append(
            Recommendation(
                cloud=record.cloud,
                service=record.service,
                resource_id=resource_id,
                severity="medium" if record.utilization_pct > 10 else "high",
                title=f"Rightsize {record.service} in {record.cloud}",
                description=(
                    f"{record.service} utilization {record.utilization_pct:.1f}% hai aur cost ${record.amount:.2f} hai. "
                    "Smaller SKU ya downgrade evaluate karo."
                ),
                estimated_monthly_savings=round(record.amount * 0.25, 2),
                created_at=datetime.now(timezone.utc),
                metadata={
                    "utilization_pct": record.utilization_pct,
                    "region": record.region,
                },
            )
        )
    return recommendations
