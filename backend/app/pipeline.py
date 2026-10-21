"""One-time book ingest: classify pages → extract each DAY → link expressions."""

import logging
import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from app import pdf, repository
from app.extraction import DayExtraction, Extractor, PageClassification, PageInfo

logger = logging.getLogger(__name__)

# Pages per classification request — fewer requests, still small payloads at CLASSIFY_EDGE.
CLASSIFY_BATCH = 20
# Parallel DAY extractions; bounded to stay well under API rate limits.
EXTRACT_WORKERS = 4

ConnFactory = Callable[[], sqlite3.Connection]


@dataclass
class DaySpan:
    day_no: int
    pages: list[int]


def group_day_spans(pages: list[PageInfo]) -> list[DaySpan]:
    """Turn per-page labels into DAY page ranges; an 'other' page closes the open DAY."""
    spans: list[DaySpan] = []
    current: DaySpan | None = None
    for info in sorted(pages, key=lambda p: p.page):
        if info.kind == "unit_start":
            day_no = info.unit_no if info.unit_no is not None else len(spans) + 1
            current = DaySpan(day_no=day_no, pages=[info.page])
            spans.append(current)
        elif info.kind == "unit_content" and current is not None:
            current.pages.append(info.page)
        else:
            current = None
    return spans


def _classify(
    pdf_path: Path, page_count: int, cache_file: Path, extractor: Extractor
) -> list[PageInfo]:
    if cache_file.exists():
        return PageClassification.model_validate_json(cache_file.read_text()).pages
    pages: list[PageInfo] = []
    for start in range(1, page_count + 1, CLASSIFY_BATCH):
        batch = list(range(start, min(start + CLASSIFY_BATCH, page_count + 1)))
        images = pdf.render_pages(pdf_path, batch, pdf.CLASSIFY_EDGE)
        result = extractor.classify_pages(images)
        # Keep only labels for pages we sent; the model echoes page numbers from the labels.
        pages.extend(p for p in result if p.page in batch)
    cache_file.write_text(PageClassification(pages=pages).model_dump_json(indent=1))
    return pages


def _extract(
    pdf_path: Path, span: DaySpan, cache_file: Path, extractor: Extractor
) -> DayExtraction:
    if cache_file.exists():
        return DayExtraction.model_validate_json(cache_file.read_text())
    images = pdf.render_pages(pdf_path, span.pages, pdf.OCR_EDGE)
    day = extractor.extract_day(span.day_no, images)
    # The page heading found in classification is authoritative for numbering.
    day.day_no = span.day_no
    cache_file.write_text(day.model_dump_json(indent=1))
    return day


def ingest_book(
    conn_factory: ConnFactory, book_id: int, book_dir: Path, extractor: Extractor
) -> None:
    """Run (or resume) the ingest; per-step caches in book_dir make retries cheap."""
    pdf_path = book_dir / "source.pdf"
    with closing(conn_factory()) as conn:
        try:
            _run(conn, book_id, pdf_path, book_dir, extractor)
        except Exception as exc:
            logger.exception("ingest failed", extra={"book_id": book_id})
            repository.update_book(
                conn, book_id, status="failed", error=f"{type(exc).__name__}: {exc}"
            )
            raise


def _run(
    conn: sqlite3.Connection, book_id: int, pdf_path: Path, book_dir: Path, extractor: Extractor
) -> None:
    page_count = pdf.count_pages(pdf_path)
    repository.update_book(conn, book_id, status="classifying", page_count=page_count, error=None)
    pages = _classify(pdf_path, page_count, book_dir / "pages.json", extractor)
    spans = group_day_spans(pages)
    if not spans:
        raise ValueError(f"no lesson start pages found in {page_count} pages")

    days_dir = book_dir / "days"
    days_dir.mkdir(exist_ok=True)
    todo = [s for s in spans if not repository.has_day(conn, book_id, s.day_no)]
    done = len(spans) - len(todo)
    repository.update_book(
        conn, book_id, status="extracting", progress_done=done, progress_total=len(spans)
    )
    with ThreadPoolExecutor(max_workers=EXTRACT_WORKERS) as pool:
        futures = {
            pool.submit(_extract, pdf_path, s, days_dir / f"{s.day_no}.json", extractor): s
            for s in todo
        }
        for future in as_completed(futures):
            span = futures[future]
            day = future.result()
            # DB writes stay on this thread; sqlite connections aren't shared across threads.
            repository.save_day(conn, book_id, day, span.pages[0], span.pages[-1])
            done += 1
            repository.update_book(conn, book_id, progress_done=done)
            logger.info("day saved", extra={"book_id": book_id, "day_no": span.day_no})

    repository.update_book(conn, book_id, status="linking")
    expressions = repository.list_reading_points(conn, book_id)
    if len(expressions) > 1:
        relations = extractor.find_relations(expressions)
        saved = repository.save_relations(conn, relations, {e.id for e in expressions})
        logger.info("relations saved", extra={"book_id": book_id, "count": saved})
    repository.update_book(conn, book_id, status="done")
