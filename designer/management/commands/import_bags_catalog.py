import csv, re, zipfile
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Category, Product, ProductImage

BAGS = {
543: ("Multi-Functional Baby Diaper Bag Backpack – Large Capacity Travel Bag","backpack","Baby-Diaper-Bag.webp",[]),
544: ("Non-Woven Shopper Tote Bag","non-woven-shopper-tote-bag","Non-Woven-Shopper-Tote-Bag.webp",["Black-Non-Woven-Tote-Bag.png","Green-Non-Woven-tote-bag.png","Orange-non-woven-bag.png","Pink-Non-Woven-tote-bag.png","Purple-Non-Woven-tote-bag.png","Red-Non-Woven-tote-bag.png","Royal-Blue-Non-Woven-tote-bag.png","Yellow-Non-Woven-tote-bag.png"]),
548: ("Budget Cotton Tote Bag","budget-cotton-tote-bag","Budget-Cotton-Tote-Bag.webp",["Black-Tote-Bag.png","Green-Tote.png","Orange-Tote.png","Purple-tote.png","Red-Tote-Bag.png","Royal-Blue-tote.png","Yellow-Tote.png","Tote-bag.png"]),
553: ("Unisex Belt Waist Bag- Stylish Fanny Pack","waist-bag","waist-bag-1.png",["waist-bag.png"]),
617: ("Personalized Foil Stamped Paper Bags","personalized-foil-stamped-paper-bags","Personalized-Foil-Stamped-Paper-Bags.webp",["Paper-twisted-handle-Bag.webp","Rivet-Handle-Bag.webp","satin-Ribbon-handle-bag.webp"]),
686: ("Classic Backpack – Durable, Lightweight & Multi-Purpose Travel & School Bag","classic-backpack-durable-lightweight-and-multi-pur","classic-backpack.png",["classic-backpack-768x768-1.png"]),
687: ("Outdoor Leisure Backpack –  Multi-Purpose Travel & Hiking Bag","outdoor-leisure-backpack-multi-purpose-travel-and-","backpack.jpeg",["backpack-1.jpeg","Red-backpack.jpeg","Light-Blue-backpack-1-e1773027092767.jpeg"]),
688: ("Crossbody Waist Bag for Men & Women – Stylish Unisex Fanny Pack","crossbody-waist-bag-for-men-and-women-stylish-unis","waist-bag.png",["waist-bag-1.png"]),
689: ("Custom Drawstring Backpack with Logo – Lightweight Promotional Cinch Bag","custom-drawstring-backpack-with-logo-lightweight-p","drawstring-bag.webp",[]),
704: ("Custom Insulated Lunch Bag with Multiple Pockets","custom-insulated-lunch-bag-with-multiple-pockets","Custom-Lunch-Bag.webp",["Black-Lunch-Bag-template.png","Blue-Lunch-Bag-template.png","grey-Lunch-Bag-template.png","Red-Lunch-Bag-template.png","Teal-Color-Lunch-Bag.png","Lunch-Bag-Color-Option.webp","Lunch-Box-Size-Info.webp","Lunch-Box-Water-test.webp"]),
}
class Command(BaseCommand):
    help="Import the canonical 10 ZenVibe Bags and local assets from Bags.zip. Runtime stays local."
    def add_arguments(self,p):
        p.add_argument("--zip",dest="zip_path",required=True); p.add_argument("--apply",action="store_true"); p.add_argument("--disable-legacy",action="store_true")
    def handle(self,*args,**o):
        zp=Path(o["zip_path"])
        if not zp.exists(): raise CommandError(f"ZIP not found: {zp}")
        cat=Category.objects.filter(name__iexact="Bags").first()
        if not cat: raise CommandError("Bags category not found")
        with zipfile.ZipFile(zp) as z:
            files={Path(n).name.lower():n for n in z.namelist() if not n.endswith("/")}
            missing=[]; rows=[]
            for sid,(name,slug,main,gallery) in BAGS.items():
                if main.lower() not in files: missing.append(main)
                p=Product.objects.filter(category=cat).filter(source_attributes__source_product_id=str(sid)).first()
                if not p: p=Product.objects.filter(category=cat,name__iexact=name).first()
                rows.append((sid,name,slug,main,gallery,p))
            self.stdout.write(f"Canonical Bags: {len(rows)}"); self.stdout.write(f"Matched local Bags: {sum(bool(x[-1]) for x in rows)}"); self.stdout.write(f"Missing ZIP main assets: {len(missing)}")
            for x in missing:self.stdout.write(self.style.ERROR("MISSING "+x))
            if missing: raise CommandError("Bags.zip is incomplete for canonical main assets")
            if not o["apply"]: self.stdout.write(self.style.WARNING("REPORT ONLY. Add --apply when ready.")); return
            with transaction.atomic():
                keep=[]
                for sid,name,slug,main,gallery,p in rows:
                    if not p:
                        p=Product(category=cat,name=name,slug=slug,is_active=True)
                    p.name=name; p.slug=slug; p.is_active=True
                    attrs=p.source_attributes if isinstance(p.source_attributes,dict) else {}
                    attrs.update({"source_product_id":str(sid),"source_localized":True,"catalogue_family":"bags"})
                    p.source_attributes=attrs
                    data=z.read(files[main.lower()]); ext=Path(main).suffix.lower()
                    p.image.save(f"bags/{slug}{ext}",ContentFile(data),save=False); p.save(); keep.append(p.pk)
                    ProductImage.objects.filter(product=p).delete()
                    order=0
                    for g in gallery:
                        member=files.get(g.lower())
                        if not member: continue
                        pi=ProductImage(product=p,label=Path(g).stem,sort_order=order)
                        pi.image.save(f"bags/gallery/{slug}-{order}{Path(g).suffix.lower()}",ContentFile(z.read(member)),save=False); pi.save(); order+=1
                if o["disable_legacy"]: Product.objects.filter(category=cat).exclude(pk__in=keep).update(is_active=False)
            self.stdout.write(self.style.SUCCESS("Bags localized: 10/10 canonical products; main/gallery images stored in local MEDIA."))
