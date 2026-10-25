from django.db import migrations


def seed_exact_awards(apps, schema_editor):
    Category = apps.get_model("designer", "Category")
    Product = apps.get_model("designer", "Product")
    category, _ = Category.objects.update_or_create(
        slug="awards",
        defaults={
            "name": "Awards",
            "icon": "🏆",
            "description": "Custom awards and trophies.",
            "is_active": True,
            "is_out_of_stock": False,
            "sort_order": 40,
        },
    )
    products = [
        ("3 Star Gold Plastic Trophy", "gold-star-trophy", 15.99, "products/awards/gold-star-trophy.png"),
        ("Achievement Crystal Award – Custom Engraved Recognition Trophy", "premium-crystal-achievement", 124.99, "products/awards/premium-crystal-achievement.png"),
        ("Blue White Artistic Crystal Award – Premium Custom Engraved Glass Trophy", "blue-white-artistic-crystal", 124.99, "products/awards/blue-resin-pillar.png"),
        ("Crystal Appreciation Trophy", "crystal-appreciation-trophy", 124.99, "products/awards/player-match-crystal.png"),
        ("Crystal Diamond Cut Silver Medal – Premium Custom Engraved Award", "crystal-diamond-cut-silver-medal", 9.99, "products/awards/custom-logo-medal.png"),
        ("Crystal Diamond Cut Sports Medal – Premium Custom Engraved Award", "crystal-diamond-cut-sports-medal", 9.99, "products/awards/excellence-crystal-medal.png"),
        ("Custom Crystal Diamond Award – Premium Engraved Awards", "custom-crystal-diamond-award", 124.99, "products/awards/crystal-diamond.png"),
        ("Custom Crystal Star Award – Premium Engraved Crystal Awards", "custom-crystal-star-award", 124.99, "products/awards/acrylic-star.png"),
        ("Custom Design Crystal Glass Award Plaque", "custom-design-crystal-glass-plaque", 79.99, "products/awards/certificate-appreciation-plaque.png"),
        ("Custom Engraved Wooden Plaque | Personalized Recognition & Appreciation Award", "custom-engraved-wooden-plaque", 79.99, "products/awards/timber-plaque.png"),
        ("Custom Five-Pointed Star Crystal Award – Premium Engraved Award", "custom-five-pointed-star-crystal-award", 124.99, "products/awards/glass-plaque.png"),
        ("Custom Gold Plastic Trophy | Personalized Trophy", "custom-gold-plastic-trophy", 20.99, "products/awards/metal-trophy.png"),
    ]
    allowed = {slug for _, slug, _, _ in products}
    Product.objects.filter(category=category).exclude(slug__in=allowed).update(is_active=False)
    for name, slug, price, image in products:
        Product.objects.update_or_create(
            category=category,
            slug=slug,
            defaults={
                "name": name,
                "description": "",
                "price": price,
                "image": image,
                "width": 720,
                "height": 720,
                "orientation": "portrait",
                "min_dpi": 150,
                "is_active": True,
                "is_out_of_stock": False,
                "is_on_sale": False,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("designer", "0011_update_awards_real_products")]
    operations = [migrations.RunPython(seed_exact_awards, migrations.RunPython.noop)]
