"""
Production settings — DEBUG=False, HTTPS enforcement, SMTP email.
"""

import os
from django.core.exceptions import ImproperlyConfigured
import dj_database_url
from .base import *  # noqa: F401,F403

DEBUG = False

def _required_env(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise ImproperlyConfigured(f'{name} must be configured for production.')
    return value


# Production must never silently fall back to development credentials or local
# storage that disappears when an Elastic Beanstalk instance is replaced.
SECRET_KEY = _required_env('DJANGO_SECRET_KEY')
if SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be a unique production secret.')

ALLOWED_HOSTS = [
    host.strip()
    for host in _required_env('DJANGO_ALLOWED_HOSTS').split(',')
    if host.strip()
]
if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS must list explicit production hostnames.')

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in _required_env('CSRF_TRUSTED_ORIGINS').split(',')
    if origin.strip()
]
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured('CSRF_TRUSTED_ORIGINS must list the production HTTPS origin.')
if any(not origin.startswith('https://') for origin in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured('Every CSRF_TRUSTED_ORIGINS entry must use HTTPS.')

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

AWS_REGION = _required_env('AWS_REGION')
AWS_STORAGE_BUCKET_NAME = _required_env('AWS_STORAGE_BUCKET_NAME')
STORAGES = {
    **STORAGES,
    'default': {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': AWS_STORAGE_BUCKET_NAME,
            'region_name': AWS_REGION,
            'location': 'media',
            'default_acl': None,
            'file_overwrite': False,
            'querystring_auth': True,
            'querystring_expire': 3600,
        },
    },
}
AWS_S3_FILE_OVERWRITE = False

REDIS_URL = os.environ.get('REDIS_URL', '').strip()
if not REDIS_URL:
    raise ImproperlyConfigured('REDIS_URL must point to a shared ElastiCache Redis instance.')
if not REDIS_URL.startswith('rediss://'):
    raise ImproperlyConfigured('REDIS_URL must use rediss:// to require TLS in production.')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    },
}

PUBLIC_SITE_URL = _required_env('PUBLIC_SITE_URL').rstrip('/')
if not PUBLIC_SITE_URL.startswith('https://'):
    raise ImproperlyConfigured('PUBLIC_SITE_URL must use HTTPS in production.')
AWS_SMS_ENABLED = os.environ.get('AWS_SMS_ENABLED', 'false').lower() in ('true', '1', 'yes')

# ── Security ──
SECURE_HSTS_SECONDS = 31_536_000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ── Email ──
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = _required_env('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = _required_env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = _required_env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = _required_env('DEFAULT_FROM_EMAIL')
