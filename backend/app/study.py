"""Pure study logic: spaced-repetition scheduling, quiz building/grading, streaks and levels."""

import re
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Literal

Grade = Literal["again", "hard", "good"]
QuizKind = Literal["cloze", "ko_to_en"]

# Answers per day that earn the stamp (docs/UI.md: review 10 + new 5).
DAILY_GOAL = 15
# New cards introduced per day before due reviews are exhausted.
NEW_PER_DAY = 5
# A card whose interval reaches this many days counts as "mastered".
MASTERED_INTERVAL = 21
# SM-2 ease bounds/start; lower ease = shorter intervals for hard cards.
START_EASE = 2.5
MIN_EASE = 1.3

# Points per action (docs/UI.md XP table).
XP_NEW_CARD = 5
XP_CORRECT = 10
XP_CORRECT_HARD = 5
XP_FEEDBACK = 15
XP_GOAL_BONUS = 30
XP_COMIC_READ = 10

LEVEL_NAMES = ["새 노트", "첫 페이지", "메모 습관", "꾸준한 메모러", "형광펜 장인", "노트 마스터"]


# --- Spaced repetition -----------------------------------------------------------


@dataclass(frozen=True)
class CardState:
    interval_days: int = 0
    ease: float = START_EASE
    reps: int = 0
    lapses: int = 0
    due_date: date | None = None


def schedule(card: CardState, grade: Grade, today: date) -> CardState:
    """SM-2-lite: 'again' brings the card back today, 'good' grows the interval by ease."""
    if grade == "again":
        return replace(
            card,
            interval_days=0,
            ease=max(MIN_EASE, card.ease - 0.2),
            reps=0,
            lapses=card.lapses + 1,
            due_date=today,
        )
    if grade == "hard":
        interval = max(1, round(card.interval_days * 1.2))
        ease = max(MIN_EASE, card.ease - 0.15)
    elif card.reps == 0:
        interval, ease = 1, card.ease
    elif card.reps == 1:
        interval, ease = 3, card.ease
    else:
        interval, ease = (
            max(card.interval_days + 1, round(card.interval_days * card.ease)),
            card.ease,
        )
    return replace(
        card,
        interval_days=interval,
        ease=ease,
        reps=card.reps + 1,
        due_date=today + timedelta(days=interval),
    )


# --- Quiz ------------------------------------------------------------------------


@dataclass(frozen=True)
class Quiz:
    kind: QuizKind
    prompt_ko: str
    prompt_en: str  # cloze sentence with the answer replaced by "____"; empty for ko_to_en
    hint: str
    answers: tuple[str, ...]


def normalize_answer(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[~.,!?\"]", " ", text.lower())
    return " ".join(text.split())


def build_quiz(
    text: str,
    highlight: str,
    meaning_ko: str,
    sentence_en: str | None,
    sentence_ko: str | None,
    reps: int,
) -> Quiz:
    """Alternate cloze and Korean→English by repetition count; cloze needs a findable highlight."""
    expected = normalize_answer(text)
    answers = tuple(dict.fromkeys(a for a in (expected, normalize_answer(highlight)) if a))
    start = sentence_en.lower().find(highlight.lower()) if sentence_en and highlight else -1
    if reps % 2 == 0 and start >= 0:
        blanked = sentence_en[:start] + "____" + sentence_en[start + len(highlight) :]
        return Quiz(
            kind="cloze",
            prompt_ko=sentence_ko or meaning_ko,
            prompt_en=blanked,
            hint=highlight[:1],
            answers=(normalize_answer(highlight),),
        )
    return Quiz(kind="ko_to_en", prompt_ko=meaning_ko, prompt_en="", hint=text[:1], answers=answers)


def check_answer(quiz: Quiz, answer: str) -> bool:
    return normalize_answer(answer) in quiz.answers


# --- Streaks & levels --------------------------------------------------------------


@dataclass(frozen=True)
class Streak:
    days: int
    rest_dates: frozenset[date]


def compute_streak(goal_met_dates: set[date], today: date) -> Streak:
    """Count consecutive goal days back from today; one missed day per ISO week is a free rest."""
    cursor = today if today in goal_met_dates else today - timedelta(days=1)
    days = 0
    rests: set[date] = set()
    rest_weeks: set[tuple[int, int]] = set()
    while True:
        if cursor in goal_met_dates:
            days += 1
        else:
            week = cursor.isocalendar()[:2]
            # A rest only bridges to an earlier goal day; never count trailing gaps.
            if week in rest_weeks or (cursor - timedelta(days=1)) not in goal_met_dates:
                break
            rest_weeks.add(week)
            rests.add(cursor)
        cursor -= timedelta(days=1)
    return Streak(days=days, rest_dates=frozenset(rests))


@dataclass(frozen=True)
class Level:
    level: int
    name: str
    xp_into_level: int
    xp_for_next: int


def compute_level(total_xp: int) -> Level:
    """Level n starts at 100·n(n-1)/2 XP, so each level needs 100 more XP than the last."""
    level, floor = 1, 0
    while total_xp >= floor + 100 * level:
        floor += 100 * level
        level += 1
    name = LEVEL_NAMES[min(level, len(LEVEL_NAMES)) - 1]
    return Level(level=level, name=name, xp_into_level=total_xp - floor, xp_for_next=100 * level)
