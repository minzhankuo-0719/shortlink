from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.analytics.services import record_click

from .forms import ShortLinkForm
from .services import create_short_link, resolve_active_link


@login_required
def create_link(request: HttpRequest) -> HttpResponse:
    """Show the create-link form (GET) or create a link and redirect (POST)."""
    if request.method == "POST":
        form = ShortLinkForm(request.POST)
        if form.is_valid():
            create_short_link(
                owner=request.user,
                original_url=form.cleaned_data["original_url"],
                title=form.cleaned_data["title"],
            )
            return redirect("shortener:my_links")
    else:
        form = ShortLinkForm()
    return render(request, "shortener/create.html", {"form": form})


@login_required
def my_links(request: HttpRequest) -> HttpResponse:
    """Dashboard: every link the current user owns, with click counts and
    the most recent clicks shown inline (no separate detail page yet)."""
    links = request.user.short_links.annotate(click_count=Count("clicks")).prefetch_related(
        "clicks"
    )
    return render(request, "shortener/my_links.html", {"links": links})


def redirect_short_link(request: HttpRequest, short_code: str) -> HttpResponse:
    """Resolve a short code and redirect to its destination, recording a Click.

    The resolve step is cache-aside (Redis first, DB on a miss), so this hot
    path usually avoids the database. See docs/adr/0010.

    Uses Django's default 302 (temporary) redirect rather than 301
    (permanent): a 301 gets cached by the browser, so the *second* visit
    never reaches this view again — and the click goes unrecorded. 302
    guarantees every visit hits the server. See docs/adr/0002.
    """
    resolved = resolve_active_link(short_code)
    if resolved is None:
        raise Http404
    link_id, original_url = resolved
    record_click(link_id, request)
    return redirect(original_url)
