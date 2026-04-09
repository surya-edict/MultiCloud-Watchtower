from __future__ import annotations

from src.models.schemas import AlertEvent

"""
Slack Integration Module.
Responsible for delivering structured alert payloads to configured
Slack webhook endpoints for incident response.
"""


def send_slack_alert(webhook_url: str, event: AlertEvent) -> bool:
    """
    Constructs and dispatches a Slack Block Kit payload based on an AlertEvent.
    
    Args:
        webhook_url (str): The destination Slack webhook URL.
        event (AlertEvent): The anomaly event containing the title and detailed body.
        
    Returns:
        bool: True if the alert was successfully delivered, False otherwise.
    """
    # Silently drop the alert if no webhook is configured (e.g., in mock/dev mode)
    if not webhook_url:
        return False
        
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("requests is required for Slack alerts") from exc

    # Construct the payload using Slack's Block Kit for richer formatting
    payload = {
        "text": event.title,
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": event.title}},
            {"type": "section", "text": {"type": "mrkdwn", "text": event.body}},
        ],
    }
    
    # Enforce a strict timeout to prevent the pipeline from hanging on a dead webhook
    response = requests.post(webhook_url, json=payload, timeout=10)
    return response.ok
