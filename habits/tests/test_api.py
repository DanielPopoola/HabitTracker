from datetime import timedelta

import pytest
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from habits.models import Completion, Habit, Periodicity
from habits.services.period import get_period_key
from habits.tests.factories import CompletionFactory, HabitFactory, UserFactory


@pytest.mark.django_db
class TestHabitEndpoints:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.other_habit = HabitFactory(user=self.other_user)
        self.client.force_authenticate(user=self.user)

    def test_list_habits(self):
        own_habit = HabitFactory(user=self.user)
        HabitFactory(user=self.other_user)

        response = self.client.get('/api/v1/habits/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == str(own_habit.id)
        
    def test_create_habit(self):
        payload = {
            'task_specification': 'Read 10 pages',
            'periodicity': Periodicity.DAILY,
        }

        response = self.client.post('/api/v1/habits/', payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['task_specification'] == payload['task_specification']
        assert response.data['periodicity'] == payload['periodicity']
        assert Habit.objects.filter(user=self.user, task_specification='Read 10 pages').exists()

    def test_create_habit_missing_fields(self):
        payload = {'periodicity': Periodicity.DAILY}

        response = self.client.post('/api/v1/habits/', payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'task_specification' in response.data

    def test_create_habit_blank_task(self):
        payload = {
            'task_specification': '',
            'periodicity': Periodicity.DAILY,
        }

        response = self.client.post('/api/v1/habits/', payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'task_specification' in response.data

    def test_retrieve_habit_includes_analytics(self):
        habit = HabitFactory(user=self.user)

        response = self.client.get(f'/api/v1/habits/{habit.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'current_streak' in response.data
        assert 'longest_streak' in response.data

    def test_update_habit_task(self):
        habit = HabitFactory(user=self.user, task_specification='Old task')

        response = self.client.patch(
            f'/api/v1/habits/{habit.id}/',
            {'task_specification': 'New task'},
            format='json',
        )

        habit.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert response.data['task_specification'] == 'New task'
        assert habit.task_specification == 'New task'

    def test_update_habit_periodicity_ignored(self):
        habit = HabitFactory(user=self.user, periodicity=Periodicity.DAILY)

        response = self.client.patch(
            f'/api/v1/habits/{habit.id}/',
            {'periodicity': Periodicity.WEEKLY},
            format='json',
        )

        habit.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert habit.periodicity == Periodicity.DAILY
        assert response.data['periodicity'] == Periodicity.DAILY

    def test_cannot_access_other_users_habit(self):
        response = self.client.get(f'/api/v1/habits/{self.other_habit.id}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_archive_habit(self):
        habit = HabitFactory(user=self.user, is_archived=False)

        response = self.client.patch(f'/api/v1/habits/{habit.id}/archive/')

        habit.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_archived'] is True
        assert habit.is_archived is True

    def test_analytics_action_returns_periods(self):
        habit = HabitFactory(user=self.user)

        response = self.client.get(f'/api/v1/habits/{habit.id}/analytics/')

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) >= 1
        assert {'key', 'start', 'end', 'status', 'completion_count'}.issubset(response.data[0].keys())

    def test_unauthenticated_request(self):
        client = APIClient()

        response = client.get('/api/v1/habits/')

        # SessionAuthentication + IsAuthenticated returns 403 when no credentials are provided.
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCompletionEndpoints:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.habit = HabitFactory(user=self.user)
        self.other_habit = HabitFactory(user=self.other_user)
        self.client.force_authenticate(user=self.user)

    def test_create_completion(self):
        response = self.client.post(f'/api/v1/habits/{self.habit.id}/completions/', {}, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        completion = Completion.objects.get(id=response.data['id'])
        assert completion.habit_id == self.habit.id
        assert completion.period_key

    def test_create_completion_sets_period_key(self):
        completed_at = timezone.now() - timedelta(days=3)

        response = self.client.post(
            f'/api/v1/habits/{self.habit.id}/completions/',
            {'completed_at': completed_at.isoformat()},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        completion = Completion.objects.get(id=response.data['id'])
        assert completion.period_key == get_period_key(completed_at, self.habit.periodicity)

    def test_delete_completion(self):
        completion = CompletionFactory(
            habit=self.habit,
            completed_at=timezone.now(),
            period_key=get_period_key(timezone.now(), self.habit.periodicity),
        )

        response = self.client.delete(
            f'/api/v1/habits/{self.habit.id}/completions/{completion.id}/'
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Completion.objects.filter(id=completion.id).exists()

    def test_cannot_complete_other_users_habit(self):
        response = self.client.post(
            f'/api/v1/habits/{self.other_habit.id}/completions/',
            {},
            format='json',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_delete_other_users_completion(self):
        completion = CompletionFactory(
            habit=self.other_habit,
            completed_at=timezone.now(),
            period_key=get_period_key(timezone.now(), self.other_habit.periodicity),
        )

        response = self.client.delete(
            f'/api/v1/habits/{self.other_habit.id}/completions/{completion.id}/'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestAnalyticsEndpoints:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.other_habit = HabitFactory(user=self.other_user)
        self.client.force_authenticate(user=self.user)

    def test_summary_returns_correct_counts(self):
        on_streak_habit = HabitFactory(user=self.user, created_at=timezone.now() - timedelta(days=1))
        broken_habit = HabitFactory(user=self.user, created_at=timezone.now() - timedelta(days=2))

        CompletionFactory(
            habit=on_streak_habit,
            completed_at=timezone.now() - timedelta(days=1),
            period_key=get_period_key(timezone.now() - timedelta(days=1), on_streak_habit.periodicity),
        )

        response = self.client.get('/api/v1/analytics/summary/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_habits'] == 2
        assert response.data['habits_on_streak'] == 1
        assert response.data['habits_broken'] == 1

    def test_summary_does_not_call_habit_get_analytics(self, monkeypatch):
        HabitFactory(user=self.user, created_at=timezone.now() - timedelta(days=1))

        def fail_get_analytics(_self):
            raise AssertionError('get_analytics should not be called by summary endpoint')

        monkeypatch.setattr(Habit, 'get_analytics', fail_get_analytics)

        response = self.client.get('/api/v1/analytics/summary/')

        assert response.status_code == status.HTTP_200_OK

    def test_export_json(self):
        HabitFactory(user=self.user)

        response = self.client.get(f"{reverse('analytics-export')}?format=json")

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 1
        assert {'id', 'task_specification', 'periodicity', 'current_streak'}.issubset(
            response.data[0].keys()
        )

    def test_export_csv(self):
        HabitFactory(user=self.user)

        response = self.client.get(f"{reverse('analytics-export')}?format=csv")

        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'].startswith('text/csv')
