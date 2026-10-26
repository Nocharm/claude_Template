"""Character studio tests: create → revise → finalize → appears in comics (fake painter)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.comics import build_cast_script_model
from tests.test_comics import FakePainter, FakeWriter, _build_client


@pytest.fixture
def studio(tmp_path: Path, sample_pdf: Path):
    writer, painter = FakeWriter(), FakePainter()
    client = _build_client(tmp_path, sample_pdf, writer, painter)
    yield client, writer, painter
    client.__exit__(None, None, None)


def test_default_cast_is_seeded_without_sheets(studio) -> None:
    client, _, _ = studio

    characters = client.get("/api/characters").json()

    assert [(c["name"], c["status"], c["image_url"]) for c in characters] == [
        ("Mina", "active", None),
        ("Jun", "active", None),
    ]


def test_create_revise_finalize_then_cast_in_comic(studio) -> None:
    client, writer, painter = studio

    # Act: create a draft from a prompt
    created = client.post(
        "/api/characters",
        json={"name": "Sora", "appearance": "Mina's cheerful coworker, long wavy red hair"},
    )
    sora_id = created.json()["id"]

    # Assert: draft with v1, drawn without references
    assert created.status_code == 201
    assert (created.json()["status"], created.json()["version_count"]) == ("draft", 1)
    assert painter.reference_counts == [0]
    assert "Sora" in painter.prompts[0]

    # Act: revise v1 with a change request
    revised = client.post(
        f"/api/characters/{sora_id}/versions",
        json={"base_version": 1, "instruction": "add round glasses"},
    ).json()

    # Assert: v2 drawn from v1 as reference
    assert [v["no"] for v in revised["versions"]] == [1, 2]
    assert revised["versions"][1]["instruction"] == "add round glasses"
    assert painter.reference_counts[-1] == 1
    assert "add round glasses" in painter.prompts[-1]

    # Act: finalize v2, then draw an episode
    final = client.post(f"/api/characters/{sora_id}/finalize", json={"version": 2}).json()
    client.post("/api/comics")

    # Assert: Sora joined the cast with v2 as the sheet
    assert (final["status"], final["final_version"]) == ("active", 2)
    assert final["image_url"].endswith("/versions/2/image")
    assert client.get(final["image_url"]).status_code == 200
    assert writer.cast_names == ["Mina", "Jun", "Sora"]


def test_resting_characters_leave_the_cast(studio) -> None:
    client, writer, _ = studio
    jun = client.get("/api/characters").json()[1]

    rested = client.post(f"/api/characters/{jun['id']}/status", json={"status": "resting"})
    client.post("/api/comics")

    assert rested.json()["status"] == "resting"
    assert writer.cast_names == ["Mina"]


def test_draft_cannot_join_cast_before_finalizing(studio) -> None:
    client, _, _ = studio
    draft = client.post("/api/characters", json={"name": "Hana", "appearance": "student"}).json()

    response = client.post(f"/api/characters/{draft['id']}/status", json={"status": "active"})

    assert response.status_code == 409


def test_studio_errors(tmp_path: Path, sample_pdf: Path) -> None:
    # Painter failure → 502; validation → 422; no Gemini key → 503
    failing = _build_client(tmp_path / "a", sample_pdf, FakeWriter(), FakePainter(fail_on_call=1))
    assert failing.post("/api/characters", json={"name": "X", "appearance": "y"}).status_code == 502
    assert failing.post("/api/characters", json={"name": "", "appearance": "y"}).status_code == 422
    assert failing.get("/api/characters").json()[-1]["name"] == "Jun"  # nothing half-created
    failing.__exit__(None, None, None)

    disabled = _build_client(tmp_path / "b", sample_pdf, FakeWriter(), None)
    assert (
        disabled.post("/api/characters", json={"name": "X", "appearance": "y"}).status_code == 503
    )
    disabled.__exit__(None, None, None)


def test_cast_script_model_only_accepts_cast_ids() -> None:
    model = build_cast_script_model(["c1", "c3"])
    panel = {"scene_en": "x", "characters": ["c1"], "bubbles": []}

    model.model_validate({"title_ko": "t", "panels": [panel]})
    with pytest.raises(ValidationError):
        model.model_validate({"title_ko": "t", "panels": [{**panel, "characters": ["c2"]}]})
