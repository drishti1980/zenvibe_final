from django.db.models import Prefetch

from .models import Category


def storefront_categories(request):
    """Top-level storefront categories with active children prefetched."""
    try:
        active_children = Category.objects.filter(
            is_active=True, is_out_of_stock=False
        ).order_by("sort_order", "name")
        categories = (
            Category.objects.filter(
                parent__isnull=True, is_active=True, is_out_of_stock=False
            )
            .prefetch_related(Prefetch("children", queryset=active_children))
            .order_by("sort_order", "name")
        )
    except Exception:
        categories = Category.objects.none()
    return {"storefront_categories": categories}

def editor_configuration(request):
    """
    Global editor configuration exposed to Django templates.

    Kept intentionally lightweight so normal storefront pages can render
    without depending on a specific product or editor session.
    """
    return {
        "editor_configuration": {}
    }