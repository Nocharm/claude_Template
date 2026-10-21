"""TTS tests: SSML building, Azure retry behaviour (urlopen mocked), cached endpoint."""

import io
import urllib.error
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import tts
from app.config import Settings
from app.main import create_app
from tests.conftest import FakeExtractor


class FakeSynthesizer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bool]] = []

    def synthesize(self, text: str, accent: str, is_slow: bool) -> bytes:
        self.calls.append((text, accent, is_slow))
        return b"ID3-fake-mp3"


def make_client(tmp_path: Path, synthesizer: FakeSynthesizer | None) -> TestClient:
    settings = Settings(data_dir=tmp_path / "data", anthropic_api_key="", azure_speech_key="")
    app = create_app(
        settings, extractor_factory=lambda _: FakeExtractor(), tts_factory=lambda _: synthesizer
    )
    return TestClient(app)


def test_build_ssml_escapes_text_and_slows_down() -> None:
    ssml = tts.build_ssml('Tom & "Jerry" <3', "uk", is_slow=True)

    assert "<voice name='en-GB-RyanNeural'>" in ssml
    assert "xml:lang='en-GB'" in ssml
    assert "<prosody rate='-25%'>Tom &amp; \"Jerry\" &lt;3</prosody>" in ssml


def test_azure_tts_retries_server_errors_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: two 503s, then audio
    responses = [
        urllib.error.HTTPError("u", 503, "busy", {}, None),
        urllib.error.HTTPError("u", 503, "busy", {}, None),
        io.BytesIO(b"mp3"),
    ]

    def fake_urlopen(request, timeout):
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(tts.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(tts.time, "sleep", lambda _: None)

    # Act
    audio = tts.AzureTts("key", "koreacentral").synthesize("hi", "us", is_slow=False)

    # Assert
    assert audio == b"mp3"
    assert responses == []


def test_azure_tts_does_not_retry_auth_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request)
        raise urllib.error.HTTPError("u", 401, "unauthorized", {}, None)

    monkeypatch.setattr(tts.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(tts.TtsError, match="401"):
        tts.AzureTts("bad", "koreacentral").synthesize("hi", "au", is_slow=False)
    assert len(calls) == 1
    assert calls[0].full_url == "https://koreacentral.tts.speech.microsoft.com/cognitiveservices/v1"


def test_tts_endpoint_caches_audio_per_text_and_voice(tmp_path: Path) -> None:
    # Arrange
    synthesizer = FakeSynthesizer()

    with make_client(tmp_path, synthesizer) as client:
        # Act
        first = client.get("/api/tts", params={"text": "I'm down!", "accent": "au"})
        again = client.get("/api/tts", params={"text": "I'm down!", "accent": "au"})
        slow = client.get("/api/tts", params={"text": "I'm down!", "accent": "au", "slow": True})

    # Assert
    assert first.status_code == 200
    assert first.headers["content-type"] == "audio/mpeg"
    assert first.content == b"ID3-fake-mp3"
    assert again.content == first.content
    assert slow.status_code == 200
    assert synthesizer.calls == [("I'm down!", "au", False), ("I'm down!", "au", True)]


def test_tts_endpoint_validates_input_and_reports_missing_key(tmp_path: Path) -> None:
    with make_client(tmp_path, None) as client:
        assert client.get("/api/tts", params={"text": "hi"}).status_code == 503
    with make_client(tmp_path, FakeSynthesizer()) as client:
        assert client.get("/api/tts", params={"text": "hi", "accent": "fr"}).status_code == 422
        assert client.get("/api/tts", params={"text": ""}).status_code == 422
