from django.conf import settings
from django.db import models


class ShortLink(models.Model):
    """A user-owned mapping from a short code to a destination URL."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="short_links",
    )
    original_url = models.URLField(max_length=2048)
    # unique=True also creates a DB index — this is the field looked up on
    # every redirect, so it must stay fast even as the table grows.
    short_code = models.CharField(max_length=10, unique=True)
    title = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["owner"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.short_code
