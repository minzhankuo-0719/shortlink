#!/bin/sh
set -e

# Known trade-off (see docs/adr/0005): running migrate on every container
# boot races if multiple instances cold-start at once. Acceptable for this
# low-traffic, single-revision portfolio deployment; a real multi-instance
# service would run migrations as a separate one-off Cloud Run Job instead.
python manage.py migrate --noinput

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8080}"
