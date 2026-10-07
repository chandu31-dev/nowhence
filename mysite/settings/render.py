"""Production settings for deployment on Render."""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403


def _required_env(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise ImproperlyConfigured(f'{name} must be configured for production.')
    return value


DEBUG = False

SECRET_KEY = _required_env('DJANGO_SECRET_KEY')
if SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be a unique production secret.')

RENDER_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', RENDER_HOSTNAME).split(',')
    if host.strip()
]
if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'Set DJANGO_ALLOWED_HOSTS to the Render hostname and any custom domain hostnames.'
    )

default_origin = f'https://{RENDER_HOSTNAME}' if RENDER_HOSTNAME else ''
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', default_origin).split(',')
    if origin.strip()
]
if not CSRF_TRUSTED_ORIGINS or any(
    not origin.startswith('https://') for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured(
        'CSRF_TRUSTED_ORIGINS must contain the production HTTPS origin(s).'
    )

PUBLIC_SITE_URL = _required_env('PUBLIC_SITE_URL').rstrip('/')
if not PUBLIC_SITE_URL.startswith('https://'):
    raise ImproperlyConfigured('PUBLIC_SITE_URL must use HTTPS in production.')

DATABASE_URL = _required_env('DATABASE_URL')
DATABASES = {
    'default': dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=True,
    ),
}
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('Production DATABASE_URL must use PostgreSQL.')

REDIS_URL = _required_env('REDIS_URL')
if not REDIS_URL.startswith(('redis://', 'rediss://')):
    raise ImproperlyConfigured('REDIS_URL must be a Redis connection URL.')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    },
}

# Render's persistent disk must be mounted at /var/data and MEDIA_ROOT must
# point inside it. Otherwise user uploads disappear when an instance restarts.
MEDIA_ROOT = Path(_required_env('MEDIA_ROOT'))
if not MEDIA_ROOT.is_absolute():
    raise ImproperlyConfigured('MEDIA_ROOT must be an absolute persistent-disk path.')
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = _required_env('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = _required_env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = _required_env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = _required_env('DEFAULT_FROM_EMAIL')

AWS_SMS_ENABLED = False

SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
