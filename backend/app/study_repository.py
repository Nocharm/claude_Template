"""Database reads and writes for review cards, daily logs, XP and AI example sentences."""

import sqlite3
from datetime import date

from app.coach import AppliedSentence
from app.study import CardState

# Columns needed to build a quiz for one expression.
_QUIZ_COLUMNS = (
    "e.id, e.text, e.highlight, e.meaning_ko, d.day_no, "
    "s.text_en AS sentence_en, s.text_ko AS sentence_ko, COALESCE(c.reps, 0) AS reps, "
    "c.expression_id IS NULL AS is_new"
)
_QUIZ_JOINS = (
    "FROM expressions e JOIN days d ON d.id = e.day_id "
    "LEFT JOIN sentences s ON s.id = e.sentence_id "
    "LEFT JOIN review_cards c ON c.expression_id = e.id"
)


# --- Review cards ----------------------------------------------------------------


def get_card(conn: sqlite3.Connection, expression_id: int) -> CardState | None:
    row = conn.execute(
        "SELECT * FROM review_cards WHERE expression_id = ?", (expression_id,)
    ).fetchone()
    if row is None:
        return None
    return CardState(
        interval_days=row["interval_days"],
        ease=row["ease"],
        reps=row["reps"],
        lapses=row["lapses"],
        due_date=date.fromisoformat(row["due_date"]),
    )


def save_card(conn: sqlite3.Connection, expression_id: int, card: CardState, today: date) -> None:
    conn.execute(
        "INSERT INTO review_cards (expression_id, interval_days, ease, reps, lapses, due_date, "
        "last_reviewed) VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (expression_id) DO UPDATE SET interval_days = excluded.interval_days, "
        "ease = excluded.ease, reps = excluded.reps, lapses = excluded.lapses, "
        "due_date = excluded.due_date, last_reviewed = excluded.last_reviewed",
        (
            expression_id,
            card.interval_days,
            card.ease,
            card.reps,
            card.lapses,
            card.due_date.isoformat(),
            today.isoformat(),
        ),
    )


def get_quiz_row(conn: sqlite3.Connection, expression_id: int) -> sqlite3.Row | None:
    return conn.execute(
        f"SELECT {_QUIZ_COLUMNS} {_QUIZ_JOINS} WHERE e.id = ?", (expression_id,)
    ).fetchone()


def list_due(conn: sqlite3.Connection, today: date, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        f"SELECT {_QUIZ_COLUMNS} {_QUIZ_JOINS} WHERE c.due_date <= ? "
        "ORDER BY c.due_date, e.id LIMIT ?",
        (today.isoformat(), limit),
    ).fetchall()


def list_new(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    """Not-yet-studied reading points in book order."""
    return conn.execute(
        f"SELECT {_QUIZ_COLUMNS} {_QUIZ_JOINS} "
        "WHERE c.expression_id IS NULL AND e.origin = 'reading_point' "
        "ORDER BY d.book_id, d.day_no, e.id LIMIT ?",
        (limit,),
    ).fetchall()


def count_mastered(conn: sqlite3.Connection, min_interval: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM review_cards WHERE interval_days >= ?", (min_interval,)
    ).fetchone()
    return row[0]


# --- Daily logs & XP ---------------------------------------------------------------


def get_daily_log(conn: sqlite3.Connection, day: date) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM daily_logs WHERE date = ?", (day.isoformat(),)).fetchone()


def record_answer(conn: sqlite3.Connection, day: date, is_new: bool) -> None:
    column = "new_done" if is_new else "reviews_done"
    conn.execute(
        f"INSERT INTO daily_logs (date, {column}) VALUES (?, 1) "
        f"ON CONFLICT (date) DO UPDATE SET {column} = {column} + 1",
        (day.isoformat(),),
    )


def mark_goal_met(conn: sqlite3.Connection, day: date) -> None:
    conn.execute("UPDATE daily_logs SET goal_met = 1 WHERE date = ?", (day.isoformat(),))


def list_goal_met_dates(conn: sqlite3.Connection) -> set[date]:
    rows = conn.execute("SELECT date FROM daily_logs WHERE goal_met = 1").fetchall()
    return {date.fromisoformat(r["date"]) for r in rows}


def list_daily_logs(conn: sqlite3.Connection, start: date, end: date) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM daily_logs WHERE date BETWEEN ? AND ? ORDER BY date",
        (start.isoformat(), end.isoformat()),
    ).fetchall()


def add_xp(
    conn: sqlite3.Connection, day: date, kind: str, points: int, expression_id: int | None
) -> None:
    conn.execute(
        "INSERT INTO xp_events (date, kind, points, expression_id) VALUES (?, ?, ?, ?)",
        (day.isoformat(), kind, points, expression_id),
    )


def get_total_xp(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COALESCE(SUM(points), 0) FROM xp_events").fetchone()[0]


def get_xp_on(conn: sqlite3.Connection, day: date) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(points), 0) FROM xp_events WHERE date = ?", (day.isoformat(),)
    ).fetchone()
    return row[0]


# --- AI example sentences ------------------------------------------------------------


def save_applications(
    conn: sqlite3.Connection, expression_id: int, scenario: str, sentences: list[AppliedSentence]
) -> None:
    conn.executemany(
        "INSERT INTO applications (expression_id, scenario, text_en, text_ko, highlight) "
        "VALUES (?, ?, ?, ?, ?)",
        [(expression_id, scenario, s.text_en, s.text_ko, s.highlight) for s in sentences],
    )
    conn.commit()


def list_applications(conn: sqlite3.Connection, expression_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, scenario, text_en, text_ko, highlight FROM applications "
        "WHERE expression_id = ? ORDER BY id DESC",
        (expression_id,),
    ).fetchall()
