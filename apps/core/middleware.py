"""Project middleware."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django_ratelimit.exceptions import Ratelimited


class RatelimitTo429Middleware:
    """Turn django-ratelimit's block into a proper 429 response.

    With `block=True` the @ratelimit decorator raises Ratelimited (a subclass
    of PermissionDenied), which Django would render as 403. Rate limiting's
    correct status is 429 Too Many Requests, so we catch that one exception and
    return 429 instead. Anything else is left untouched for the normal handler.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse | None:
        if isinstance(exception, Ratelimited):
            return HttpResponse("Too many requests — please slow down.", status=429)
        return None
