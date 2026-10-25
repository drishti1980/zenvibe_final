import zipfile
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from designer.models import Category, Product, ProductImage, ProductColorVariant

# Canonical ZenVibe Drinkware catalogue (9 products). Assets are from the supplied
# Drinkware.zip only; runtime never calls zenvibe.ca.
DRINKWARE = [
    ("20oz Stainless Steel Tumbler | Leak-Proof Insulated Travel Mug for Hot & Cold Drinks","671",
     [("Black","1-5.png"),("Navy Blue","2-9.png"),("Red","3-9.png"),("Teal","4-8.png"),("Pink","5-8.png"),("Rose Gold","6-7.png")]),
    ("510ml Smart Thermo Bottle with LED Temperature Display | Insulated Coffee Bottle","",
     [("White","8.png"),("Gold","9-1.png"),("Pink","10-1.png"),("Blue","11-1.png"),("Red","12.png")]),
    ("Custom 12oz Leak-Proof Stainless Steel Travel Mug","",
     [("Blue","15.png"),("Black","16.png"),("White","17.png"),("Olive","18.png")]),
    ("Custom 12oz Stainless Steel Mug | Custom Engraved Insulated Travel Mug","",
     [("White","1-4.png"),("Stainless Steel","2-8.png"),("Yellow","3-8.png"),("Black","4-7.png"),("Red","5-7.png"),("Rose Gold","6-6.png"),("Orange","7-2.png")]),
    ("Custom Print Ceramic Mug | Personalized Coffee Mug with Logo","694",
     [("White","2-7.png"),("Black","3-7.png"),("Yellow","4-6.png"),("Red","5-6.png")]),
    ("Kids BPA-Free Water Bottle | Custom Logo Bottle for Children","674",
     [("Pink","19.png"),("Blue","20.png"),("Purple","21.png"),("Mint","22.png")]),
    ("Kids Insulated Stainless Steel Water Bottle with Straw","673",
     [("Peach","1-7.png"),("Yellow","2-11.png"),("Aqua","3-11.png"),("Pink","4-10.png"),("Purple","5-10.png"),("Blue","6-8.png")]),
    ("Premium Custom Stainless Steel Water Bottle | Hot & Cold Drink Bottle with Logo","670",
     [("Black","1-6.png"),("Yellow","2-10.png"),("Blue","3-10.png"),("Pink","4-9.png"),("White","5-9.png"),("Mint","6-7.png"),("Rose","7-3.png"),("Lavender","8-2.png")]),
    ("Smart Thermos Bottle with LED Temperature Display","672",
     [("White","8.png"),("Gold","9-1.png"),("Pink","10-1.png"),("Blue","11-1.png"),("Red","12.png")]),
]
HEX={"White":"#FFFFFF","Black":"#111111","Red":"#D92323","Yellow":"#F2D83A","Blue":"#3568B8","Navy Blue":"#223A69","Teal":"#43B8B0","Pink":"#E996B7","Rose Gold":"#C98D86","Gold":"#C9A45B","Olive":"#69734A","Stainless Steel":"#B8BDC2","Orange":"#F17832","Mint":"#A9D6C8","Purple":"#8A67A8","Peach":"#F0B38E","Aqua":"#74CAD0","Rose":"#DFA0A8","Lavender":"#B7A5D5"}

class Command(BaseCommand):
    help="Localize the canonical 9 ZenVibe Drinkware products from the supplied Drinkware.zip."
    def add_arguments(self,p):
        p.add_argument("--zip",dest="zip_path",required=True)
        p.add_argument("--apply",action="store_true")
        p.add_argument("--disable-legacy",action="store_true")
    def handle(self,*args,**o):
        zp=Path(o["zip_path"])
        if not zp.exists(): raise CommandError(f"ZIP not found: {zp}")
        cat=Category.objects.filter(name__iexact="Drinkware").first()
        if not cat: raise CommandError("Drinkware category not found")
        with zipfile.ZipFile(zp) as z:
            files={Path(n).name.lower():n for n in z.namelist() if not n.endswith("/")}
            required={fn.lower() for _,_,variants in DRINKWARE for _,fn in variants}
            missing=sorted(x for x in required if x not in files)
            if missing: raise CommandError("Drinkware.zip missing: "+", ".join(missing))
            matched=0
            rows=[]
            for name,sid,variants in DRINKWARE:
                p=None
                if sid: p=Product.objects.filter(category=cat,source_attributes__source_product_id=sid).first()
                if not p: p=Product.objects.filter(category=cat,name__iexact=name).first()
                matched += bool(p); rows.append((name,sid,variants,p))
            self.stdout.write(f"Canonical Drinkware: {len(rows)}")
            self.stdout.write(f"Matched local Drinkware: {matched}")
            if not o["apply"]:
                self.stdout.write(self.style.WARNING("REPORT ONLY. Add --apply when ready.")); return
            keep=[]
            with transaction.atomic():
                for name,sid,variants,p in rows:
                    if not p: p=Product(category=cat,name=name,slug=slugify(name)[:50],is_active=True)
                    p.name=name; p.is_active=True
                    attrs=p.source_attributes if isinstance(p.source_attributes,dict) else {}
                    attrs.update({"source_localized":True,"catalogue_family":"drinkware"})
                    if sid: attrs["source_product_id"]=sid
                    p.source_attributes=attrs
                    main=variants[0][1]
                    p.image.save(f"drinkware/{slugify(name)[:55]}{Path(main).suffix.lower()}",ContentFile(z.read(files[main.lower()])),save=False)
                    p.save(); keep.append(p.pk)
                    ProductImage.objects.filter(product=p).delete()
                    ProductColorVariant.objects.filter(product=p).delete()
                    for order,(colour,fn) in enumerate(variants):
                        pi=ProductImage(product=p,label=colour,sort_order=order)
                        pi.image.save(f"drinkware/gallery/{p.pk}-{slugify(colour)}{Path(fn).suffix.lower()}",ContentFile(z.read(files[fn.lower()])),save=False); pi.save()
                        ProductColorVariant.objects.create(product=p,name=colour,color_key=slugify(colour),hex_value=HEX.get(colour,""),sort_order=order,is_active=True)
                if o["disable_legacy"]:
                    Product.objects.filter(category=cat).exclude(pk__in=keep).update(is_active=False)
            self.stdout.write(self.style.SUCCESS("Drinkware localized: 9/9; colour mockups and selectors are local."))