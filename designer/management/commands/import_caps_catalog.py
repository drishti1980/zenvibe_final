import zipfile
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from designer.models import Category, Product, ProductImage, ProductColorVariant

# Canonical ZenVibe Custom Caps. The supplied ZIP contains clean front views for
# the eight published Embroidered colours. DTF shares the same physical cap
# colour artwork; decoration method remains product-specific.
CAPS = [
    ("Custom Embroidered Caps – Premium Logo Stitching","480",[
        ("White","14.png"),("Black","7-1.png"),("Navy Blue","13.png"),
        ("Neon Orange","12-1.png"),("Kelly Green","11-2.png"),("Red","10-2.png"),
        ("Purple","8-1.png"),("Light Pink","9-2.png"),
    ]),
    ("Premium Custom Caps with DTF Logo Canada | Stylish & Durable","481",[
        ("White","14.png"),("Black","7-1.png"),("Navy Blue","13.png"),
        ("Neon Orange","12-1.png"),("Kelly Green","11-2.png"),("Red","10-2.png"),
        ("Purple","8-1.png"),("Light Pink","9-2.png"),
    ]),
]
HEX={"White":"#FFFFFF","Black":"#111111","Navy Blue":"#172433","Neon Orange":"#F28C18",
     "Kelly Green":"#15723D","Red":"#D51F2A","Purple":"#4C327B","Light Pink":"#E7B5C8"}

class Command(BaseCommand):
    help="Localize the two canonical ZenVibe Custom Caps from Caps ZIP."
    def add_arguments(self,p):
        p.add_argument("--zip",dest="zip_path",required=True)
        p.add_argument("--apply",action="store_true")
        p.add_argument("--disable-legacy",action="store_true")
    def handle(self,*args,**o):
        zp=Path(o["zip_path"])
        if not zp.exists(): raise CommandError(f"ZIP not found: {zp}")
        cat=Category.objects.filter(name__iexact="Custom Caps").first()
        if not cat:
            cat=Category.objects.filter(name__icontains="Caps").first()
        if not cat: raise CommandError("Custom Caps category not found")
        with zipfile.ZipFile(zp) as z:
            files={Path(n).name.lower():n for n in z.namelist() if not n.endswith("/")}
            required={fn.lower() for _,_,vs in CAPS for _,fn in vs}
            missing=sorted(required-set(files))
            if missing: raise CommandError("Caps ZIP missing: "+", ".join(missing))
            rows=[]
            for name,sid,variants in CAPS:
                p=Product.objects.filter(category=cat,source_attributes__source_product_id=sid).first()
                if not p: p=Product.objects.filter(category=cat,name__iexact=name).first()
                rows.append((name,sid,variants,p))
            self.stdout.write(f"Canonical Caps: {len(rows)}")
            self.stdout.write(f"Matched local Caps: {sum(bool(x[3]) for x in rows)}")
            if not o["apply"]:
                self.stdout.write(self.style.WARNING("REPORT ONLY. Add --apply when ready.")); return
            keep=[]
            with transaction.atomic():
                for name,sid,variants,p in rows:
                    if not p: p=Product(category=cat,name=name,slug=slugify(name)[:50],is_active=True)
                    p.name=name; p.is_active=True
                    attrs=p.source_attributes if isinstance(p.source_attributes,dict) else {}
                    attrs.update({"source_product_id":sid,"source_localized":True,"catalogue_family":"caps"})
                    p.source_attributes=attrs
                    main=variants[1][1] # black front view is the clearest neutral storefront/reference
                    p.image.save(f"caps/{sid}-{slugify(name)[:40]}.png",ContentFile(z.read(files[main.lower()])),save=False)
                    p.save(); keep.append(p.pk)
                    ProductImage.objects.filter(product=p).delete()
                    ProductColorVariant.objects.filter(product=p).delete()
                    for order,(colour,fn) in enumerate(variants):
                        pi=ProductImage(product=p,label=colour,sort_order=order)
                        pi.image.save(f"caps/gallery/{sid}-{slugify(colour)}.png",ContentFile(z.read(files[fn.lower()])),save=False); pi.save()
                        ProductColorVariant.objects.create(product=p,name=colour,color_key=slugify(colour),hex_value=HEX[colour],sort_order=order,is_active=True)
                if o["disable_legacy"]: Product.objects.filter(category=cat).exclude(pk__in=keep).update(is_active=False)
            self.stdout.write(self.style.SUCCESS("Caps localized: 2/2; colour artwork stored in local MEDIA."))