"""Root URL configuration. App-specific routes live in each app's urls.py."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # allauth provides login/logout/signup *and* the Google/Facebook OAuth
    # flow under the same "accounts/" prefix Stage 1 used for the built-in
    # views — shortener/analytics never reference this, so swapping it out
    # didn't require touching either app.
    path("accounts/", include("allauth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.shortener.urls")),
]
