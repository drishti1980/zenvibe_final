from django.apps import apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .seeders.catalog import ensure_pen_catalogue


@receiver(post_migrate, dispatch_uid="designer.ensure_default_pen_catalogue")
def create_default_pen_catalogue(sender, **kwargs):
    """Ensure Pen catalogue records exist after database migrations.

    Restricted to the designer app's post_migrate event so it runs once per migrate
    command and does not perform database work during normal module import.
    """
    if sender.label != "designer":
        return

    Category = apps.get_model("designer", "Category")
    Product = apps.get_model("designer", "Product")
    DesignTemplate = apps.get_model("designer", "DesignTemplate")
    ensure_pen_catalogue(Category, Product, DesignTemplate)
