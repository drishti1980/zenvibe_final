from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Category, Product, ProductPrintArea

# Pen editor workspace is a horizontal physical product face. The ruler must
# therefore always have a valid wide aspect ratio instead of collapsing to a few pixels.
# Keep print-zone percentages product-specific; Admin can refine physical values later.
WORKSPACE = ("36.000", "18.000")
# Individual barrel branding zones. Do not collapse these to one generic Pens area:
# the nine mockups have different barrel/trim/stylus geometry.
AREA = {
"Business Signature Metal Gel Pen":("18","44","36","12"),
"Custom Ballpoint Pen with Soft Touch Grip":("23","43","34","12"),
"Custom Logo Metal Gel Pen with Engraved Branding":("20","43","36","12"),
"Metal Ballpoint Pen – Premium Writing Pen for Corporate & Promotional Use":("21","43","35","12"),
"Metal Ballpoint Pen With Stylus":("22","43","34","12"),
"Premium High End Metal Gel Pen Silver Trim":("20","43","36","12"),
"Rubber Coated Ballpoint Pen with Printed logo":("22","42","36","14"),
"Soft Touch Pen with Silver Trim and Stylus":("22","43","34","12"),
"Soft Touch Stylus Pen with Rose Gold Trim":("22","43","34","12"),
}
class Command(BaseCommand):
    help="Configure localized ZenVibe Pens for the universal restricted editor without inventing physical dimensions."
    def handle(self,*args,**o):
        cat=Category.objects.filter(name__iexact="Pens").first()
        if not cat: raise CommandError("Pens category not found")
        qs=Product.objects.filter(category=cat,is_active=True,source_attributes__catalogue_family="pens",source_attributes__source_localized=True)
        if qs.count()!=9: raise CommandError(f"Expected exactly 9 localized Pens; found {qs.count()}. Run import_pens_catalog first.")
        with transaction.atomic():
            for p in qs:
                a=AREA.get(p.name)
                if not a: raise CommandError("Missing print zone for "+p.name)
                l,t,w,h=map(Decimal,a)
                p.customizer_mode="pen"; p.editor_layout_mode="print_area"
                p.workspace_width_in=Decimal(WORKSPACE[0]); p.workspace_height_in=Decimal(WORKSPACE[1])
                p.constrain_to_print_area=True; p.show_product_reference=True
                p.print_left_pct=l; p.print_top_pct=t; p.print_width_pct=w; p.print_height_pct=h
                if not p.editor_reference_image and p.image: p.editor_reference_image.name=p.image.name
                p.save()
                ProductPrintArea.objects.filter(product=p).delete()
                ProductPrintArea.objects.create(product=p,name="Logo / engraving area",left=l,top=t,width=w,height=h,print_width_in=p.print_width_in,print_height_in=p.print_height_in,sort_order=0)
        self.stdout.write(self.style.SUCCESS("Pens editor configured: 9/9; 36 x 18 in ruler/workspace + individual logo/engraving zones."))