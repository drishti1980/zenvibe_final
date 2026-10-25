from django.db import migrations


def seed(apps, schema_editor):
    Category=apps.get_model("designer","Category"); Product=apps.get_model("designer","Product")
    category,_=Category.objects.update_or_create(slug="drinkware",defaults={"name":"Drinkware","icon":"☕","description":"Custom mugs, tumblers and bottles with front, back, wrap and engraving options.","is_active":True,"is_out_of_stock":False,"sort_order":35})
    rows=[
      ("Classic Ceramic Mug","ceramic-mug",14.99,"products/drinkware/mug-white.png"),
      ("Insulated Travel Mug","travel-mug",24.99,"products/drinkware/camp-mug-white.png"),
      ("Stainless Steel Tumbler","tumbler",27.99,"products/drinkware/tumbler-black.png"),
      ("Reusable Water Bottle","water-bottle",22.99,"products/drinkware/bottle-black.png"),
      ("Kids Sports Bottle","sports-bottle",16.99,"products/drinkware/sports-bottle-pink.png"),
    ]
    for name,slug,price,image in rows:
      Product.objects.update_or_create(category=category,slug=slug,defaults={"name":name,"description":"Customisable drinkware with professional printable areas and live editing.","price":price,"image":image,"width":720,"height":720,"orientation":"portrait","min_dpi":150,"bleed_mm":3,"safe_margin_mm":5,"is_active":True,"is_out_of_stock":False})


def reverse(apps,schema_editor):
    Category=apps.get_model("designer","Category"); Category.objects.filter(slug="drinkware").delete()

class Migration(migrations.Migration):
    dependencies=[("designer","0008_seed_default_pen_catalogue")]
    operations=[migrations.RunPython(seed,reverse)]
