"""Minimal Django settings for adapter HTTP-contract tests."""

SECRET_KEY = "test-secret-key"
DEBUG = True
ALLOWED_HOSTS = ["testserver", "localhost"]
ROOT_URLCONF = "support.django_conf.urls"
INSTALLED_APPS: list[str] = []
MIDDLEWARE: list[str] = []
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
