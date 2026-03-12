from django.contrib import admin

from .models import Completion, Habit, User

admin.site.register(User)
admin.site.register(Habit)
admin.site.register(Completion)
