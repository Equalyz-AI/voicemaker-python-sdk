from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ExplainAction = Literal["explain", "summarize", "translate", "simplify"]


@dataclass
class ExplainResponse:
    id: str
    action: str
    language: str
    result: str
    tokens_used: int
    credits_used: int
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExplainResponse:
        return cls(
            id=data["id"],
            action=data["action"],
            language=data["language"],
            result=data["result"],
            tokens_used=data["tokens_used"],
            credits_used=data["credits_used"],
            created_at=data["created_at"],
        )
