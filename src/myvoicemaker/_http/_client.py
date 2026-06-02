from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .._errors import create_api_error
from ._types import ApiResponse, RateLimitHeaders


class HttpClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> ApiResponse[Any]:
        response = self._client.get(
            f"{self._base_url}{path}",
            params={k: v for k, v in (params or {}).items() if v is not None},
        )
        return self._parse(response)

    def post(self, path: str, json: dict[str, Any]) -> ApiResponse[Any]:
        response = self._client.post(
            f"{self._base_url}{path}",
            json=json,
        )
        return self._parse(response)

    def post_multipart(
        self,
        path: str,
        file_path: str,
        fields: dict[str, str | None],
    ) -> ApiResponse[Any]:
        p = Path(file_path)
        with p.open("rb") as f:
            file_bytes = f.read()

        files: dict[str, Any] = {"audio": (p.name, file_bytes)}
        data = {k: v for k, v in fields.items() if v is not None}

        response = self._client.post(
            f"{self._base_url}{path}",
            files=files,
            data=data,
        )
        return self._parse(response)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _parse_rate_limit(
        self, response: httpx.Response
    ) -> RateLimitHeaders | None:
        limit = response.headers.get("X-RateLimit-Limit")
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        if limit is None or remaining is None or reset is None:
            return None
        return RateLimitHeaders(
            limit=int(limit),
            remaining=int(remaining),
            reset=int(reset),
        )

    def _parse(self, response: httpx.Response) -> ApiResponse[Any]:
        request_id = response.headers.get("X-Request-Id")
        rate_limit = self._parse_rate_limit(response)

        if response.is_error:
            try:
                body: dict[str, Any] = response.json()
            except Exception:
                body = {
                    "error": "Unknown error",
                    "detail": f"HTTP {response.status_code}",
                }
            retry_after = response.headers.get("Retry-After")
            raise create_api_error(response.status_code, body, retry_after)

        return ApiResponse(
            data=response.json(),
            request_id=request_id,
            rate_limit=rate_limit,
        )
