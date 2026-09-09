# myvoicemaker

Official Python SDK for the [VoiceMaker](https://myvoicemaker.ai) API.

Generate dialect-accurate speech, transcribe audio in Nigerian languages, create lip-sync animations, and more — all from a single, fully typed client.

[![PyPI version](https://img.shields.io/pypi/v/myvoicemaker)](https://pypi.org/project/myvoicemaker/)
[![Python versions](https://img.shields.io/pypi/pyversions/myvoicemaker)](https://pypi.org/project/myvoicemaker/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Supported Languages](#supported-languages)
- [Modules](#modules)
  - [Text-to-Speech (TTS)](#text-to-speech-tts)
  - [Automatic Speech Recognition (ASR)](#automatic-speech-recognition-asr)
  - [Lip-Sync Animation](#lip-sync-animation)
  - [Explain](#explain)
  - [Usage & Billing](#usage--billing)
- [Error Handling](#error-handling)
- [Polling Async Jobs](#polling-async-jobs)
- [Type Hints](#type-hints)
- [Rate Limits](#rate-limits)

---

## Installation

```bash
pip install myvoicemaker
```

Requires **Python 3.9+**. The only runtime dependency is [`httpx`](https://www.python-httpx.org/).

---

## Quick Start

```python
from myvoicemaker import VoiceMaker

client = VoiceMaker(api_key="vmk_live_...")

# Generate speech
tts = client.tts.generate(
    text="Bawo ni o se wa?",
    voice_id="masoyinbo-male-conversational",
    language="yo",
)
print(tts.audio_url)

# Transcribe an audio file
job = client.asr.transcribe_file("./sermon.mp3", language="yo")
result = client.asr.poll(job.job_id, timeout_seconds=120)
print(result.text)
```

---

## Authentication

All requests require a developer API key. Create and manage your keys from the [VoiceMaker Developer Dashboard](https://myvoicemaker.ai).

```python
client = VoiceMaker(api_key="vmk_live_...")
```

| Key environment | Prefix | Credits consumed |
| :--- | :--- | :--- |
| Production | `vmk_live_` | Yes |
| Test / Sandbox | `vmk_test_` | No |

**Keep your API key secret.** Use environment variables in production:

```python
import os
from myvoicemaker import VoiceMaker

client = VoiceMaker(api_key=os.environ["VOICEMAKER_API_KEY"])
```

### Configuration options

```python
client = VoiceMaker(
    api_key="vmk_live_...",
    base_url="https://api.myvoicemaker.ai",  # default
    timeout=30.0,                             # default: 30 seconds
)
```

### Context manager

```python
with VoiceMaker(api_key="vmk_live_...") as client:
    result = client.tts.generate(...)
# underlying HTTP connection is closed automatically
```

---

## Supported Languages

Discover the current set with `client.tts.list_languages()` instead
of hardcoding codes:

```python
response = client.tts.list_languages()

print(response.default_language)  # e.g. "auto"
for language in response.languages:
    print(f"{language.code} — {language.label}")
```

Codes known at this SDK release: `yo` (Yoruba), `ig` (Igbo), `ha` (Hausa),
`pcm` (Nigerian Pidgin), `en` (English) and `auto` (let the model detect the
language). Omitting `language` uses the platform's default
(`default_language` above).

---

## Modules

### Text-to-Speech (TTS)

Convert text into natural-sounding speech. Requests are **synchronous** — the audio URL is returned immediately.

#### `client.tts.list_languages()`

Retrieve the languages currently enabled for synthesis.

**Returns** `TtsLanguageListResponse`

| Field | Type | Description |
| :--- | :--- | :--- |
| `default_language` | `str` | Code requests without a `language` resolve to |
| `languages` | `list[TtsLanguage]` | `code`, `label`, `supports_voice_clone`, `supports_tone`, `supports_speed`, `streaming_supported` |

---

#### `client.tts.list_voices(*, language=None)`

Retrieve all available voices, optionally filtered by language.

```python
response = client.tts.list_voices(language="yo")

for voice in response.voices:
    print(f"{voice.id} — {voice.name} ({voice.gender}, {voice.style})")
    print(f"  Sample: {voice.sample_url}")
```

**Parameters**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `language` | `str` (optional) | Filter by language code (see `list_languages()`) |

**Returns** `VoiceListResponse`

| Field | Type |
| :--- | :--- |
| `voices` | `list[Voice]` |

Each `Voice` has: `id`, `name`, `gender`, `language`, `style`, `sample_url`,
and `type` (`"preset"` for catalog voices, `"custom"` for your own cloned
voices).

---

#### `client.tts.generate(text, voice_id, language=None, *, speed=None, output_format=None)`

```python
result = client.tts.generate(
    text="Nne, ka anyị bido oge a.",
    voice_id="amaka",
    language="ig",
    speed=0.9,
    output_format="mp3",
)

print(result.audio_url)        # https://media.myvoicemaker.ai/...
print(result.duration_seconds) # e.g. 3.2
print(result.credits_used)     # e.g. 28
```

**Parameters**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `text` | `str` | ✓ | Text to synthesise (max 5,000 characters) |
| `voice_id` | `str` | ✓ | Voice identifier from `list_voices()` |
| `language` | `str` | | Language code from `list_languages()` (default: the platform's default language) |
| `speed` | `float` | | Playback speed: `0.5`–`2.0` (default `1.0`) |
| `output_format` | `str` | | `mp3` \| `wav` \| `ogg` (default `mp3`) |

**Returns** `TtsGenerateResponse`

| Field | Type |
| :--- | :--- |
| `id` | `str` |
| `audio_url` | `str` |
| `duration_seconds` | `float \| None` |
| `characters` | `int` |
| `credits_used` | `int` |
| `language` | `str` |
| `voice_id` | `str` |
| `created_at` | `str` (ISO 8601) |

---

#### `client.tts.generate(..., mode="async")`, `client.tts.get_result(id)`, `client.tts.poll(id, *, interval_seconds=2.0, timeout_seconds=120.0)` — async TTS

Sync `generate()` holds the HTTP connection while the engine synthesises, so it
can raise `ServiceWarmingError` (`503 tts_warming`, engine cold start) or
`ConcurrencyLimitError` (`429 concurrency_limit_reached`, your plan's processing
cap is in use). Async mode never hits either: the job is queued and returned as
a `TtsJobResponse`, then fetched with `get_result()` or awaited with `poll()`.

```python
job = client.tts.generate(
    "Sannu da zuwa.",
    voice_id="amaka",
    language="ha",
    mode="async",                  # → TtsJobResponse(id, status="queued", credits_reserved, ...)
)

result = client.tts.poll(job.id, timeout_seconds=180)
if result.status == "completed":
    print(result.audio_url)        # TtsResultResponse
else:
    print(result.error)            # status == "failed"
```

`poll()` raises `PollTimeoutError` if the job is still running when
`timeout_seconds` elapses — the job itself continues; call `get_result(id)` later.

#### `client.tts.stream(*, voice_id, language=None, speed=1.0, quality="standard", access_token=None)` — real-time streaming synthesis

Open a WebSocket session (`wss /dev/v1/tts/stream`): audio starts arriving
while later text is still being sent. See `examples/tts_stream_to_file.py`
for a full flow.

```python
connection = client.tts.stream(voice_id="amaka")
```

**Parameters**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `voice_id` | `str` | ✓ | Voice identifier from `list_voices()` |
| `language` | `str` | | Language code from `list_languages()` — only languages with `streaming_supported` are accepted (default: the platform's default language) |
| `speed` | `float` | | Playback speed: `0.5`–`2.0` (default `1.0`) |
| `quality` | `str` | | `"standard"` (default, lowest latency) or `"high"` |
| `access_token` | `str` | | Single-use `vmst_*` stream token minted by your backend |

Output is mono PCM16LE @ 24 kHz.

---

### Automatic Speech Recognition (ASR)

Transcribe pre-recorded audio files. Jobs are **asynchronous** — submit a job, then poll for the result.

#### `client.asr.transcribe(audio, *, language="auto", webhook_url=None)` — from URL

```python
job = client.asr.transcribe(
    "https://storage.example.com/interview.wav",
    language="ha",
    webhook_url="https://myapp.com/webhooks/voicemaker",
)
print(job.job_id)  # use this to poll
```

**Parameters**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `audio` | `str` | ✓ | Publicly accessible URL of the audio file |
| `language` | `str` | | Language code or `auto` (default) |
| `webhook_url` | `str` | | Callback URL when the job completes |

---

#### `client.asr.transcribe_file(file_path, *, language="auto", webhook_url=None)` — from file

```python
job = client.asr.transcribe_file(
    "./hausa-interview.mp3",
    language="ha",
)
```

**Parameters**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `file_path` | `str` | ✓ | Path to the audio file |
| `language` | `str` | | Language code or `auto` (default) |
| `webhook_url` | `str` | | Callback URL when the job completes |

Supported formats: `.mp3`, `.wav`, `.ogg`, `.m4a`, `.webm` — max 500 MB.

---

#### `client.asr.get_result(job_id)`

```python
result = client.asr.get_result("trans_1a2b3c...")
print(result.status)  # 'queued' | 'processing' | 'completed' | 'failed'
print(result.text)
```

---

#### `client.asr.list(*, limit=20, cursor=None, status=None)`

```python
page = client.asr.list(limit=10, status="COMPLETED")

for job in page.items:
    print(f"{job.job_id}: {(job.text or '')[:60]}")

# Load the next page
if page.next_cursor:
    next_page = client.asr.list(cursor=page.next_cursor)
```

**Parameters**

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `limit` | `int` | Items per page: 1–100 (default `20`) |
| `cursor` | `str` | Pagination cursor from a previous response |
| `status` | `str` | Filter: `QUEUED` \| `PROCESSING` \| `COMPLETED` \| `FAILED` |

---

#### `client.asr.poll(job_id, *, interval_seconds=2.0, timeout_seconds=120.0)` — wait for completion

Polls `get_result` at a regular interval until the job reaches a terminal state (`completed` or `failed`).

```python
result = client.asr.poll(
    job.job_id,
    interval_seconds=3.0,   # poll every 3 seconds (default: 2.0)
    timeout_seconds=120.0,  # give up after 2 minutes (default: 120.0)
)

if result.status == "completed":
    print(f"Transcript: {result.text}")
    print(f"Language detected: {result.detected_language}")
    print(f"Duration: {result.duration_seconds}s")
```

Raises `TimeoutError` if `timeout_seconds` is exceeded before the job completes.

**TranscriptionJob fields**

| Field | Type |
| :--- | :--- |
| `job_id` | `str` |
| `status` | `Literal['queued', 'processing', 'completed', 'failed']` |
| `language` | `str` |
| `detected_language` | `str \| None` |
| `text` | `str \| None` |
| `confidence` | `float \| None` |
| `duration_seconds` | `float \| None` |
| `credits_used` | `int \| None` |
| `created_at` | `str` (ISO 8601) |
| `completed_at` | `str \| None` (ISO 8601) |

#### `client.asr.stream(*, language, sample_rate=16000, interim_results=True)` — real-time streaming (WebSocket)

Transcribe live audio with interim results as you speak. Uses the bundled
`websockets` dependency; no extra setup.

```python
import threading
from myvoicemaker import StreamTranscript, StreamSessionEnd

with client.asr.stream(language="yo", sample_rate=16000) as conn:
    def send_audio():
        for chunk in pcm_chunks:      # PCM16LE mono bytes, 50-250ms per chunk
            conn.send_audio(chunk)
        conn.close()                  # flushes the tail, then ends the session

    threading.Thread(target=send_audio, daemon=True).start()

    for event in conn:
        if isinstance(event, StreamTranscript):
            print("FINAL" if event.is_final else "interim", event.text)
        elif isinstance(event, StreamSessionEnd):
            print(f"used {event.credits_used} credits over {event.duration_seconds}s")
```

**Parameters**

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `language` | `Literal['yo', 'ig', 'ha', 'pcm', 'en']` | Yes | Explicit language — `auto` is batch-only. |
| `sample_rate` | `int` | No | Sample rate of your PCM16LE mono audio. Default `16000` (8000-48000). |
| `interim_results` | `bool` | No | Emit revisable interim transcripts. Default `True`. |

**Connection API**: `send_audio(bytes)`, `finalize()` (flush pending words into a
final without closing), `close()` (graceful end, returns `StreamSessionEnd`),
`recv(timeout=None)` (next event or `None`), iteration (`for event in conn`),
callbacks (`conn.on("transcript", fn)` — fired on a background thread),
`conn.session` / `conn.result` properties.

**Events**: `StreamSessionBegin`, `StreamTranscript` (`text`, `is_final`, `start`,
`end`, `confidence`), `StreamSessionEnd` (`duration_seconds`, `credits_used`,
`reason`), `StreamError` (`code`, `message`).

**Billing**: purchased credits only, at the transcription per-second rate; reserved
in 60-second blocks while streaming and settled to the exact second at close. Idle
connections (no audio or keep-alive for 30s) are closed; stream duration is capped
per plan (up to 60 minutes) — reconnect to continue. The finished session is also
retrievable afterwards via `client.asr.get_result(job_id)`.

---

### Lip-Sync Animation

Generate a lip-sync video by combining a portrait image with an audio file. Jobs are **asynchronous**.

#### `client.animate.generate(image_url, audio_url, *, output_format="mp4")`

```python
job = client.animate.generate(
    image_url="https://example.com/speaker-portrait.jpg",
    audio_url=tts.audio_url,
    output_format="mp4",
)
print(job.job_id)
print(f"Estimated credits: {job.estimated_credits}")
```

**Parameters**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `image_url` | `str` | ✓ | URL of the source portrait image (max 5 MB, up to 4K) |
| `audio_url` | `str` | ✓ | URL of the audio file (max 30 seconds) |
| `output_format` | `str` | | `mp4` \| `webm` (default `mp4`) |

---

#### `client.animate.get_result(job_id)`

```python
result = client.animate.get_result("anim_1a2b3c...")
print(result.status)    # 'queued' | 'processing' | 'completed' | 'failed'
print(result.video_url) # None until completed
```

---

#### `client.animate.poll(job_id, *, interval_seconds=2.0, timeout_seconds=120.0)`

```python
result = client.animate.poll(
    job.job_id,
    interval_seconds=5.0,
    timeout_seconds=300.0,
)

if result.status == "completed":
    print(f"Video: {result.video_url}")
    print(f"Duration: {result.duration_seconds}s")
```

---

### Explain

Process text in Nigerian languages — explain, summarise, translate, or simplify content using AI.

#### `client.explain.process(text, language, action, *, target_language=None, max_words=None)`

```python
result = client.explain.process(
    text="Ìwé Mímọ̀ sọ pé...",
    language="yo",
    action="translate",
    target_language="en",
    max_words=250,
)

print(result.result)        # translated text
print(result.tokens_used)   # e.g. 145
print(result.credits_used)  # e.g. 145
```

**Parameters**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `text` | `str` | ✓ | Input text to process |
| `language` | `str` | ✓ | Source language code |
| `action` | `str` | ✓ | `explain` \| `summarize` \| `translate` \| `simplify` |
| `target_language` | `str` | | Required when `action` is `translate` |
| `max_words` | `int` | | Soft length target in words: 1–1000 (default `250`). Not a hard cap — sentences always complete. |

---

### Usage & Billing

#### `client.usage.get_balance()`

```python
balance = client.usage.get_balance()

print(f"Tier:              {balance.tier}")
print(f"Credits remaining: {balance.credits_remaining:,}")
print(f"Credits used:      {balance.credits_used:,}")
```

**Returns** `UsageBalanceResponse`

| Field | Type |
| :--- | :--- |
| `account_id` | `str` |
| `tier` | `Literal['free', 'starter', 'growth', 'pro', 'enterprise']` |
| `credits_remaining` | `int` |
| `credits_used` | `int` |
| `credits_total` | `int \| None` (present only if credits were ever purchased) |
| `credits_expire` | `str \| None` |
| `created_at` | `str` (ISO 8601) |

---

#### `client.usage.get_breakdown(start_date, end_date, *, module=None)`

```python
report = client.usage.get_breakdown(
    start_date="2026-05-01T00:00:00Z",
    end_date="2026-05-31T23:59:59Z",
    module="asr",  # optional filter
)

for entry in report.breakdown:
    print(f"{entry.module}: {entry.requests} requests, {entry.credits_used} credits")

print(f"Total: {report.total_credits_used} credits")
```

**Parameters**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `start_date` | `str` | ✓ | ISO 8601 datetime (inclusive) |
| `end_date` | `str` | ✓ | ISO 8601 datetime (inclusive) |
| `module` | `str` | | Filter: `tts` \| `asr` \| `animate` \| `explain` |

---

## Error Handling

Every failure is raised as a typed exception that subclasses `VoiceMakerError`.
The message names the **SDK method** that failed, explains what went wrong in
SDK terms, and ends with the machine-readable code and the request id to quote
to support:

```
tts.generate(): Unknown voice — voice_id 'foo' does not match an enabled voice
preset or one of your custom voices. Use tts.list_voices() for the list of
available voices. [unknown_voice_id · request 8f1c2d3e]
```

Catch the class for coarse handling and check `e.code` for exact cases:

```python
import time
from myvoicemaker import (
    VoiceMakerError,
    VoiceMakerAPIError,
    AuthenticationError,
    InsufficientCreditsError,
    RateLimitError,
    ServiceWarmingError,
    UnknownVoiceError,
    ValidationError,
    PollTimeoutError,
)

try:
    result = client.tts.generate(text, voice_id="amaka")
except UnknownVoiceError as e:
    voices = client.tts.list_voices().voices        # e.hint says the same
except ServiceWarmingError as e:
    time.sleep(e.retry_after or 60)                  # or generate(..., mode="async")
except RateLimitError as e:
    time.sleep(e.retry_after or 60)
except InsufficientCreditsError as e:
    notify_billing(e.request_id)
except ValidationError as e:
    print(e.issues)                                  # [{"field", "code", "message"}]
except AuthenticationError:
    rotate_key()
except VoiceMakerAPIError as e:
    if e.retryable:
        schedule_retry()
    else:
        report(e.code, e.request_id)
except PollTimeoutError as e:
    pass                                             # job still running — get_result(e.job_id) later
except VoiceMakerError as e:
    print(e.code, e)                                 # network_error, request_timeout, ...
```

### Exception classes

Classes by HTTP status, refined by error code where developers need to branch:

| Class | Status | Codes | Meaning |
| :--- | :--- | :--- | :--- |
| `AuthenticationError` | 401 | `missing_api_key`, `invalid_api_key`, `api_key_expired` | The key is missing, wrong, or expired |
| ↳ `StreamTokenError` | 401/403 | `invalid_stream_token`, `stream_token_kind_mismatch` | Ephemeral stream token rejected — mint a fresh one with `auth.create_stream_token()` |
| `ForbiddenError` (alias `PermissionError`, deprecated) | 403 | `api_key_revoked`, `project_disabled`, `api_access_not_enabled`, `insufficient_scope` | The key exists but may not make this call |
| `InsufficientCreditsError` | 402 | `insufficient_credits` | Not enough purchased credits |
| `NotFoundError` | 404 | `not_found`, `endpoint_not_found` | Unknown job id, or a wrong `base_url` |
| `FileSizeLimitError` | 413 | `file_size_limit_exceeded`, `file_too_large` | Audio exceeds the plan / endpoint limit |
| `UnsupportedMediaTypeError` | 415 | `unsupported_media`, `missing_audio_stream`, `unsupported_content_type`, … | Media format or content type not accepted |
| `ValidationError` | 400/422 | `invalid_payload`, `invalid_query`, `voice_id_required`, `file_url_unreachable`, … | Bad request values — check `e.issues` |
| ↳ `UnsupportedLanguageError` | 400 | `unsupported_language`, `streaming_unsupported_language` | Language not enabled / not streamable — see `tts.list_languages()` |
| ↳ `UnknownVoiceError` | 422 | `unknown_voice_id` | Voice id matches nothing — see `tts.list_voices()` |
| ↳ `VoiceNotReadyError` | 422 | `voice_not_ready` | Custom voice still processing or failed |
| `RateLimitError` | 429 | `rate_limited` | Per-minute / daily request limit — wait `e.retry_after` |
| ↳ `ConcurrencyLimitError` | 429 | `concurrency_limit_reached` | Plan's processing cap in use — retry or use `mode="async"` |
| ↳ `QueueLimitError` | 429 | `queue_limit_reached` | Too many jobs queued |
| ↳ `StreamConcurrencyError` | 429 | `stream_concurrency_limit` | Concurrent-stream cap in use |
| `ServiceUnavailableError` | 503 | `stream_capacity`, `streaming_unavailable`, `token_service_unavailable`, `file_storage_unavailable`, … | Temporarily unavailable — retry later |
| ↳ `ServiceWarmingError` | 503 | `tts_warming` | Speech engine cold-starting — retry in `e.retry_after`s or use `mode="async"` |
| `ServerError` | 5xx | `synthesis_failed`, `explain_failed`, `internal_error`, … | Server failed while processing — usually retryable |
| `VoiceMakerAPIError` | any | any | Base class of everything above |

Client-side errors (no HTTP exchange happened) also subclass `VoiceMakerError`:

| Class | Code | When |
| :--- | :--- | :--- |
| `ConfigurationError` | `api_key_required`, `credential_required`, `websocket_unavailable` | Missing key / stream credential / `websockets` package |
| `InvalidArgumentError` | `invalid_argument` | An argument was rejected before any request (`e.argument`) |
| `StreamClosedError` | `stream_not_open` | `send_audio()`/`send_text()` on a closed stream |
| `NetworkError` | `network_error` | DNS, refused connection, TLS, proxy (`e.__cause__` is the httpx error) |
| `RequestTimeoutError` | `request_timeout` | No response within `timeout` |
| `PollTimeoutError` (alias `TimeoutError`, deprecated) | `poll_timeout` | `poll()` gave up; the job keeps running (`e.job_id`) |

> `PermissionError` and `TimeoutError` are kept as deprecated aliases for 0.1.x
> compatibility. Prefer `ForbiddenError` / `PollTimeoutError`: importing the
> aliases shadows Python's builtins of the same name.

### Exception attributes

```python
e.code         # stable machine-readable code, e.g. "unknown_voice_id" (or "http_502")
e.method       # SDK method that failed, e.g. "tts.generate"
str(e)         # "tts.generate(): Unknown voice — … [unknown_voice_id · request 8f1c2d3e]"
# API errors (VoiceMakerAPIError and subclasses) additionally expose:
e.status       # HTTP status code
e.error        # Short title from the API
e.detail       # Explanation, with endpoint references rewritten to SDK methods
e.hint         # What to do about it (from the catalog)
e.description  # What the code means (from the catalog)
e.retryable    # Whether repeating the same call later can succeed
e.retry_after  # Seconds to wait, when the API sent Retry-After
e.request_id   # Request id for support (body or X-Request-Id header)
e.issues       # Validation issues [{"field", "code", "message"}] (400/422 only)
e.error_code   # Raw errorCode from the response body (None if the API sent none)
```

### Error-code catalog

`ERROR_CODES`, `CLIENT_ERROR_CODES` and `STREAM_ERROR_CODES` are exported so you
can look codes up (or build your own messages):

```python
from myvoicemaker import ERROR_CODES, describe_error_code, describe_stream_close

ERROR_CODES["tts_warming"].retryable      # True
describe_error_code(e.code).hint          # "Retry in about e.retry_after seconds, or …"
describe_stream_close(4002)               # "Purchased credits were exhausted."
```

The full list with meanings lives on the [Error Codes](https://docs.myvoicemaker.ai/error-codes)
page of the API docs.

### Streaming errors

A refused connection (`asr.stream()` / `tts.stream()`) raises the **same typed
exception a REST call would** — the server's JSON error body (with its
`errorCode`) is read from the rejected handshake, so a missing credit reserve
is an `InsufficientCreditsError`, a used-up token a `StreamTokenError`, and so
on. Errors **during** a session arrive as `StreamError` / `TtsStreamError`
events (`invalid_message`, `text_too_large`, `session_char_limit`,
`insufficient_credits`, `idle_timeout`, `upstream_unavailable`,
`internal_error`); a transport failure that ends the reader thread is kept on
`conn.error`.

---

## Polling Async Jobs

ASR and Animation jobs are processed asynchronously. The SDK's `poll()` helper handles the retry loop for you:

```python
# Submit
job = client.asr.transcribe_file("./audio.mp3", language="en")

# Poll until done
result = client.asr.poll(
    job.job_id,
    interval_seconds=2.0,   # how often to check (default: 2.0)
    timeout_seconds=120.0,  # maximum wait time (default: 120.0)
)
```

Alternatively, manage polling manually:

```python
import time

result = client.asr.get_result(job.job_id)

while result.status in ("queued", "processing"):
    time.sleep(3)
    result = client.asr.get_result(job.job_id)
```

---

## Type Hints

The SDK is fully typed. All response models are plain Python `dataclasses` and all parameters carry type annotations — no stubs or additional packages required.

```python
from myvoicemaker import (
    VoiceMaker,
    # Response models
    TranscriptionJob,
    TtsGenerateResponse,
    AnimateResultResponse,
    VoiceListResponse,
    Voice,
    UsageBalanceResponse,
    UsageBreakdownResponse,
    UsageBreakdownEntry,
    # Literals
    SupportedLanguage,
    JobStatus,
    AccountTier,
    # Errors
    VoiceMakerError,
    VoiceMakerAPIError,
)
```

Editor auto-complete and static analysers (mypy, pyright, Pylance) will surface all fields and parameter types without additional configuration.

---

## Rate Limits

Rate limits are enforced per API key and vary by plan:

| Plan | Requests / min | Concurrent jobs |
| :--- | :--- | :--- |
| Growth | 60 | 5 |
| Pro | 120 | 10 |
| Enterprise | Custom | Custom |

When a limit is exceeded the SDK raises `RateLimitError`. The `Retry-After` header value (seconds) is available as `err.retry_after`.

---

## Credit Costs

| Module | Billable unit | Cost |
| :--- | :--- | :--- |
| TTS | Input characters | 1 credit / character |
| ASR | Audio duration | 5 credits / second |
| Animate | Video duration | 50 credits / second |
| Explain | LLM tokens | 1 credit / token |

---

## License

MIT © [EqualyzAI](https://github.com/equalyzai)
