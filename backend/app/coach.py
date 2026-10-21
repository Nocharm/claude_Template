"""Claude-backed study helpers: situational example sentences and sentence feedback."""

from typing import Literal, Protocol

import anthropic
from pydantic import BaseModel, Field

from app.extraction import parse_structured

Scenario = Literal["work", "travel", "daily", "romance"]

# Korean label shown in the UI → situation described to the model.
SCENARIOS: dict[Scenario, tuple[str, str]] = {
    "work": ("회사", "at work, with coworkers or in meetings"),
    "travel": ("여행", "while traveling: airports, hotels, sightseeing"),
    "daily": ("일상", "in everyday life with friends or family"),
    "romance": ("연애", "on a date or with a partner"),
}

COACH_SYSTEM = (
    "You are a friendly English coach for a Korean adult learner. Write natural, everyday "
    "spoken English — short sentences a native speaker would actually say. Korean explanations "
    "are concise and kind."
)


class AppliedSentence(BaseModel):
    text_en: str
    text_ko: str = Field(description="Natural Korean translation.")
    highlight: str = Field(
        description="Exact substring of text_en where the target expression appears (as inflected)."
    )


class ApplicationSet(BaseModel):
    sentences: list[AppliedSentence]


class SentenceFeedback(BaseModel):
    uses_expression: bool = Field(description="Whether the learner used the target expression.")
    is_natural: bool = Field(description="Grammatical and natural as written.")
    corrected_en: str = Field(description="Minimal correction; identical to the input if fine.")
    explanation_ko: str = Field(description="1–3 sentences in Korean on what to fix, or praise.")


class Coach(Protocol):
    def apply(self, text: str, meaning_ko: str, scenario: Scenario) -> list[AppliedSentence]: ...

    def review(self, text: str, meaning_ko: str, sentence: str) -> SentenceFeedback: ...


class ClaudeCoach:
    def __init__(self, client: anthropic.Anthropic, model: str) -> None:
        self._client = client
        self._model = model

    def apply(self, text: str, meaning_ko: str, scenario: Scenario) -> list[AppliedSentence]:
        prompt = (
            f"Target expression: {text} (뜻: {meaning_ko})\n"
            f"Write 2 short example sentences using it naturally {SCENARIOS[scenario][1]}. "
            "Inflect it as needed."
        )
        content = [{"type": "text", "text": prompt}]
        result = parse_structured(
            self._client, self._model, COACH_SYSTEM, content, ApplicationSet, f"apply {text}"
        )
        return result.sentences

    def review(self, text: str, meaning_ko: str, sentence: str) -> SentenceFeedback:
        prompt = (
            f"Target expression: {text} (뜻: {meaning_ko})\n"
            "The learner wrote the sentence below to practice it. Check it.\n"
            f"<learner_sentence>{sentence}</learner_sentence>"
        )
        content = [{"type": "text", "text": prompt}]
        return parse_structured(
            self._client, self._model, COACH_SYSTEM, content, SentenceFeedback, f"review {text}"
        )
