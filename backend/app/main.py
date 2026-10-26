"""FastAPI app: book upload/ingest status, reading data, and the built PWA."""

import asyncio
import hashlib
import logging
import shutil
import sqlite3
import tempfile
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, closing
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import comics_repository as store_comics
from app import db, pipeline, repository
from app.characters import DEFAULT_CHARACTERS
from app.characters_api import build_characters_router
from app.coach import ClaudeCoach, Coach
from app.comics import ClaudeWriter, Writer
from app.comics_api import (
    ComicService,
    Runner,
    build_comics_router,
    run_comic_scheduler,
    run_in_thread,
)
from app.config import Settings
from app.extraction import ClaudeExtractor, Extractor
from app.gemini import GeminiPainter, Painter
from app.study_api import build_study_router
from app.tts import Accent, AzureTts, Synthesizer, TtsError, get_cached_audio

logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
# Upload chunk size for hashing/copying without loading the whole PDF into memory.
CHUNK_BYTES = 1024 * 1024


# --- Response models -----------------------------------------------------------


class BookOut(BaseModel):
    id: int
    title: str
    page_count: int | None
    status: str
    progress_done: int
    progress_total: int
    error: str | None


class DaySummary(BaseModel):
    id: int
    day_no: int
    title: str
    expression_count: int


class ExpressionRef(BaseModel):
    id: int
    text: str
    highlight: str
    meaning_ko: str


class SentenceOut(BaseModel):
    id: int
    no: int
    text_en: str
    text_ko: str
    expressions: list[ExpressionRef]


class DayDetail(BaseModel):
    id: int
    book_id: int
    day_no: int
    title: str
    passage_en: str
    prev_day_id: int | None
    next_day_id: int | None
    sentences: list[SentenceOut]


class ExampleOut(BaseModel):
    text_en: str
    text_ko: str
    origin: str


class RelatedOut(BaseModel):
    id: int
    text: str
    meaning_ko: str
    day_no: int
    type: str
    note: str


class SentenceRef(BaseModel):
    no: int
    text_en: str
    text_ko: str


class ExpressionDetail(BaseModel):
    id: int
    text: str
    meaning_ko: str
    explanation_ko: str
    origin: str
    day_id: int
    day_no: int
    day_title: str
    sentence: SentenceRef | None
    examples: list[ExampleOut]
    related: list[RelatedOut]


# --- App -----------------------------------------------------------------------

_LOG_RECORD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class KeyValueFormatter(logging.Formatter):
    """Append `extra=` fields as key=value so structured log fields stay visible."""

    def format(self, record: logging.LogRecord) -> str:
        fields = {k: v for k, v in vars(record).items() if k not in _LOG_RECORD_ATTRS}
        suffix = " ".join(f"{k}={v}" for k, v in fields.items())
        return f"{super().format(record)} {suffix}".rstrip()


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(KeyValueFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    app_logger = logging.getLogger("app")
    app_logger.handlers = [handler]
    app_logger.setLevel(logging.INFO)


def build_client(settings: Settings) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key or None, max_retries=4)


def build_claude_extractor(settings: Settings) -> Extractor:
    return ClaudeExtractor(build_client(settings), settings.claude_model)


def build_claude_coach(settings: Settings) -> Coach:
    return ClaudeCoach(build_client(settings), settings.claude_model)


def build_azure_tts(settings: Settings) -> Synthesizer | None:
    if not settings.azure_speech_key:
        return None
    return AzureTts(settings.azure_speech_key, settings.azure_speech_region)


def build_claude_writer(settings: Settings) -> Writer:
    return ClaudeWriter(build_client(settings), settings.claude_model)


def build_gemini_painter(settings: Settings) -> Painter | None:
    if not settings.gemini_api_key:
        return None
    return GeminiPainter(settings.gemini_api_key, settings.gemini_image_model)


def create_app(
    settings: Settings | None = None,
    extractor_factory: Callable[[Settings], Extractor] = build_claude_extractor,
    coach_factory: Callable[[Settings], Coach] = build_claude_coach,
    clock: Callable[[], date] | None = None,
    tts_factory: Callable[[Settings], Synthesizer | None] = build_azure_tts,
    writer_factory: Callable[[Settings], Writer] = build_claude_writer,
    painter_factory: Callable[[Settings], Painter | None] = build_gemini_painter,
    comic_runner: Runner = run_in_thread,
    is_scheduler_enabled: bool = True,
) -> FastAPI:
    settings = settings or Settings()

    def get_now() -> datetime:
        return datetime.now(ZoneInfo(settings.timezone))

    # "Today" for streaks and due dates is the learner's local date, not the server's UTC date.
    get_today = clock or (lambda: get_now().date())
    painter = painter_factory(settings)
    comic_service = ComicService(
        lambda: db.connect(settings.db_path),
        settings.comics_dir,
        lambda: writer_factory(settings),
        painter,
        get_now,
        comic_runner,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        db.init_db(settings.db_path)
        with closing(db.connect(settings.db_path)) as conn:
            interrupted = repository.mark_interrupted_books(conn)
            interrupted += store_comics.mark_interrupted_comics(conn)
            store_comics.seed_characters(conn, DEFAULT_CHARACTERS)
        if interrupted:
            logger.warning("marked interrupted jobs as failed", extra={"count": interrupted})
        scheduler = None
        if is_scheduler_enabled and comic_service.is_enabled:
            scheduler = asyncio.create_task(run_comic_scheduler(comic_service, get_now))
        yield
        if scheduler is not None:
            scheduler.cancel()

    app = FastAPI(title="Phrasebook Study", lifespan=lifespan)

    def get_conn() -> Iterator[sqlite3.Connection]:
        with closing(db.connect(settings.db_path)) as conn:
            yield conn

    app.include_router(build_study_router(get_conn, get_today, lambda: coach_factory(settings)))
    app.include_router(build_comics_router(get_conn, comic_service, settings.comics_dir, get_today))
    app.include_router(
        build_characters_router(get_conn, painter, settings.comics_dir / "characters")
    )

    def run_ingest(book_id: int, book_dir: Path) -> None:
        extractor = extractor_factory(settings)
        pipeline.ingest_book(lambda: db.connect(settings.db_path), book_id, book_dir, extractor)

    def get_book_or_404(conn: sqlite3.Connection, book_id: int) -> sqlite3.Row:
        book = repository.get_book(conn, book_id)
        if book is None:
            raise HTTPException(404, f"book {book_id} not found")
        return book

    synthesizer = tts_factory(settings)

    @app.get("/api/tts")
    def speak(
        text: str = Query(min_length=1, max_length=1000),
        accent: Accent = "us",
        slow: bool = False,
    ) -> FileResponse:
        if synthesizer is None:
            raise HTTPException(503, "Azure TTS is not configured (set AZURE_SPEECH_KEY)")
        try:
            path = get_cached_audio(settings.audio_dir, synthesizer, text.strip(), accent, slow)
        except TtsError as exc:
            raise HTTPException(502, str(exc)) from exc
        # Same query → same audio forever, so let Safari cache it too.
        headers = {"Cache-Control": "public, max-age=31536000, immutable"}
        return FileResponse(path, media_type="audio/mpeg", headers=headers)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/books")
    def list_books(conn: sqlite3.Connection = Depends(get_conn)) -> list[BookOut]:
        return [BookOut(**dict(row)) for row in repository.list_books(conn)]

    @app.post("/api/books", status_code=201)
    def upload_book(
        file: UploadFile,
        background: BackgroundTasks,
        conn: sqlite3.Connection = Depends(get_conn),
    ) -> BookOut:
        file_name = file.filename or "book.pdf"
        if not file.file.read(5).startswith(b"%PDF"):
            raise HTTPException(400, f"{file_name} is not a PDF")
        file.file.seek(0)

        settings.books_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with tempfile.NamedTemporaryFile(dir=settings.books_dir, delete=False) as tmp:
            while chunk := file.file.read(CHUNK_BYTES):
                digest.update(chunk)
                tmp.write(chunk)
        file_hash = digest.hexdigest()

        existing = repository.find_book_by_hash(conn, file_hash)
        if existing is not None:
            Path(tmp.name).unlink()
            # Same PDF again: never re-run OCR, just hand back the existing book.
            return JSONResponse(BookOut(**dict(existing)).model_dump(), status_code=200)

        book_dir = settings.books_dir / file_hash
        book_dir.mkdir(exist_ok=True)
        shutil.move(tmp.name, book_dir / "source.pdf")
        book_id = repository.create_book(conn, Path(file_name).stem, file_name, file_hash)
        background.add_task(run_ingest, book_id, book_dir)
        return BookOut(**dict(get_book_or_404(conn, book_id)))

    @app.get("/api/books/{book_id}")
    def get_book(book_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> BookOut:
        return BookOut(**dict(get_book_or_404(conn, book_id)))

    @app.post("/api/books/{book_id}/retry", status_code=202)
    def retry_book(
        book_id: int, background: BackgroundTasks, conn: sqlite3.Connection = Depends(get_conn)
    ) -> BookOut:
        book = get_book_or_404(conn, book_id)
        if book["status"] != "failed":
            raise HTTPException(409, f"book {book_id} is {book['status']}, only failed can retry")
        repository.update_book(conn, book_id, status="queued", error=None)
        background.add_task(run_ingest, book_id, settings.books_dir / book["file_hash"])
        return BookOut(**dict(get_book_or_404(conn, book_id)))

    @app.get("/api/books/{book_id}/days")
    def list_days(book_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> list[DaySummary]:
        get_book_or_404(conn, book_id)
        return [DaySummary(**dict(row)) for row in repository.list_days(conn, book_id)]

    @app.get("/api/days/{day_id}")
    def get_day(day_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> DayDetail:
        day = repository.get_day(conn, day_id)
        if day is None:
            raise HTTPException(404, f"day {day_id} not found")
        by_sentence: dict[int, list[ExpressionRef]] = {}
        for row in repository.list_sentence_expressions(conn, day_id):
            ref = ExpressionRef(
                id=row["id"],
                text=row["text"],
                highlight=row["highlight"],
                meaning_ko=row["meaning_ko"],
            )
            by_sentence.setdefault(row["sentence_id"], []).append(ref)
        sentences = [
            SentenceOut(
                id=s["id"],
                no=s["no"],
                text_en=s["text_en"],
                text_ko=s["text_ko"],
                expressions=by_sentence.get(s["id"], []),
            )
            for s in repository.list_sentences(conn, day_id)
        ]
        prev_id, next_id = repository.get_adjacent_day_ids(conn, day["book_id"], day["day_no"])
        return DayDetail(
            id=day["id"],
            book_id=day["book_id"],
            day_no=day["day_no"],
            title=day["title"],
            passage_en=day["passage_en"],
            prev_day_id=prev_id,
            next_day_id=next_id,
            sentences=sentences,
        )

    @app.get("/api/expressions/{expression_id}")
    def get_expression(
        expression_id: int, conn: sqlite3.Connection = Depends(get_conn)
    ) -> ExpressionDetail:
        row = repository.get_expression(conn, expression_id)
        if row is None:
            raise HTTPException(404, f"expression {expression_id} not found")
        sentence = None
        if row["sentence_no"] is not None:
            sentence = SentenceRef(
                no=row["sentence_no"], text_en=row["sentence_en"], text_ko=row["sentence_ko"]
            )
        return ExpressionDetail(
            id=row["id"],
            text=row["text"],
            meaning_ko=row["meaning_ko"],
            explanation_ko=row["explanation_ko"],
            origin=row["origin"],
            day_id=row["day_id"],
            day_no=row["day_no"],
            day_title=row["day_title"],
            sentence=sentence,
            examples=[ExampleOut(**dict(e)) for e in repository.list_examples(conn, expression_id)],
            related=[RelatedOut(**dict(r)) for r in repository.list_related(conn, expression_id)],
        )

    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def serve_spa(path: str) -> FileResponse:
            # Real files (manifest, icons) are served as-is; every other route is the SPA shell.
            candidate = (FRONTEND_DIST / path).resolve()
            if path and candidate.is_file() and candidate.is_relative_to(FRONTEND_DIST):
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app
