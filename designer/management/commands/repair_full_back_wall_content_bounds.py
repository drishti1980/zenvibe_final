
import copy, math
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, DesignTemplate

PRODUCT_ID = 199
RATIO_W = 117.0
RATIO_H = 80.0

TEXT_TYPES = {"text","i-text","textbox"}

def num(v, default=0.0):
    try: return float(v)
    except (TypeError, ValueError): return float(default)

def obj_box(o):
    x=num(o.get("left", o.get("x",0)))
    y=num(o.get("top", o.get("y",0)))
    sx=abs(num(o.get("scaleX",1),1))
    sy=abs(num(o.get("scaleY",1),1))
    typ=str(o.get("type","")).lower()
    if typ in TEXT_TYPES:
        fs=max(1,num(o.get("fontSize",32),32))
        txt=str(o.get("text",""))
        w=num(o.get("width"),0)
        if w <= 0:
            lines=txt.splitlines() or [txt]
            w=max(1,max(len(line) for line in lines))*fs*0.62
        h=num(o.get("height"),0) or fs*max(1,len(txt.splitlines()))*1.25
    elif typ=="circle":
        r=num(o.get("radius",o.get("r",0)))
        w=h=2*r
    elif typ=="ellipse":
        w=2*num(o.get("rx",0)); h=2*num(o.get("ry",0))
    elif typ=="line" and isinstance(o.get("points"),list) and len(o["points"])>=4:
        pts=o["points"]; w=abs(num(pts[2])-num(pts[0])); h=abs(num(pts[3])-num(pts[1]))
    else:
        w=num(o.get("width",o.get("w",0)))
        h=num(o.get("height",o.get("h",0)))
    return x,y,x+w*sx,y+h*sy

def scale_object(o, ox, oy, scale, tx, ty):
    o["left"]=tx+(num(o.get("left",o.get("x",0)))-ox)*scale
    o["top"]=ty+(num(o.get("top",o.get("y",0)))-oy)*scale
    o.pop("x",None); o.pop("y",None)
    # Keep Fabric scale fields, but scale geometry itself so editing remains intuitive.
    for k in ("width","height","w","h","radius","r","rx","ry","fontSize","strokeWidth"):
        if k in o and o[k] is not None:
            o[k]=num(o[k])*scale
    if isinstance(o.get("points"),list):
        pts=o["points"]
        if len(pts)>=4 and all(isinstance(v,(int,float)) for v in pts):
            o["points"]=[num(v)*scale for v in pts]
    if isinstance(o.get("points"),list) and o.get("type")=="polygon":
        for p in o["points"]:
            if isinstance(p,dict):
                p["x"]=num(p.get("x"))*scale; p["y"]=num(p.get("y"))*scale

def is_background(o, base_w, base_h):
    if str(o.get("type","")).lower()!="rect": return False
    x=num(o.get("left",o.get("x",0))); y=num(o.get("top",o.get("y",0)))
    w=num(o.get("width",o.get("w",0))); h=num(o.get("height",o.get("h",0)))
    return x <= 5 and y <= 5 and w >= base_w*.82 and h >= base_h*.82 and not o.get("customerEditable",True)

def repair(data):
    data=copy.deepcopy(data or {})
    doc=data.setdefault("document",{})
    base_w=max(720.0,num(doc.get("width"),720))
    base_h=max(480.0,num(doc.get("height"),720))

    # Logical artboard follows the real 117 x 80 inch print ratio.
    target_h=base_h
    target_w=target_h*(RATIO_W/RATIO_H)
    if base_w/base_h > RATIO_W/RATIO_H:
        target_w=base_w
        target_h=target_w/(RATIO_W/RATIO_H)

    doc["width"]=round(target_w,3)
    doc["height"]=round(target_h,3)
    doc["physical"]={"widthIn":RATIO_W,"heightIn":RATIO_H,"unit":"in"}

    pages=data.get("pages") or []
    changed=0
    for page in pages:
        objs=page.get("objects") or []
        content=[]
        for o in objs:
            if is_background(o,base_w,base_h):
                o["left"]=0; o["top"]=0
                o["width"]=target_w; o["height"]=target_h
                continue
            content.append(o)

        if not content: continue
        boxes=[obj_box(o) for o in content]
        minx=min(b[0] for b in boxes); miny=min(b[1] for b in boxes)
        maxx=max(b[2] for b in boxes); maxy=max(b[3] for b in boxes)
        cw=max(1,maxx-minx); ch=max(1,maxy-miny)

        # 4% safe inset, comfortably beyond ZenVibe's 2-inch edge guidance.
        mx=target_w*.04; my=target_h*.04
        avail_w=target_w-2*mx; avail_h=target_h-2*my
        scale=min(avail_w/cw, avail_h/ch, 1.0)

        # Even when scale=1, shift the composition back inside the safe box.
        new_w=cw*scale; new_h=ch*scale
        tx=max(mx, min(mx+(avail_w-new_w)/2, target_w-mx-new_w))
        ty=max(my, min(my+(avail_h-new_h)/2, target_h-my-new_h))
        for o in content:
            scale_object(o,minx,miny,scale,tx,ty)
        changed += 1

    data["pageCount"]=len(pages)
    data["contentBoundsRepaired"]=True
    data["contentBoundsRepairVersion"]=14
    return data,changed

class Command(BaseCommand):
    help="Repair Product 199 Full Back Wall V11 content so no editable objects are clipped."

    def add_arguments(self, parser):
        parser.add_argument("--product-id",type=int,default=PRODUCT_ID)
        parser.add_argument("--dry-run",action="store_true")

    def handle(self,*args,**opts):
        pid=opts["product_id"]
        try: product=Product.objects.get(pk=pid)
        except Product.DoesNotExist: raise CommandError(f"Product {pid} not found")

        qs=DesignTemplate.objects.filter(product=product,is_active=True).order_by("id")
        if not qs.exists(): raise CommandError("No active templates found.")

        repaired=[]
        for t in qs:
            data,pages_changed=repair(t.json_data or {})
            if pages_changed:
                repaired.append((t,data,pages_changed))

        self.stdout.write(f"Product: {product.pk} {product.name}")
        self.stdout.write(f"Active templates: {qs.count()}")
        self.stdout.write(f"Templates to repair: {len(repaired)}")
        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("DRY RUN only — database unchanged."))
            return

        with transaction.atomic():
            for t,data,_ in repaired:
                t.json_data=data
                t.save(update_fields=["json_data","updated_at"] if hasattr(t,"updated_at") else ["json_data"])

        self.stdout.write(self.style.SUCCESS(
            f"Repaired {len(repaired)} templates. All page content is now fitted inside the 117 × 80 in artboard safe area."
        ))
