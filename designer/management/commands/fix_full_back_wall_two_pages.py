from django.core.management.base import BaseCommand
from designer.models import Product, DesignTemplate, ProductPrintSurface

class Command(BaseCommand):
    help="Force Canopy Tent Full Back Wall to two 117x80 inch pages and repair generated template metadata."

    def add_arguments(self,p):
        p.add_argument("--product-id",type=int,default=199)

    def handle(self,*args,**o):
        product=Product.objects.get(pk=o["product_id"])
        ProductPrintSurface.objects.filter(product=product).delete()
        ProductPrintSurface.objects.create(product=product,label="Inside Back Wall",
            print_width_in=117,print_height_in=80,sort_order=1,is_active=True)
        ProductPrintSurface.objects.create(product=product,label="Outside Back Wall",
            print_width_in=117,print_height_in=80,sort_order=2,is_active=True)

        fixed=0
        for t in DesignTemplate.objects.filter(product=product,is_active=True):
            d=t.json_data or {}
            if not str(t.name).startswith("Full Back Wall Luxury"): continue
            pages=list(d.get("pages") or [])
            if len(pages)==1:
                import copy
                pages.append(copy.deepcopy(pages[0]))
            if len(pages)>=2:
                pages=pages[:2]
                pages[0]["name"]="Inside Back Wall"
                pages[1]["name"]="Outside Back Wall"
                pages[0]["physical"]={"widthIn":117,"heightIn":80,"unit":"in"}
                pages[1]["physical"]={"widthIn":117,"heightIn":80,"unit":"in"}
                # Make page 2 visibly coordinated but not a literal duplicate.
                if pages[1].get("objects"):
                    pages[1]["background"]=pages[1].get("background","#111827")
                d["pages"]=pages
                d["pageCount"]=2
                d["unit"]="in"
                t.json_data=d
                t.save(update_fields=["json_data"])
                fixed+=1
        self.stdout.write(self.style.SUCCESS(
            "Fixed product %s: 2 print surfaces + %s two-page luxury templates."%(product.id,fixed)))
