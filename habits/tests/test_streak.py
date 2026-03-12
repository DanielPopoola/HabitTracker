import pytest
from datetime import timedelta
from django.utils import timezone

from habits.models import Completion
from habits.services.period import get_period_key
from habits.services.streak import compute_streak
from habits.tests.factories import HabitFactory, CompletionFactory

def midnight(days_ago=0):
    """Return today's date at midnight UTC, minus N days."""
    now = timezone.now()
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_midnight - timedelta(days=days_ago)

def make_completion(habit, days_ago):
    dt = timezone.now() - timedelta(days=days_ago)
    key = get_period_key(dt, "DAILY")
    CompletionFactory(habit=habit, completed_at=dt, period_key=key)


def make_weekly_completion(habit, weeks_ago):
    dt = timezone.now() - timedelta(weeks=weeks_ago)
    key = get_period_key(dt, "WEEKLY")
    CompletionFactory(habit=habit, completed_at=dt, period_key=key)


@pytest.mark.django_db
def test_no_completions():
    habit = HabitFactory()

    stats = compute_streak(habit)

    assert stats["current_streak"] == 0
    assert stats["longest_streak"] == 0
    assert stats["total_completed"] == 0


@pytest.mark.django_db
def test_consecutive_5_days():
    habit = HabitFactory(created_at=midnight(4))
    for d in [4, 3, 2, 1, 0]:
        make_completion(habit, d)

    stats = compute_streak(habit)

    assert stats["current_streak"] == 5


@pytest.mark.django_db
def test_streak_broken_yesterday():
    habit = HabitFactory()

    for d in [4, 3, 2]:
        make_completion(habit, d)

    stats = compute_streak(habit)

    assert stats["current_streak"] == 0


@pytest.mark.django_db
def test_recovery_after_break():
    habit = HabitFactory(created_at=midnight(9))

    for d in [9, 8, 7]:
        make_completion(habit, d)

    for d in [4, 3, 2, 1, 0]:
        make_completion(habit, d)

    stats = compute_streak(habit)

    assert stats["current_streak"] == 5
    assert stats["longest_streak"] == 5


@pytest.mark.django_db
def test_longest_streak_is_historical():
    habit = HabitFactory(created_at=midnight(13))

    for d in range(13, 6, -1):
        make_completion(habit, d)

    for d in range(5, -1, -1):
        make_completion(habit, d)

    stats = compute_streak(habit)

    assert stats["current_streak"] == 6
    assert stats["longest_streak"] == 7


@pytest.mark.django_db
def test_active_period_does_not_break_streak():
    habit = HabitFactory(created_at=timezone.now() - timedelta(days=1))

    make_completion(habit, 1)

    stats = compute_streak(habit)

    assert stats["current_streak"] == 1


@pytest.mark.django_db
def test_completion_rate():
    habit = HabitFactory(created_at=midnight(5))

    for d in [4, 3, 2]:
        make_completion(habit, d)

    stats = compute_streak(habit)

    assert stats["completion_rate"] == 60.0


@pytest.mark.django_db
def test_weekly_habit_3_consecutive_weeks():
    habit = HabitFactory(created_at=midnight(14), periodicity="WEEKLY")

    for w in [2, 1, 0]:
        make_weekly_completion(habit, w)

    stats = compute_streak(habit)

    assert stats["current_streak"] == 3