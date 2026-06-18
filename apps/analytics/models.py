from django.db import models


class Click(models.Model):
    """One record per visit to a ShortLink's redirect URL."""

    link = models.ForeignKey(
        "shortener.ShortLink",
        on_delete=models.CASCADE,
        related_name="clicks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    referer = models.CharField(max_length=512, blank=True)

    class Meta:
        # Composite index: dashboard queries filter by link and sort by time.
        indexes = [models.Index(fields=["link", "created_at"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.link.short_code} @ {self.created_at:%Y-%m-%d %H:%M}"
