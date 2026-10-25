import os

from django.conf import settings
from django.http import HttpResponseRedirect
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


COOKIE_NAME = "tb_preview_auth"
TOKEN_SALT = "techorbyte-client-preview"


class PreviewAuthenticationMiddleware:
    """Require a signed Techorbyte portal cookie for the public Zenvibe preview."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.secret = os.environ.get("PREVIEW_AUTH_SECRET", settings.SECRET_KEY)
        self.max_age = int(os.environ.get("PREVIEW_AUTH_MAX_AGE", "28800"))
        self.serializer = URLSafeTimedSerializer(self.secret, salt=TOKEN_SALT)

    def __call__(self, request):
        # Keep Django admin and asset delivery reachable. The customer-facing
        # website itself remains protected.
        path = request.path_info or "/"
        if path.startswith("/admin/") or path.startswith("/static/") or path.startswith("/media/"):
            return self.get_response(request)

        token = request.COOKIES.get(COOKIE_NAME)
        if not token:
            return self._return_to_login()

        try:
            payload = self.serializer.loads(token, max_age=self.max_age)
        except (BadSignature, SignatureExpired):
            return self._return_to_login()

        demo_url = str(payload.get("demo_url", ""))
        if not demo_url.startswith("/zenvibe"):
            return self._return_to_login()

        request.techorbyte_customer_id = payload.get("customer_id")
        request.techorbyte_customer_username = payload.get("username")
        return self.get_response(request)

    @staticmethod
    def _return_to_login():
        return HttpResponseRedirect("/login")
