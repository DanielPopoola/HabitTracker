from django.utils import timezone

from .period import generate_periods
from habits.models import Completion


def compute_streak(habit) -> dict:
	now = timezone.now()

	periods = generate_periods(habit.created_at, now, habit.periodicity)

	completion_counts = {
		row['period_key']: row['count'] for row in Completion.objects.grouped_by_period(habit)
	}

	labelled = []

	for period in periods:
		key = period['key']
		count = completion_counts.get(key, 0)

		if key in completion_counts:
			status = 'COMPLETED'
		elif period['end'] > now:
			status = 'ACTIVE'
		else:
			status = 'FAILED'

		labelled.append(
			{
				'key': key,
				'start': period['start'],
				'end': period['end'],
				'status': status,
				'completion_count': count,
			}
		)

	current_streak = 0
	for period in reversed(labelled):
		if period['status'] == 'ACTIVE':
			continue
		if period['status'] == 'COMPLETED':
			current_streak += 1
		else:
			break

	longest_streak = 0
	running = 0

	for period in labelled:
		if period['status'] == 'COMPLETED':
			running += 1
			longest_streak = max(longest_streak, running)
		elif period['status'] == 'FAILED':
			running = 0

	total_completed = sum(1 for p in labelled if p['status'] == 'COMPLETED')
	total_failed = sum(1 for p in labelled if p['status'] == 'FAILED')
	total_active = sum(1 for p in labelled if p['status'] == 'ACTIVE')

	closed_periods = total_completed + total_failed

	completion_rate = (total_completed / closed_periods) * 100.0 if closed_periods else 0.0

	labelled = list(reversed(labelled))

	return {
		'current_streak': current_streak,
		'longest_streak': longest_streak,
		'total_completed': total_completed,
		'total_failed': total_failed,
		'total_active': total_active,
		'completion_rate': round(completion_rate, 2),
		'periods': labelled,
	}
