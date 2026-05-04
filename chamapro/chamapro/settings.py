"""
Django settings for chamapro project.
"""

from pathlib import Path
from django.contrib.messages import constants as messages
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-2i5^ib6s%m&5z2m=p@!zm(3jgbz)s6u6%5yn^)mm97z64taq6i'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']  # Allow ngrok and local during development


# Application definition

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
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'chamapro.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'  # ← Changed to Nairobi time
USE_I18N = True
USE_TZ = True


# Static files

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'chamapro.User'

# Message tags
MESSAGE_TAGS = {messages.ERROR: 'danger'}


# ── M-Pesa Daraja API ─────────────────────────────────────────────────────────
# Get credentials from https://developer.safaricom.co.ke
# Create an account → My Apps → Create App → Copy keys below

MPESA_ENV             = os.getenv('MPESA_ENV', 'sandbox')        # change to 'production' when live
MPESA_CONSUMER_KEY    = os.getenv('MPESA_CONSUMER_KEY', '')       # from Daraja portal
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')    # from Daraja portal
MPESA_SHORTCODE       = os.getenv('MPESA_SHORTCODE', '174379')    # sandbox default shortcode
MPESA_PASSKEY         = os.getenv('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')  # sandbox default passkey
MPESA_CALLBACK_URL    = os.getenv('MPESA_CALLBACK_URL', 'https://yourcallback.ngrok.io/mpesa/callback/')

# ── How to test locally ───────────────────────────────────────────────────────
# 1. Install ngrok:  https://ngrok.com/download
# 2. Run your server: python manage.py runserver
# 3. In another terminal: ngrok http 8000
# 4. Copy the https URL e.g. https://abc123.ngrok-free.app
# 5. Update MPESA_CALLBACK_URL above with that URL + /mpesa/callback/
# 6. Sandbox test phone: 254708374149