from django.apps import AppConfig


class ShortenerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.shortener"

    def ready(self) -> None:
        # Import for side effects: registers the cache-invalidation signal
        # receivers (see signals.py). Done here, not at module top, because the
        # app registry / models aren't ready when apps.py is first imported.
        from . import signals  # noqa: F401
