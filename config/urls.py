from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
	path('admin/', admin.site.urls),
	path('api/v1/', include('habits.urls')),
]


urlpatterns = [
	path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='habits/index.html'), name='dashboard'),
	path('login/', TemplateView.as_view(template_name='habits/login.html'), name='login'),
	path('api/v1/', include('habits.urls')),
	path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
	path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
