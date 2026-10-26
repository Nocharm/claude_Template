"""SQLite connection helpers and schema."""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL UNIQUE,
    page_count INTEGER,
    status TEXT NOT NULL,
    progress_done INTEGER NOT NULL DEFAULT 0,
    progress_total INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS days (
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    day_no INTEGER NOT NULL,
    title TEXT NOT NULL,
    passage_en TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    UNIQUE (book_id, day_no)
);

CREATE TABLE IF NOT EXISTS sentences (
    id INTEGER PRIMARY KEY,
    day_id INTEGER NOT NULL REFERENCES days(id) ON DELETE CASCADE,
    no INTEGER NOT NULL,
    text_en TEXT NOT NULL,
    text_ko TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expressions (
    id INTEGER PRIMARY KEY,
    day_id INTEGER NOT NULL REFERENCES days(id) ON DELETE CASCADE,
    sentence_id INTEGER REFERENCES sentences(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES expressions(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    highlight TEXT NOT NULL DEFAULT '',
    meaning_ko TEXT NOT NULL,
    explanation_ko TEXT NOT NULL DEFAULT '',
    origin TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS examples (
    id INTEGER PRIMARY KEY,
    expression_id INTEGER NOT NULL REFERENCES expressions(id) ON DELETE CASCADE,
    text_en TEXT NOT NULL,
    text_ko TEXT NOT NULL,
    origin TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY,
    from_id INTEGER NOT NULL REFERENCES expressions(id) ON DELETE CASCADE,
    to_id INTEGER NOT NULL REFERENCES expressions(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    UNIQUE (from_id, to_id, type)
);

CREATE TABLE IF NOT EXISTS review_cards (
    expression_id INTEGER PRIMARY KEY REFERENCES expressions(id) ON DELETE CASCADE,
    interval_days INTEGER NOT NULL,
    ease REAL NOT NULL,
    reps INTEGER NOT NULL,
    lapses INTEGER NOT NULL,
    due_date TEXT NOT NULL,
    last_reviewed TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_logs (
    date TEXT PRIMARY KEY,
    reviews_done INTEGER NOT NULL DEFAULT 0,
    new_done INTEGER NOT NULL DEFAULT 0,
    goal_met INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS xp_events (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    kind TEXT NOT NULL,
    points INTEGER NOT NULL,
    expression_id INTEGER REFERENCES expressions(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY,
    expression_id INTEGER NOT NULL REFERENCES expressions(id) ON DELETE CASCADE,
    scenario TEXT NOT NULL,
    text_en TEXT NOT NULL,
    text_ko TEXT NOT NULL,
    highlight TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS comics (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    title_ko TEXT NOT NULL DEFAULT '',
    expression_ids TEXT NOT NULL,
    error TEXT,
    read_at TEXT
);

CREATE TABLE IF NOT EXISTS comic_panels (
    id INTEGER PRIMARY KEY,
    comic_id INTEGER NOT NULL REFERENCES comics(id) ON DELETE CASCADE,
    no INTEGER NOT NULL,
    script TEXT NOT NULL,
    image_file TEXT,
    UNIQUE (comic_id, no)
);
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    appearance TEXT NOT NULL,
    status TEXT NOT NULL,
    final_version INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS character_versions (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    no INTEGER NOT NULL,
    instruction TEXT NOT NULL,
    appearance TEXT NOT NULL,
    image_file TEXT NOT NULL,
    UNIQUE (character_id, no)
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """Open a connection owned by one request or job; never share it concurrently."""
    # FastAPI opens a dependency in one worker thread and runs the endpoint in another,
    # so the same-thread check must be off; each connection is still used by one caller.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        # WAL lets the reader UI query while a background ingest is writing.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
