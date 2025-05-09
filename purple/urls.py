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
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.views.static import serve
from django.conf import settings
from rest_framework.authtoken.views import obtain_auth_token
from django.http import HttpResponse
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView

def home(request):
    return HttpResponse("Hello, World!")

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
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('account/', include('account_module.urls')),
    path('service/', include('services_module.urls')),
    path('conversations/', include('ChatAPI.urls')),

    # Favicon
    path('favicon.ico', serve, {'document_root': settings.BASE_DIR / 'frontend/build/web', 'path': 'favicon.ico'}),

    # Static & media
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'static'}),

    # Flutter assets (e.g. /assets/**)
    re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'frontend/build/web/assets'}),

    # Catch-all to serve index.html for Flutter Web routes
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)