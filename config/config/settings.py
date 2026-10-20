"""
Django settings for the Boski store.

Secrets and per-server values come from environment variables or from a `.env`
file next to manage.py (see .env.example). Nothing secret is stored in this file.
"""

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path):
    """Tiny .env reader: KEY=value lines, '#' comments. Real environment variables win."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


TESTING = "test" in sys.argv

# ---- Core -------------------------------------------------------------------

DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or TESTING:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-online"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is not set. Copy .env.example to .env and fill it in "
            "(see HOSTING_GUIDE.md)."
        )

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# The admin lives at /admin/ by default. Set DJANGO_ADMIN_URL=some-secret-name/ to hide it a little.
ADMIN_URL = os.environ.get("DJANGO_ADMIN_URL", "admin/").strip("/") + "/"

# Boski's dashboard (the easy editing pages) lives here. The Django admin must use a different address.
DASHBOARD_URL = os.environ.get("DJANGO_DASHBOARD_URL", "manage/").strip("/") + "/"
if ADMIN_URL == DASHBOARD_URL:
    # Same address would hide the dashboard behind the admin, so the admin steps aside.
    ADMIN_URL = "admin/" if DASHBOARD_URL != "admin/" else "django-admin/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Admin login button on the website goes here, and a successful login lands on the dashboard.
LOGIN_URL = "dashboard:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "shop:home"

# ---- Apps -------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "shop",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "shop.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---- Database ---------------------------------------------------------------
# SQLite is plenty for a catalogue shop with one admin. The file is db.sqlite3 next to manage.py.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---- Language and time ------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Accra"
USE_I18N = True
USE_TZ = True

# ---- Static and media files -------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# ---- Visitors' preorder list and wishlist live in the session ---------------

SESSION_COOKIE_AGE = 60 * 60 * 24 * 60  # 60 days
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# ---- Security when the site is live ----------------------------------------

if not DEBUG and not TESTING:
    # Harmless when the host does not send this header; lets Django see "https" when it does
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # Cookies (login, preorder list) are only sent over HTTPS. Set DJANGO_SECURE_COOKIES=0
    # only while testing the site over plain http.
    SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", True)
    CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
    # Off by default: use the host's own "Force HTTPS" switch (see HOSTING_GUIDE.md).
    # Turning this on at a host that does not send X-Forwarded-Proto causes endless redirects.
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", False)
    # Leave at 0 until HTTPS works everywhere, then raise it (e.g. 31536000) as the guide explains
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "0"))
    SECURE_REFERRER_POLICY = "same-origin"
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ---- Boski's store defaults -------------------------------------------------
# Used only until Store settings are saved in the admin. After that the admin values win.
# WhatsApp number: international format, digits only (no +, spaces or dashes).

WHATSAPP_NUMBER = os.environ.get("STORE_WHATSAPP_NUMBER", "8613250576403")
WHATSAPP_DISPLAY = os.environ.get("STORE_WHATSAPP_DISPLAY", "+86 132 5057 6403")
STORE_NAME = os.environ.get("STORE_NAME", "Boski")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
