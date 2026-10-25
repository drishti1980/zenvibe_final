import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "dev-only-change-me"
DEBUG = True
ALLOWED_HOSTS = [
    "client.techorbyte.com",
    "www.client.techorbyte.com",
    "demo.techorbyte.com",
    "www.demo.techorbyte.com",
    "localhost",
    "127.0.0.1",
]
CSRF_TRUSTED_ORIGINS = [
    "https://client.techorbyte.com",
    "https://www.client.techorbyte.com",
    "https://demo.techorbyte.com",
    "https://www.demo.techorbyte.com",
]
INSTALLED_APPS = [
    "django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
    "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
    "designer.apps.DesignerConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "zenvibe_site.urls"
TEMPLATES = [{
    "BACKEND":"django.template.backends.django.DjangoTemplates",
    "DIRS":[BASE_DIR / "templates"],
    "APP_DIRS":True,
    "OPTIONS":{"context_processors":[
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "designer.context_processors.storefront_categories",
        "designer.context_processors.editor_configuration",
    ]},
}]
WSGI_APPLICATION = "zenvibe_site.wsgi.application"
DATABASES = {"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR/"db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Australia/Melbourne"
USE_I18N = True
USE_TZ = True
URL_PREFIX = os.environ.get("ZENVIBE_URL_PREFIX", "").strip("/")
STATIC_URL = f"/{URL_PREFIX + '/' if URL_PREFIX else ''}static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = f"/{URL_PREFIX + '/' if URL_PREFIX else ''}media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/accounts/login/"

# Admin Template Builder can submit a large first-save payload while a freshly
# reconstructed PNG/JPG still contains browser data-URL layer sources. The save
# endpoint immediately externalises those data URLs into MEDIA/template_layers
# and stores only normal media URLs in DesignTemplate.json_data, so subsequent
# saves are small. 128 MiB gives the first reconstruction enough headroom.
DATA_UPLOAD_MAX_MEMORY_SIZE = 128 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 16 * 1024 * 1024


# V65 transactional email + Stripe configuration. Keep secrets in environment variables.
DEFAULT_FROM_EMAIL = os.environ.get("ZENVIBE_FROM_EMAIL", "webmaster@localhost")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_BACKEND = os.environ.get("ZENVIBE_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("ZENVIBE_EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("ZENVIBE_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("ZENVIBE_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("ZENVIBE_EMAIL_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("ZENVIBE_EMAIL_USE_TLS", "1") == "1"
ZENVIBE_ADMIN_ORDER_EMAILS = os.environ.get("ZENVIBE_ADMIN_ORDER_EMAILS", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

