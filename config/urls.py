"""Root URL configuration. App-specific routes live in each app's urls.py."""

from django.conf import settings
from django.contrib import admin
from django.http import Http404
from django.urls import include, path, re_path

from apps.accounts import views as account_views


def _disabled(request, *args, **kwargs):
    """Always 404. Used to switch off allauth's password-reset URLs in
    environments without SMTP (prod), where the flow can't deliver its email."""
    raise Http404


# When password reset is disabled (prod: no mail server), shadow allauth's two
# functional reset URLs with a 404 view. Declared *before* the allauth include
# below so first-match-wins makes these win. Empty in dev, so dev is untouched.
# The "key" URL mirrors allauth's own regex so we intercept exactly that route.
_password_reset_overrides = []
if not settings.PASSWORD_RESET_ENABLED:
    _password_reset_overrides = [
        path("accounts/password/reset/", _disabled),
        re_path(
            r"^accounts/password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$",
            _disabled,
        ),
    ]

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
    # Password-reset 404 shims (prod only; empty list in dev). Must sit before
    # the allauth include for first-match-wins to take effect.
    *_password_reset_overrides,
    # allauth provides login/logout/signup *and* the Google/Facebook OAuth
    # flow under the same "accounts/" prefix Stage 1 used for the built-in
    # views — shortener/analytics never reference this, so swapping it out
    # didn't require touching either app.
    path("accounts/", include("allauth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.shortener.urls")),
]
