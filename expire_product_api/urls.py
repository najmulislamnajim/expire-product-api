from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/v1/material/', include('material_app.urls')),
    path('api/v1/withdrawal/', include('withdrawal_app.urls')),
    path('api/v1/radisoft/withdrawal/', include('withdrawal_app.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
