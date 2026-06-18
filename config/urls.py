"""Root URL configuration. App-specific routes live in each app's urls.py."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Django's built-in login/logout/password views. Stage 2 swaps this for
    # django-allauth (Google/Facebook) without touching shortener/analytics.
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.shortener.urls")),
]
