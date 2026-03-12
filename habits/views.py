import csv
from datetime import datetime

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Completion, Habit
from .serializers import (
	AnalyticsSummarySerializer,
	CompletionSerializer,
	HabitDetailSerializer,
	HabitSerializer,
	PeriodHistorySerializer,
)


class HabitViewSet(viewsets.ModelViewSet):
	serializer_class = HabitSerializer

	def get_queryset(self):
		return Habit.objects.for_user(self.request.user)

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


class AnalyticsSummaryView(APIView):
	def get(self, request):
		habits = Habit.objects.for_user(request.user, include_archived=True)
		total_habits = habits.count()
		total_completions = Completion.objects.filter(habit__user=request.user).count()

		habits_on_streak = 0
		habits_broken = 0

		# NOTE: This loops over habits and calls get_analytics per habit (N+1-ish).
		# Acceptable for v1; optimize with denormalization/query-level aggregates later.
		for habit in habits:
			analytics = habit.get_analytics()
			if analytics['current_streak'] > 0:
				habits_on_streak += 1
			elif analytics['total_failed'] > 0:
				habits_broken += 1

		data = {
			'total_habits': total_habits,
			'total_completions': total_completions,
			'habits_on_streak': habits_on_streak,
			'habits_broken': habits_broken,
		}
		serializer = AnalyticsSummarySerializer(data)
		return Response(serializer.data)


class ExportView(APIView):
	def get(self, request):
		format_param = request.query_params.get('format', 'json').lower()
		habits = Habit.objects.for_user(request.user, include_archived=True)

		export_rows = []
		for habit in habits:
			analytics = habit.get_analytics()
			export_rows.append(
				{
					'id': str(habit.id),
					'task_specification': habit.task_specification,
					'periodicity': habit.periodicity,
					'is_archived': habit.is_archived,
					'created_at': habit.created_at.isoformat(),
					'current_streak': analytics['current_streak'],
					'longest_streak': analytics['longest_streak'],
					'completion_rate': analytics['completion_rate'],
					'total_completed': analytics['total_completed'],
					'total_failed': analytics['total_failed'],
				}
			)

		if format_param == 'csv':
			return self._export_csv(export_rows)
		if format_param == 'json':
			return Response(export_rows)
		return Response(
			{'detail': 'Unsupported format. Use csv or json.'},
			status=status.HTTP_400_BAD_REQUEST,
		)

	def _export_csv(self, rows):
		fieldnames = [
			'id',
			'task_specification',
			'periodicity',
			'is_archived',
			'created_at',
			'current_streak',
			'longest_streak',
			'completion_rate',
			'total_completed',
			'total_failed',
		]

		class Echo:
			def write(self, value):
				return value

		pseudo_buffer = Echo()
		writer = csv.DictWriter(pseudo_buffer, fieldnames=fieldnames)

		def row_stream():
			yield writer.writerow(dict(zip(fieldnames, fieldnames, strict=False)))
			for row in rows:
				yield writer.writerow(row)

		response = StreamingHttpResponse(row_stream(), content_type='text/csv')
		response['Content-Disposition'] = 'attachment; filename="habits_export.csv"'
		return response
