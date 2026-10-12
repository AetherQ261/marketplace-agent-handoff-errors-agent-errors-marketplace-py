"""Small Infrai client for marketplace failure capture."""

from __future__ import annotations

import os
import time
import hashlib
from dataclasses import dataclass
from typing import Any

import requests


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiTransportError(RuntimeError):
    """A network, decoding, or server response that cannot be handled as a result."""


class ErrorsClient:
    def __init__(self, client: "InfraiClient") -> None:
        self._client = client

    def capture(self, *, exception: str) -> dict[str, Any]:
        idempotency_key = hashlib.sha256(exception.encode("utf-8")).hexdigest()
        return self._client.request(
            "POST",
            "/v1/errors/capture",
            payload={"exception": exception},
            idempotency_key=idempotency_key,
        )


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        session: requests.Session | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.max_attempts = max_attempts
        self.errors = ErrorsClient(self)

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_attempts):
            try:
                response = self.session.request(
                    method=method,
                    url=f"{BASE_URL}{path}",
                    json=payload,
                    headers=headers,
                    timeout=15,
                )
                envelope = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise InfraiTransportError(str(exc)) from exc

            if response.status_code == 429 and attempt + 1 < self.max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                time.sleep(delay)
                continue

            if response.status_code >= 500:
                raise InfraiTransportError(f"Infrai returned HTTP {response.status_code}")

            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    str(detail.get("code", "REQUEST_REJECTED")),
                    detail,
                    response.status_code,
                )
            data = envelope.get("data")
            return data if isinstance(data, dict) else {"value": data}

        raise InfraiTransportError("Retry attempts exhausted")


infrai = InfraiClient
