from decimal import Decimal

from django.db import migrations


def seed_pen_catalogue(apps, schema_editor):
    Category = apps.get_model("designer", "Category")
    Product = apps.get_model("designer", "Product")
    DesignTemplate = apps.get_model("designer", "DesignTemplate")

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
        category.is_active = True
        category.is_out_of_stock = False
        if not category.icon:
            category.icon = "🖊️"
        if not category.description:
            category.description = "Premium custom pens for corporate gifts, events and everyday branding."
        category.save()

    products = (
        ("Business Signature Metal Gel Pen", "business-signature-metal-gel-pen", "Premium metal gel pen with custom logo or text printing. Available in navy, black and silver with black or blue ink.", "2.49"),
        ("Executive Metal Roller Pen", "executive-metal-roller-pen", "Elegant metal roller pen for corporate branding and executive gifts.", "3.95"),
        ("Classic Twist Action Pen", "classic-twist-action-pen", "Reliable twist-action promotional pen with a clean printable barrel.", "1.85"),
        ("Premium Stylus Metal Pen", "premium-stylus-metal-pen", "Metal ballpoint pen with touchscreen stylus and custom branding area.", "2.95"),
        ("Eco Bamboo Signature Pen", "eco-bamboo-signature-pen", "Natural-look bamboo pen suited to sustainable campaigns and events.", "2.25"),
        ("Luxury Gift Box Pen", "luxury-gift-box-pen", "Premium presentation pen designed for personalised corporate gifting.", "8.50"),
    )

    for name, slug, description, price in products:
        product = Product.objects.filter(slug=slug).order_by("id").first()
        values = dict(
            category=category,
            name=name,
            orientation="landscape",
            description=description,
            price=Decimal(price),
            width=36,
            height=18,
            bleed_mm=Decimal("1.00"),
            safe_margin_mm=Decimal("2.00"),
            min_dpi=300,
            is_active=True,
            is_out_of_stock=False,
        )
        if product is None:
            product = Product.objects.create(slug=slug, **values)
        else:
            for field, value in values.items():
                setattr(product, field, value)
            product.save()

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
                    "json_data": {"type": "pen-template", "preset": preset, "version": 1},
                },
            )


class Migration(migrations.Migration):
    dependencies = [("designer", "0007_saveddesign_source_template")]
    operations = [migrations.RunPython(seed_pen_catalogue, migrations.RunPython.noop)]
