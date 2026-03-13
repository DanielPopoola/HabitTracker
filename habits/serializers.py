from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Completion, Habit
from .services.period import get_period_key


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()

class HabitSerializer(serializers.ModelSerializer):
	class Meta:
		model = Habit
		fields = ['id', 'task_specification', 'periodicity', 'is_archived', 'created_at']
		read_only_fields = ['id', 'created_at']

	def validate_task_specification(self, value):
		if not value.strip():
			raise serializers.ValidationError('Task specification cannot be blank.')
		return value.strip()

	def update(self, instance, validated_data):
		validated_data.pop('periodicity', None)
		return super().update(instance, validated_data)


class HabitDetailSerializer(HabitSerializer):
	current_streak = serializers.SerializerMethodField()
	longest_streak = serializers.SerializerMethodField()
	completion_rate = serializers.SerializerMethodField()
	is_broken = serializers.SerializerMethodField()

	class Meta(HabitSerializer.Meta):
		fields = HabitSerializer.Meta.fields + [
			'current_streak',
			'longest_streak',
			'completion_rate',
			'is_broken',
		]

	def _get_analytics(self, obj):
		if not hasattr(self, '_analytics_cache'):
			self._analytics_cache = {}
		if obj.pk not in self._analytics_cache:
			self._analytics_cache[obj.pk] = obj.get_analytics()
		return self._analytics_cache[obj.pk]

	@extend_schema_field(serializers.IntegerField())
	def get_current_streak(self, obj):
		return self._get_analytics(obj)['current_streak']

	@extend_schema_field(serializers.IntegerField())
	def get_longest_streak(self, obj):
		return self._get_analytics(obj)['longest_streak']

	@extend_schema_field(serializers.FloatField())
	def get_completion_rate(self, obj):
		return self._get_analytics(obj)['completion_rate']

	@extend_schema_field(serializers.BooleanField())
	def get_is_broken(self, obj):
		analytics = self._get_analytics(obj)
		return analytics['current_streak'] == 0 and analytics['total_failed'] > 0


class CompletionSerializer(serializers.ModelSerializer):
	completed_at = serializers.DateTimeField(required=False, default=timezone.now)

	class Meta:
		model = Completion
		fields = ['id', 'completed_at', 'note']
		read_only_fields = ['id']

	def create(self, validated_data):
		habit = self.context['habit']
		completed_at = validated_data.get('completed_at', timezone.now())
		validated_data['habit'] = habit
		validated_data['period_key'] = get_period_key(completed_at, habit.periodicity)
		return super().create(validated_data)


class PeriodHistorySerializer(serializers.Serializer):
	key = serializers.CharField()
	start = serializers.DateTimeField()
	end = serializers.DateTimeField()
	status = serializers.CharField()
	completion_count = serializers.IntegerField()


class AnalyticsSummarySerializer(serializers.Serializer):
	total_habits = serializers.IntegerField()
	total_completions = serializers.IntegerField()
	habits_on_streak = serializers.IntegerField()
	habits_broken = serializers.IntegerField()
