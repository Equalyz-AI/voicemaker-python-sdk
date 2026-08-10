from __future__ import annotations

import re
import time
from typing import Callable, TypeVar

from ._errors import TimeoutError

T = TypeVar("T")

_DEFAULT_INTERVAL = 2.0
_DEFAULT_TIMEOUT = 120.0

# --- streaming TTS text chunking -------------------------------------------------

_SENTENCE_RE = re.compile(r"[^.!?…]*[.!?…]+[\"'”’)\]]*(?:\s+|$)|[^.!?…]+$")
_TRAILING_PUNCT_RE = re.compile(r"[.!?…\"'”’)\]]+$")
# Terminators right after these are usually abbreviations, not sentence ends.
_ABBREVIATIONS = frozenset(
    {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "no", "vs", "etc", "e.g", "i.e"}
)


def _split_sentences(text: str) -> list[str]:
    pieces = [m.group(0).strip() for m in _SENTENCE_RE.finditer(text)]
    merged: list[str] = []
    for piece in pieces:
        if not piece:
            continue
        if merged:
            last_word = _TRAILING_PUNCT_RE.sub("", merged[-1]).rsplit(" ", 1)[-1]
            if last_word.lower() in _ABBREVIATIONS:
                merged[-1] = f"{merged[-1]} {piece}"
                continue
        merged.append(piece)
    return merged


def _hard_split(sentence: str, max_chars: int) -> list[str]:
    words = sentence.split(" ")
    pieces: list[str] = []
    current = ""
    for word in words:
        if not word:
            continue
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars or not current:
            current = candidate
            continue
        pieces.append(current)
        current = word
    if current:
        pieces.append(current)
    return pieces


def chunk_text(
    text: str,
    max_chars: int = 280,
    first_chunk_max_chars: int = 160,
) -> list[str]:
    """Split text into sentence-aligned chunks sized for streaming TTS.

    Tiny sentences merge up to the cap, over-long sentences split at word
    boundaries (never mid-word), and the first chunk uses a smaller cap so the
    session's first audio arrives sooner. Client convenience for driving
    ``send_text`` sentence-by-sentence — the server re-chunks authoritatively.
    """
    max_chars = max(1, int(max_chars))
    first_cap = max(1, min(int(first_chunk_max_chars), max_chars))
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    chunks: list[str] = []
    current = ""

    def cap() -> int:
        return first_cap if not chunks else max_chars

    for sentence in _split_sentences(normalized):
        if len(sentence) > cap() and not current:
            pieces = _hard_split(sentence, cap())
            chunks.extend(pieces[:-1])
            current = pieces[-1] if pieces else ""
            continue
        candidate = f"{current} {sentence}" if current else sentence
        if len(candidate) <= cap():
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(sentence) <= cap():
            current = sentence
        else:
            pieces = _hard_split(sentence, cap())
            chunks.extend(pieces[:-1])
            current = pieces[-1] if pieces else ""

    if current:
        chunks.append(current)
    return chunks


def poll(
    job_id: str,
    fn: Callable[[], T],
    is_done: Callable[[T], bool],
    interval_seconds: float = _DEFAULT_INTERVAL,
    timeout_seconds: float = _DEFAULT_TIMEOUT,
) -> T:
    deadline = time.monotonic() + timeout_seconds
    while True:
        result = fn()
        if is_done(result):
            return result
        if time.monotonic() >= deadline:
            raise TimeoutError(job_id, timeout_seconds)
        time.sleep(interval_seconds)
