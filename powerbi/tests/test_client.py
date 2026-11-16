"""Tests for the Power BI client against a simulated REST API."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from streampulse_powerbi.cli import DEFAULT_CHECKS
from streampulse_powerbi.client import PowerBIClient, PowerBIError, PowerBISettings
from streampulse_powerbi.validate import Check, load_checks, run_checks

SETTINGS = PowerBISettings("tenant", "client", "secret", "workspace", "dataset")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeApi:
    """Records requests and answers them from a queue of refresh statuses."""

    def __init__(self, statuses=("Completed",), rows=None):
        self.requests = []
        self.statuses = list(statuses)
        self.rows = rows or [{"[MRR EUR]": 100.0}]

    def __call__(self, request, timeout):
        self.requests.append(request)
        url, method = request.full_url, request.get_method()
        if "oauth2/v2.0/token" in url:
            body = {"access_token": "token-123"}
        elif url.endswith("/refreshes") and method == "POST":
            body = {}
        elif "/refreshes?$top=1" in url:
            status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            body = {"value": [{"status": status, "endTime": "2026-11-16T05:30:00Z"}]}
        elif url.endswith("/executeQueries"):
            body = {"results": [{"tables": [{"rows": self.rows}]}]}
        else:
            raise AssertionError(f"unexpected request {method} {url}")
        return FakeResponse(json.dumps(body).encode())


def test_settings_name_every_missing_variable():
    with pytest.raises(SystemExit, match="POWERBI_TENANT_ID, POWERBI_CLIENT_ID"):
        PowerBISettings.from_environment({"POWERBI_WORKSPACE_ID": "w"})


def test_refresh_uses_a_service_principal_token():
    api = FakeApi()
    client = PowerBIClient(SETTINGS, opener=api)
    client.trigger_refresh()
    token_request, refresh_request = api.requests
    assert token_request.full_url.endswith("/tenant/oauth2/v2.0/token")
    assert b"grant_type=client_credentials" in token_request.data
    assert refresh_request.full_url.endswith("/groups/workspace/datasets/dataset/refreshes")
    assert refresh_request.get_header("Authorization") == "Bearer token-123"
    assert json.loads(refresh_request.data) == {"notifyOption": "NoNotification"}


def test_wait_polls_until_the_refresh_completes():
    sleeps = []
    api = FakeApi(statuses=["Unknown", "Unknown", "Completed"])
    refresh = PowerBIClient(SETTINGS, opener=api, sleep=sleeps.append).wait_for_refresh(
        timeout_seconds=600, poll_seconds=30
    )
    assert refresh["status"] == "Completed"
    assert sleeps == [30, 30]


@pytest.mark.parametrize("status", ["Failed", "Cancelled", "Disabled"])
def test_wait_fails_when_the_refresh_does_not_complete(status):
    client = PowerBIClient(SETTINGS, opener=FakeApi(statuses=[status]), sleep=lambda _: None)
    with pytest.raises(PowerBIError, match=status):
        client.wait_for_refresh()


def test_wait_gives_up_after_the_timeout():
    client = PowerBIClient(SETTINGS, opener=FakeApi(statuses=["Unknown"]), sleep=lambda _: None)
    with pytest.raises(PowerBIError, match="after 60 seconds"):
        client.wait_for_refresh(timeout_seconds=60, poll_seconds=30)


def test_execute_query_returns_rows():
    rows = PowerBIClient(SETTINGS, opener=FakeApi()).execute_query("EVALUATE ROW(...)")
    assert rows == [{"[MRR EUR]": 100.0}]


def test_checks_compare_within_a_relative_tolerance():
    checks = [Check("mrr", "select 1", "EVALUATE 1", tolerance=0.01), Check("subs", "s", "d")]
    values = {"select 1": 100.0, "s": 50.0}
    dax_values = {"EVALUATE 1": 100.9, "d": 51.0}
    results = run_checks(checks, values.__getitem__, dax_values.__getitem__)
    assert [r.passed for r in results] == [True, False]


def test_checks_file_is_packaged_and_loads(tmp_path: Path):
    assert load_checks(DEFAULT_CHECKS) == []
    path = tmp_path / "checks.json"
    path.write_text(json.dumps([{"name": "n", "sql": "s", "dax": "d"}]))
    assert load_checks(path) == [Check("n", "s", "d")]
