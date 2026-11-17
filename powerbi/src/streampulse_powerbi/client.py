"""Minimal Power BI REST client: service principal token, refresh, refresh status, DAX queries.

Standard library only. The HTTP opener and the sleep function are injectable, so the client is
tested against a simulated API (ADR-008: the workspace exists from Phase 5).
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

API = "https://api.powerbi.com/v1.0/myorg"
LOGIN = "https://login.microsoftonline.com"
SCOPE = "https://analysis.windows.net/powerbi/api/.default"
REQUIRED = (
    "POWERBI_TENANT_ID",
    "POWERBI_CLIENT_ID",
    "POWERBI_CLIENT_SECRET",
    "POWERBI_WORKSPACE_ID",
    "POWERBI_DATASET_ID",
)
FINISHED = {"Completed", "Failed", "Disabled", "Cancelled"}


@dataclass(frozen=True)
class PowerBISettings:
    tenant_id: str
    client_id: str
    client_secret: str
    workspace_id: str
    dataset_id: str

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> PowerBISettings:
        environ = os.environ if environ is None else environ
        missing = [name for name in REQUIRED if not environ.get(name)]
        if missing:
            raise SystemExit(f"Missing settings: {', '.join(missing)} (see .env.example).")
        return cls(*(environ[name] for name in REQUIRED))


class PowerBIError(RuntimeError):
    pass


class PowerBIClient:
    def __init__(
        self,
        settings: PowerBISettings,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self._open = opener
        self._sleep = sleep
        self._token: str | None = None

    def _request(self, method: str, url: str, body: dict | None = None, form: dict | None = None):
        headers = {}
        data = None
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            headers["Authorization"] = f"Bearer {self.token()}"
            if body is not None:
                data = json.dumps(body).encode()
                headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with self._open(request, timeout=60) as response:
            payload = response.read()
            return json.loads(payload) if payload else {}

    def token(self) -> str:
        """Client-credentials token for the service principal (cached for the client's life)."""
        if self._token is None:
            response = self._request(
                "POST",
                f"{LOGIN}/{self.settings.tenant_id}/oauth2/v2.0/token",
                form={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.client_id,
                    "client_secret": self.settings.client_secret,
                    "scope": SCOPE,
                },
            )
            self._token = response["access_token"]
        return self._token

    @property
    def _dataset_url(self) -> str:
        s = self.settings
        return f"{API}/groups/{s.workspace_id}/datasets/{s.dataset_id}"

    def trigger_refresh(self) -> None:
        self._request(
            "POST", f"{self._dataset_url}/refreshes", body={"notifyOption": "NoNotification"}
        )

    def latest_refresh(self) -> dict:
        response = self._request("GET", f"{self._dataset_url}/refreshes?$top=1")
        refreshes = response.get("value", [])
        if not refreshes:
            raise PowerBIError("No refresh found for the semantic model.")
        return refreshes[0]

    def wait_for_refresh(self, timeout_seconds: int = 3600, poll_seconds: int = 30) -> dict:
        """Poll the latest refresh until it finishes; raise if it did not complete."""
        waited = 0
        while True:
            refresh = self.latest_refresh()
            status = refresh.get("status")
            if status in FINISHED:
                if status != "Completed":
                    detail = refresh.get("serviceExceptionJson", "")
                    raise PowerBIError(f"Refresh ended with status {status}. {detail}".strip())
                return refresh
            if waited >= timeout_seconds:
                raise PowerBIError(f"Refresh still {status} after {timeout_seconds} seconds.")
            self._sleep(poll_seconds)
            waited += poll_seconds

    def execute_query(self, dax: str) -> list[dict]:
        """Run one DAX query and return its rows."""
        response = self._request(
            "POST",
            f"{self._dataset_url}/executeQueries",
            body={"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}},
        )
        return response["results"][0]["tables"][0]["rows"]
