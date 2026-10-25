from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Category, Product, ProductPrintArea

# Product-photo-specific editor geometry. These are deliberately separate per
# vessel shape so mugs, tumblers, thermoses and bottles never share one box.
GEOMETRY = {
"20oz Stainless Steel Tumbler | Leak-Proof Insulated Travel Mug for Hot & Cold Drinks":(("4.000","8.000"),("30","30","40","42"),("1.600","3.360")),
"510ml Smart Thermo Bottle with LED Temperature Display | Insulated Coffee Bottle":(("3.000","10.000"),("29","31","42","43"),("1.260","4.300")),
"Custom 12oz Leak-Proof Stainless Steel Travel Mug":(("4.000","7.000"),("27","29","46","42"),("1.840","2.940")),
"Custom 12oz Stainless Steel Mug | Custom Engraved Insulated Travel Mug":(("5.000","5.000"),("28","29","40","42"),("2.000","2.100")),
"Custom Print Ceramic Mug | Personalized Coffee Mug with Logo":(("5.000","4.500"),("24","25","47","48"),("2.350","2.160")),
"Kids BPA-Free Water Bottle | Custom Logo Bottle for Children":(("3.500","8.000"),("31","35","38","35"),("1.330","2.800")),
"Kids Insulated Stainless Steel Water Bottle with Straw":(("4.000","10.000"),("30","36","40","35"),("1.600","3.500")),
"Premium Custom Stainless Steel Water Bottle | Hot & Cold Drink Bottle with Logo":(("3.500","10.000"),("31","31","38","43"),("1.330","4.300")),
"Smart Thermos Bottle with LED Temperature Display":(("3.000","10.000"),("29","31","42","43"),("1.260","4.300")),
}
class Command(BaseCommand):
    help="Configure the 9 localized Drinkware products for the universal product-first editor."
    def handle(self,*args,**o):
        cat=Category.objects.filter(name__iexact="Drinkware").first()
        if not cat: raise CommandError("Drinkware category not found")
        qs=Product.objects.filter(category=cat,is_active=True,source_attributes__catalogue_family="drinkware",source_attributes__source_localized=True)
        if qs.count()!=9: raise CommandError(f"Expected exactly 9 localized Drinkware products; found {qs.count()}. Run import_drinkware_catalog first.")
        with transaction.atomic():
            for p in qs:
                cfg=GEOMETRY.get(p.name)
                if not cfg: raise CommandError("Missing geometry for "+p.name)
                (ww,wh),(l,t,w,h),(pw,ph)=cfg
                p.customizer_mode="drinkware"; p.editor_layout_mode="print_area"
                p.workspace_width_in=Decimal(ww); p.workspace_height_in=Decimal(wh)
                p.constrain_to_print_area=True; p.show_product_reference=True
                p.print_left_pct=Decimal(l); p.print_top_pct=Decimal(t); p.print_width_pct=Decimal(w); p.print_height_pct=Decimal(h)
                p.print_width_in=Decimal(pw); p.print_height_in=Decimal(ph)
                # Selected colour is resolved from ProductImage; keep editor_reference as fallback only.
                if not p.editor_reference_image and p.image: p.editor_reference_image.name=p.image.name
                p.save()
                ProductPrintArea.objects.filter(product=p).delete()
                ProductPrintArea.objects.create(product=p,name="Front print area",left=Decimal(l),top=Decimal(t),width=Decimal(w),height=Decimal(h),print_width_in=Decimal(pw),print_height_in=Decimal(ph),sort_order=0)
        self.stdout.write(self.style.SUCCESS("Drinkware editor configured: 9/9 with individual rulers and front print areas."))