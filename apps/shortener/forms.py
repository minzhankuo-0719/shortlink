from django import forms

from .models import ShortLink

# Shared input styling (light + dark). Kept as a constant so both widgets stay
# in sync and no single line blows past the line-length limit.
_INPUT_CLASS = (
    "border rounded px-3 py-2 w-full "
    "dark:bg-neutral-800 dark:border-neutral-700 dark:text-gray-100 dark:placeholder-gray-500"
)


class ShortLinkForm(forms.ModelForm):
    class Meta:
        model = ShortLink
        fields = ["original_url", "title"]
        widgets = {
            "original_url": forms.URLInput(
                attrs={
                    "placeholder": "https://example.com/...",
                    "class": _INPUT_CLASS,
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Give this link a name (optional)",
                    "class": _INPUT_CLASS,
                }
            ),
        }
