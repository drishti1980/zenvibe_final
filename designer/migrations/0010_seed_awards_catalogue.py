from django.db import migrations


def seed_awards(apps, schema_editor):
    Category=apps.get_model("designer","Category")
    Product=apps.get_model("designer","Product")
    category,_=Category.objects.update_or_create(slug="awards",defaults={"name":"Awards","icon":"🏆","description":"Personalised crystal, glass, acrylic, timber and metal awards.","is_active":True,"is_out_of_stock":False,"sort_order":40})
    products=[
        ("Crystal Diamond Award","crystal-diamond-award",69.99,"products/awards/crystal-diamond.png"),
        ("Glass Plaque Award","glass-plaque-award",64.99,"products/awards/glass-plaque.png"),
        ("Acrylic Star Award","acrylic-star-award",49.99,"products/awards/acrylic-star.png"),
        ("Timber Recognition Plaque","timber-plaque-award",54.99,"products/awards/timber-plaque.png"),
        ("Metal Achievement Trophy","metal-trophy-award",59.99,"products/awards/metal-trophy.png"),
    ]
    for name,slug,price,image in products:
        Product.objects.update_or_create(category=category,slug=slug,defaults={"name":name,"description":"Premium personalised award with a dedicated engraving area and live preview.","price":price,"image":image,"width":720,"height":720,"orientation":"portrait","min_dpi":150,"is_active":True,"is_out_of_stock":False})

def unseed_awards(apps,schema_editor):
    Category=apps.get_model("designer","Category")
    Category.objects.filter(slug="awards").delete()

class Migration(migrations.Migration):
    dependencies=[("designer","0009_seed_drinkware_catalogue")]
    operations=[migrations.RunPython(seed_awards,unseed_awards)]
