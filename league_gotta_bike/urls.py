"""
URL configuration for league_gotta_bike project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Custom accounts URLs (must come before allauth)
    path('accounts/', include('accounts.urls')),
    # Django-allauth URLs
    path('accounts/', include('allauth.urls')),
]

# Development-only URLs
if settings.DEBUG:
    # Django Debug Toolbar
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]

    # Django Browser Reload
    urlpatterns += [
        path('__reload__/', include('django_browser_reload.urls')),
    ]

    # Serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Membership URLs (before organizations due to more specific patterns)
urlpatterns += [
    path('membership/', include('apps.membership.urls')),
]

# Messaging URLs
urlpatterns += [
    path('chat/', include('apps.messaging.urls')),
]

# Events URLs
urlpatterns += [
    path('events/', include('apps.events.urls')),
]

# Sponsors URLs
urlpatterns += [
    path('sponsors/', include('apps.sponsors.urls')),
]

# Mobile API URLs
urlpatterns += [
    path('api/mobile/', include('apps.mobile_api.urls')),
]

# Admin API URLs
urlpatterns += [
    path('api/admin/', include('apps.admin_api.urls')),
]

# Organizations URLs (must be last due to catch-all slug patterns)
urlpatterns += [
    path('', include('apps.organizations.urls')),
]
