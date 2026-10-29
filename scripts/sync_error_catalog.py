#!/usr/bin/env python3
"""Regenerate src/myvoicemaker/_error_catalog.py from the JS SDK catalog.

The JavaScript SDK (../sdk/src/errors/catalog.ts) is the source of truth for
the API error-code contract. This script parses it and emits the Python
mirror, transliterating SDK method references in hints into Python names
(tts.listVoices() -> tts.list_voices(), ...). Run it whenever the JS catalog
changes:

    python scripts/sync_error_catalog.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_CATALOG = ROOT.parent / "sdk" / "src" / "errors" / "catalog.ts"
OUT = ROOT / "src" / "myvoicemaker" / "_error_catalog.py"

# JS → Python spelling of SDK references inside hints/descriptions.
TRANSLITERATE: list[tuple[str, str]] = [
    ("voice_id to tts.generate() or voiceId to tts.stream()", "voice_id to tts.generate() or tts.stream()"),
    ("tts.listVoices()", "tts.list_voices()"),
    ("tts.listLanguages()", "tts.list_languages()"),
    ("tts.getResult()", "tts.get_result()"),
    ("asr.transcribeFile()", "asr.transcribe_file()"),
    ("asr.getResult()", "asr.get_result()"),
    ("animate.getResult()", "animate.get_result()"),
    ("usage.getBalance()", "usage.get_balance()"),
    ("usage.getBreakdown()", "usage.get_breakdown()"),
    ("auth.createStreamToken({ type: \"asr\" })", 'auth.create_stream_token(type="asr")'),
    ("{ type: \"tts\" }", 'type="tts"'),
    ("auth.createStreamToken()", "auth.create_stream_token()"),
    ("new VoiceMaker({ apiKey })", "VoiceMaker(api_key=...)"),
    ("new VoiceMaker({ baseUrl })", "VoiceMaker(base_url=...)"),
    ("new VoiceMaker({ timeoutMs })", "VoiceMaker(timeout=...)"),
    ("timeoutMs in VoiceMaker(timeout=...)", "timeout in VoiceMaker(timeout=...)"),
    ("Pass apiKey to new VoiceMaker() on a backend", "Pass api_key to VoiceMaker() on a backend"),
    ("pass it as accessToken", "pass it as access_token"),
    ("mode: \"async\"", 'mode="async"'),
    ("output_format: \"wav\"", 'output_format="wav"'),
    ("streaming_supported: true", "streaming_supported=True"),
    ("err.retryAfter", "e.retry_after"),
    ("err.issues", "e.issues"),
    ("nextCursor", "next_cursor"),
    ("webhookUrl", "webhook_url"),
    ("chunkText()", "chunk_text()"),
    ("sendAudio()/sendText()", "send_audio()/send_text()"),
    ("sendText()", "send_text()"),
    ("connection.close()", "conn.close()"),
    ("Keep the default keepAliveMs", "Keep the default keepalive_interval"),
    ("raise timeoutMs in the poll options", "raise timeout_seconds on poll()"),
    ("call getResult() again later", "call get_result() again later"),
    ('Wait for the "open" event (session.begin) before sending', "Wait for the StreamSessionBegin event before sending"),
    ("Streaming needs Node >= 22, Bun, Deno or a browser.", "Install the 'websockets' package (pip install websockets)."),
    ("Browsers and Node hide the HTTP status of a rejected WebSocket upgrade, so the exact reason is not available here.",
     "The HTTP status of a rejected WebSocket upgrade was not available."),
    ("check the console for a CORS or mixed-content block", "check proxies and TLS interception"),
]

ENTRY_RE = re.compile(
    r"^  (?P<code>[a-z_]+): \{\n"
    r"    status: (?P<status>\d+),\n"
    r"    title: (?P<title>\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'),\n"
    r"    description:\s*\n?\s*(?P<description>\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'),\n"
    r"    hint:\s*\n?\s*(?P<hint>\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'),\n"
    r"    retryable: (?P<retryable>true|false),\n"
    r"  \},",
    re.M,
)
TABLE_RE = re.compile(r"export const (?P<name>[A-Z_]+) = define\(\{\n(?P<body>.*?)\n\}\);", re.S)
CLOSE_RE = re.compile(r"  (?P<code>\d{4}): (?P<text>\"(?:[^\"\\]|\\.)*\"),")


def js_string(token: str) -> str:
    quote = token[0]
    inner = token[1:-1]
    return inner.replace(f"\\{quote}", quote).replace("\\\\", "\\")


def transliterate(text: str) -> str:
    for js, py in TRANSLITERATE:
        text = text.replace(js, py)
    return text


def py_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main() -> int:
    src = JS_CATALOG.read_text()
    tables: dict[str, list[dict[str, str]]] = {}
    for table in TABLE_RE.finditer(src):
        entries = []
        body = table.group("body")
        for m in ENTRY_RE.finditer(body + "\n"):
            entries.append(
                {
                    "code": m.group("code"),
                    "status": m.group("status"),
                    "title": transliterate(js_string(m.group("title"))),
                    "description": transliterate(js_string(m.group("description"))),
                    "hint": transliterate(js_string(m.group("hint"))),
                    "retryable": "True" if m.group("retryable") == "true" else "False",
                }
            )
        expected = body.count("retryable:")
        if len(entries) != expected:
            print(f"{table.group('name')}: parsed {len(entries)} of {expected} entries", file=sys.stderr)
            return 1
        tables[table.group("name")] = entries

    close_block = re.search(r"STREAM_CLOSE_CODES[^{]*\{\n(.*?)\n\};", src, re.S)
    assert close_block
    close_codes = [(m.group("code"), js_string(m.group("text"))) for m in CLOSE_RE.finditer(close_block.group(1))]

    out = [
        '"""Error-code catalog for the VoiceMaker developer API (Python mirror).',
        "",
        "GENERATED by scripts/sync_error_catalog.py from ../sdk/src/errors/catalog.ts —",
        "do not edit by hand; edit the JS catalog and re-run the script.",
        "",
        "Every non-2xx response from ``/dev/v1`` carries a stable, machine-readable",
        "``errorCode``. This module maps each code to its canonical HTTP status, a",
        "one-line meaning and what to do about it, phrased in terms of SDK methods",
        "rather than raw endpoints. Codes never get renamed once shipped.",
        '"""',
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from typing import Dict, Optional",
        "",
        "",
        "@dataclass(frozen=True)",
        "class ErrorCodeInfo:",
        "    #: Canonical HTTP status the API uses for this code (0 for client-side/stream codes).",
        "    status: int",
        "    #: Short title, matching the API's ``error`` field.",
        "    title: str",
        "    #: What went wrong.",
        "    description: str",
        "    #: What to do about it, in SDK terms.",
        "    hint: str",
        "    #: Whether repeating the same call later can succeed without changes.",
        "    retryable: bool",
        "",
        "",
    ]
    docs = {
        "ERROR_CODES": "Codes returned by the REST API and by the pre-upgrade HTTP phase of the WebSocket endpoints.",
        "CLIENT_ERROR_CODES": "Codes the SDK itself raises before or instead of a request (no HTTP exchange happened).",
        "STREAM_ERROR_CODES": "Codes carried by ``{type: \"error\", code, message}`` frames inside an open streaming session.",
    }
    for name, entries in tables.items():
        out.append(f"#: {docs[name]}")
        out.append(f"{name}: Dict[str, ErrorCodeInfo] = {{")
        for e in entries:
            out.append(f'    "{e["code"]}": ErrorCodeInfo(')
            out.append(f'        status={e["status"]},')
            out.append(f'        title={py_string(e["title"])},')
            out.append(f'        description={py_string(e["description"])},')
            out.append(f'        hint={py_string(e["hint"])},')
            out.append(f'        retryable={e["retryable"]},')
            out.append("    ),")
        out.append("}")
        out.append("")
    out.append("#: Meaning of the WebSocket close codes the streaming endpoints use.")
    out.append("STREAM_CLOSE_CODES: Dict[int, str] = {")
    for code, text in close_codes:
        out.append(f"    {code}: {py_string(text)},")
    out.append("}")
    out.append("")
    out.append("")
    out.append("def describe_stream_close(code: int) -> str:")
    out.append('    """Human-readable meaning of a WebSocket close code."""')
    out.append('    return STREAM_CLOSE_CODES.get(code, f"Connection closed with code {code}.")')
    out.append("")
    out.append("")
    out.append("def describe_error_code(code: str) -> Optional[ErrorCodeInfo]:")
    out.append('    """Look up an API, client-side or in-session stream code (None if unknown)."""')
    out.append("    return ERROR_CODES.get(code) or CLIENT_ERROR_CODES.get(code) or STREAM_ERROR_CODES.get(code)")
    out.append("")
    OUT.write_text("\n".join(out))
    total = sum(len(v) for v in tables.values())
    print(f"wrote {OUT.relative_to(ROOT)}: {total} codes across {len(tables)} tables, {len(close_codes)} close codes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
