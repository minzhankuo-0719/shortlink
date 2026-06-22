"""Business logic for shortener. Kept out of views/models so both stay thin
(fat view/model is an anti-pattern — logic here is easy to find, test, and
reuse from the admin, a management command, or the future DRF API)."""

import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser
from django.core.cache import cache

from .models import ShortLink

# Base62: digits + lowercase + uppercase. No padding/separator characters,
# so codes are URL-safe with no escaping needed.
_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_CODE_LENGTH = 7
_MAX_ATTEMPTS = 5


def generate_short_code(length: int = _CODE_LENGTH) -> str:
    """Generate a random, unique base62 short code.

    Random sampling (via `secrets`, a CSPRNG) was chosen over two common
    alternatives:
    - Incrementing ID -> base62: trivially enumerable (visiting /1, /2, /3...
      reveals every link and the total link count).
    - Hashing the URL: collides whenever two users shorten the same URL, and
      can't support the same URL having different codes per owner.

    7 base62 characters give 62**7 (~3.5 trillion) possibilities, so random
    collisions are rare; we still retry on the unlikely chance one occurs.
    """
    for _ in range(_MAX_ATTEMPTS):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        if not ShortLink.objects.filter(short_code=code).exists():
            return code
    raise RuntimeError("Could not generate a unique short code; check ShortLink table size.")


def create_short_link(owner: AbstractBaseUser, original_url: str, title: str = "") -> ShortLink:
    """Create and persist a new ShortLink for `owner`."""
    return ShortLink.objects.create(
        owner=owner,
        original_url=original_url,
        short_code=generate_short_code(),
        title=title,
    )


# How long a resolved short code stays cached. Short codes rarely change, so an
# hour trades a little freshness for far fewer DB reads. It's also a safety net:
# if active invalidation is ever missed, a stale entry self-corrects within the TTL.
_CACHE_TTL = int(timedelta(hours=1).total_seconds())


def _cache_key(short_code: str) -> str:
    # Namespaced so it won't collide with other caches (e.g. future rate limits).
    return f"shortlink:resolve:{short_code}"


def resolve_active_link(short_code: str) -> tuple[int, str] | None:
    """Cache-aside resolve: return (link_id, original_url), or None if no active link."""
    key = _cache_key(short_code)
    cached = cache.get(key)  # check the cache first
    if cached is not None:
        return cached  # hit: skip the database entirely

    # miss: hit the DB once. values_list returns a plain (id, url) tuple instead
    # of a full ShortLink object, and is_active=True keeps disabled links unresolvable.
    row = (
        ShortLink.objects.filter(short_code=short_code, is_active=True)
        .values_list("id", "original_url")
        .first()
    )
    if row is None:
        return  # not found -> view raises 404; deliberately not cached

    cache.set(key, row, _CACHE_TTL)  # populate the cache so next time hits
    return row


def invalidate_short_code(short_code: str) -> None:
    """Drop a short code's cached entry so the next resolve re-reads the DB."""
    cache.delete(_cache_key(short_code))
