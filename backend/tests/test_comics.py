"""Webtoon tests: schedule math, Gemini payloads, and the episode pipeline with fakes."""

import base64
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app import gemini
from app.characters import CastMember
from app.comics import ComicScript, get_latest_slot, get_next_slot
from app.config import Settings
from app.extraction import ExpressionBrief
from app.main import create_app
from tests.conftest import FakeExtractor

KST = ZoneInfo("Asia/Seoul")


class FakeWriter:
    def __init__(self) -> None:
        self.calls = 0

    def write(self, expressions: list[ExpressionBrief], cast: list[CastMember]) -> ComicScript:
        self.calls += 1
        self.cast_names = [m.name for m in cast]
        keys = [m.key for m in cast]
        first = expressions[0].text
        return ComicScript.model_validate(
            {
                "title_ko": "비 오는 스쿠터 데이트",
                "panels": [
                    {
                        "scene_en": f"Scene {i}: Mina and Jun on scooters.",
                        "characters": keys[:2] if i % 2 else keys[:1],
                        "bubbles": [
                            {
                                "speaker": keys[0],
                                "text_en": f"Line {i} with {first}.",
                                "text_ko": f"대사 {i}",
                                "highlight": first,
                            }
                        ],
                    }
                    for i in range(1, 11)
                ],
            }
        )


class FakePainter:
    def __init__(self, fail_on_call: int | None = None) -> None:
        self.prompts: list[str] = []
        self.reference_counts: list[int] = []
        self.fail_on_call = fail_on_call

    def paint(self, prompt: str, references: list[gemini.ReferenceImage]) -> bytes:
        self.prompts.append(prompt)
        self.reference_counts.append(len(references))
        if len(self.prompts) == self.fail_on_call:
            raise gemini.ImageGenerationError("simulated safety block")
        return b"\x89PNG-fake"


@pytest.fixture
def make_client(tmp_path: Path, sample_pdf: Path):
    clients: list[TestClient] = []

    def build(writer: FakeWriter, painter: FakePainter | None) -> TestClient:
        client = _build_client(tmp_path, sample_pdf, writer, painter)
        clients.append(client)
        return client

    yield build
    for client in clients:
        client.__exit__(None, None, None)


def _build_client(
    tmp_path: Path, sample_pdf: Path, writer: FakeWriter, painter: FakePainter | None
) -> TestClient:
    settings = Settings(data_dir=tmp_path / "data", anthropic_api_key="", gemini_api_key="")
    app = create_app(
        settings,
        extractor_factory=lambda _: FakeExtractor(),
        writer_factory=lambda _: writer,
        painter_factory=lambda _: painter,
        comic_runner=lambda job: job(),  # run inline so tests see the finished episode
        is_scheduler_enabled=False,
    )
    client = TestClient(app)
    client.__enter__()
    with sample_pdf.open("rb") as f:
        client.post("/api/books", files={"file": ("book.pdf", f, "application/pdf")})
    return client


def test_schedule_slots_are_mon_wed_fri_at_3am() -> None:
    wed_morning = datetime(2026, 10, 21, 10, 0, tzinfo=KST)
    tue_night = datetime(2026, 10, 20, 2, 0, tzinfo=KST)

    assert get_latest_slot(wed_morning) == datetime(2026, 10, 21, 3, 0, tzinfo=KST)
    assert get_next_slot(wed_morning) == datetime(2026, 10, 23, 3, 0, tzinfo=KST)
    assert get_latest_slot(tue_night) == datetime(2026, 10, 19, 3, 0, tzinfo=KST)
    assert get_next_slot(tue_night) == datetime(2026, 10, 21, 3, 0, tzinfo=KST)


def test_gemini_request_and_response_parsing() -> None:
    # Arrange
    body = gemini.build_request_body("draw", [gemini.ReferenceImage("image/png", b"ref")])
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "here"},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": base64.b64encode(b"img").decode(),
                            }
                        },
                    ]
                }
            }
        ]
    }

    # Act / Assert
    assert (
        body["contents"][0]["parts"][0]["inlineData"]["data"] == base64.b64encode(b"ref").decode()
    )
    assert body["contents"][0]["parts"][-1] == {"text": "draw"}
    assert body["generationConfig"] == {"responseModalities": ["IMAGE"]}
    assert gemini.extract_image(response) == b"img"
    with pytest.raises(gemini.ImageGenerationError, match="SAFETY"):
        gemini.extract_image({"candidates": [{"finishReason": "SAFETY", "content": {}}]})


def test_episode_is_written_drawn_and_read_once(make_client) -> None:
    # Arrange
    writer, painter = FakeWriter(), FakePainter()
    client = make_client(writer, painter)

    # Act
    created = client.post("/api/comics")
    detail = client.get(f"/api/comics/{created.json()['id']}").json()
    image = client.get(detail["panels"][0]["image_url"])
    first_read = client.post(f"/api/comics/{detail['id']}/read").json()
    second_read = client.post(f"/api/comics/{detail['id']}/read").json()

    # Assert
    assert created.status_code == 202
    assert (detail["status"], detail["panels_done"], detail["title_ko"]) == (
        "done",
        10,
        "비 오는 스쿠터 데이트",
    )
    assert len(detail["expressions"]) == 6
    assert detail["panels"][0]["bubbles"][0]["highlight"] in {
        e["text"] for e in detail["expressions"]
    }
    assert image.status_code == 200 and image.content == b"\x89PNG-fake"
    # 2 character sheets (no references) + 10 panels with 1–2 references each
    assert painter.reference_counts[:2] == [0, 0]
    assert len(painter.prompts) == 12
    assert "no text" in painter.prompts[2].lower()
    assert (first_read, second_read) == ({"xp_gained": 10}, {"xp_gained": 0})


def test_failed_episode_resumes_without_rewriting_or_redrawing(make_client) -> None:
    # Arrange: 2 character sheets + 3 panels succeed, 4th panel fails
    writer, painter = FakeWriter(), FakePainter(fail_on_call=6)
    client = make_client(writer, painter)
    with pytest.raises(gemini.ImageGenerationError):
        client.post("/api/comics")
    comic = client.get("/api/comics").json()[0]
    assert (comic["status"], comic["panels_done"]) == ("failed", 3)
    assert "safety" in comic["error"]

    # Act
    retried = client.post(f"/api/comics/{comic['id']}/retry")

    # Assert: script reused, character sheets reused, only panels 4–10 drawn
    assert retried.status_code == 202
    assert client.get(f"/api/comics/{comic['id']}").json()["status"] == "done"
    assert writer.calls == 1
    assert len(painter.prompts) == 6 + 7


def test_comics_disabled_without_gemini_key(make_client) -> None:
    client = make_client(FakeWriter(), None)

    assert client.post("/api/comics").status_code == 503
    assert client.get("/api/comics").json() == []


def test_catch_up_draws_a_missed_slot_only_once(tmp_path: Path, sample_pdf: Path) -> None:
    # Arrange: server "wakes up" Wednesday 10:00, after the 03:00 slot was missed
    from app import db
    from app.comics_api import ComicService

    client = _build_client(tmp_path, sample_pdf, FakeWriter(), FakePainter())
    db_path = tmp_path / "data" / "app.db"
    painter = FakePainter()
    service = ComicService(
        lambda: db.connect(db_path),
        tmp_path / "data" / "comics",
        FakeWriter,
        painter,
        lambda: datetime(2026, 10, 21, 10, 0, tzinfo=KST),
        runner=lambda job: job(),
    )

    # Act
    service.run_due_catch_up()
    service.run_due_catch_up()

    # Assert
    assert len(client.get("/api/comics").json()) == 1
    client.__exit__(None, None, None)
