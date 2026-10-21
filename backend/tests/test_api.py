"""API tests: upload → background ingest (fake extractor) → reading endpoints."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import FakeExtractor


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(data_dir=tmp_path / "data", anthropic_api_key="")
    app = create_app(settings, extractor_factory=lambda _: FakeExtractor())
    with TestClient(app) as test_client:
        yield test_client


def upload(client: TestClient, pdf_path: Path):
    with pdf_path.open("rb") as f:
        return client.post("/api/books", files={"file": ("가브리엘.pdf", f, "application/pdf")})


def test_upload_rejects_non_pdf(client: TestClient) -> None:
    response = client.post("/api/books", files={"file": ("notes.txt", b"hello", "text/plain")})

    assert response.status_code == 400
    assert "notes.txt" in response.json()["detail"]


def test_upload_ingests_once_and_dedupes_same_file(client: TestClient, sample_pdf: Path) -> None:
    # Act
    first = upload(client, sample_pdf)
    second = upload(client, sample_pdf)

    # Assert: TestClient runs the background ingest before returning
    assert first.status_code == 201
    assert first.json()["title"] == "가브리엘"
    book_id = first.json()["id"]
    assert client.get(f"/api/books/{book_id}").json()["status"] == "done"
    assert second.status_code == 200
    assert second.json()["id"] == book_id
    assert len(client.get("/api/books").json()) == 1


def test_reading_endpoints_return_day_and_expression_graph(
    client: TestClient, sample_pdf: Path
) -> None:
    # Arrange
    book_id = upload(client, sample_pdf).json()["id"]

    # Act
    days = client.get(f"/api/books/{book_id}/days").json()
    day3 = client.get(f"/api/days/{days[0]['id']}").json()
    spot = next(e for s in day3["sentences"] for e in s["expressions"] if e["text"] == "spot")
    detail = client.get(f"/api/expressions/{spot['id']}").json()

    # Assert
    assert [d["day_no"] for d in days] == [3, 4]
    assert day3["title"] == "Scooter Ride Turned Rainy Adventure"
    assert day3["prev_day_id"] is None and day3["next_day_id"] == days[1]["id"]
    assert spot["highlight"] == "spotted"
    assert detail["sentence"]["no"] == 1
    assert detail["examples"][0]["text_en"].startswith("I spotted")
    assert {r["text"] for r in detail["related"] if r["type"] == "similar"} == {
        "notice",
        "catch sight of",
    }


def test_missing_resources_return_404(client: TestClient) -> None:
    assert client.get("/api/books/1").status_code == 404
    assert client.get("/api/days/1").status_code == 404
    assert client.get("/api/expressions/1").status_code == 404


def test_retry_only_allowed_for_failed_books(client: TestClient, sample_pdf: Path) -> None:
    book_id = upload(client, sample_pdf).json()["id"]

    response = client.post(f"/api/books/{book_id}/retry")

    assert response.status_code == 409


def test_concurrent_requests_share_no_connection_errors(
    client: TestClient, sample_pdf: Path
) -> None:
    # Regression: dependency and endpoint run on different threadpool threads.
    upload(client, sample_pdf)
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda _: client.get("/api/books").status_code, range(40)))

    assert set(statuses) == {200}
