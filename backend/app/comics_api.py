"""Webtoon endpoints, the job runner, and the Mon/Wed/Fri 03:00 scheduler."""

import asyncio
import logging
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import comics_repository as store
from app import study_repository
from app.comics import (
    EXPRESSIONS_PER_COMIC,
    PANEL_COUNT,
    Bubble,
    PanelScript,
    Writer,
    generate_comic,
    get_latest_slot,
    get_next_slot,
)
from app.gemini import Painter
from app.study import XP_COMIC_READ

logger = logging.getLogger(__name__)

Runner = Callable[[Callable[[], None]], None]


def run_in_thread(job: Callable[[], None]) -> None:
    threading.Thread(target=job, daemon=True).start()


class ComicService:
    """Starts at most one episode at a time, from the API or the scheduler."""

    def __init__(
        self,
        conn_factory: Callable[[], sqlite3.Connection],
        comics_dir: Path,
        writer_factory: Callable[[], Writer],
        painter: Painter | None,
        get_now: Callable[[], datetime],
        runner: Runner = run_in_thread,
    ) -> None:
        self._conn_factory = conn_factory
        self._comics_dir = comics_dir
        self._writer_factory = writer_factory
        self._painter = painter
        self._get_now = get_now
        self._runner = runner
        self._lock = threading.Lock()

    @property
    def is_enabled(self) -> bool:
        return self._painter is not None

    def _launch(self, comic_id: int) -> None:
        painter = self._painter
        assert painter is not None

        def job() -> None:
            generate_comic(
                self._conn_factory, comic_id, self._comics_dir, self._writer_factory(), painter
            )

        self._runner(job)

    def start_new(self) -> int | None:
        """Create and launch an episode; None if one is already in progress."""
        with self._lock, closing(self._conn_factory()) as conn:
            if store.has_active_comic(conn):
                return None
            ids = store.pick_expression_ids(conn, EXPRESSIONS_PER_COMIC)
            comic_id = store.create_comic(conn, self._get_now(), ids)
        self._launch(comic_id)
        return comic_id

    def retry(self, comic_id: int) -> None:
        with self._lock, closing(self._conn_factory()) as conn:
            store.update_comic(conn, comic_id, status="queued", error=None)
        self._launch(comic_id)

    def run_due_catch_up(self) -> None:
        """Draw the latest scheduled episode if the server was off at that time."""
        with closing(self._conn_factory()) as conn:
            is_missed = not store.has_comic_since(conn, get_latest_slot(self._get_now()))
        if is_missed:
            logger.info("catching up missed comic slot")
            self.start_new()


async def run_comic_scheduler(service: ComicService, get_now: Callable[[], datetime]) -> None:
    service.run_due_catch_up()
    while True:
        now = get_now()
        await asyncio.sleep((get_next_slot(now) - now).total_seconds())
        try:
            service.start_new()
        except Exception:
            # Keep the scheduler alive for the next slot; the failure is logged with traceback.
            logger.exception("scheduled comic failed to start")


class ComicSummary(BaseModel):
    id: int
    created_at: datetime
    status: str
    title_ko: str
    panels_done: int
    panel_count: int
    error: str | None
    cover_url: str | None
    is_read: bool


class PanelOut(BaseModel):
    no: int
    image_url: str | None
    bubbles: list[Bubble]


class ComicExpression(BaseModel):
    id: int
    text: str
    meaning_ko: str


class ComicDetail(ComicSummary):
    expressions: list[ComicExpression]
    panels: list[PanelOut]


def panel_url(comic_id: int, no: int) -> str:
    return f"/api/comics/{comic_id}/panels/{no}"


def build_comics_router(
    get_conn: Callable[[], Iterator[sqlite3.Connection]],
    service: ComicService,
    comics_dir: Path,
    get_today: Callable[[], date],
) -> APIRouter:
    router = APIRouter(prefix="/api/comics")

    def to_summary(row: sqlite3.Row) -> ComicSummary:
        return ComicSummary(
            id=row["id"],
            created_at=row["created_at"],
            status=row["status"],
            title_ko=row["title_ko"],
            panels_done=row["panels_done"],
            panel_count=PANEL_COUNT,
            error=row["error"],
            is_read=row["read_at"] is not None,
            cover_url=panel_url(row["id"], 1) if row["panels_done"] else None,
        )

    def get_summary_or_404(conn: sqlite3.Connection, comic_id: int) -> ComicSummary:
        row = next((r for r in store.list_comics(conn) if r["id"] == comic_id), None)
        if row is None:
            raise HTTPException(404, f"comic {comic_id} not found")
        return to_summary(row)

    def ensure_enabled() -> None:
        if not service.is_enabled:
            raise HTTPException(503, "comics are disabled (set GEMINI_API_KEY)")

    @router.get("")
    def list_comics(conn: sqlite3.Connection = Depends(get_conn)) -> list[ComicSummary]:
        return [to_summary(r) for r in store.list_comics(conn)]

    @router.post("", status_code=202)
    def create_comic(conn: sqlite3.Connection = Depends(get_conn)) -> ComicSummary:
        ensure_enabled()
        comic_id = service.start_new()
        if comic_id is None:
            raise HTTPException(409, "an episode is already being drawn")
        return get_summary_or_404(conn, comic_id)

    @router.post("/{comic_id}/retry", status_code=202)
    def retry_comic(comic_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> ComicSummary:
        ensure_enabled()
        summary = get_summary_or_404(conn, comic_id)
        if summary.status != "failed":
            raise HTTPException(409, f"comic {comic_id} is {summary.status}, only failed can retry")
        service.retry(comic_id)
        return get_summary_or_404(conn, comic_id)

    @router.get("/{comic_id}")
    def get_comic(comic_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> ComicDetail:
        summary = get_summary_or_404(conn, comic_id)
        panels = [
            PanelOut(
                no=row["no"],
                image_url=panel_url(comic_id, row["no"]) if row["image_file"] else None,
                bubbles=PanelScript.model_validate_json(row["script"]).bubbles,
            )
            for row in store.list_panels(conn, comic_id)
        ]
        expressions = [
            ComicExpression(id=e.id, text=e.text, meaning_ko=e.meaning_ko)
            for e in store.get_comic_expressions(conn, comic_id)
        ]
        return ComicDetail(**summary.model_dump(), expressions=expressions, panels=panels)

    @router.get("/{comic_id}/panels/{no}")
    def get_panel_image(
        comic_id: int, no: int, conn: sqlite3.Connection = Depends(get_conn)
    ) -> FileResponse:
        row = next((p for p in store.list_panels(conn, comic_id) if p["no"] == no), None)
        if row is None or not row["image_file"]:
            raise HTTPException(404, f"panel {no} of comic {comic_id} not drawn")
        headers = {"Cache-Control": "public, max-age=31536000, immutable"}
        path = comics_dir / str(comic_id) / row["image_file"]
        return FileResponse(path, media_type="image/png", headers=headers)

    @router.post("/{comic_id}/read")
    def mark_read(comic_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, int]:
        summary = get_summary_or_404(conn, comic_id)
        if summary.is_read or summary.status != "done":
            return {"xp_gained": 0}
        today = get_today()
        store.update_comic(conn, comic_id, read_at=today.isoformat())
        study_repository.add_xp(conn, today, "comic_read", XP_COMIC_READ, None)
        conn.commit()
        return {"xp_gained": XP_COMIC_READ}

    return router
