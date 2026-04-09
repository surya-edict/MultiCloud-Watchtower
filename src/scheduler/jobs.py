from __future__ import annotations

import logging
import time

from src.config.settings import Settings
from src.service.pipeline import run_sync

"""
Scheduler orchestration module.
Manages the background execution loops and cron-like timing logic
for running continuous pipeline synchronizations.
"""

LOGGER = logging.getLogger(__name__)


def register_jobs(settings: Settings):
    """
    Wires up the recurring job triggers to the core pipeline `run_sync` function.
    Reads frequency configuration directly from the Settings object.
    
    Args:
        settings (Settings): The fully loaded configuration block.
        
    Returns:
        schedule: The configured schedule module instance.
    """
    try:
        import schedule
    except ImportError as exc:
        raise RuntimeError("schedule is required for scheduler mode") from exc

    schedule.every(settings.scheduler_hourly_interval_minutes).minutes.do(run_sync, settings=settings)
    schedule.every().day.at(settings.scheduler_daily_at).do(run_sync, settings=settings)
    return schedule


def run_scheduler(settings: Settings) -> None:
    """
    Enters a blocking infinite loop to evaluate and execute scheduled tasks.
    Triggers an immediate initial sync before entering the sleep cycle.
    
    Args:
        settings (Settings): The configuration to pass to the running jobs.
    """
    schedule_module = register_jobs(settings)
    
    # Run once immediately on startup so users don't have to wait for the first interval
    run_sync(settings)
    
    LOGGER.info("Scheduler started, running sync cycles in background...")
    while True:
        schedule_module.run_pending()
        # Sleep for a small interval to prevent CPU pegging in the infinite loop
        time.sleep(15)
