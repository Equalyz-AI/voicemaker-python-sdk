from __future__ import annotations

from ._base import BaseModule
from .._types._explain import ExplainResponse


class ExplainModule(BaseModule):
    def process(
        self,
        text: str,
        language: str,
        action: str,
        *,
        target_language: str | None = None,
        max_tokens: int | None = None,
    ) -> ExplainResponse:
        body: dict[str, object] = {
            "text": text,
            "language": language,
            "action": action,
        }
        if target_language is not None:
            body["target_language"] = target_language
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        resp = self._http.post("/dev/v1/explain", body)
        return ExplainResponse.from_dict(resp.data)
