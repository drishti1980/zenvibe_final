from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, ProductPrintArea

CATEGORY_SLUG = "custom-notebooks"

# Only dimensions already supported by the existing catalogue are encoded here.
# Unknown products are reported and left untouched rather than guessed.
PROFILES = {
    "Custom Hardcover Notebook": ("5.500","8.500","8","7","84","86","4.620","7.310","Front cover"),
    "Custom Spiral Notebook": ("5.500","8.500","10","7","80","86","4.400","7.310","Front cover"),
    "Custom Spiral Notebook | Promotional Spiral Bound Notebook with Logo": ("5.500","8.500","10","7","80","86","4.400","7.310","Front cover"),
}

def d(v): return Decimal(str(v))

class Command(BaseCommand):
    help = "Configure Custom Notebook products for the universal inch-based restricted editor."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int)
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        qs = Product.objects.filter(category__slug=CATEGORY_SLUG, is_active=True).order_by("id")
        if opts["product_id"]:
            qs = qs.filter(id=opts["product_id"])
        if not qs.exists():
            raise CommandError("No active Custom Notebook products found.")

        ready=pending=0
        for p in qs:
            profile=PROFILES.get(p.name)
            # Preserve complete Admin geometry if already configured.
            area=p.print_areas.filter(print_width_in__isnull=False, print_height_in__isnull=False).order_by("sort_order","id").first()
            if area and p.workspace_width_in and p.workspace_height_in:
                self.stdout.write(f"{p.id} — {p.name}: existing admin geometry preserved")
                ready+=1
                continue
            if not profile:
                pending+=1
                self.stdout.write(self.style.WARNING(f"{p.id} — {p.name}: ADMIN GEOMETRY REQUIRED; unchanged"))
                continue
            ww,wh,left,top,width,height,pw,ph,label=profile
            vals=[d(x) for x in (ww,wh,left,top,width,height,pw,ph)]
            ww,wh,left,top,width,height,pw,ph=vals
            self.stdout.write(f"{p.id} — {p.name}: ruler={ww} x {wh} in; print={pw} x {ph} in")
            ready+=1
            if opts["dry_run"]: continue
            p.customizer_mode="editor"; p.editor_layout_mode="print_area"
            p.constrain_to_print_area=True; p.show_product_reference=True
            p.workspace_width_in=ww; p.workspace_height_in=wh
            p.print_width_in=pw; p.print_height_in=ph
            p.print_left_pct=left; p.print_top_pct=top
            p.print_width_pct=width; p.print_height_pct=height
            p.orientation="portrait"
            p.save(update_fields=["customizer_mode","editor_layout_mode","constrain_to_print_area","show_product_reference","workspace_width_in","workspace_height_in","print_width_in","print_height_in","print_left_pct","print_top_pct","print_width_pct","print_height_pct","orientation"])
            area=p.print_areas.order_by("sort_order","id").first()
            if area:
                area.left=left; area.top=top; area.width=width; area.height=height
                area.print_width_in=pw; area.print_height_in=ph; area.name=area.name or label
                area.save()
            else:
                ProductPrintArea.objects.create(product=p,name=label,left=left,top=top,width=width,height=height,print_width_in=pw,print_height_in=ph,sort_order=0)
        if opts["dry_run"]: transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f"Done. Configured/preserved: {ready}; admin geometry required: {pending}."))