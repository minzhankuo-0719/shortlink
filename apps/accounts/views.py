"""Email-first ("identifier-first") authentication entrance.

OpenAI/ChatGPT-style flow: the user first enters just an email. If that email
already belongs to an account we send them to allauth's password login (with
the email pre-filled); otherwise we send them to allauth's signup (allauth's
own SignupView pre-fills the email from the `?email=` query string).

We deliberately let allauth keep doing the actual authentication and account
creation — this module only routes the user to the right allauth page.

Trade-off: branching on "does this email exist?" reveals whether an email is
registered (user enumeration). That is inherent to this UX (OpenAI does the
same) and is mitigated by allauth's built-in login/signup rate limiting.
"""

from urllib.parse import urlencode

from allauth.account.models import EmailAddress
from allauth.account.views import LoginView
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import EmailFirstForm


def _user_for_email(email: str) -> AbstractBaseUser | None:
    """The account that owns this email, or None.

    Prefers allauth's EmailAddress table (social logins store their email
    there) and falls back to the User table (plain username/password accounts
    keep the email only on the user row).
    """
    email_address = EmailAddress.objects.filter(email__iexact=email).select_related("user").first()
    if email_address is not None:
        return email_address.user
    return get_user_model().objects.filter(email__iexact=email).first()


def _social_providers(user: AbstractBaseUser) -> list[str]:
    """Provider ids (e.g. ['google']) connected to this user."""
    return list(SocialAccount.objects.filter(user=user).values_list("provider", flat=True))


def _login_target(email: str) -> str:
    """Decide where an email-first submission for an *existing* email goes.

    A social-only account (no usable password) can never complete the password
    form, so we send it to a dedicated "continue with <provider>" screen
    instead of a dead password field. Everyone else goes to the password login.
    """
    user = _user_for_email(email)
    if user is not None and not user.has_usable_password() and _social_providers(user):
        return "account_social_only"
    return "account_login"


def entrance(request: HttpRequest) -> HttpResponse:
    """GET: show the single email field. POST: route to login or signup."""
    if request.user.is_authenticated:
        return redirect("shortener:my_links")
    if request.method == "POST":
        form = EmailFirstForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            target = "account_signup"
            if _user_for_email(email) is not None:
                target = _login_target(email)
            return redirect(f"{reverse(target)}?{urlencode({'email': email})}")
    else:
        form = EmailFirstForm()
    return render(request, "account/entrance.html", {"form": form})


def social_only(request: HttpRequest) -> HttpResponse:
    """Guidance screen for an email that belongs to a password-less social
    account: show only the provider(s) that account actually uses."""
    email = request.GET.get("email", "")
    user = _user_for_email(email) if email else None
    providers = _social_providers(user) if user is not None else []
    # If anything looks off (no such user, it has a password, or no social
    # account after all), fall back to the normal password login rather than
    # showing an empty screen.
    if user is None or user.has_usable_password() or not providers:
        return redirect(f"{reverse('account_login')}?{urlencode({'email': email})}")
    return render(
        request,
        "account/social_only.html",
        {"email": email, "account_providers": providers},
    )


class PrefillLoginView(LoginView):
    """allauth's login view, but with the email from the entrance step
    pre-filled into the login field. (allauth's SignupView already pre-fills
    the email for the signup branch, so only login needs this.)"""

    def get_initial(self) -> dict:
        initial = super().get_initial()
        email = self.request.GET.get("email")
        if email:
            initial["login"] = email
        return initial
