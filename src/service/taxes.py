from __future__ import annotations

from typing import List
from src.models.schemas import CostRecord
from src.config.settings import Settings

"""
Tax & Compliance Engine (Global Context).
Evaluates cost records to calculate explicit taxes or indirect notional costs.
This module is configurable via environment variables to support global tax 
laws (e.g., VAT in Europe, GST in India/Australia, Sales Tax in the US).
"""

def apply_taxes_and_compliance(records: List[CostRecord], settings: Settings) -> List[CostRecord]:
    """
    Applies configurable tax rules to cost records.
    - Global Tax Rate: Configurable percentage applied to compute resources.
    - Notional Cost: Optional compliance tax applied to 'exempt' or 'free tier' 
      resources (like Storage) to support laws like India's Rule 14.
    
    Args:
        records (List[CostRecord]): The normalized cost records.
        settings (Settings): Global configuration containing tax rates.
        
    Returns:
        List[CostRecord]: Records with updated `tax_amount` fields reflecting regional tax logic.
    """
    taxed_records: List[CostRecord] = []
    
    # Pre-calculate multipliers from percentages
    tax_multiplier = settings.global_tax_rate_pct / 100.0
    notional_multiplier = settings.notional_cost_pct / 100.0
    
    for record in records:
        calculated_tax = 0.0
        tax_rule_applied = "None"
        
        if record.service == "Storage":
            if settings.apply_notional_cost:
                # e.g., Rule 14 Notional cost rule (1% on exempt/free-tier equivalent)
                calculated_tax = record.amount * notional_multiplier
                tax_rule_applied = f"Notional Cost ({settings.notional_cost_pct}%)"
            
        elif record.service in ["EC2", "Compute Engine", "Virtual Machines"]:
            if settings.global_tax_rate_pct > 0:
                # Standard configurable tax (e.g., 18% GST, 20% VAT)
                calculated_tax = record.amount * tax_multiplier
                tax_rule_applied = f"Standard Tax ({settings.global_tax_rate_pct}%)"
            
        # Create new record with tax applied
        taxed_records.append(
            CostRecord(
                cloud=record.cloud,
                service=record.service,
                account_id=record.account_id,
                currency=record.currency,
                amount=record.amount,
                tax_amount=round(calculated_tax, 4),
                period_start=record.period_start,
                period_end=record.period_end,
                region=record.region,
                utilization_pct=record.utilization_pct,
                metadata={
                    **record.metadata,
                    "tax_applied": calculated_tax > 0,
                    "tax_rule": tax_rule_applied
                }
            )
        )
        
    return taxed_records
