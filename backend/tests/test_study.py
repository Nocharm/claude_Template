"""Pure study logic tests: scheduling, quizzes, streaks, levels."""

from datetime import date, timedelta

from app.study import (
    CardState,
    build_quiz,
    check_answer,
    compute_level,
    compute_streak,
    schedule,
)

TODAY = date(2026, 10, 21)  # a Wednesday


def test_schedule_grows_intervals_and_resets_on_again() -> None:
    # Arrange / Act
    first = schedule(CardState(), "good", TODAY)
    second = schedule(first, "good", TODAY)
    third = schedule(second, "good", TODAY)
    lapsed = schedule(third, "again", TODAY)

    # Assert
    assert [first.interval_days, second.interval_days, third.interval_days] == [1, 3, 8]
    assert third.due_date == TODAY + timedelta(days=8)
    assert (lapsed.interval_days, lapsed.reps, lapsed.lapses) == (0, 0, 1)
    assert lapsed.due_date == TODAY
    assert lapsed.ease < third.ease


def test_schedule_hard_keeps_ease_above_floor() -> None:
    card = CardState(interval_days=10, ease=1.35, reps=4)

    result = schedule(card, "hard", TODAY)

    assert result.interval_days == 12
    assert result.ease == 1.3


def test_build_quiz_alternates_cloze_and_korean_to_english() -> None:
    # Arrange
    args = (
        "come out",
        "came out",
        "나오다",
        '"Did you check the weather forecast before we came out?" I asked.',
        '"나오기 전에 일기 예보 확인했어?" 내가 물었다.',
    )

    # Act
    cloze = build_quiz(*args, reps=0)
    ko_to_en = build_quiz(*args, reps=1)

    # Assert
    assert cloze.kind == "cloze"
    assert cloze.prompt_en == '"Did you check the weather forecast before we ____?" I asked.'
    assert check_answer(cloze, "Came out")
    assert not check_answer(cloze, "come out")
    assert ko_to_en.kind == "ko_to_en"
    assert check_answer(ko_to_en, "come out")


def test_build_quiz_falls_back_when_highlight_missing_and_normalizes_answers() -> None:
    quiz = build_quiz("have always been ~", "", "항상 ~해 왔다", None, None, reps=0)

    assert quiz.kind == "ko_to_en"
    assert check_answer(quiz, "  Have always been. ")
    assert check_answer(build_quiz("couldn't resist", "", "x", None, None, 0), "couldn’t resist")


def test_compute_streak_uses_one_rest_day_per_week() -> None:
    # Arrange: met Mon–Tue this week, missed Wed (today not done yet) → streak from yesterday
    met = {TODAY - timedelta(days=d) for d in (1, 2, 4, 5, 6)}  # Tue, Mon, last Sat, Fri, Thu

    # Act
    streak = compute_streak(met, TODAY)

    # Assert: Sun (day 3) is bridged as a rest in last week's ISO week
    assert streak.days == 5
    assert streak.rest_dates == {TODAY - timedelta(days=3)}


def test_compute_streak_breaks_on_two_missed_days() -> None:
    met = {TODAY, TODAY - timedelta(days=3)}

    streak = compute_streak(met, TODAY)

    assert streak.days == 1
    assert streak.rest_dates == frozenset()


def test_compute_level_thresholds() -> None:
    assert compute_level(0).level == 1
    assert compute_level(99).level == 1
    assert (compute_level(100).level, compute_level(100).xp_into_level) == (2, 0)
    level = compute_level(1240)
    assert (level.level, level.name, level.xp_into_level, level.xp_for_next) == (
        5,
        "형광펜 장인",
        240,
        500,
    )
