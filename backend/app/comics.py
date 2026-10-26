"""10-panel webtoon generation: Claude writes the script, Gemini draws text-free panels."""

import logging
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Protocol

import anthropic
from pydantic import BaseModel, Field, create_model

from app import comics_repository as store
from app.characters import NO_TEXT, STYLE, CastMember, load_cast
from app.extraction import ExpressionBrief, parse_structured
from app.gemini import Painter, ReferenceImage

logger = logging.getLogger(__name__)

PANEL_COUNT = 10
# Expressions woven into one episode; more makes dialogue feel forced.
EXPRESSIONS_PER_COMIC = 6
# Automatic episodes: Mon/Wed/Fri at 03:00 local time (user asked for 2–3 per week).
COMIC_WEEKDAYS = (0, 2, 4)
COMIC_HOUR = 3

# --- Script (Claude) -------------------------------------------------------------


class Bubble(BaseModel):
    speaker: str = Field(description="A cast id from the list, or 'narration'.")
    text_en: str = Field(description="One short line, at most 15 words.")
    text_ko: str = Field(description="Natural Korean translation.")
    highlight: str = Field(
        description="Exact substring of text_en that is a target expression, or empty string."
    )


class PanelScript(BaseModel):
    scene_en: str = Field(
        description="Visual description for an illustrator: setting, action, facial expressions, "
        "camera angle. No dialogue or written words."
    )
    characters: list[str] = Field(description="Cast ids visible in the panel.")
    bubbles: list[Bubble] = Field(description="1–2 speech bubbles or narration boxes.")


class ComicScript(BaseModel):
    title_ko: str = Field(description="Short, catchy Korean episode title.")
    panels: list[PanelScript]


class ComicError(Exception):
    """The episode could not be produced."""


class Writer(Protocol):
    def write(self, expressions: list[ExpressionBrief], cast: list[CastMember]) -> ComicScript: ...


def build_cast_script_model(keys: list[str]) -> type[ComicScript]:
    """ComicScript variant whose speaker/character fields only accept this episode's cast ids."""
    cast_key = Literal[tuple(keys)]  # type: ignore[valid-type]  # enum built at runtime
    speaker_key = Literal[tuple([*keys, "narration"])]  # type: ignore[valid-type]
    bubble = create_model("CastBubble", __base__=Bubble, speaker=(speaker_key, ...))
    panel = create_model(
        "CastPanel",
        __base__=PanelScript,
        characters=(list[cast_key], ...),
        bubbles=(list[bubble], ...),
    )
    return create_model("CastComicScript", __base__=ComicScript, panels=(list[panel], ...))


WRITER_SYSTEM = (
    "You write cozy slice-of-life webtoons that help a Korean adult learn English expressions. "
    "Dialogue is natural spoken English a native speaker would really say."
)

WRITER_PROMPT = """Write a {count}-panel webtoon episode with this cast \
(use the ids in speaker/characters fields):
{cast}

Use every target expression below naturally in the dialogue at least once, and set each \
bubble's highlight to the exact words used. Give the story a small twist or punchline at the end.

Target expressions (expression — Korean meaning):
{lines}"""


class ClaudeWriter:
    def __init__(self, client: anthropic.Anthropic, model: str) -> None:
        self._client = client
        self._model = model

    def write(self, expressions: list[ExpressionBrief], cast: list[CastMember]) -> ComicScript:
        lines = "\n".join(f"- {e.text} — {e.meaning_ko}" for e in expressions)
        cast_lines = "\n".join(f"- {m.key}: {m.name} — {m.appearance}" for m in cast)
        prompt = WRITER_PROMPT.format(count=PANEL_COUNT, cast=cast_lines, lines=lines)
        content = [{"type": "text", "text": prompt}]
        model = build_cast_script_model([m.key for m in cast])
        script = parse_structured(
            self._client, self._model, WRITER_SYSTEM, content, model, "write comic"
        )
        return ComicScript.model_validate(script.model_dump())


# --- Drawing (Gemini) ------------------------------------------------------------


def build_panel_prompt(panel: PanelScript, cast: dict[str, CastMember]) -> str:
    members = [cast[k] for k in panel.characters if k in cast]
    cast_text = "; ".join(f"{m.name} ({m.appearance})" for m in members) or "no main characters"
    return (
        f"{STYLE}. One vertical webtoon panel in 4:5 portrait composition. Cast: {cast_text}. "
        f"{panel.scene_en} Characters must match the reference images exactly (same face, "
        f"hair and outfit). Keep the top quarter of the image as simple background so "
        f"speech bubbles can be placed there. {NO_TEXT}"
    )


# --- Episode pipeline ----------------------------------------------------------------


def generate_comic(
    conn_factory: Callable[[], sqlite3.Connection],
    comic_id: int,
    comics_dir: Path,
    writer: Writer,
    painter: Painter,
) -> None:
    """Write (once) and draw (missing panels only), so a retry resumes where it stopped."""
    with closing(conn_factory()) as conn:
        try:
            _run(conn, comic_id, comics_dir, writer, painter)
        except Exception as exc:
            logger.exception("comic failed", extra={"comic_id": comic_id})
            store.update_comic(
                conn, comic_id, status="failed", error=f"{type(exc).__name__}: {exc}"
            )
            raise


def _run(
    conn: sqlite3.Connection, comic_id: int, comics_dir: Path, writer: Writer, painter: Painter
) -> None:
    store.update_comic(conn, comic_id, status="writing", error=None)
    cast = load_cast(conn, painter, comics_dir / "characters")
    if not cast:
        raise ComicError("no active characters — finalize one in the character studio")
    if not store.list_panels(conn, comic_id):
        expressions = store.get_comic_expressions(conn, comic_id)
        if not expressions:
            raise ComicError("no expressions to use — study some cards first")
        script = writer.write(expressions, cast)
        if len(script.panels) != PANEL_COUNT:
            raise ComicError(f"script has {len(script.panels)} panels, expected {PANEL_COUNT}")
        store.save_script(conn, comic_id, script)

    store.update_comic(conn, comic_id, status="drawing")
    cast_by_key = {m.key: m for m in cast}
    episode_dir = comics_dir / str(comic_id)
    episode_dir.mkdir(parents=True, exist_ok=True)
    for row in store.list_panels(conn, comic_id):
        if row["image_file"]:
            continue
        panel = PanelScript.model_validate_json(row["script"])
        # A character retired after the script was written is drawn from the text alone.
        references = [
            ReferenceImage("image/png", cast_by_key[k].image_path.read_bytes())
            for k in panel.characters
            if k in cast_by_key
        ]
        image = painter.paint(build_panel_prompt(panel, cast_by_key), references)
        file_name = f"{row['no']}.png"
        (episode_dir / file_name).write_bytes(image)
        store.set_panel_image(conn, row["id"], file_name)
        logger.info("panel drawn", extra={"comic_id": comic_id, "panel": row["no"]})
    store.update_comic(conn, comic_id, status="done")


# --- Schedule ------------------------------------------------------------------------


def _slot_on(day: datetime) -> datetime:
    return day.replace(hour=COMIC_HOUR, minute=0, second=0, microsecond=0)


def get_latest_slot(now: datetime) -> datetime:
    """Most recent scheduled run at or before now (timezone-aware in, aware out)."""
    for back in range(8):
        slot = _slot_on(now - timedelta(days=back))
        if slot.weekday() in COMIC_WEEKDAYS and slot <= now:
            return slot
    raise AssertionError("COMIC_WEEKDAYS must not be empty")


def get_next_slot(now: datetime) -> datetime:
    for ahead in range(8):
        slot = _slot_on(now + timedelta(days=ahead))
        if slot.weekday() in COMIC_WEEKDAYS and slot > now:
            return slot
    raise AssertionError("COMIC_WEEKDAYS must not be empty")
