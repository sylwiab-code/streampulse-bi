"""Slack notifications for DAG runs (ADR-010).

The webhook URL comes from SLACK_WEBHOOK_URL. Without it, the message is only logged, so local
runs without Slack still work. A failing notification never fails the task itself.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

log = logging.getLogger(__name__)


def post(text: str) -> bool:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        log.warning("SLACK_WEBHOOK_URL is not set; alert not sent: %s", text)
        return False
    request = urllib.request.Request(
        url,
        data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            return True
    except OSError as error:
        log.error("Slack alert failed: %s", error)
        return False


def failure_message(context: dict[str, Any]) -> str:
    ti = context["ti"]
    exception = context.get("exception")
    reason = f"\n> {str(exception)[:300]}" if exception else ""
    return (
        f":red_circle: *StreamPulse* `{ti.dag_id}.{ti.task_id}` failed "
        f"(run `{ti.run_id}`, try {ti.try_number}).{reason}"
    )


def notify_failure(context: dict[str, Any]) -> None:
    """on_failure_callback: called once a task has failed its last retry."""
    post(failure_message(context))


def notify_success(dag_id: str, run_id: str) -> None:
    post(f":large_green_circle: *StreamPulse* `{dag_id}` succeeded (run `{run_id}`).")
