"""Cache invalidation for ShortLink.

We invalidate via model signals rather than at each call site so that *every*
way a link can change — the create flow, a future edit/deactivate view, the
Django admin, a management command — clears the cache automatically. One place
to get right, impossible to forget at a call site. See docs/adr/0010.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import ShortLink
from .services import invalidate_short_code


@receiver(post_save, sender=ShortLink)
@receiver(post_delete, sender=ShortLink)
def invalidate_shortlink_cache(
    sender: type[ShortLink], instance: ShortLink, **kwargs: object
) -> None:
    """Clear the cached resolution whenever a link is saved or deleted."""
    invalidate_short_code(instance.short_code)
