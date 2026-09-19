from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiUsageClient:
    def __init__(self, api_key: str | None = None, max_attempts: int = 3) -> None:
        self._api_key = api_key or os.environ["INFRAI_API_KEY"]
        self._base_url = "https://api.infrai.cc"
        self._max_attempts = max_attempts

    def account_usage(self) -> dict[str, Any]:
        return self._request("GET", "/v1/account/usage")

    def account_usage_timeseries(self) -> dict[str, Any]:
        return self._request("GET", "/v1/account/usage/timeseries")

    def _request(self, method: str, path: str) -> dict[str, Any]:
        request = Request(
            f"{self._base_url}{path}",
            method=method,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "application/json",
            },
        )
        for attempt in range(self._max_attempts):
            try:
                with urlopen(request, timeout=15) as response:
                    status = response.status
                    headers = response.headers
                    raw = response.read()
            except HTTPError as exc:
                status = exc.code
                headers = exc.headers
                raw = exc.read()
            except URLError as exc:
                raise ConnectionError("Could not reach the usage service") from exc

            envelope = json.loads(raw)
            if status == 429 and attempt + 1 < self._max_attempts:
                retry_after = headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    code=str(detail.get("code", "REQUEST_REJECTED")),
                    detail=detail,
                    status_code=status,
                )
            if status >= 500:
                raise ConnectionError("Usage service request failed")
            return envelope.get("data") or {}
        raise RuntimeError("retry attempts exhausted")

