"""Root URL configuration. App-specific routes live in each app's urls.py."""

from django.contrib import admin
from django.urls import include, path

from apps.accounts import views as account_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAI-style email-first entrance: the single front door for signing in
    # (LOGIN_URL points here). It routes to the password login or signup based
    # on whether the email is already registered.
    path("accounts/start/", account_views.entrance, name="account_entrance"),
    # Guidance screen for a password-less social account reached via the
    # entrance: shows "Continue with <provider>" instead of a dead password
    # form. (See apps/accounts/views.social_only.)
    path("accounts/continue/", account_views.social_only, name="account_social_only"),
    # Override allauth's login view with one that pre-fills the email carried
    # over from the entrance step. Declared *before* allauth's include so it
    # wins for this exact path; reverse('account_login') still resolves to
    # /accounts/login/, which this view serves.
    path("accounts/login/", account_views.PrefillLoginView.as_view()),
    # allauth provides login/logout/signup *and* the Google/Facebook OAuth
    # flow under the same "accounts/" prefix Stage 1 used for the built-in
    # views — shortener/analytics never reference this, so swapping it out
    # didn't require touching either app.
    path("accounts/", include("allauth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.shortener.urls")),
]
