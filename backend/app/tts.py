"""Azure neural text-to-speech with an on-disk MP3 cache (each text/voice is billed once)."""

import hashlib
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal, Protocol
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

Accent = Literal["us", "uk", "au", "in"]

# Accent → (SSML language, Azure neural voice).
VOICES: dict[Accent, tuple[str, str]] = {
    "us": ("en-US", "en-US-JennyNeural"),
    "uk": ("en-GB", "en-GB-RyanNeural"),
    "au": ("en-AU", "en-AU-NatashaNeural"),
    "in": ("en-IN", "en-IN-PrabhatNeural"),
}
# Slow playback for shadowing; 0.75× speed.
SLOW_RATE = "-25%"
OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
# Attempts for transient failures (429 / 5xx / network) before giving up.
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 20


class TtsError(Exception):
    """Azure TTS failed after retries."""


class Synthesizer(Protocol):
    def synthesize(self, text: str, accent: Accent, is_slow: bool) -> bytes: ...


def build_ssml(text: str, accent: Accent, is_slow: bool) -> str:
    lang, voice = VOICES[accent]
    body = escape(text)
    if is_slow:
        body = f"<prosody rate='{SLOW_RATE}'>{body}</prosody>"
    return f"<speak version='1.0' xml:lang='{lang}'><voice name='{voice}'>{body}</voice></speak>"


class AzureTts:
    def __init__(self, key: str, region: str) -> None:
        self._key = key
        self._url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

    def synthesize(self, text: str, accent: Accent, is_slow: bool) -> bytes:
        request = urllib.request.Request(
            self._url,
            data=build_ssml(text, accent, is_slow).encode("utf-8"),
            method="POST",
            headers={
                "Ocp-Apim-Subscription-Key": self._key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": OUTPUT_FORMAT,
                "User-Agent": "phrasebook-study",
            },
        )
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                if exc.code != 429 and exc.code < 500:
                    raise TtsError(
                        f"azure tts {exc.code} for accent={accent}: {exc.reason}"
                    ) from exc
                last_error = exc
            except urllib.error.URLError as exc:
                last_error = exc
            logger.warning(
                "azure tts retry", extra={"attempt": attempt, "accent": accent, "error": last_error}
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(attempt)
        raise TtsError(f"azure tts failed after {MAX_ATTEMPTS} attempts: {last_error}")


def get_cached_audio(
    cache_dir: Path, synthesizer: Synthesizer, text: str, accent: Accent, is_slow: bool
) -> Path:
    """Return the MP3 path for this text/voice, synthesizing only on a cache miss."""
    key = hashlib.sha256(f"{accent}|{is_slow}|{text}".encode()).hexdigest()
    path = cache_dir / f"{key}.mp3"
    if not path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        audio = synthesizer.synthesize(text, accent, is_slow)
        # Write-then-rename so a crash never leaves a truncated file in the cache.
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(audio)
        tmp.replace(path)
    return path
