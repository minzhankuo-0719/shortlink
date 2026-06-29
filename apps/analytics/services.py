"""Business logic for analytics: turning a redirect request into a Click row."""

import ipaddress

from django.http import HttpRequest

from .models import Click


def get_client_ip(request: HttpRequest) -> str | None:
    """Extract the real, un-spoofable client IP from the request.

    On Cloud Run the app sits behind Google's front end, which appends the
    real client IP as the **last** entry of `X-Forwarded-For` (verified
    against the live service: a client-supplied `1.2.3.4` arrives as
    `1.2.3.4,<real-ip>`). Anything the client puts in the header therefore
    lands to the *left* of that trusted last entry and is ignored, so the
    recorded source IP can't be spoofed. We take the last entry — **not** the
    left-most (client-controlled) nor the "second-to-last" (that's the rule
    for a separate Cloud Load Balancer, not direct `*.run.app`).

    `REMOTE_ADDR` here is only Google's internal proxy, so it's used solely as
    the no-proxy fallback for local development (where it's 127.0.0.1).

    The chosen value is validated with `ipaddress`: a malformed header must not
    crash the redirect when the value reaches the Postgres `inet` column, so an
    invalid value yields None (stored as NULL) instead of raising a 500.
    See docs/adr/0003-client-ip-parsing.md.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    parts = [part.strip() for part in forwarded_for.split(",") if part.strip()]
    candidate = parts[-1] if parts else request.META.get("REMOTE_ADDR", "")
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return candidate


def client_ip_ratelimit_key(group: str, request: HttpRequest) -> str:
    """django-ratelimit key function: throttle by the real client IP.

    django-ratelimit's built-in `ip` key uses REMOTE_ADDR, which behind Cloud
    Run is Google's proxy — so every visitor would share one bucket and get
    throttled together. We key on get_client_ip() instead (the last, trusted
    X-Forwarded-For entry), which is the actual per-visitor IP and can't be
    spoofed to dodge the limit. A missing IP falls back to a shared bucket.
    """
    return get_client_ip(request) or "0.0.0.0"


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
