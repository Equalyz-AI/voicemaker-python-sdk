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

| Language | Code | Auto-detect (ASR) |
| :--- | :--- | :---: |
| Yoruba | `yo` | ✓ |
| Igbo | `ig` | ✓ |
| Hausa | `ha` | ✓ |
| Nigerian Pidgin | `pcm` | ✓ |
| English | `en` | ✓ |
| Auto-detect | `auto` | — |

---

## Modules

### Text-to-Speech (TTS)

Convert text into natural-sounding speech. Requests are **synchronous** — the audio URL is returned immediately.

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
| `language` | `str` (optional) | Filter by language code: `yo`, `ig`, `ha`, `pcm`, `en` |

**Returns** `VoiceListResponse`

| Field | Type |
| :--- | :--- |
| `voices` | `list[Voice]` |

Each `Voice` has: `id`, `name`, `gender`, `language`, `style`, `sample_url`.

---

#### `client.tts.generate(text, voice_id, language, *, speed=None, output_format=None)`

```python
result = client.tts.generate(
    text="Nne, ka anyị bido oge a.",
    voice_id="sunday-okafor-male-conversational",
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
| `language` | `str` | ✓ | Language code |
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

> **Note:** This module targets a planned endpoint. Check the [changelog](https://myvoicemaker.ai/docs/changelog) for availability.

#### `client.explain.process(text, language, action, *, target_language=None, max_tokens=None)`

```python
result = client.explain.process(
    text="Ìwé Mímọ̀ sọ pé...",
    language="yo",
    action="translate",
    target_language="en",
    max_tokens=500,
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
| `max_tokens` | `int` | | Response length limit: 1–2000 (default `500`) |

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

Every API error is raised as a typed exception that subclasses `VoiceMakerAPIError`.

```python
from myvoicemaker import (
    VoiceMakerError,
    AuthenticationError,
    InsufficientCreditsError,
    RateLimitError,
    ValidationError,
    NotFoundError,
    TimeoutError,
)

try:
    result = client.tts.generate(...)
except AuthenticationError:
    print("Invalid or expired API key")
except InsufficientCreditsError:
    print("Not enough credits. Top up at myvoicemaker.ai/billing")
except RateLimitError as e:
    wait = e.retry_after or 60
    print(f"Rate limited. Retry in {wait}s")
except ValidationError as e:
    print("Invalid parameters:", e.issues)
except TimeoutError as e:
    print(f"Job {e.job_id} timed out after {e.timeout_seconds}s")
except VoiceMakerError as e:
    print(f"API error {e.status}: {e.detail}")
```

### Exception classes

| Class | HTTP Status | Description |
| :--- | :--- | :--- |
| `AuthenticationError` | 401 | Missing or invalid API key |
| `InsufficientCreditsError` | 402 | Insufficient purchased credits |
| `PermissionError` | 403 | Key lacks required scope or plan |
| `NotFoundError` | 404 | Resource not found |
| `FileSizeLimitError` | 413 | Audio file exceeds plan size limit |
| `UnsupportedMediaTypeError` | 415 | Unsupported file format |
| `ValidationError` | 422 | Invalid request parameters (check `.issues`) |
| `RateLimitError` | 429 | Rate limit or concurrency limit exceeded |
| `ServerError` | 500/503 | Internal server error |
| `TimeoutError` | — | `poll()` timed out waiting for job completion |

All HTTP exception classes expose:

```python
e.status      # HTTP status code (int)
e.error       # Short error title from the API
e.detail      # Human-readable explanation
e.request_id  # Request ID for support (from X-Request-Id header)
e.issues      # List of validation issue dicts (ValidationError only)
```

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

MIT © [Collins Edim](https://github.com/equalyzai)
