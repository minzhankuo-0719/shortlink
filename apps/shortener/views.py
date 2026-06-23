from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.analytics.services import record_click

from .forms import ShortLinkForm
from .services import create_short_link, resolve_active_link


@login_required
def my_links(request: HttpRequest) -> HttpResponse:
    """Dashboard: the create form (shown in a modal) plus every link the user
    owns, with click counts and recent clicks inline.

    Handles the create POST here so the form can live on this page in a modal.
    On success we redirect back (Post/Redirect/Get) so a refresh won't re-submit;
    on a validation error we fall through and re-render, so the template can
    re-open the modal with the errors shown.
    """
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

    links = request.user.short_links.annotate(click_count=Count("clicks")).prefetch_related(
        "clicks"
    )
    return render(request, "shortener/my_links.html", {"links": links, "form": form})


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
