"""Database reads and writes for webtoon episodes and panels."""

import json
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING

from app.extraction import ExpressionBrief

if TYPE_CHECKING:  # avoids a runtime cycle: comics imports this module
    from app.comics import ComicScript

# Statuses an episode can be left in if the server stops mid-run.
ACTIVE_STATUSES = ("queued", "writing", "drawing")


def pick_expression_ids(conn: sqlite3.Connection, limit: int) -> list[int]:
    """Soonest-due studied cards first (reinforce what's coming up), then unstudied ones."""
    rows = conn.execute(
        "SELECT expression_id FROM review_cards ORDER BY due_date, expression_id LIMIT ?",
        (limit,),
    ).fetchall()
    ids = [r[0] for r in rows]
    if len(ids) < limit:
        rows = conn.execute(
            "SELECT e.id FROM expressions e JOIN days d ON d.id = e.day_id "
            "LEFT JOIN review_cards c ON c.expression_id = e.id "
            "WHERE c.expression_id IS NULL AND e.origin = 'reading_point' "
            "ORDER BY d.book_id, d.day_no, e.id LIMIT ?",
            (limit - len(ids),),
        ).fetchall()
        ids += [r[0] for r in rows]
    return ids


def create_comic(conn: sqlite3.Connection, created_at: datetime, expression_ids: list[int]) -> int:
    cursor = conn.execute(
        "INSERT INTO comics (created_at, status, expression_ids) VALUES (?, 'queued', ?)",
        (created_at.isoformat(), json.dumps(expression_ids)),
    )
    conn.commit()
    return cursor.lastrowid


def update_comic(conn: sqlite3.Connection, comic_id: int, **fields: object) -> None:
    allowed = {"status", "error", "title_ko", "read_at"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"unknown comic fields: {sorted(unknown)}")
    assignments = ", ".join(f"{name} = ?" for name in fields)
    conn.execute(f"UPDATE comics SET {assignments} WHERE id = ?", (*fields.values(), comic_id))
    conn.commit()


def get_comic(conn: sqlite3.Connection, comic_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM comics WHERE id = ?", (comic_id,)).fetchone()


def get_comic_expressions(conn: sqlite3.Connection, comic_id: int) -> list[ExpressionBrief]:
    ids = json.loads(get_comic(conn, comic_id)["expression_ids"])
    if not ids:
        return []
    placeholders = ", ".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT e.id, d.day_no, e.text, e.meaning_ko FROM expressions e "
        f"JOIN days d ON d.id = e.day_id WHERE e.id IN ({placeholders})",
        ids,
    ).fetchall()
    return [ExpressionBrief(r["id"], r["day_no"], r["text"], r["meaning_ko"]) for r in rows]


def save_script(conn: sqlite3.Connection, comic_id: int, script: "ComicScript") -> None:
    conn.execute("UPDATE comics SET title_ko = ? WHERE id = ?", (script.title_ko, comic_id))
    conn.executemany(
        "INSERT INTO comic_panels (comic_id, no, script) VALUES (?, ?, ?)",
        [(comic_id, i + 1, p.model_dump_json()) for i, p in enumerate(script.panels)],
    )
    conn.commit()


def list_panels(conn: sqlite3.Connection, comic_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM comic_panels WHERE comic_id = ? ORDER BY no", (comic_id,)
    ).fetchall()


def set_panel_image(conn: sqlite3.Connection, panel_id: int, image_file: str) -> None:
    conn.execute("UPDATE comic_panels SET image_file = ? WHERE id = ?", (image_file, panel_id))
    conn.commit()


def list_comics(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT c.*, "
        "(SELECT COUNT(*) FROM comic_panels p WHERE p.comic_id = c.id "
        " AND p.image_file IS NOT NULL) AS panels_done "
        "FROM comics c ORDER BY c.id DESC"
    ).fetchall()


def has_active_comic(conn: sqlite3.Connection) -> bool:
    placeholders = ", ".join("?" for _ in ACTIVE_STATUSES)
    row = conn.execute(
        f"SELECT 1 FROM comics WHERE status IN ({placeholders}) LIMIT 1", ACTIVE_STATUSES
    ).fetchone()
    return row is not None


def has_comic_since(conn: sqlite3.Connection, since: datetime) -> bool:
    rows = conn.execute("SELECT created_at FROM comics").fetchall()
    return any(datetime.fromisoformat(r["created_at"]) >= since for r in rows)


def mark_interrupted_comics(conn: sqlite3.Connection) -> int:
    placeholders = ", ".join("?" for _ in ACTIVE_STATUSES)
    cursor = conn.execute(
        f"UPDATE comics SET status = 'failed', error = 'interrupted by server restart' "
        f"WHERE status IN ({placeholders})",
        ACTIVE_STATUSES,
    )
    conn.commit()
    return cursor.rowcount


# --- Characters ---------------------------------------------------------------------


def seed_characters(conn: sqlite3.Connection, defaults: list[tuple[str, str]]) -> None:
    """Insert the default cast once, as active characters whose sheet is drawn on first use."""
    if conn.execute("SELECT 1 FROM characters LIMIT 1").fetchone():
        return
    conn.executemany(
        "INSERT INTO characters (name, appearance, status) VALUES (?, ?, 'active')", defaults
    )
    conn.commit()


def create_character(conn: sqlite3.Connection, name: str, appearance: str) -> int:
    cursor = conn.execute(
        "INSERT INTO characters (name, appearance, status) VALUES (?, ?, 'draft')",
        (name, appearance),
    )
    conn.commit()
    return cursor.lastrowid


def get_character(conn: sqlite3.Connection, character_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()


def list_characters(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT c.*, (SELECT COUNT(*) FROM character_versions v WHERE v.character_id = c.id) "
        "AS version_count FROM characters c ORDER BY c.id"
    ).fetchall()


def list_active_characters(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM characters WHERE status = 'active' ORDER BY id").fetchall()


def list_versions(conn: sqlite3.Connection, character_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM character_versions WHERE character_id = ? ORDER BY no", (character_id,)
    ).fetchall()


def get_version(conn: sqlite3.Connection, character_id: int, no: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM character_versions WHERE character_id = ? AND no = ?", (character_id, no)
    ).fetchone()


def add_version(
    conn: sqlite3.Connection, character_id: int, instruction: str, appearance: str, image_file: str
) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(no), 0) + 1 FROM character_versions WHERE character_id = ?",
        (character_id,),
    ).fetchone()
    no = row[0]
    conn.execute(
        "INSERT INTO character_versions (character_id, no, instruction, appearance, image_file) "
        "VALUES (?, ?, ?, ?, ?)",
        (character_id, no, instruction, appearance, image_file),
    )
    conn.commit()
    return no


def finalize_character(
    conn: sqlite3.Connection, character_id: int, no: int, appearance: str
) -> None:
    conn.execute(
        "UPDATE characters SET status = 'active', final_version = ?, appearance = ? WHERE id = ?",
        (no, appearance, character_id),
    )
    conn.commit()


def set_character_status(conn: sqlite3.Connection, character_id: int, status: str) -> None:
    conn.execute("UPDATE characters SET status = ? WHERE id = ?", (status, character_id))
    conn.commit()
