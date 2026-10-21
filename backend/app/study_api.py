"""Study endpoints: review queue/grading, daily progress, AI example sentences and feedback."""

import calendar
import sqlite3
from collections.abc import Callable, Iterator
from datetime import date

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import repository
from app import study_repository as store
from app.coach import SCENARIOS, Coach, Scenario
from app.extraction import ExtractionError
from app.study import (
    DAILY_GOAL,
    MASTERED_INTERVAL,
    NEW_PER_DAY,
    XP_CORRECT,
    XP_CORRECT_HARD,
    XP_FEEDBACK,
    XP_GOAL_BONUS,
    XP_NEW_CARD,
    CardState,
    Grade,
    QuizKind,
    build_quiz,
    check_answer,
    compute_level,
    compute_streak,
    schedule,
)

# Upper bound on cards returned per session request.
MAX_QUEUE = 50


class DailyOut(BaseModel):
    date: date
    answered: int
    goal: int
    goal_met: bool
    xp_today: int


class QuizItem(BaseModel):
    expression_id: int
    day_no: int
    kind: QuizKind
    prompt_ko: str
    prompt_en: str
    hint: str
    is_new: bool


class QueueOut(BaseModel):
    items: list[QuizItem]
    today: DailyOut


class CheckIn(BaseModel):
    answer: str = Field(max_length=200)


class CheckOut(BaseModel):
    is_correct: bool
    expected: str
    meaning_ko: str


class GradeIn(BaseModel):
    grade: Grade


class GradeOut(BaseModel):
    xp_gained: int
    next_due: date
    goal_just_met: bool
    today: DailyOut


class CalendarDay(BaseModel):
    date: date
    status: str  # met | partial | rest | none | future


class ProgressOut(BaseModel):
    today: DailyOut
    streak_days: int
    level: int
    level_name: str
    xp_total: int
    xp_into_level: int
    xp_for_next: int
    mastered: int
    month: str
    calendar: list[CalendarDay]


class ApplyIn(BaseModel):
    scenario: Scenario


class ApplicationOut(BaseModel):
    id: int
    scenario: str
    scenario_label: str
    text_en: str
    text_ko: str
    highlight: str


class FeedbackIn(BaseModel):
    sentence: str = Field(min_length=1, max_length=300)


class FeedbackOut(BaseModel):
    uses_expression: bool
    is_natural: bool
    corrected_en: str
    explanation_ko: str
    xp_gained: int


def build_study_router(
    get_conn: Callable[[], Iterator[sqlite3.Connection]],
    get_today: Callable[[], date],
    get_coach: Callable[[], Coach],
) -> APIRouter:
    router = APIRouter(prefix="/api")

    def build_daily(conn: sqlite3.Connection, today: date) -> DailyOut:
        log = store.get_daily_log(conn, today)
        answered = (log["reviews_done"] + log["new_done"]) if log else 0
        return DailyOut(
            date=today,
            answered=answered,
            goal=DAILY_GOAL,
            goal_met=bool(log and log["goal_met"]),
            xp_today=store.get_xp_on(conn, today),
        )

    def to_quiz_item(row: sqlite3.Row) -> QuizItem:
        quiz = build_quiz(
            row["text"],
            row["highlight"],
            row["meaning_ko"],
            row["sentence_en"],
            row["sentence_ko"],
            row["reps"],
        )
        return QuizItem(
            expression_id=row["id"],
            day_no=row["day_no"],
            kind=quiz.kind,
            prompt_ko=quiz.prompt_ko,
            prompt_en=quiz.prompt_en,
            hint=quiz.hint,
            is_new=bool(row["is_new"]),
        )

    def get_quiz_row_or_404(conn: sqlite3.Connection, expression_id: int) -> sqlite3.Row:
        row = store.get_quiz_row(conn, expression_id)
        if row is None:
            raise HTTPException(404, f"expression {expression_id} not found")
        return row

    @router.get("/study/queue")
    def get_queue(conn: sqlite3.Connection = Depends(get_conn)) -> QueueOut:
        today = get_today()
        daily = build_daily(conn, today)
        log = store.get_daily_log(conn, today)
        new_done = log["new_done"] if log else 0
        due = store.list_due(conn, today, MAX_QUEUE)
        # Fill the daily goal with new cards when there aren't enough reviews due yet.
        shortfall = DAILY_GOAL - daily.answered - len(due)
        new_limit = min(max(NEW_PER_DAY - new_done, shortfall, 0), MAX_QUEUE - len(due))
        rows = due + store.list_new(conn, new_limit)
        return QueueOut(items=[to_quiz_item(r) for r in rows], today=daily)

    @router.post("/study/{expression_id}/check")
    def check(
        expression_id: int, body: CheckIn, conn: sqlite3.Connection = Depends(get_conn)
    ) -> CheckOut:
        row = get_quiz_row_or_404(conn, expression_id)
        quiz = build_quiz(
            row["text"],
            row["highlight"],
            row["meaning_ko"],
            row["sentence_en"],
            row["sentence_ko"],
            row["reps"],
        )
        expected = row["highlight"] if quiz.kind == "cloze" else row["text"]
        return CheckOut(
            is_correct=check_answer(quiz, body.answer),
            expected=expected,
            meaning_ko=row["meaning_ko"],
        )

    @router.post("/study/{expression_id}/grade")
    def grade(
        expression_id: int, body: GradeIn, conn: sqlite3.Connection = Depends(get_conn)
    ) -> GradeOut:
        get_quiz_row_or_404(conn, expression_id)
        today = get_today()
        card = store.get_card(conn, expression_id)
        is_new = card is None
        next_card = schedule(card or CardState(), body.grade, today)
        store.save_card(conn, expression_id, next_card, today)
        store.record_answer(conn, today, is_new)

        xp = 0
        if is_new:
            store.add_xp(conn, today, "new_card", XP_NEW_CARD, expression_id)
            xp += XP_NEW_CARD
        points = {"good": XP_CORRECT, "hard": XP_CORRECT_HARD}.get(body.grade, 0)
        if points:
            store.add_xp(conn, today, "correct", points, expression_id)
            xp += points

        log = store.get_daily_log(conn, today)
        goal_just_met = not log["goal_met"] and log["reviews_done"] + log["new_done"] >= DAILY_GOAL
        if goal_just_met:
            store.mark_goal_met(conn, today)
            store.add_xp(conn, today, "goal_bonus", XP_GOAL_BONUS, None)
            xp += XP_GOAL_BONUS
        conn.commit()
        return GradeOut(
            xp_gained=xp,
            next_due=next_card.due_date,
            goal_just_met=goal_just_met,
            today=build_daily(conn, today),
        )

    @router.get("/study/progress")
    def get_progress(
        month: str | None = None, conn: sqlite3.Connection = Depends(get_conn)
    ) -> ProgressOut:
        today = get_today()
        try:
            year, mon = map(int, (month or today.strftime("%Y-%m")).split("-"))
            first = date(year, mon, 1)
        except ValueError as exc:
            raise HTTPException(400, f"month must be YYYY-MM, got {month!r}") from exc
        last = date(year, mon, calendar.monthrange(year, mon)[1])

        streak = compute_streak(store.list_goal_met_dates(conn), today)
        logs = {r["date"]: r for r in store.list_daily_logs(conn, first, last)}
        days = []
        for day_no in range(1, last.day + 1):
            day = date(year, mon, day_no)
            log = logs.get(day.isoformat())
            if day > today:
                status = "future"
            elif log and log["goal_met"]:
                status = "met"
            elif day in streak.rest_dates:
                status = "rest"
            elif log and log["reviews_done"] + log["new_done"] > 0:
                status = "partial"
            else:
                status = "none"
            days.append(CalendarDay(date=day, status=status))

        total_xp = store.get_total_xp(conn)
        level = compute_level(total_xp)
        return ProgressOut(
            today=build_daily(conn, today),
            streak_days=streak.days,
            level=level.level,
            level_name=level.name,
            xp_total=total_xp,
            xp_into_level=level.xp_into_level,
            xp_for_next=level.xp_for_next,
            mastered=store.count_mastered(conn, MASTERED_INTERVAL),
            month=first.strftime("%Y-%m"),
            calendar=days,
        )

    def list_application_out(conn: sqlite3.Connection, expression_id: int) -> list[ApplicationOut]:
        return [
            ApplicationOut(**dict(r), scenario_label=SCENARIOS[r["scenario"]][0])
            for r in store.list_applications(conn, expression_id)
        ]

    def get_expression_or_404(conn: sqlite3.Connection, expression_id: int) -> sqlite3.Row:
        row = repository.get_expression(conn, expression_id)
        if row is None:
            raise HTTPException(404, f"expression {expression_id} not found")
        return row

    @router.get("/expressions/{expression_id}/applications")
    def list_applications(
        expression_id: int, conn: sqlite3.Connection = Depends(get_conn)
    ) -> list[ApplicationOut]:
        get_expression_or_404(conn, expression_id)
        return list_application_out(conn, expression_id)

    @router.post("/expressions/{expression_id}/applications", status_code=201)
    def create_applications(
        expression_id: int, body: ApplyIn, conn: sqlite3.Connection = Depends(get_conn)
    ) -> list[ApplicationOut]:
        row = get_expression_or_404(conn, expression_id)
        try:
            sentences = get_coach().apply(row["text"], row["meaning_ko"], body.scenario)
        except (ExtractionError, anthropic.APIError) as exc:
            raise HTTPException(502, f"example generation failed: {exc}") from exc
        store.save_applications(conn, expression_id, body.scenario, sentences)
        return list_application_out(conn, expression_id)

    @router.post("/expressions/{expression_id}/feedback")
    def create_feedback(
        expression_id: int, body: FeedbackIn, conn: sqlite3.Connection = Depends(get_conn)
    ) -> FeedbackOut:
        row = get_expression_or_404(conn, expression_id)
        try:
            feedback = get_coach().review(row["text"], row["meaning_ko"], body.sentence)
        except (ExtractionError, anthropic.APIError) as exc:
            raise HTTPException(502, f"feedback failed: {exc}") from exc
        xp = 0
        if feedback.uses_expression:
            store.add_xp(conn, get_today(), "feedback", XP_FEEDBACK, expression_id)
            conn.commit()
            xp = XP_FEEDBACK
        return FeedbackOut(**feedback.model_dump(), xp_gained=xp)

    return router
