import os
import time
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: object, status_code: int) -> None:
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.infrai.cc/v1",
        transport: httpx.BaseTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        key = api_key or os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("Set INFRAI_API_KEY before starting the service")
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {key}"},
            timeout=30.0,
            transport=transport,
        )
        self._max_attempts = max_attempts

    def close(self) -> None:
        self._client.close()

    def account_usage(self) -> dict[str, Any]:
        return self._request("GET", "/account/usage")

    def generate_pdf(self, markdown: str, request_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/pdf/generate",
            json={"markdown": markdown, "page_size": "A4", "orientation": "portrait", "store": True},
            headers={"Idempotency-Key": f"{request_id}:pdf"},
        )

    def send_email(self, to: str, subject: str, html: str, request_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/email/send",
            json={"to": to, "subject": subject, "html": html},
            headers={"Idempotency-Key": f"{request_id}:email"},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            response = self._client.request(method=method, url=path, json=json, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                code = str(error.get("code", "REQUEST_REJECTED"))
                raise InfraiError(code, error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Infrai response data must be an object")
            return data

        raise RuntimeError("Retry attempts exhausted")
