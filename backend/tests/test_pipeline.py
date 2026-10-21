"""Ingest pipeline tests with a fake extractor (no network)."""

import shutil
from contextlib import closing
from pathlib import Path

import pytest

from app import db, pipeline, repository
from app.extraction import PageInfo, Relation
from tests.conftest import FakeExtractor


def make_book(tmp_path: Path, sample_pdf: Path) -> tuple[Path, Path, int]:
    db_path = tmp_path / "app.db"
    db.init_db(db_path)
    book_dir = tmp_path / "books" / "hash"
    book_dir.mkdir(parents=True)
    shutil.copy(sample_pdf, book_dir / "source.pdf")
    with closing(db.connect(db_path)) as conn:
        book_id = repository.create_book(conn, "book", "book.pdf", "hash")
    return db_path, book_dir, book_id


def test_group_day_spans_splits_on_starts_and_other_pages() -> None:
    # Arrange
    pages = [
        PageInfo(page=1, kind="other", unit_no=None),
        PageInfo(page=3, kind="unit_content", unit_no=None),  # orphan before any start
        PageInfo(page=2, kind="unit_start", unit_no=1),
        PageInfo(page=4, kind="unit_start", unit_no=None),  # number unreadable
        PageInfo(page=5, kind="unit_content", unit_no=None),
        PageInfo(page=6, kind="other", unit_no=None),
        PageInfo(page=7, kind="unit_content", unit_no=None),  # after 'other' → dropped
    ]

    # Act
    spans = pipeline.group_day_spans(pages)

    # Assert
    assert [(s.day_no, s.pages) for s in spans] == [(1, [2, 3]), (2, [4, 5])]


def test_ingest_book_stores_days_expressions_and_relations(
    tmp_path: Path, sample_pdf: Path
) -> None:
    # Arrange
    db_path, book_dir, book_id = make_book(tmp_path, sample_pdf)
    extractor = FakeExtractor()

    # Act
    pipeline.ingest_book(lambda: db.connect(db_path), book_id, book_dir, extractor)

    # Assert
    with closing(db.connect(db_path)) as conn:
        book = repository.get_book(conn, book_id)
        assert (book["status"], book["progress_done"], book["progress_total"]) == ("done", 2, 2)
        days = repository.list_days(conn, book_id)
        assert [(d["day_no"], d["expression_count"]) for d in days] == [(3, 7), (4, 1)]
        day3 = repository.get_day(conn, days[0]["id"])
        assert (day3["page_start"], day3["page_end"]) == (2, 4)

        spot_id = conn.execute("SELECT id FROM expressions WHERE text = 'spot'").fetchone()[0]
        related = {(r["text"], r["type"]) for r in repository.list_related(conn, spot_id)}
        assert ("notice", "similar") in related
        assert ("catch sight of", "similar") in related
        assert ("couldn't resist", "same_sentence") in related

        come_out = conn.execute(
            "SELECT id FROM expressions WHERE text = 'come out' AND origin = 'reading_point'"
        ).fetchone()[0]
        related = [
            (r["meaning_ko"], r["type"], r["day_no"])
            for r in repository.list_related(conn, come_out)
        ]
        assert ("(비밀이나 정보가) 밝혀지다, 드러나다", "sense", 3) in related
        assert ("[test meaning]", "similar", 4) in related
        # The relation pointing at an unknown id was dropped.
        assert (
            conn.execute("SELECT COUNT(*) FROM relations WHERE type = 'contrast'").fetchone()[0]
            == 0
        )

    assert extractor.classify_calls == [[1, 2, 3, 4, 5, 6, 7]]
    assert sorted(extractor.extract_calls) == [3, 4]
    assert (book_dir / "pages.json").exists()
    assert (book_dir / "days" / "3.json").exists()


def test_ingest_book_resumes_without_repeating_finished_work(
    tmp_path: Path, sample_pdf: Path
) -> None:
    # Arrange: first run fails on DAY 4
    db_path, book_dir, book_id = make_book(tmp_path, sample_pdf)
    failing = FakeExtractor(fail_on_day=4)
    with pytest.raises(RuntimeError, match="day 4"):
        pipeline.ingest_book(lambda: db.connect(db_path), book_id, book_dir, failing)
    with closing(db.connect(db_path)) as conn:
        book = repository.get_book(conn, book_id)
        assert book["status"] == "failed"
        assert "simulated API failure" in book["error"]

    # Act: retry with a working extractor
    retry = FakeExtractor()
    pipeline.ingest_book(lambda: db.connect(db_path), book_id, book_dir, retry)

    # Assert: classification cached, DAY 3 kept, only DAY 4 extracted again
    assert retry.classify_calls == []
    assert retry.extract_calls == [4]
    with closing(db.connect(db_path)) as conn:
        assert repository.get_book(conn, book_id)["status"] == "done"
        assert [d["day_no"] for d in repository.list_days(conn, book_id)] == [3, 4]


def test_save_relations_skips_self_links_and_unknown_ids(tmp_path: Path, sample_pdf: Path) -> None:
    # Arrange
    db_path, book_dir, book_id = make_book(tmp_path, sample_pdf)
    pipeline.ingest_book(lambda: db.connect(db_path), book_id, book_dir, FakeExtractor())
    with closing(db.connect(db_path)) as conn:
        ids = [e.id for e in repository.list_reading_points(conn, book_id)]
        relations = [
            Relation(from_id=ids[0], to_id=ids[0], type="similar", note_ko=""),
            Relation(from_id=ids[0], to_id=-1, type="similar", note_ko=""),
            Relation(from_id=ids[0], to_id=ids[-1], type="contrast", note_ko="ok"),
        ]

        # Act
        saved = repository.save_relations(conn, relations, set(ids))

    # Assert
    assert saved == 1
