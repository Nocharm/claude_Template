"""Database reads and writes for books, days and the expression graph."""

import sqlite3

from app.extraction import DayExtraction, ExpressionBrief, ExpressionItem, Relation

# Statuses an ingest can be left in if the server stops mid-run.
ACTIVE_STATUSES = ("queued", "classifying", "extracting", "linking")


# --- Books ---------------------------------------------------------------------


def find_book_by_hash(conn: sqlite3.Connection, file_hash: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM books WHERE file_hash = ?", (file_hash,)).fetchone()


def create_book(conn: sqlite3.Connection, title: str, file_name: str, file_hash: str) -> int:
    cursor = conn.execute(
        "INSERT INTO books (title, file_name, file_hash, status) VALUES (?, ?, ?, 'queued')",
        (title, file_name, file_hash),
    )
    conn.commit()
    return cursor.lastrowid


def update_book(conn: sqlite3.Connection, book_id: int, **fields: object) -> None:
    allowed = {"status", "progress_done", "progress_total", "error", "page_count"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"unknown book fields: {sorted(unknown)}")
    assignments = ", ".join(f"{name} = ?" for name in fields)
    conn.execute(f"UPDATE books SET {assignments} WHERE id = ?", (*fields.values(), book_id))
    conn.commit()


def mark_interrupted_books(conn: sqlite3.Connection) -> int:
    placeholders = ", ".join("?" for _ in ACTIVE_STATUSES)
    cursor = conn.execute(
        f"UPDATE books SET status = 'failed', error = 'interrupted by server restart' "
        f"WHERE status IN ({placeholders})",
        ACTIVE_STATUSES,
    )
    conn.commit()
    return cursor.rowcount


def list_books(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()


def get_book(conn: sqlite3.Connection, book_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()


# --- Ingest writes -------------------------------------------------------------


def has_day(conn: sqlite3.Connection, book_id: int, day_no: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM days WHERE book_id = ? AND day_no = ?", (book_id, day_no)
    ).fetchone()
    return row is not None


def _insert_expression(
    conn: sqlite3.Connection,
    day_id: int,
    sentence_id: int | None,
    parent_id: int | None,
    text: str,
    highlight: str,
    meaning_ko: str,
    explanation_ko: str,
    origin: str,
) -> int:
    cursor = conn.execute(
        "INSERT INTO expressions (day_id, sentence_id, parent_id, text, highlight, meaning_ko, "
        "explanation_ko, origin) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (day_id, sentence_id, parent_id, text, highlight, meaning_ko, explanation_ko, origin),
    )
    return cursor.lastrowid


def _insert_examples(conn: sqlite3.Connection, expression_id: int, examples: list) -> None:
    conn.executemany(
        "INSERT INTO examples (expression_id, text_en, text_ko, origin) VALUES (?, ?, ?, 'book')",
        [(expression_id, e.text_en, e.text_ko) for e in examples],
    )


def _insert_relation(
    conn: sqlite3.Connection, from_id: int, to_id: int, rel_type: str, note: str
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO relations (from_id, to_id, type, note) VALUES (?, ?, ?, ?)",
        (from_id, to_id, rel_type, note),
    )


def _save_expression(
    conn: sqlite3.Connection, day_id: int, sentence_id: int, item: ExpressionItem
) -> int:
    expression_id = _insert_expression(
        conn,
        day_id,
        sentence_id,
        None,
        item.text,
        item.highlight,
        item.meaning_ko,
        item.explanation_ko,
        "reading_point",
    )
    _insert_examples(conn, expression_id, item.examples)
    # Tip boxes become their own nodes so the map can show them as neighbours.
    for box in item.tip_boxes:
        for tip in box.items:
            tip_id = _insert_expression(
                conn,
                day_id,
                None,
                expression_id,
                tip.text,
                "",
                tip.meaning_ko,
                "",
                "tip_box",
            )
            _insert_examples(conn, tip_id, tip.examples)
            _insert_relation(conn, expression_id, tip_id, box.kind, box.title_ko)
    return expression_id


def save_day(
    conn: sqlite3.Connection, book_id: int, day: DayExtraction, page_start: int, page_end: int
) -> int:
    """Insert one extracted DAY with its sentences, expressions and in-book relations."""
    cursor = conn.execute(
        "INSERT INTO days (book_id, day_no, title, passage_en, page_start, page_end) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (book_id, day.day_no, day.title, day.passage_en, page_start, page_end),
    )
    day_id = cursor.lastrowid
    for sentence in day.sentences:
        sentence_id = conn.execute(
            "INSERT INTO sentences (day_id, no, text_en, text_ko) VALUES (?, ?, ?, ?)",
            (day_id, sentence.no, sentence.text_en, sentence.text_ko),
        ).lastrowid
        ids = [_save_expression(conn, day_id, sentence_id, e) for e in sentence.expressions]
        for i, from_id in enumerate(ids):
            for to_id in ids[i + 1 :]:
                _insert_relation(conn, from_id, to_id, "same_sentence", "")
    conn.commit()
    return day_id


def list_reading_points(conn: sqlite3.Connection, book_id: int) -> list[ExpressionBrief]:
    rows = conn.execute(
        "SELECT e.id, d.day_no, e.text, e.meaning_ko FROM expressions e "
        "JOIN days d ON d.id = e.day_id "
        "WHERE d.book_id = ? AND e.origin = 'reading_point' ORDER BY d.day_no, e.id",
        (book_id,),
    ).fetchall()
    return [ExpressionBrief(r["id"], r["day_no"], r["text"], r["meaning_ko"]) for r in rows]


def save_relations(conn: sqlite3.Connection, relations: list[Relation], valid_ids: set[int]) -> int:
    """Store model-proposed links, dropping ones that point outside valid_ids."""
    saved = 0
    for rel in relations:
        if rel.from_id == rel.to_id or not {rel.from_id, rel.to_id} <= valid_ids:
            continue
        _insert_relation(conn, rel.from_id, rel.to_id, rel.type, rel.note_ko)
        saved += 1
    conn.commit()
    return saved


# --- Reads for the API ---------------------------------------------------------


def list_days(conn: sqlite3.Connection, book_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT d.id, d.day_no, d.title, "
        "(SELECT COUNT(*) FROM expressions e WHERE e.day_id = d.id "
        " AND e.origin = 'reading_point') AS expression_count "
        "FROM days d WHERE d.book_id = ? ORDER BY d.day_no",
        (book_id,),
    ).fetchall()


def get_day(conn: sqlite3.Connection, day_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM days WHERE id = ?", (day_id,)).fetchone()


def get_adjacent_day_ids(
    conn: sqlite3.Connection, book_id: int, day_no: int
) -> tuple[int | None, int | None]:
    prev_row = conn.execute(
        "SELECT id FROM days WHERE book_id = ? AND day_no < ? ORDER BY day_no DESC LIMIT 1",
        (book_id, day_no),
    ).fetchone()
    next_row = conn.execute(
        "SELECT id FROM days WHERE book_id = ? AND day_no > ? ORDER BY day_no LIMIT 1",
        (book_id, day_no),
    ).fetchone()
    return (prev_row["id"] if prev_row else None, next_row["id"] if next_row else None)


def list_sentences(conn: sqlite3.Connection, day_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM sentences WHERE day_id = ? ORDER BY no", (day_id,)
    ).fetchall()


def list_sentence_expressions(conn: sqlite3.Connection, day_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, sentence_id, text, highlight, meaning_ko FROM expressions "
        "WHERE day_id = ? AND origin = 'reading_point' ORDER BY id",
        (day_id,),
    ).fetchall()


def get_expression(conn: sqlite3.Connection, expression_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT e.*, d.day_no, d.title AS day_title, d.book_id, "
        "s.no AS sentence_no, s.text_en AS sentence_en, s.text_ko AS sentence_ko "
        "FROM expressions e JOIN days d ON d.id = e.day_id "
        "LEFT JOIN sentences s ON s.id = e.sentence_id WHERE e.id = ?",
        (expression_id,),
    ).fetchone()


def list_examples(conn: sqlite3.Connection, expression_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT text_en, text_ko, origin FROM examples WHERE expression_id = ? ORDER BY id",
        (expression_id,),
    ).fetchall()


def list_related(conn: sqlite3.Connection, expression_id: int) -> list[sqlite3.Row]:
    """Neighbours in either direction; relations are stored once but read as undirected."""
    return conn.execute(
        "SELECT e.id, e.text, e.meaning_ko, d.day_no, r.type, r.note FROM relations r "
        "JOIN expressions e ON e.id = CASE WHEN r.from_id = :id THEN r.to_id ELSE r.from_id END "
        "JOIN days d ON d.id = e.day_id "
        "WHERE r.from_id = :id OR r.to_id = :id ORDER BY r.type, e.id",
        {"id": expression_id},
    ).fetchall()
