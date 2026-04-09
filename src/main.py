from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict

from src.config.settings import load_settings, validate_required_settings
from src.scheduler.jobs import run_scheduler
from src.service.pipeline import run_sync

"""
Entrypoint for the Multi-Cloud Cost Optimization Pipeline.
Parses CLI arguments, loads configuration, and invokes either a single
synchronization run or the continuous scheduler loop.
"""


def build_parser() -> argparse.ArgumentParser:
    """
    Constructs the command-line argument parser for the application.
    
    Returns:
        argparse.ArgumentParser: The configured CLI parser.
    """
    parser = argparse.ArgumentParser(description="Multi-cloud Cost Optimization Dashboard sync runner")
    parser.add_argument("--run-once", action="store_true", help="Run one sync cycle and exit")
    parser.add_argument("--loop", action="store_true", help="Run the continuous scheduler loop")
    parser.add_argument("--cloud-mode", choices=["live", "mock"], help="Override cloud mode for this run")
    return parser


def main() -> None:
    """
    Main application bootstrap.
    Initializes environment settings, configures logging, validates 
    required live credentials, and executes the requested pipeline mode.
    """
    args = build_parser().parse_args()
    
    # Load configuration from the OS environment
    settings = load_settings()
    
    # Allow CLI to override the cloud mode for quick testing
    if args.cloud_mode:
        settings = settings.__class__(**{**asdict(settings), "cloud_mode": args.cloud_mode})

    # Configure the global logging framework based on settings
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Pre-flight check: ensure we aren't missing critical API keys before starting
    validation_error = validate_required_settings(settings)
    if validation_error:
        raise SystemExit(validation_error)

    # Branch into infinite daemon mode if requested
    if args.loop:
        run_scheduler(settings)
        return

    # Default: Run a single synchronization cycle and exit
    cost_records, recommendations, sent_alerts = run_sync(settings)
    
    summary = {
        "records_ingested": len(cost_records),
        "recommendations_generated": len(recommendations),
        "alerts_sent": sent_alerts,
        "cloud_mode": settings.cloud_mode,
    }
    
    # Output the JSON summary to stdout for potential external capture
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
