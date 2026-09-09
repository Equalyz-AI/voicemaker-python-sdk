from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .._errors import (
    ConfigurationError,
    InvalidArgumentError,
    NetworkError,
    RequestTimeoutError,
    create_api_error,
)
from ._types import ApiResponse, RateLimitHeaders


class HttpClient:
    """Thin httpx wrapper. Every request is tagged with the SDK method that made
    it (``method``, e.g. ``"tts.generate"``) so any error names the call a
    developer actually wrote instead of the endpoint behind it."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        timeout: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        # Kept for transports (WebSocket streaming) that build their own
        # connections and cannot reuse this httpx client's headers. Optional so
        # untrusted clients can stream with ephemeral tokens only — REST calls
        # without a key raise ConfigurationError below.
        self._api_key = api_key
        self._timeout = timeout
        self._client = httpx.Client(
            headers=(
                {"Authorization": f"Bearer {api_key}"} if api_key else {}
            ),
            timeout=timeout,
        )

    @property
    def api_key(self) -> str | None:
        return self._api_key

    def require_api_key(self, method: str = "request") -> str:
        if not self._api_key:
            raise ConfigurationError("api_key_required", method)
        return self._api_key

    def ws_url(self, path: str, params: dict[str, Any] | None = None) -> str:
        """ws(s):// form of an API URL, for the streaming endpoints."""
        base = self._base_url
        if base.startswith("https://"):
            base = "wss://" + base[len("https://"):]
        elif base.startswith("http://"):
            base = "ws://" + base[len("http://"):]
        url = f"{base}{path}"
        query = {k: v for k, v in (params or {}).items() if v is not None}
        if query:
            url = f"{url}?{httpx.QueryParams(query)}"
        return url

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        method: str,
    ) -> ApiResponse[Any]:
        self.require_api_key(method)
        response = self._send(
            method,
            lambda: self._client.get(
                f"{self._base_url}{path}",
                params={k: v for k, v in (params or {}).items() if v is not None},
            ),
        )
        return self._parse(response, method)

    def post(self, path: str, json: dict[str, Any], *, method: str) -> ApiResponse[Any]:
        self.require_api_key(method)
        response = self._send(
            method, lambda: self._client.post(f"{self._base_url}{path}", json=json)
        )
        return self._parse(response, method)

    def post_multipart(
        self,
        path: str,
        file_path: str,
        fields: dict[str, str | None],
        *,
        method: str,
    ) -> ApiResponse[Any]:
        self.require_api_key(method)
        p = Path(file_path)
        try:
            with p.open("rb") as f:
                file_bytes = f.read()
        except OSError as exc:
            raise InvalidArgumentError(
                "file_path", f"cannot read '{file_path}' ({exc.strerror or exc}).", method
            ) from exc

        files: dict[str, Any] = {"audio": (p.name, file_bytes)}
        data = {k: v for k, v in fields.items() if v is not None}

        response = self._send(
            method,
            lambda: self._client.post(
                f"{self._base_url}{path}", files=files, data=data
            ),
        )
        return self._parse(response, method)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _send(self, method: str, request: Any) -> httpx.Response:
        try:
            return request()
        except httpx.TimeoutException as exc:
            raise RequestTimeoutError(method, self._timeout) from exc
        except httpx.TransportError as exc:
            # DNS, refused connection, TLS, proxy: the request never reached
            # the API. Wrap so the message names the SDK call and the code is
            # stable.
            raise NetworkError(method, exc) from exc

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

    def _parse(self, response: httpx.Response, method: str) -> ApiResponse[Any]:
        request_id = response.headers.get("X-Request-Id")
        rate_limit = self._parse_rate_limit(response)

        if response.is_error:
            try:
                body: dict[str, Any] = response.json()
                if not isinstance(body, dict):
                    raise ValueError("error body is not an object")
            except Exception:
                # Non-JSON error (a proxy or CDN page, an HTML 404 from a wrong
                # base_url): synthesise the standard shape so the error still
                # names the call and carries a code.
                reason = response.reason_phrase
                body = {
                    "error": f"HTTP {response.status_code}",
                    "detail": (
                        f"The server answered {response.status_code} {reason} without a JSON error body."
                        if reason
                        else f"The server answered {response.status_code} without a JSON error body."
                    ),
                }
            raise create_api_error(
                response.status_code,
                body,
                response.headers.get("Retry-After"),
                method=method,
                request_id=request_id,
            )

        return ApiResponse(
            data=response.json(),
            request_id=request_id,
            rate_limit=rate_limit,
        )
