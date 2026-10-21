"""Shared test fixtures: a fake Claude extractor and small generated PDFs."""

from pathlib import Path

import pypdfium2 as pdfium
import pytest

from app.extraction import DayExtraction, ExpressionBrief, PageImage, PageInfo, Relation

FIXTURES = Path(__file__).parent / "fixtures"

# Page layout of the generated test book: front matter, DAY 3 (3 pages), DAY 4 (2 pages), index.
PAGE_PLAN: dict[int, tuple[str, int | None]] = {
    1: ("other", None),
    2: ("unit_start", 3),
    3: ("unit_content", None),
    4: ("unit_content", None),
    5: ("unit_start", 4),
    6: ("unit_content", None),
    7: ("other", None),
}


def load_day3() -> DayExtraction:
    return DayExtraction.model_validate_json((FIXTURES / "day3.json").read_text())


def build_day4() -> DayExtraction:
    return DayExtraction.model_validate(
        {
            "day_no": 4,
            "title": "A Much-Needed Jeju Getaway",
            "passage_en": "Have you ever had one of those cravings where you just want to get "
            "out of the house?",
            "sentences": [
                {
                    "no": 1,
                    "text_en": "Have you ever had one of those cravings where you just want to "
                    "get out of the house?",
                    "text_ko": "[test translation]",
                    "expressions": [
                        {
                            "text": "get out of the house",
                            "highlight": "get out of the house",
                            "meaning_ko": "[test meaning]",
                            "explanation_ko": "",
                            "examples": [],
                            "tip_boxes": [],
                        }
                    ],
                }
            ],
        }
    )


class FakeExtractor:
    """Stands in for Claude; records calls so tests can assert what was (not) re-run."""

    def __init__(self, fail_on_day: int | None = None) -> None:
        self.fail_on_day = fail_on_day
        self.classify_calls: list[list[int]] = []
        self.extract_calls: list[int] = []
        self.relation_calls: list[list[ExpressionBrief]] = []

    def classify_pages(self, images: list[PageImage]) -> list[PageInfo]:
        self.classify_calls.append([i.page for i in images])
        return [
            PageInfo(page=i.page, kind=PAGE_PLAN[i.page][0], unit_no=PAGE_PLAN[i.page][1])
            for i in images
        ]

    def extract_day(self, day_no: int, images: list[PageImage]) -> DayExtraction:
        self.extract_calls.append(day_no)
        if day_no == self.fail_on_day:
            raise RuntimeError(f"simulated API failure on day {day_no}")
        return load_day3() if day_no == 3 else build_day4()

    def find_relations(self, expressions: list[ExpressionBrief]) -> list[Relation]:
        self.relation_calls.append(expressions)
        by_text = {e.text: e.id for e in expressions}
        return [
            Relation(
                from_id=by_text["come out"],
                to_id=by_text["get out of the house"],
                type="similar",
                note_ko="밖으로 나가는 움직임",
            ),
            # Invalid id must be dropped, not stored.
            Relation(from_id=by_text["spot"], to_id=999_999, type="contrast", note_ko="x"),
        ]


def write_pdf(path: Path, pages: int) -> Path:
    pdf = pdfium.PdfDocument.new()
    for _ in range(pages):
        pdf.new_page(420, 595)
    pdf.save(path)
    pdf.close()
    return path


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    return write_pdf(tmp_path / "book.pdf", len(PAGE_PLAN))
