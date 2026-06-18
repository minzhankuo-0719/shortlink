from django.urls import path

from . import views

app_name = "shortener"

urlpatterns = [
    path("links/new", views.create_link, name="create_link"),
    path("links/", views.my_links, name="my_links"),
    # Short code last: it's a catch-all single path segment, so it must not
    # shadow the more specific routes above.
    path("<str:short_code>", views.redirect_short_link, name="redirect"),
]
