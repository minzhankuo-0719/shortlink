"""Development settings: convenient and verbose. Never used in production."""

from .base import *  # noqa: F403

DEBUG = True

# Hosts allowed when developing locally (incl. 0.0.0.0 for Docker port mapping).
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
