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
        max_words: int | None = None,
    ) -> ExplainResponse:
        body: dict[str, object] = {
            "text": text,
            "language": language,
            "action": action,
        }
        if target_language is not None:
            body["target_language"] = target_language
        if max_words is not None:
            body["max_words"] = max_words

        resp = self._http.post("/dev/v1/explain", body)
        return ExplainResponse.from_dict(resp.data)
