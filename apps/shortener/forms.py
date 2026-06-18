from django import forms

from .models import ShortLink


class ShortLinkForm(forms.ModelForm):
    class Meta:
        model = ShortLink
        fields = ["original_url", "title"]
        widgets = {
            "original_url": forms.URLInput(
                attrs={
                    "placeholder": "https://example.com/...",
                    "class": "border rounded px-3 py-2 w-full",
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "placeholder": "（選填）幫這個連結取個名字",
                    "class": "border rounded px-3 py-2 w-full",
                }
            ),
        }
