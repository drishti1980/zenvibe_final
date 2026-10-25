from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Category, Product, ProductPrintArea

# Front-panel decoration zones are intentionally separate by decoration method.
# Admin remains the source of truth after this initial setup.
CONFIG={
"Custom Embroidered Caps – Premium Logo Stitching":{
    "workspace":("12.000","10.000"), "area":("31","25","38","31"), "label":"Front embroidery area"},
"Premium Custom Caps with DTF Logo Canada | Stylish & Durable":{
    "workspace":("12.000","10.000"), "area":("29","23","42","35"), "label":"Front DTF print area"},
}
class Command(BaseCommand):
    help="Configure canonical Custom Caps for the universal product-first editor."
    def handle(self,*args,**o):
        cat=Category.objects.filter(name__iexact="Custom Caps").first() or Category.objects.filter(name__icontains="Caps").first()
        if not cat: raise CommandError("Custom Caps category not found")
        qs=Product.objects.filter(category=cat,is_active=True,source_attributes__catalogue_family="caps",source_attributes__source_localized=True)
        if qs.count()!=2: raise CommandError(f"Expected 2 localized Caps; found {qs.count()}. Run import_caps_catalog first.")
        with transaction.atomic():
            for p in qs:
                cfg=CONFIG.get(p.name)
                if not cfg: raise CommandError("Missing Caps config: "+p.name)
                ww,wh=map(Decimal,cfg["workspace"]); l,t,w,h=map(Decimal,cfg["area"])
                p.customizer_mode="editor"; p.editor_layout_mode="print_area"
                p.workspace_width_in=ww; p.workspace_height_in=wh
                p.constrain_to_print_area=True; p.show_product_reference=True
                p.print_left_pct=l; p.print_top_pct=t; p.print_width_pct=w; p.print_height_pct=h
                if not p.editor_reference_image and p.image: p.editor_reference_image.name=p.image.name
                p.save()
                ProductPrintArea.objects.filter(product=p).delete()
                ProductPrintArea.objects.create(product=p,name=cfg["label"],left=l,top=t,width=w,height=h,
                    print_width_in=p.print_width_in,print_height_in=p.print_height_in,sort_order=0)
        self.stdout.write(self.style.SUCCESS("Caps editor configured: 2/2; locked cap reference + front-panel decoration zones."))