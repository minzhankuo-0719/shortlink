"""Template context processors: small bits of state every template can read."""

from django.conf import settings
from django.http import HttpRequest


def template_flags(request: HttpRequest) -> dict[str, bool]:
    """Expose render flags to all templates.

    `tailwind_cdn` chooses the stylesheet source in base.html: dev (DEBUG) uses
    Tailwind's Play CDN for zero-config iteration, while prod uses the
    self-hosted CSS compiled at image-build time — no third-party runtime
    dependency, smaller and faster.
    """
    return {"tailwind_cdn": settings.DEBUG}
