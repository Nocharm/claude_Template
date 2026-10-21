"""Study API tests: queue → check → grade → progress, plus AI examples/feedback (fakes)."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.study import DAILY_GOAL
from tests.conftest import FakeCoach, FakeExtractor


class Clock:
    def __init__(self, today: date) -> None:
        self.today = today

    def __call__(self) -> date:
        return self.today


@pytest.fixture
def clock() -> Clock:
    return Clock(date(2026, 10, 21))


@pytest.fixture
def client(tmp_path: Path, sample_pdf: Path, clock: Clock) -> TestClient:
    settings = Settings(data_dir=tmp_path / "data", anthropic_api_key="")
    app = create_app(
        settings,
        extractor_factory=lambda _: FakeExtractor(),
        coach_factory=lambda _: FakeCoach(),
        clock=clock,
    )
    with TestClient(app) as test_client:
        with sample_pdf.open("rb") as f:
            test_client.post("/api/books", files={"file": ("book.pdf", f, "application/pdf")})
        yield test_client


def answer_all(client: TestClient, grade: str = "good") -> list[dict]:
    queue = client.get("/api/study/queue").json()
    return [
        client.post(f"/api/study/{item['expression_id']}/grade", json={"grade": grade}).json()
        for item in queue["items"]
    ]


def test_queue_starts_with_new_cards_in_book_order(client: TestClient) -> None:
    queue = client.get("/api/study/queue").json()

    # 8 reading points exist (< DAILY_GOAL), so all are offered as new cards.
    assert len(queue["items"]) == 8
    assert all(item["is_new"] for item in queue["items"])
    assert [i["day_no"] for i in queue["items"]] == [3] * 7 + [4]
    assert queue["today"] == {
        "date": "2026-10-21",
        "answered": 0,
        "goal": DAILY_GOAL,
        "goal_met": False,
        "xp_today": 0,
    }


def test_check_grades_cloze_answer_without_side_effects(client: TestClient) -> None:
    # Arrange
    item = client.get("/api/study/queue").json()["items"][2]  # "spot" → cloze on "spotted"
    assert item["kind"] == "cloze" and "____" in item["prompt_en"]

    # Act
    wrong = client.post(f"/api/study/{item['expression_id']}/check", json={"answer": "spot"})
    right = client.post(f"/api/study/{item['expression_id']}/check", json={"answer": "Spotted"})

    # Assert
    assert wrong.json() == {
        "is_correct": False,
        "expected": "spotted",
        "meaning_ko": "(우연히) 발견하다, 보다",
    }
    assert right.json()["is_correct"] is True
    assert client.get("/api/study/queue").json()["today"]["answered"] == 0


def test_grading_awards_xp_schedules_cards_and_tracks_goal(
    client: TestClient, clock: Clock
) -> None:
    # Act: day 1 — answer all 8 new cards correctly
    results = answer_all(client)

    # Assert: new (+5) + correct (+10) each; goal of 15 not reached with 8 answers
    assert [r["xp_gained"] for r in results] == [15] * 8
    assert results[-1]["today"]["answered"] == 8
    assert results[-1]["next_due"] == "2026-10-22"
    assert client.get("/api/study/queue").json()["items"] == []

    # Day 2: all 8 due again; wrong answers come back the same day
    clock.today += timedelta(days=1)
    queue = client.get("/api/study/queue").json()["items"]
    assert len(queue) == 8 and not any(i["is_new"] for i in queue)
    again = client.post(f"/api/study/{queue[0]['expression_id']}/grade", json={"grade": "again"})
    assert again.json()["xp_gained"] == 0
    assert again.json()["next_due"] == "2026-10-22"


def test_goal_bonus_stamp_and_progress_calendar(client: TestClient, clock: Clock) -> None:
    # Arrange: reach 15 answers today (8 new + 7 retries of "again" cards)
    answer_all(client, grade="again")
    retry = client.get("/api/study/queue").json()["items"][:7]
    results = [
        client.post(f"/api/study/{i['expression_id']}/grade", json={"grade": "good"}).json()
        for i in retry
    ]

    # Assert: 15th answer gets the one-time goal bonus
    assert results[-1]["goal_just_met"] is True
    assert results[-1]["xp_gained"] == 10 + 30

    progress = client.get("/api/study/progress").json()
    assert progress["today"]["goal_met"] is True
    assert progress["streak_days"] == 1
    assert progress["month"] == "2026-10"
    statuses = {d["date"]: d["status"] for d in progress["calendar"]}
    assert statuses["2026-10-21"] == "met"
    assert statuses["2026-10-22"] == "future"
    assert statuses["2026-10-20"] == "none"
    assert progress["xp_total"] == 8 * 5 + 7 * 10 + 30
    assert progress["level"] == 2


def test_progress_rejects_bad_month(client: TestClient) -> None:
    assert client.get("/api/study/progress?month=oct").status_code == 400


def test_applications_and_feedback(client: TestClient) -> None:
    # Arrange
    spot_id = client.get("/api/study/queue").json()["items"][2]["expression_id"]

    # Act
    created = client.post(f"/api/expressions/{spot_id}/applications", json={"scenario": "work"})
    listed = client.get(f"/api/expressions/{spot_id}/applications")
    good = client.post(f"/api/expressions/{spot_id}/feedback", json={"sentence": "I spot it."})
    off = client.post(f"/api/expressions/{spot_id}/feedback", json={"sentence": "Hello there."})

    # Assert
    assert created.status_code == 201
    assert created.json()[0]["scenario_label"] == "회사"
    assert listed.json() == created.json()
    assert good.json()["xp_gained"] == 15
    assert off.json()["xp_gained"] == 0
    bad = client.post(f"/api/expressions/{spot_id}/applications", json={"scenario": "space"})
    assert bad.status_code == 422
