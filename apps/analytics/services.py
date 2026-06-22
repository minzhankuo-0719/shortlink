"""Business logic for analytics: turning a redirect request into a Click row."""

from django.http import HttpRequest

from .models import Click


def get_client_ip(request: HttpRequest) -> str | None:
    """Best-effort extraction of the real client IP.

    Checks `X-Forwarded-For` first, falling back to `REMOTE_ADDR`. This
    header is only trustworthy once the app sits behind a reverse proxy we
    control (Cloud Run, from Stage 3 onward) — a proxy strips/overwrites any
    client-supplied value before forwarding. Running locally (no proxy in
    front), the header is absent and we simply fall back to REMOTE_ADDR.
    See docs/adr/0003-client-ip-parsing.md.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def record_click(link_id: int, request: HttpRequest) -> Click:
    """Record one visit to a link, identified by id.

    Takes link_id rather than a ShortLink instance so the redirect can log a
    click straight from the cache-aside result (which carries only the id)
    without loading the row. Django lets you set a FK by its raw id via `link_id`.
    """
    return Click.objects.create(
        link_id=link_id,
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        referer=request.META.get("HTTP_REFERER", ""),
    )
