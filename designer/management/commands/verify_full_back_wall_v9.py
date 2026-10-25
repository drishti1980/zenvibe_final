from django.core.management.base import BaseCommand
from designer.models import DesignTemplate
import json, hashlib

class Command(BaseCommand):
    def add_arguments(self,p):
        p.add_argument("--product-id",type=int,default=199)
    def handle(self,*a,**o):
        qs=DesignTemplate.objects.filter(product_id=o["product_id"],
            name__startswith="Full Back Wall Luxury V9",is_active=True).order_by("id")
        bad=[]; sigs=set()
        for t in qs:
            d=t.json_data or {}; pages=d.get("pages") or []
            if len(pages)!=2 or any(len((p or {}).get("objects") or [])<3 for p in pages):
                bad.append((t.id,t.name,len(pages),[len((p or {}).get("objects") or []) for p in pages]))
                continue
            # Structural signature ignores colors/text strings so recolours don't count as unique.
            shape=[]
            for p in pages:
                shape.append([(x.get("type"),round(float(x.get("left",0)),1),
                    round(float(x.get("top",0)),1),round(float(x.get("width",0) or 0),1),
                    round(float(x.get("height",0) or 0),1),round(float(x.get("angle",0) or 0),1))
                    for x in (p.get("objects") or [])])
            sig=hashlib.sha1(json.dumps(shape,sort_keys=True).encode()).hexdigest()
            sigs.add(sig)
        self.stdout.write("Templates: %s"%qs.count())
        self.stdout.write("Two-page nonblank failures: %s"%len(bad))
        self.stdout.write("Unique structural signatures: %s"%len(sigs))
        if bad:self.stdout.write(str(bad[:10]))
        if qs.count()==100 and not bad and len(sigs)==100:
            self.stdout.write(self.style.SUCCESS("PASS: 100 distinct templates, both pages populated."))
        else:
            self.stdout.write(self.style.ERROR("FAIL: expected 100 distinct two-page templates."))
