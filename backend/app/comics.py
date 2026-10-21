"""10-panel webtoon generation: Claude writes the script, Gemini draws text-free panels."""

import logging
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Protocol

import anthropic
from pydantic import BaseModel, Field

from app import comics_repository as store
from app.extraction import ExpressionBrief, parse_structured
from app.gemini import Painter, ReferenceImage

logger = logging.getLogger(__name__)

PANEL_COUNT = 10
# Expressions woven into one episode; more makes dialogue feel forced.
EXPRESSIONS_PER_COMIC = 6
# Automatic episodes: Mon/Wed/Fri at 03:00 local time (user asked for 2–3 per week).
COMIC_WEEKDAYS = (0, 2, 4)
COMIC_HOUR = 3

Character = Literal["mina", "jun"]

STYLE = (
    "Korean webtoon style illustration, clean confident line art, soft cel shading, "
    "bright natural colors, expressive faces, detailed but uncluttered backgrounds"
)
# Fixed looks; generated once as reference sheets so every panel keeps the same faces.
CHARACTERS: dict[Character, str] = {
    "mina": "Korean woman in her early 30s, shoulder-length dark brown bob with bangs, "
    "warm brown eyes, mustard cardigan over a white T-shirt, light blue jeans",
    "jun": "Korean man in his early 30s, short neat black hair, round thin-framed glasses, "
    "friendly smile, forest green hoodie, khaki pants",
}
NO_TEXT = "Absolutely no text, letters, captions, signs with writing, or speech bubbles."


# --- Script (Claude) -------------------------------------------------------------


class Bubble(BaseModel):
    speaker: Literal["mina", "jun", "narration"]
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
    characters: list[Character]
    bubbles: list[Bubble] = Field(description="1–2 speech bubbles or narration boxes.")


class ComicScript(BaseModel):
    title_ko: str = Field(description="Short, catchy Korean episode title.")
    panels: list[PanelScript]


class ComicError(Exception):
    """The episode could not be produced."""


class Writer(Protocol):
    def write(self, expressions: list[ExpressionBrief]) -> ComicScript: ...


WRITER_SYSTEM = (
    "You write cozy slice-of-life webtoons that help a Korean adult learn English expressions. "
    "Dialogue is natural spoken English a native speaker would really say."
)

WRITER_PROMPT = """Write a {count}-panel webtoon episode starring Mina (the narrator) and her \
husband Jun, a fun Korean couple in their 30s.
Use every target expression below naturally in the dialogue at least once, and set each \
bubble's highlight to the exact words used. Give the story a small twist or punchline at the end.

Target expressions (expression — Korean meaning):
{lines}"""


class ClaudeWriter:
    def __init__(self, client: anthropic.Anthropic, model: str) -> None:
        self._client = client
        self._model = model

    def write(self, expressions: list[ExpressionBrief]) -> ComicScript:
        lines = "\n".join(f"- {e.text} — {e.meaning_ko}" for e in expressions)
        prompt = WRITER_PROMPT.format(count=PANEL_COUNT, lines=lines)
        content = [{"type": "text", "text": prompt}]
        return parse_structured(
            self._client, self._model, WRITER_SYSTEM, content, ComicScript, "write comic"
        )


# --- Drawing (Gemini) ------------------------------------------------------------


def build_character_prompt(character: Character) -> str:
    return (
        f"{STYLE}. Character reference sheet of a single character: {CHARACTERS[character]}. "
        f"Front view, full body, neutral pose, plain white background. {NO_TEXT}"
    )


def build_panel_prompt(panel: PanelScript) -> str:
    cast = ", ".join(c.capitalize() for c in panel.characters) or "no main characters"
    return (
        f"{STYLE}. One vertical webtoon panel in 4:5 portrait composition. Cast: {cast}. "
        f"{panel.scene_en} Characters must match the reference images exactly (same face, "
        f"hair and outfit). Keep the top quarter of the image as simple background so "
        f"speech bubbles can be placed there. {NO_TEXT}"
    )


def ensure_character_refs(characters_dir: Path, painter: Painter) -> dict[Character, Path]:
    characters_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[Character, Path] = {}
    for character in CHARACTERS:
        path = characters_dir / f"{character}.png"
        if not path.exists():
            path.write_bytes(painter.paint(build_character_prompt(character), []))
            logger.info("character reference drawn", extra={"character": character})
        paths[character] = path
    return paths


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
    if not store.list_panels(conn, comic_id):
        expressions = store.get_comic_expressions(conn, comic_id)
        if not expressions:
            raise ComicError("no expressions to use — study some cards first")
        script = writer.write(expressions)
        if len(script.panels) != PANEL_COUNT:
            raise ComicError(f"script has {len(script.panels)} panels, expected {PANEL_COUNT}")
        store.save_script(conn, comic_id, script)

    store.update_comic(conn, comic_id, status="drawing")
    refs = ensure_character_refs(comics_dir / "characters", painter)
    episode_dir = comics_dir / str(comic_id)
    episode_dir.mkdir(parents=True, exist_ok=True)
    for row in store.list_panels(conn, comic_id):
        if row["image_file"]:
            continue
        panel = PanelScript.model_validate_json(row["script"])
        references = [ReferenceImage("image/png", refs[c].read_bytes()) for c in panel.characters]
        image = painter.paint(build_panel_prompt(panel), references)
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
