from django.apps import AppConfig


class DesignerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "designer"

    def ready(self):
        # Register post_migrate catalogue seeders.
        from . import signals  # noqa: F401
