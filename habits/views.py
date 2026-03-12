import csv
from datetime import datetime

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.renderers import BaseRenderer, JSONRenderer
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
	queryset = Habit.objects.none()
	serializer_class = HabitSerializer
	lookup_field = 'pk'
	filterset_fields = ['is_archived']

	def get_queryset(self):
		if getattr(self, 'swagger_fake_view', False):
			return Habit.objects.none()
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
	@extend_schema(responses=AnalyticsSummarySerializer)
	def get(self, request):
		habits = Habit.objects.for_user(request.user, include_archived=True)
		total_habits = habits.count()
		total_completions = Completion.objects.filter(habit__user=request.user).count()

		habits_on_streak = 0
		habits_broken = 0

		completion_counts_by_habit = {}
		completion_rows = (
			Completion.objects.filter(habit__user=request.user)
			.values('habit_id', 'period_key')
			.annotate(count=Count('id'))
		)

		for row in completion_rows:
			habit_counts = completion_counts_by_habit.setdefault(row['habit_id'], {})
			habit_counts[row['period_key']] = row['count']

		for habit in habits:
			analytics = habit.get_analytics_for_counts(
				completion_counts_by_habit.get(habit.id, {})
			)
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


class CSVRenderer(BaseRenderer):
	media_type = 'text/csv'
	format = 'csv'
	charset = 'utf-8'
	render_style = 'binary'

	def render(self, data, accepted_media_type=None, renderer_context=None):
		if data is None:
			return b''
		if isinstance(data, bytes):
			return data
		return str(data).encode(self.charset)


class ExportView(APIView):
	renderer_classes = [JSONRenderer, CSVRenderer]

	@extend_schema(responses={'200': {'type': 'string', 'format': 'binary'}})
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
