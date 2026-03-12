from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AnalyticsSummaryView, CompletionViewSet, ExportView, HabitViewSet

router = DefaultRouter()
router.register(r'habits', HabitViewSet, basename='habit')

urlpatterns = [
	path('', include(router.urls)),
	path(
		'habits/<uuid:habit_pk>/completions/',
		CompletionViewSet.as_view({'post': 'create'}),
		name='habit-completions-create',
	),
	path(
		'habits/<uuid:habit_pk>/completions/<uuid:pk>/',
		CompletionViewSet.as_view({'delete': 'destroy'}),
		name='habit-completions-delete',
	),
	path('analytics/summary/', AnalyticsSummaryView.as_view(), name='analytics-summary'),
	path('analytics/export/', ExportView.as_view(), name='analytics-export'),
]
