import calendar
from datetime import UTC, timedelta, datetime, timezone as dt_timezone

from django.utils import timezone


def get_period_bounds(dt, periodicity):
	"""
	Given a timezone-aware datetime and periodicity,
	return the (start, end) datetime of the period in UTC.
	"""
	if timezone.is_naive(dt):
		raise ValueError('Input datetime must be timezone-aware')

	dt = dt.astimezone(UTC)

	if periodicity == 'DAILY':
		start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
		end = start + timedelta(days=1) - timedelta(microseconds=1)
		return start, end

	if periodicity == 'WEEKLY':
		monday = dt - timedelta(days=dt.weekday())
		start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
		end = start + timedelta(days=7) - timedelta(microseconds=1)
		return start, end

	if periodicity == 'MONTHLY':
		start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
		_, num_days = calendar.monthrange(dt.year, dt.month)
		end = start.replace(day=num_days) + timedelta(days=1) - timedelta(microseconds=1)
		return start, end

	raise ValueError(f'Unsupported periodicity: {periodicity}')


def get_period_key(dt, periodicity) -> str:
	"""
	Return canonical period string used for Completion.period_key.
	"""
	if timezone.is_naive(dt):
		raise ValueError('Datetime must be timezone-aware')

	dt = dt.astimezone(UTC)

	if periodicity == 'DAILY':
		return dt.strftime('%Y-%m-%d')

	if periodicity == 'WEEKLY':
		return dt.strftime('%G-W%V')

	if periodicity == 'MONTHLY':
		return dt.strftime('%Y-%m')

	raise ValueError(f'Unsupported periodicity: {periodicity}')


def generate_periods(start_dt, end_dt, periodicity):
	"""
	Enumerates every period between two datetimes.
	Returns a list of dicts.
	"""
	if timezone.is_naive(start_dt) or timezone.is_naive(end_dt):
		raise ValueError('Datetimes must be timezone-aware')

	start_dt = start_dt.astimezone(UTC)
	end_dt = end_dt.astimezone(UTC)

	periods = []
	current_start, current_end = get_period_bounds(start_dt, periodicity)

	while current_start <= end_dt:
		periods.append(
			{
				'key': get_period_key(current_start, periodicity),
				'start': current_start,
				'end': current_end,
			}
		)
		current = current_end + timedelta(microseconds=1)
		current_start, current_end = get_period_bounds(current, periodicity)

	return periods