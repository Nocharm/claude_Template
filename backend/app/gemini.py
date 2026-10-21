"""Gemini image generation over REST (stdlib HTTP; no SDK needed for one endpoint)."""

import base64
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# Transient failures (429 / 5xx / network) are retried; image calls can take ~10–30 s.
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 120


class ImageGenerationError(Exception):
    """Gemini returned no image after retries (or refused the prompt)."""


@dataclass
class ReferenceImage:
    mime_type: str
    data: bytes


class Painter(Protocol):
    def paint(self, prompt: str, references: list[ReferenceImage]) -> bytes: ...


def build_request_body(prompt: str, references: list[ReferenceImage]) -> dict:
    parts: list[dict] = [
        {"inlineData": {"mimeType": r.mime_type, "data": base64.b64encode(r.data).decode()}}
        for r in references
    ]
    parts.append({"text": prompt})
    return {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }


def extract_image(response: dict) -> bytes:
    for candidate in response.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    reasons = [c.get("finishReason") for c in response.get("candidates", [])]
    feedback = response.get("promptFeedback")
    raise ImageGenerationError(f"no image in response (finish={reasons}, feedback={feedback})")


class GeminiPainter:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._url = f"{API_BASE}/{model}:generateContent"

    def paint(self, prompt: str, references: list[ReferenceImage]) -> bytes:
        request = urllib.request.Request(
            self._url,
            data=json.dumps(build_request_body(prompt, references)).encode(),
            method="POST",
            headers={"x-goog-api-key": self._api_key, "Content-Type": "application/json"},
        )
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                    return extract_image(json.load(response))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:300]
                if exc.code != 429 and exc.code < 500:
                    raise ImageGenerationError(f"gemini {exc.code}: {detail}") from exc
                last_error = exc
            except urllib.error.URLError as exc:
                last_error = exc
            logger.warning("gemini retry", extra={"attempt": attempt, "error": last_error})
            if attempt < MAX_ATTEMPTS:
                time.sleep(5 * attempt)
        raise ImageGenerationError(f"gemini failed after {MAX_ATTEMPTS} attempts: {last_error}")
