from typing import Any

from allauth.account.forms import LoginForm, SignupForm
from django import forms

# Same Tailwind classes as the allauth field element (templates/allauth/
# elements/field.html) so the entrance input matches the login/signup inputs.
_INPUT_CLASS = (
    "border border-gray-300 rounded-xl px-4 py-3 w-full text-sm "
    "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent "
    "dark:bg-neutral-800 dark:border-neutral-700 dark:text-gray-100 dark:placeholder-gray-500"
)


class EmailFirstForm(forms.Form):
    """Single email field for the OpenAI-style email-first entrance step."""

    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "you@example.com",
                "autocomplete": "email",
                "autofocus": True,
                "class": _INPUT_CLASS,
            }
        ),
    )


class CustomSignupForm(SignupForm):
    """allauth signup form with the password requirements help text removed.

    The four AUTH_PASSWORD_VALIDATORS still run — a weak password is rejected
    on submit with a red error. We just drop the always-on `<ul>` of rules that
    allauth attaches as `password1.help_text`, because it renders as a big block
    of white text before the user has typed anything. Surfacing the rules only
    when one is actually violated keeps the form clean without weakening it.
    Wired up via ACCOUNT_FORMS["signup"] in config/settings/base.py.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = ""


class CustomLoginForm(LoginForm):
    """allauth login form with the "Forgot your password?" link removed.

    allauth attaches that link as the password field's `help_text`. Password
    reset works by emailing a link, and we have no mail server in production
    (this app is social-login-first; password accounts are a minor path), so
    rather than expose an entry point that would error in prod, we drop the
    link. Wired up via ACCOUNT_FORMS["login"] in config/settings/base.py.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["password"].help_text = ""
