from django.shortcuts import redirect

class DemoAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        allowed_urls = [
            "/demo-login/",
            "/admin/login/",
            "/static/",
            "/media/",
        ]

        if not request.session.get("demo_access"):
            if not any(request.path.startswith(url) for url in allowed_urls):
                return redirect("/demo-login/")

        return self.get_response(request)