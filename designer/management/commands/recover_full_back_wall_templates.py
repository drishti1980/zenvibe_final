from django.core.management.base import BaseCommand
from django.core.management import call_command
from designer.models import DesignTemplate, Product

class Command(BaseCommand):
    help="Rebuild and reactivate Product 199 Full Back Wall templates after V11."
    def add_arguments(self,p):
        p.add_argument("--product-id",type=int,default=199)
    def handle(self,*a,**o):
        pid=o["product_id"]
        p=Product.objects.get(pk=pid)

        # Remove only our generated luxury versions; do not touch unrelated admin templates.
        old=DesignTemplate.objects.filter(product=p,name__startswith="Full Back Wall Luxury V")
        self.stdout.write(f"Removing old generated luxury versions: {old.count()}")
        old.delete()

        call_command("rebuild_full_back_wall_100",product_id=pid,count=100,replace=False)

        qs=DesignTemplate.objects.filter(
            product=p,name__startswith="Full Back Wall Luxury V11"
        )
        qs.update(is_active=True)

        total=qs.count()
        active=qs.filter(is_active=True).count()
        two=0
        for t in qs:
            d=t.json_data or {}
            pages=d.get("pages") or []
            if len(pages)==2 and all((x.get("objects") or []) for x in pages):
                two+=1

        self.stdout.write(f"V11 templates: {total}")
        self.stdout.write(f"Active: {active}")
        self.stdout.write(f"Two populated pages: {two}")
        if total==100 and active==100 and two==100:
            self.stdout.write(self.style.SUCCESS("PASS: 100 templates restored and ready for editor."))
        else:
            self.stdout.write(self.style.ERROR("FAIL: template library did not rebuild correctly."))
