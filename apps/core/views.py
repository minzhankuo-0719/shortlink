from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from apps.accounts.forms import EmailFirstForm


def home(request: HttpRequest) -> HttpResponse:
    """Landing page for anonymous visitors; logged-in users go to their dashboard."""
    if request.user.is_authenticated:
        return redirect("shortener:my_links")
    # Embed the same email-first form the entrance uses, right on the landing
    # page, so a visitor can start signing in without an extra click.
    return render(request, "core/home.html", {"form": EmailFirstForm()})


def livez(request: HttpRequest) -> JsonResponse:
    """Liveness probe for Cloud Run / load balancers.

    Named after Kubernetes's `/livez` convention (the modern, more specific
    successor to the older combined `/healthz`) rather than `/healthz`
    itself: Cloud Run's front end reserves the exact path `/healthz` on the
    shared `*.run.app` domain for its own internal checks and never forwards
    it to the container, so a route literally named `/healthz` is silently
    unreachable from outside (see docs/adr/0006-livez-not-healthz.md).

    Intentionally cheap (no database or cache access) so it stays fast and
    cannot be taken down by a slow dependency.
    """
    return JsonResponse({"status": "ok"})
