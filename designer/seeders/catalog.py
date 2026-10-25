"""Idempotent default catalogue seeders.

These helpers deliberately use update_or_create/get_or_create so running migrate,
post_migrate, or the management command multiple times never duplicates records.
"""
from decimal import Decimal

from django.db import transaction


PEN_PRODUCTS = (
    {
        "name": "Business Signature Metal Gel Pen",
        "slug": "business-signature-metal-gel-pen",
        "description": (
            "Premium metal gel pen with custom logo or text printing. "
            "Available in navy, black and silver with black or blue ink."
        ),
        "price": Decimal("2.49"),
    },
    {
        "name": "Executive Metal Roller Pen",
        "slug": "executive-metal-roller-pen",
        "description": "Elegant metal roller pen for corporate branding and executive gifts.",
        "price": Decimal("3.95"),
    },
    {
        "name": "Classic Twist Action Pen",
        "slug": "classic-twist-action-pen",
        "description": "Reliable twist-action promotional pen with a clean printable barrel.",
        "price": Decimal("1.85"),
    },
    {
        "name": "Premium Stylus Metal Pen",
        "slug": "premium-stylus-metal-pen",
        "description": "Metal ballpoint pen with touchscreen stylus and custom branding area.",
        "price": Decimal("2.95"),
    },
    {
        "name": "Eco Bamboo Signature Pen",
        "slug": "eco-bamboo-signature-pen",
        "description": "Natural-look bamboo pen suited to sustainable campaigns and events.",
        "price": Decimal("2.25"),
    },
    {
        "name": "Luxury Gift Box Pen",
        "slug": "luxury-gift-box-pen",
        "description": "Premium presentation pen designed for personalised corporate gifting.",
        "price": Decimal("8.50"),
    },
)


@transaction.atomic
def ensure_pen_catalogue(Category, Product, DesignTemplate=None):
    """Create or repair the default Pen category and products.

    Existing manually-created Pen/Pens categories are reused rather than duplicated.
    Existing products with the same slug are updated only with safe catalogue fields;
    uploaded images and other administrator-controlled fields remain untouched.
    """
    category = (
        Category.objects.filter(slug__in=("pen", "pens")).order_by("id").first()
        or Category.objects.filter(name__iexact="Pen").order_by("id").first()
        or Category.objects.filter(name__iexact="Pens").order_by("id").first()
    )

    if category is None:
        category = Category.objects.create(
            name="Pens",
            slug="pen",
            icon="🖊️",
            description="Premium custom pens for corporate gifts, events and everyday branding.",
            is_active=True,
            is_out_of_stock=False,
            sort_order=3,
        )
    else:
        changed = False
        # Keep the user's chosen name/slug, but guarantee it is visible.
        if not category.is_active:
            category.is_active = True
            changed = True
        if category.is_out_of_stock:
            category.is_out_of_stock = False
            changed = True
        if not category.icon:
            category.icon = "🖊️"
            changed = True
        if not category.description:
            category.description = "Premium custom pens for corporate gifts, events and everyday branding."
            changed = True
        if changed:
            category.save()

    created_products = []
    for position, data in enumerate(PEN_PRODUCTS, start=1):
        product = Product.objects.filter(slug=data["slug"]).order_by("id").first()
        defaults = {
            "category": category,
            "name": data["name"],
            "orientation": "landscape",
            "description": data["description"],
            "price": data["price"],
            "width": 36,
            "height": 18,
            "bleed_mm": Decimal("1.00"),
            "safe_margin_mm": Decimal("2.00"),
            "min_dpi": 300,
            "is_active": True,
            "is_out_of_stock": False,
        }
        if product is None:
            product = Product.objects.create(slug=data["slug"], **defaults)
            created_products.append(product)
        else:
            # Repair catalogue assignment/visibility but retain uploaded image.
            for field, value in defaults.items():
                setattr(product, field, value)
            product.save()

        if DesignTemplate is not None:
            for template_name, preset in (
                ("Company Name & Phone", "company"),
                ("Centered Logo", "logo"),
                ("Personal Name", "name"),
            ):
                DesignTemplate.objects.get_or_create(
                    product=product,
                    name=template_name,
                    defaults={
                        "is_active": True,
                        "json_data": {
                            "type": "pen-template",
                            "preset": preset,
                            "version": 1,
                        },
                    },
                )

    return category, created_products
