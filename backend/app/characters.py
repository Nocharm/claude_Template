"""Character studio: draw a sheet from a prompt, revise it, then finalize it into the cast."""

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app import comics_repository as store
from app.gemini import Painter, ReferenceImage

logger = logging.getLogger(__name__)

STYLE = (
    "Korean webtoon style illustration, clean confident line art, soft cel shading, "
    "bright natural colors, expressive faces, detailed but uncluttered backgrounds"
)
NO_TEXT = "Absolutely no text, letters, captions, signs with writing, or speech bubbles."
# Gemini keeps resemblance for up to ~4 characters per image; more drifts.
MAX_CAST = 4

# The narrator couple from the sample book; editable in the studio like any other character.
DEFAULT_CHARACTERS: list[tuple[str, str]] = [
    (
        "Mina",
        "Korean woman in her early 30s, the narrator. Shoulder-length dark brown bob with bangs, "
        "warm brown eyes, mustard cardigan over a white T-shirt, light blue jeans",
    ),
    (
        "Jun",
        "Korean man in his early 30s, Mina's husband. Short neat black hair, round thin-framed "
        "glasses, friendly smile, forest green hoodie, khaki pants",
    ),
]


class CharacterError(Exception):
    """A studio action is not allowed in the character's current state."""


@dataclass
class CastMember:
    key: str  # speaker id used in scripts, e.g. "c3"
    name: str
    appearance: str
    image_path: Path


def get_character_dir(characters_dir: Path, character_id: int) -> Path:
    return characters_dir / str(character_id)


def build_sheet_prompt(name: str, appearance: str) -> str:
    return (
        f"{STYLE}. Character reference sheet of a single character named {name}: {appearance}. "
        f"Front view, full body, neutral pose, plain white background. {NO_TEXT}"
    )


def build_revision_prompt(name: str, appearance: str, instruction: str) -> str:
    return (
        f"{STYLE}. Revise the attached character reference sheet of {name} ({appearance}). "
        f"Keep the same person, art style and framing, and change only this: {instruction}. "
        f"Front view, full body, neutral pose, plain white background. {NO_TEXT}"
    )


def _save_version(
    conn: sqlite3.Connection,
    characters_dir: Path,
    character_id: int,
    instruction: str,
    appearance: str,
    image: bytes,
) -> int:
    folder = get_character_dir(characters_dir, character_id)
    folder.mkdir(parents=True, exist_ok=True)
    next_no = len(store.list_versions(conn, character_id)) + 1
    file_name = f"v{next_no}.png"
    (folder / file_name).write_bytes(image)
    return store.add_version(conn, character_id, instruction, appearance, file_name)


def create_character(
    conn: sqlite3.Connection, painter: Painter, characters_dir: Path, name: str, appearance: str
) -> int:
    """Create a draft and draw its first sheet; nothing joins the cast until finalized."""
    image = painter.paint(build_sheet_prompt(name, appearance), [])
    character_id = store.create_character(conn, name, appearance)
    _save_version(conn, characters_dir, character_id, appearance, appearance, image)
    return character_id


def revise_character(
    conn: sqlite3.Connection,
    painter: Painter,
    characters_dir: Path,
    character_id: int,
    base_no: int,
    instruction: str,
) -> int:
    """Redraw from an existing version (sent as reference) with one requested change."""
    character = store.get_character(conn, character_id)
    base = store.get_version(conn, character_id, base_no)
    if character is None or base is None:
        raise CharacterError(f"version {base_no} of character {character_id} not found")
    base_image = (get_character_dir(characters_dir, character_id) / base["image_file"]).read_bytes()
    prompt = build_revision_prompt(character["name"], base["appearance"], instruction)
    image = painter.paint(prompt, [ReferenceImage("image/png", base_image)])
    # Keep the change in the text description too, so panel prompts agree with the sheet.
    appearance = f"{base['appearance']}. Update: {instruction}"
    return _save_version(conn, characters_dir, character_id, instruction, appearance, image)


def finalize_character(conn: sqlite3.Connection, character_id: int, no: int) -> None:
    version = store.get_version(conn, character_id, no)
    if version is None:
        raise CharacterError(f"version {no} of character {character_id} not found")
    store.finalize_character(conn, character_id, no, version["appearance"])


def load_cast(conn: sqlite3.Connection, painter: Painter, characters_dir: Path) -> list[CastMember]:
    """Active characters (first MAX_CAST), drawing a first sheet for any seeded one lacking it."""
    cast = []
    for row in store.list_active_characters(conn)[:MAX_CAST]:
        no = row["final_version"]
        appearance = row["appearance"]
        if no is None:
            image = painter.paint(build_sheet_prompt(row["name"], appearance), [])
            no = _save_version(conn, characters_dir, row["id"], appearance, appearance, image)
            store.finalize_character(conn, row["id"], no, appearance)
            logger.info("default character sheet drawn", extra={"character_id": row["id"]})
        version = store.get_version(conn, row["id"], no)
        image_path = get_character_dir(characters_dir, row["id"]) / version["image_file"]
        cast.append(CastMember(f"c{row['id']}", row["name"], appearance, image_path))
    return cast
