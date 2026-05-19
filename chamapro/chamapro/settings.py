"""
Django settings for chamapro project.
"""

from pathlib import Path
from django.contrib.messages import constants as messages
from decimal import Decimal
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-2i5^ib6s%m&5z2m=p@!zm(3jgbz)s6u6%5yn^)mm97z64taq6i'

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'chamapro',
    'wallets',
    'messaging',
    'investments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',       # ← added (must be 2nd)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'chamapro.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'chamapro.context_processors.user_subscription',
                'chamapro.context_processors.active_chama',
            ],
        },
    },
]

WSGI_APPLICATION = 'chamapro.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# ── Static files ──────────────────────────────────────────────────────────────

STATIC_URL = '/static/'

STATICFILES_DIRS = [BASE_DIR / 'static']          # your source static folder

STATIC_ROOT = BASE_DIR / 'staticfiles'            # ← added: where collectstatic outputs

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'  # ← added

# ── Media files (user uploads — avatars etc.) ─────────────────────────────────

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'chamapro.User'

MESSAGE_TAGS = {messages.ERROR: 'danger'}

# ── M-Pesa Daraja API ─────────────────────────────────────────────────────────

MPESA_ENV             = os.getenv('MPESA_ENV', 'sandbox')
MPESA_CONSUMER_KEY    = os.getenv('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
MPESA_SHORTCODE       = os.getenv('MPESA_SHORTCODE', '174379')
MPESA_PASSKEY         = os.getenv('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
MPESA_CALLBACK_URL    = os.getenv('MPESA_CALLBACK_URL', 'https://yourcallback.ngrok.io/mpesa/callback/')

# ── Investments ───────────────────────────────────────────────────────────────

INVESTMENT_DEFAULT_NAV          = Decimal('100.00')
INVESTMENT_DEFAULT_RETURN_MODE  = 'distribute'
INVESTMENT_CURRENCY             = 'KES'
INVESTMENT_UNIT_DECIMAL_PLACES  = 4
INVESTMENT_NAV_DECIMAL_PLACES   = 2

# ── Email ─────────────────────────────────────────────────────────────────────

# Dev: prints emails to console. Switch to SMTP in production.
EMAIL_BACKEND           = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST              = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT              = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS           = True
EMAIL_HOST_USER         = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD     = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL      = os.getenv('DEFAULT_FROM_EMAIL', 'ChamaPro <info@chamapro.com>')
PARTNER_NOTIFICATION_EMAIL = os.getenv('PARTNER_NOTIFICATION_EMAIL', 'info@chamapro.com')