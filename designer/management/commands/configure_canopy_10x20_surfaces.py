from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, ProductPrintSurface

SURFACES=[
 ("Canopy Tent Top",240,160),
 ("Inside Back Wall",233,80),
 ("Outside Back Wall",233,80),
 ("Inside Right Side Wall",118,38),
 ("Outside Right Side Wall",118,38),
 ("Inside Left Side Wall",118,38),
 ("Outside Left Side Wall",118,38),
]

class Command(BaseCommand):
    help="Configure the seven ZenVibe 10x20 canopy print surfaces."
    def add_arguments(self,p):
        p.add_argument("--product-id",type=int,default=182)
        p.add_argument("--replace",action="store_true")
    @transaction.atomic
    def handle(self,*args,**o):
        product=Product.objects.filter(pk=o["product_id"]).first()
        if not product: raise CommandError("Product not found")
        if o["replace"]:
            product.print_surfaces.all().delete()
        for i,(label,w,h) in enumerate(SURFACES,1):
            ProductPrintSurface.objects.update_or_create(
                product=product,label=label,
                defaults={"print_width_in":w,"print_height_in":h,"sort_order":i,"is_active":True}
            )
        self.stdout.write(self.style.SUCCESS("Configured 7 active 10x20 canopy surfaces."))
        for s in product.print_surfaces.filter(is_active=True).order_by("sort_order","id"):
            self.stdout.write(f"{s.sort_order}. {s.label}: {s.print_width_in} x {s.print_height_in} in")
