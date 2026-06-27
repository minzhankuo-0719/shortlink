from django.urls import path

from . import views

app_name = "shortener"

urlpatterns = [
    path("links/", views.my_links, name="my_links"),
    path("links/<int:pk>/delete", views.delete_link, name="delete"),
    path("links/<int:pk>/edit", views.edit_link, name="edit"),
    # Short code last: it's a catch-all single path segment, so it must not
    # shadow the more specific routes above.
    path("<str:short_code>", views.redirect_short_link, name="redirect"),
]
