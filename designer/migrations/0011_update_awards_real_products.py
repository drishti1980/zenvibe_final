from django.db import migrations


def update_awards(apps, schema_editor):
    Category = apps.get_model("designer", "Category")
    Product = apps.get_model("designer", "Product")
    category, _ = Category.objects.update_or_create(
        slug="awards",
        defaults={
            "name": "Awards",
            "icon": "🏆",
            "description": "Personalised trophies, crystal awards, plaques and medals.",
            "is_active": True,
            "is_out_of_stock": False,
            "sort_order": 40,
        },
    )
    products = [
        ("Gold Star Achievement Trophy", "crystal-diamond-award", 59.99, "products/awards/gold-star-trophy.png"),
        ("Premium Crystal Achievement Award", "glass-plaque-award", 89.99, "products/awards/premium-crystal-achievement.png"),
        ("Blue Resin Art Award", "acrylic-star-award", 49.99, "products/awards/blue-resin-pillar.png"),
        ("Player of the Match Crystal", "timber-plaque-award", 69.99, "products/awards/player-match-crystal.png"),
        ("Custom Logo Medal", "metal-trophy-award", 29.99, "products/awards/custom-logo-medal.png"),
        ("Excellence Crystal Medal", "excellence-crystal-medal", 34.99, "products/awards/excellence-crystal-medal.png"),
        ("Certificate of Appreciation Plaque", "certificate-appreciation-plaque", 79.99, "products/awards/certificate-appreciation-plaque.png"),
    ]
    for name, slug, price, image in products:
        Product.objects.update_or_create(
            category=category,
            slug=slug,
            defaults={
                "name": name,
                "description": "Premium personalised award with product-specific engraving and live editing.",
                "price": price,
                "image": image,
                "width": 720,
                "height": 720,
                "orientation": "portrait",
                "min_dpi": 150,
                "is_active": True,
                "is_out_of_stock": False,
            },
        )


def reverse_update(apps, schema_editor):
    Product = apps.get_model("designer", "Product")
    Product.objects.filter(slug__in=["excellence-crystal-medal", "certificate-appreciation-plaque"]).delete()


class Migration(migrations.Migration):
    dependencies = [("designer", "0010_seed_awards_catalogue")]
    operations = [migrations.RunPython(update_awards, reverse_update)]
