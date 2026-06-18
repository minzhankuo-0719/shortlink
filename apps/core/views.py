from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """Landing page."""
    return render(request, "core/home.html")


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness probe for Cloud Run / load balancers.

    Intentionally cheap (no database or cache access) so it stays fast and
    cannot be taken down by a slow dependency.
    """
    return JsonResponse({"status": "ok"})
