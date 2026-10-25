from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from designer.models import Product, ProductColorVariant

COLORS={
"544":[("Black","#111111"),("Green","#39844a"),("Orange","#ef7d22"),("Pink","#e68ba7"),("Purple","#71458d"),("Red","#c62828"),("Royal Blue","#1f5fae"),("Yellow","#e6bd21")],
"548":[("Black","#111111"),("Green","#39844a"),("Orange","#ef7d22"),("Purple","#71458d"),("Red","#c62828"),("Royal Blue","#1f5fae"),("Yellow","#e6bd21"),("Natural","#e7d6b5")],
"687":[("Black","#111111"),("Red","#c62828"),("Light Blue","#74a9cf")],
"704":[("Black","#111111"),("Blue","#1f5fae"),("Grey","#777777"),("Red","#c62828"),("Teal","#188b8b")],
}
class Command(BaseCommand):
    help="Create Bag colour choices whose names match the already-localized ProductImage labels."
    def handle(self,*a,**o):
        done=0
        for sid,colors in COLORS.items():
            p=Product.objects.filter(category__name__iexact="Bags",source_attributes__source_product_id=sid,is_active=True).first()
            if not p: raise CommandError(f"Missing canonical Bag source {sid}")
            images=list(p.angle_images.all().order_by("sort_order","id"))
            for order,(name,hx) in enumerate(colors):
                # Current importer labels files by stem. Match the human colour token.
                key=name.lower().replace(" ","-")
                candidates=[im for im in images if name.lower() in (im.label or "").lower().replace("-"," ")]
                if not candidates and name=="Natural":
                    candidates=[im for im in images if "tote bag" in (im.label or "").lower().replace("-"," ")]
                if not candidates:
                    self.stderr.write(f"SKIP {p.id} {name}: no local image match")
                    continue
                ProductColorVariant.objects.update_or_create(
                    product=p,color_key=slugify(name),
                    defaults={"name":name,"hex_value":hx,"sort_order":order,"is_active":True})
                # Exact colour label makes _variant_image_url deterministic.
                im=candidates[0]; im.label=name; im.sort_order=order; im.save(update_fields=["label","sort_order"])
                done+=1
        self.stdout.write(self.style.SUCCESS(f"Bag colour mappings configured: {done}."))
