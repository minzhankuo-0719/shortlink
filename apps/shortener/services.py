"""Business logic for shortener. Kept out of views/models so both stay thin
(fat view/model is an anti-pattern — logic here is easy to find, test, and
reuse from the admin, a management command, or the future DRF API)."""

import secrets

from django.contrib.auth.models import AbstractBaseUser

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
