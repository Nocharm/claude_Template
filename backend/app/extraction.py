"""Claude-backed extraction: page classification, per-DAY OCR/structuring, cross-DAY relations."""

import base64
import logging
from dataclasses import dataclass
from typing import Literal, Protocol

import anthropic
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Server-side retry on another model when a safety classifier declines (Claude API only).
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Non-streaming ceiling that stays under SDK HTTP timeouts; a DAY needs ~4–8K output tokens.
MAX_OUTPUT_TOKENS = 16000


class ExtractionError(Exception):
    """Claude returned no usable structured output."""


# --- Structured output schemas -------------------------------------------------


class Example(BaseModel):
    text_en: str
    text_ko: str


class TipItem(BaseModel):
    text: str = Field(
        description="English expression. For a 'sense' box, repeat the base expression."
    )
    meaning_ko: str
    examples: list[Example]


class TipBox(BaseModel):
    kind: Literal["similar", "sense"] = Field(
        description="'similar' = similar/alternative expressions box, "
        "'sense' = other meanings/usages of the same expression box."
    )
    title_ko: str = Field(
        description="The box subtitle as printed, e.g. '원어민들이 자주 쓰는 비슷한 표현'."
    )
    items: list[TipItem]


class ExpressionItem(BaseModel):
    text: str = Field(
        description="The expression as the explanation names it, e.g. 'have always been ~'."
    )
    highlight: str = Field(
        description="Exact substring of the sentence's text_en that is highlighted for this "
        "expression, character for character. Empty string if none."
    )
    meaning_ko: str = Field(description="Short Korean meaning, e.g. '(우연히) 발견하다, 보다'.")
    explanation_ko: str = Field(description="Full Korean explanation paragraph as printed.")
    examples: list[Example] = Field(description="'e.g.' examples printed under this expression.")
    tip_boxes: list[TipBox] = Field(description="Callout boxes attached to this expression.")


class Sentence(BaseModel):
    no: int
    text_en: str
    text_ko: str
    expressions: list[ExpressionItem]


class DayExtraction(BaseModel):
    day_no: int
    title: str
    passage_en: str = Field(description="Full main passage; paragraphs separated by '\\n'.")
    sentences: list[Sentence]


class PageInfo(BaseModel):
    page: int = Field(description="The page number given in the label before the image.")
    kind: Literal["unit_start", "unit_content", "other"]
    unit_no: int | None = Field(description="Lesson number when kind is unit_start, else null.")


class PageClassification(BaseModel):
    pages: list[PageInfo]


class Relation(BaseModel):
    from_id: int
    to_id: int
    type: Literal["similar", "contrast"]
    note_ko: str = Field(description="One short Korean line explaining the link.")


class RelationSet(BaseModel):
    relations: list[Relation]


@dataclass
class ExpressionBrief:
    id: int
    day_no: int
    text: str
    meaning_ko: str


# --- Prompts -------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You digitize Korean-published English conversation textbooks for a personal study app. "
    "Transcribe text exactly as printed — keep spelling, punctuation and Korean wording; "
    "never paraphrase, translate or invent content that is not on the page."
)

CLASSIFY_PROMPT = """Classify each page image above.
- unit_start: the first page of a numbered lesson (e.g. "DAY 3", "Unit 5", "Chapter 2"); \
set unit_no to that number.
- unit_content: a continuation page of the current lesson (explanations, examples, exercises).
- other: cover, contents, preface, appendix, answer keys, index, blank pages.
Return one entry per page label."""

EXTRACT_PROMPT = """These pages are one lesson (DAY {day_no}) of the book, in order.
Typical layout: a main English passage, then numbered key sentences (English + Korean \
translation) with highlighted expressions, each expression explained in Korean with "e.g." \
examples, sometimes followed by a callout box of similar expressions or other usages.
Extract the whole lesson. Explanations that continue across pages belong to the same \
expression. Keep sentence numbers as printed."""

RELATIONS_PROMPT = """Below are expressions from one textbook, one per line as \
id<TAB>DAY<TAB>expression<TAB>Korean meaning.
Find pairs a learner would benefit from seeing linked:
- similar: different expressions with close meaning or use (prefer pairs from different DAYs).
- contrast: expressions often confused or explicitly compared (e.g. come out vs go out).
Skip pairs from the same sentence and trivial links. Return at most {limit} of the most useful \
relations, using only ids from the list.

{lines}"""

MAX_RELATIONS = 300


# --- Extractor -----------------------------------------------------------------


@dataclass
class PageImage:
    page: int
    jpeg: bytes


class Extractor(Protocol):
    def classify_pages(self, images: list[PageImage]) -> list[PageInfo]: ...

    def extract_day(self, day_no: int, images: list[PageImage]) -> DayExtraction: ...

    def find_relations(self, expressions: list[ExpressionBrief]) -> list[Relation]: ...


def build_image_content(images: list[PageImage]) -> list[dict]:
    content: list[dict] = []
    for image in images:
        content.append({"type": "text", "text": f"Page {image.page}"})
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(image.jpeg).decode("ascii"),
                },
            }
        )
    return content


def parse_structured[T: BaseModel](
    client: anthropic.Anthropic,
    model: str,
    system: str,
    content: list[dict],
    output_format: type[T],
    task: str,
) -> T:
    """One structured-output call; raises ExtractionError instead of returning partial data."""
    response = client.beta.messages.parse(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        system=system,
        messages=[{"role": "user", "content": content}],
        output_format=output_format,
    )
    logger.info(
        "claude call finished",
        extra={
            "task": task,
            "request_id": response._request_id,
            "stop_reason": response.stop_reason,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    )
    if response.stop_reason == "refusal":
        raise ExtractionError(f"{task}: request declined ({response.stop_details})")
    if response.stop_reason == "max_tokens":
        raise ExtractionError(f"{task}: output truncated at {MAX_OUTPUT_TOKENS} tokens")
    if response.parsed_output is None:
        raise ExtractionError(f"{task}: no structured output (stop={response.stop_reason})")
    return response.parsed_output


class ClaudeExtractor:
    def __init__(self, client: anthropic.Anthropic, model: str) -> None:
        self._client = client
        self._model = model

    def _parse[T: BaseModel](self, content: list[dict], output_format: type[T], task: str) -> T:
        return parse_structured(
            self._client, self._model, SYSTEM_PROMPT, content, output_format, task
        )

    def classify_pages(self, images: list[PageImage]) -> list[PageInfo]:
        content = build_image_content(images) + [{"type": "text", "text": CLASSIFY_PROMPT}]
        pages = f"{images[0].page}-{images[-1].page}"
        return self._parse(content, PageClassification, f"classify pages {pages}").pages

    def extract_day(self, day_no: int, images: list[PageImage]) -> DayExtraction:
        prompt = EXTRACT_PROMPT.format(day_no=day_no)
        content = build_image_content(images) + [{"type": "text", "text": prompt}]
        return self._parse(content, DayExtraction, f"extract day {day_no}")

    def find_relations(self, expressions: list[ExpressionBrief]) -> list[Relation]:
        lines = "\n".join(f"{e.id}\t{e.day_no}\t{e.text}\t{e.meaning_ko}" for e in expressions)
        prompt = RELATIONS_PROMPT.format(limit=MAX_RELATIONS, lines=lines)
        content = [{"type": "text", "text": prompt}]
        return self._parse(content, RelationSet, "find relations").relations
