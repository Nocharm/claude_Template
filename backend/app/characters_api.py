"""Character studio endpoints: create from a prompt, revise, pick a version, toggle in the cast."""

import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app import characters
from app import comics_repository as store
from app.gemini import ImageGenerationError, Painter


class CreateCharacterIn(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    appearance: str = Field(min_length=1, max_length=500)


class ReviseIn(BaseModel):
    base_version: int
    instruction: str = Field(min_length=1, max_length=300)


class FinalizeIn(BaseModel):
    version: int


class StatusIn(BaseModel):
    status: Literal["active", "resting"]


class VersionOut(BaseModel):
    no: int
    instruction: str
    image_url: str


class CharacterSummary(BaseModel):
    id: int
    name: str
    appearance: str
    status: str  # draft | active | resting
    final_version: int | None
    image_url: str | None
    version_count: int


class CharacterDetail(CharacterSummary):
    versions: list[VersionOut]


def version_url(character_id: int, no: int) -> str:
    return f"/api/characters/{character_id}/versions/{no}/image"


def build_characters_router(
    get_conn: Callable[[], Iterator[sqlite3.Connection]],
    painter: Painter | None,
    characters_dir: Path,
) -> APIRouter:
    router = APIRouter(prefix="/api/characters")

    def require_painter() -> Painter:
        if painter is None:
            raise HTTPException(503, "image generation is disabled (set GEMINI_API_KEY)")
        return painter

    def to_summary(row: sqlite3.Row, version_count: int) -> CharacterSummary:
        # Show the finalized sheet; for a draft, its latest attempt.
        shown = row["final_version"] or (version_count or None)
        return CharacterSummary(
            id=row["id"],
            name=row["name"],
            appearance=row["appearance"],
            status=row["status"],
            final_version=row["final_version"],
            version_count=version_count,
            image_url=version_url(row["id"], shown) if shown else None,
        )

    def get_detail_or_404(conn: sqlite3.Connection, character_id: int) -> CharacterDetail:
        row = store.get_character(conn, character_id)
        if row is None:
            raise HTTPException(404, f"character {character_id} not found")
        versions = store.list_versions(conn, character_id)
        return CharacterDetail(
            **to_summary(row, len(versions)).model_dump(),
            versions=[
                VersionOut(
                    no=v["no"],
                    instruction=v["instruction"],
                    image_url=version_url(character_id, v["no"]),
                )
                for v in versions
            ],
        )

    def run_painting(action: Callable[[], object]) -> object:
        try:
            return action()
        except ImageGenerationError as exc:
            raise HTTPException(502, f"drawing failed: {exc}") from exc
        except characters.CharacterError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.get("")
    def list_characters(conn: sqlite3.Connection = Depends(get_conn)) -> list[CharacterSummary]:
        return [to_summary(r, r["version_count"]) for r in store.list_characters(conn)]

    @router.post("", status_code=201)
    def create_character(
        body: CreateCharacterIn, conn: sqlite3.Connection = Depends(get_conn)
    ) -> CharacterDetail:
        active_painter = require_painter()
        character_id = run_painting(
            lambda: characters.create_character(
                conn, active_painter, characters_dir, body.name.strip(), body.appearance.strip()
            )
        )
        return get_detail_or_404(conn, character_id)

    @router.get("/{character_id}")
    def get_character(
        character_id: int, conn: sqlite3.Connection = Depends(get_conn)
    ) -> CharacterDetail:
        return get_detail_or_404(conn, character_id)

    @router.post("/{character_id}/versions", status_code=201)
    def revise_character(
        character_id: int, body: ReviseIn, conn: sqlite3.Connection = Depends(get_conn)
    ) -> CharacterDetail:
        active_painter = require_painter()
        get_detail_or_404(conn, character_id)
        run_painting(
            lambda: characters.revise_character(
                conn,
                active_painter,
                characters_dir,
                character_id,
                body.base_version,
                body.instruction.strip(),
            )
        )
        return get_detail_or_404(conn, character_id)

    @router.post("/{character_id}/finalize")
    def finalize_character(
        character_id: int, body: FinalizeIn, conn: sqlite3.Connection = Depends(get_conn)
    ) -> CharacterDetail:
        get_detail_or_404(conn, character_id)
        run_painting(lambda: characters.finalize_character(conn, character_id, body.version))
        return get_detail_or_404(conn, character_id)

    @router.post("/{character_id}/status")
    def set_status(
        character_id: int, body: StatusIn, conn: sqlite3.Connection = Depends(get_conn)
    ) -> CharacterDetail:
        detail = get_detail_or_404(conn, character_id)
        if detail.final_version is None and body.status == "active":
            raise HTTPException(409, "finalize a version before adding the character to the cast")
        store.set_character_status(conn, character_id, body.status)
        return get_detail_or_404(conn, character_id)

    @router.get("/{character_id}/versions/{no}/image")
    def get_version_image(
        character_id: int, no: int, conn: sqlite3.Connection = Depends(get_conn)
    ) -> FileResponse:
        version = store.get_version(conn, character_id, no)
        if version is None:
            raise HTTPException(404, f"version {no} of character {character_id} not found")
        path = characters.get_character_dir(characters_dir, character_id) / version["image_file"]
        headers = {"Cache-Control": "public, max-age=31536000, immutable"}
        return FileResponse(path, media_type="image/png", headers=headers)

    return router
