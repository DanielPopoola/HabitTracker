from django.db import models


class HabitManager(models.Manager):
	def for_user(self, user, include_archived=False):
		qs = self.get_queryset().filter(user=user)
		if not include_archived:
			qs = qs.filter(is_archived=False)
		return qs


class CompletionManager(models.Manager):
	def for_habit_in_range(self, habit, start, end):
		return self.get_queryset().filter(habit=habit, completed_at__gte=start, completed_at__lte=end)

	def grouped_by_period(self, habit):
		return (
			self.get_queryset()
			.filter(habit=habit)
			.values('period_key')
			.annotate(count=models.Count('id'))
			.order_by('period_key')
		)
