from datetime import datetime

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Completion, Habit
from ..serializers import (
	CompletionSerializer,
	HabitDetailSerializer,
	HabitSerializer,
	PeriodHistorySerializer,
)


class HabitViewSet(viewsets.ModelViewSet):
	queryset = Habit.objects.none()
	serializer_class = HabitSerializer
	lookup_field = 'pk'
	filterset_fields = ['is_archived']

	def get_queryset(self):
		if getattr(self, 'swagger_fake_view', False):
			return Habit.objects.none()
		# Include archived records so detail actions (e.g. unarchive) can resolve the habit.
		# List endpoints can still narrow with the `is_archived` filter query parameter.
		return Habit.objects.for_user(self.request.user, include_archived=True)

	def get_serializer_class(self):
		if self.action == 'retrieve':
			return HabitDetailSerializer
		return HabitSerializer

	def perform_create(self, serializer):
		serializer.save(user=self.request.user)

	@action(methods=['patch'], detail=True)
	def archive(self, request, pk=None):
		habit = self.get_object()
		habit.is_archived = True
		habit.save(update_fields=['is_archived', 'updated_at'])
		serializer = HabitDetailSerializer(habit)
		return Response(serializer.data)

	@action(methods=['patch'], detail=True)
	def unarchive(self, request, pk=None):
		habit = self.get_object()
		habit.is_archived = False
		habit.save(update_fields=['is_archived', 'updated_at'])
		serializer = HabitDetailSerializer(habit)
		return Response(serializer.data)

	@action(methods=['get'], detail=True)
	def analytics(self, request, pk=None):
		habit = self.get_object()
		periods = habit.get_analytics()['periods']

		start = parse_date(request.query_params.get('start', ''))
		end = parse_date(request.query_params.get('end', ''))

		if start:
			start_dt = timezone.make_aware(datetime.combine(start, datetime.min.time()))
			periods = [period for period in periods if period['end'] >= start_dt]
		if end:
			end_dt = timezone.make_aware(datetime.combine(end, datetime.max.time()))
			periods = [period for period in periods if period['start'] <= end_dt]

		serializer = PeriodHistorySerializer(periods, many=True)
		return Response(serializer.data)


class CompletionViewSet(mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
	serializer_class = CompletionSerializer

	def get_queryset(self):
		return Completion.objects.filter(
			habit__id=self.kwargs['habit_pk'],
			habit__user=self.request.user,
		)

	def get_habit(self):
		return get_object_or_404(
			Habit,
			pk=self.kwargs['habit_pk'],
			user=self.request.user,
		)

	def get_serializer_context(self):
		context = super().get_serializer_context()
		context['habit'] = self.get_habit()
		return context
