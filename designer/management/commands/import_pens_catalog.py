import zipfile
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from designer.models import Category, Product, ProductImage, ProductColorVariant

# The nine products currently published in ZenVibe's Pens category.
# Asset groups are from the supplied Pen.zip. Runtime remains fully local.
PENS = [
("Business Signature Metal Gel Pen","400",[("Black","1-3-scaled.png"),("Blue","2-3.png"),("Silver","3-3.png")]),
("Custom Ballpoint Pen with Soft Touch Grip","700",[("Black","21-scaled.png"),("Blue","15-scaled.png"),("Green","25-scaled.png"),("Purple","31.png")]),
("Custom Logo Metal Gel Pen with Engraved Branding","679",[("White","5-3.png"),("Red","6-3.png"),("Silver","5-5.png"),("Black","4-5.png"),("Navy","6-5.png"),("Gold","4-3.png")]),
("Metal Ballpoint Pen – Premium Writing Pen for Corporate & Promotional Use","681",[("Black","33.png"),("Blue","32.png"),("Purple","31.png")]),
("Metal Ballpoint Pen With Stylus","699",[("Black","Black-Stylus-pen-scaled.png"),("Blue","Blue-Stylus-Pen-scaled.png"),("Grey","Grey-Stylus-Pen-scaled.png"),("Red","Red-Stylus-Pen-scaled.png")]),
("Premium High End Metal Gel Pen Silver Trim","695",[("White","2-5-scaled.png"),("Silver","5-5.png"),("Black","4-5.png"),("Dark Blue","6-5.png"),("Grey","3-5-scaled.png")]),
("Rubber Coated Ballpoint Pen with Printed logo","698",[("Black","compress-img-10.webp"),("Blue","compress-img-14.webp"),("Green","compress-img-12.webp"),("Red","compress-img-11.webp"),("Orange","compress-img-13.webp"),("Pink","compress-img-15.webp"),("Yellow","compress-img-9.webp")]),
("Soft Touch Pen with Silver Trim and Stylus","697",[("Red","Red-Stylus-Pen-scaled.png"),("Dark Blue","Blue-Stylus-Pen-scaled.png"),("Black","Black-Stylus-pen-scaled.png"),("Grey","Grey-Stylus-Pen-scaled.png")]),
("Soft Touch Stylus Pen with Rose Gold Trim","678",[("Black","1-3-scaled.png"),("Rose Gold","download-1.webp"),("Grey","3-5-scaled.png"),("Dark Blue","3-4-scaled.png"),("Dark Green","7-1-scaled.png")]),
]
HEX={"White":"#FFFFFF","Black":"#111111","Red":"#C62828","Yellow":"#E5C62E","Blue":"#315EA8","Dark Blue":"#243B68","Royal Blue":"#315CC7","Light Blue":"#65A8D8","Aqua":"#64C6C8","Green":"#4F8B50","Dark Green":"#365E42","Orange":"#E87532","Pink":"#D879A0","Purple":"#724CA3","Navy":"#25365F","Grey":"#777777","Silver":"#B7BCC2","Gold":"#C39A55","Rose Gold":"#C88F83"}

class Command(BaseCommand):
    help="Import/localize the canonical nine ZenVibe Pens from the supplied Pen.zip."
    def add_arguments(self,p):
        p.add_argument("--zip",dest="zip_path",required=True)
        p.add_argument("--apply",action="store_true")
        p.add_argument("--disable-legacy",action="store_true")
    def handle(self,*args,**o):
        zp=Path(o["zip_path"])
        if not zp.exists(): raise CommandError(f"ZIP not found: {zp}")
        cat=Category.objects.filter(name__iexact="Pens").first()
        if not cat: raise CommandError("Pens category not found")
        with zipfile.ZipFile(zp) as z:
            files={Path(n).name.lower():n for n in z.namelist() if not n.endswith("/")}
            required={fn.lower() for _,_,variants in PENS for _,fn in variants}
            missing=sorted(x for x in required if x not in files)
            if missing: raise CommandError("Pen.zip missing mapped assets: "+", ".join(missing))
            rows=[]; matched=0
            for name,sid,variants in PENS:
                p=Product.objects.filter(category=cat,source_attributes__source_product_id=sid).first()
                if not p: p=Product.objects.filter(category=cat,name__iexact=name).first()
                matched+=bool(p); rows.append((name,sid,variants,p))
            self.stdout.write(f"Canonical Pens: {len(rows)}")
            self.stdout.write(f"Matched local Pens: {matched}")
            if not o["apply"]:
                self.stdout.write(self.style.WARNING("REPORT ONLY. Add --apply when ready.")); return
            keep=[]
            with transaction.atomic():
                for name,sid,variants,p in rows:
                    if not p: p=Product(category=cat,name=name,slug=slugify(name)[:50],is_active=True)
                    p.name=name; p.is_active=True
                    attrs=p.source_attributes if isinstance(p.source_attributes,dict) else {}
                    attrs.update({"source_product_id":sid,"source_localized":True,"catalogue_family":"pens"})
                    p.source_attributes=attrs
                    main=variants[0][1]
                    p.image.save(f"pens/{sid}-{slugify(name)[:42]}{Path(main).suffix.lower()}",ContentFile(z.read(files[main.lower()])),save=False)
                    p.save(); keep.append(p.pk)
                    ProductImage.objects.filter(product=p).delete()
                    ProductColorVariant.objects.filter(product=p).delete()
                    for order,(colour,fn) in enumerate(variants):
                        pi=ProductImage(product=p,label=colour,sort_order=order)
                        pi.image.save(f"pens/gallery/{sid}-{slugify(colour)}{Path(fn).suffix.lower()}",ContentFile(z.read(files[fn.lower()])),save=False); pi.save()
                        ProductColorVariant.objects.create(product=p,name=colour,color_key=slugify(colour),hex_value=HEX.get(colour,""),sort_order=order,is_active=True)
                if o["disable_legacy"]: Product.objects.filter(category=cat).exclude(pk__in=keep).update(is_active=False)
            self.stdout.write(self.style.SUCCESS("Pens localized: 9/9; product and colour images stored in local MEDIA."))