"""
Development settings — DEBUG=True, SMTP when configured, relaxed security.
"""

import os

import dj_database_url

from .base import *  # noqa: F401,F403

DEBUG = True
SECURE_SSL_REDIRECT = False

X_FRAME_OPTIONS = 'SAMEORIGIN'

DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
        ),
    }

EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@NowhenceClothings.com')

if EMAIL_HOST and EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_USE_TLS = True
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
