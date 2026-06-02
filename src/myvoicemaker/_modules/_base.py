from __future__ import annotations

from .._http._client import HttpClient


class BaseModule:
    def __init__(self, http: HttpClient) -> None:
        self._http = http
