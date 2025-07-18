"""
URL configuration for purple project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.views.static import serve
from django.conf import settings
from rest_framework.authtoken.views import obtain_auth_token
from django.http import HttpResponse
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView
from .views import ProtectMediaView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

def home(request):
    return render(request, 'index.html')

# urlpatterns = [
#     path('', home, name='home'),
#     path('admin/', admin.site.urls),
#     path('account/', include('account_module.urls')),
#     path('service/', include('services_module.urls')),
#     path('conversations/', include('ChatAPI.urls')),
#     path('favicon.ico', RedirectView.as_view(url='/statics/favicon.ico', permanent=True)),
#     re_path(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}),
#     re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'static'}),

# ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = [
    # path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('account/', include('account_module.urls')),
    path('service/', include('services_module.urls')),
    path('conversations/', include('ChatAPI.urls')),

    # Favicon
    path('favicon.ico', serve, {'document_root': settings.BASE_DIR / 'frontend/', 'path': 'favicon.ico'}),

    # API schema generation endpoint
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Redoc UI (optional)
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Static & media
    # re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^media/(?P<path>.*)$', ProtectMediaView.as_view()),

    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'static'}),

    # Flutter assets (e.g. /assets/**)
    re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'frontend/assets'}),
    
    re_path(r'^flutter_service_worker\.js$', serve, {
    'document_root': settings.BASE_DIR / 'frontend',
    'path': 'flutter_service_worker.js',
    }),
    
    # Catch-all to serve index.html for Flutter Web routes
    re_path(
    r'^(?!static/|media/|assets/|manifest\.json|favicon\.ico|flutter_service_worker\.js|flutter_bootstrap\.js|flutter\.js|main\.dart\.js|version\.json|icons/).*$', 
    serve, {
        'document_root': settings.BASE_DIR / 'frontend',
        'path': 'index.html'
    }
),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)