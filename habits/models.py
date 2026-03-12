import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .managers import CompletionManager, HabitManager


class User(AbstractUser):
	email = models.EmailField(unique=True)


class Periodicity(models.TextChoices):
	DAILY = 'DAILY', 'Daily'
	WEEKLY = 'WEEKLY', 'Weekly'
	MONTHLY = 'MONTHLY', 'Monthly'


class Habit(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	task_specification = models.CharField(max_length=255)
	periodicity = models.CharField(max_length=20, choices=Periodicity.choices)
	is_archived = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True, editable=False)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.task_specification

	def get_analytics(self):
		from .services.streak import compute_streak

		return compute_streak(self)

	def get_analytics_for_counts(self, completion_counts):
		from .services.streak import compute_streak

		return compute_streak(self, completion_counts=completion_counts)

	class Meta:
		indexes = [
			models.Index(fields=['user', 'is_archived']),
		]

	objects = HabitManager()


class Completion(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	habit = models.ForeignKey(Habit, on_delete=models.CASCADE)
	completed_at = models.DateTimeField(default=timezone.now)
	period_key = models.CharField(
		max_length=20, db_index=True
	)  # e.g., '2024-06-01' for daily, '2024-W23' for weekly, '2024-06' for monthly
	note = models.TextField(blank=True, null=True)

	def __str__(self):
		return f'Completion of {self.habit.task_specification} at {self.completed_at}'

	objects = CompletionManager()
