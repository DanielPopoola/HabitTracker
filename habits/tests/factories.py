import factory
from django.utils import timezone

from habits.models import User, Habit, Completion, Periodicity


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password")


class HabitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Habit

    user = factory.SubFactory(UserFactory)
    task_specification = "Test habit"
    periodicity = Periodicity.DAILY
    is_archived = False
    created_at = factory.LazyFunction(timezone.now)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        created_at = kwargs.pop('created_at', None)
        instance = super()._create(model_class, *args, **kwargs)
        if created_at:
            model_class.objects.filter(pk=instance.pk).update(created_at=created_at)
            instance.created_at = created_at
        return instance



class CompletionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Completion

    habit = factory.SubFactory(HabitFactory)
    completed_at = factory.LazyFunction(timezone.now)
    period_key = ""
    note = ""