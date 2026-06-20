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
