from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
	AnalyticsSummaryView,
	CompletionViewSet,
	ExportView,
	HabitViewSet,
	LoginView,
	LogoutView,
	MeView,
	RegisterView,
)

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
	path('auth/register/', RegisterView.as_view(), name='auth-register'),
	path('auth/login/', LoginView.as_view(), name='auth-login'),
	path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
	path('auth/me/', MeView.as_view(), name='auth-me'),
]
