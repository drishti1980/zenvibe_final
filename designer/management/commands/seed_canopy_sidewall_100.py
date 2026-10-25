from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.files.base import ContentFile
from designer.models import Product, DesignTemplate
import json, copy

GENERATOR = "zenvibe-canopy-sidewall-100-v3-unique"
W, H = 1170, 380

PALETTES = [
    ("#101828", "#FFFFFF", "#F79009"),
    ("#173F5F", "#FFFFFF", "#00A8E8"),
    ("#0B3D2E", "#FFFFFF", "#D4AF37"),
    ("#5B1535", "#FFF8F0", "#E6B566"),
    ("#202124", "#FFFFFF", "#E53935"),
]

def rect(i,x,y,w,h,fill,stroke=None,sw=0,editable=True,opacity=1):
    return {
        "id":i,"name":i.replace("_"," ").title(),"type":"rect",
        "left":x,"top":y,"width":w,"height":h,"fill":fill,
        "stroke":stroke,"strokeWidth":sw,"opacity":opacity,
        "customerEditable":editable
    }

def textbox(i,x,y,w,text,size,fill,weight=400,align="center",font="Poppins"):
    return {
        "id":i,"name":i.replace("_"," ").title(),"type":"textbox",
        "left":x,"top":y,"width":w,"text":text,"fontSize":size,
        "fontFamily":font,"fontWeight":weight,"fill":fill,
        "textAlign":align,"lineHeight":1.05,"customerEditable":True
    }

def circle(i,x,y,r,fill,editable=True):
    return {
        "id":i,"name":i.replace("_"," ").title(),"type":"circle",
        "left":x-r,"top":y-r,"radius":r,"fill":fill,
        "customerEditable":editable
    }


SAFE = 28

def polygon(i, points, fill, editable=True, opacity=1):
    return {
        "id": i, "name": i.replace("_"," ").title(), "type": "polygon",
        "points": [{"x":x,"y":y} for x,y in points],
        "fill": fill, "opacity": opacity, "customerEditable": editable
    }

def line(i, x1, y1, x2, y2, stroke, sw=4):
    return {
        "id":i, "name":i.replace("_"," ").title(), "type":"line",
        "x1":x1, "y1":y1, "x2":x2, "y2":y2,
        "stroke":stroke, "strokeWidth":sw, "customerEditable":True
    }

def _txt(i,x,y,w,s,size,fill,weight=400,align="left"):
    # IMPORTANT: s contains real newline characters, never literal HTML or "\\n".
    return textbox(i,x,y,w,s,size,fill,weight,align)

def build_unique_objects(n, brand, accent, light):
    """
    100 deterministic compositions.
    n=0..199, so page 1 and page 2 also get independent compositions.
    macro controls the overall composition; variant changes the geometry,
    alignment, hierarchy and element placement inside that macro.
    """
    macro = n % 20
    variant = (n // 20) % 10
    shift = variant * 13
    o = [rect("background",0,0,W,H,brand,editable=True)]

    # Common copy changes by composition, not HTML.
    headlines = [
        "YOUR BRAND","MAKE AN IMPACT","BE SEEN","BIG IDEAS",
        "STAND OUT","YOUR MESSAGE","CREATE MOMENTUM","HELLO THERE",
        "BUILT TO NOTICE","SHOW UP BOLD"
    ]
    subs = [
        "EVENTS • EXHIBITIONS • PROMOTIONS",
        "MAKE YOUR EVENT STAND OUT",
        "CUSTOM EVENT BRANDING",
        "YOUR MESSAGE. FRONT AND CENTRE.",
        "DESIGNED FOR REAL-WORLD EVENTS"
    ]
    h = headlines[variant]
    s = subs[(macro + variant) % len(subs)]

    if macro == 0:
        lw=210+shift
        o += [rect("left_panel",0,0,lw,H,accent),
              _txt("headline",lw+55,78,W-lw-105,h,58,light,800),
              _txt("sub",lw+55,165,W-lw-105,s,24,light,500),
              line("rule",lw+55,225,W-70,225,accent,6),
              _txt("web",lw+55,270,500,"www.yourcompany.com",20,accent,600)]
    elif macro == 1:
        rw=235+shift
        o += [rect("right_panel",W-rw,0,rw,H,accent),
              _txt("headline",65,72,W-rw-120,h,60,light,800),
              _txt("sub",65,162,W-rw-120,s,23,light,500),
              circle("mark",W-rw/2,115,38,brand),
              _txt("web",65,278,500,"www.yourcompany.com",20,accent,600)]
    elif macro == 2:
        o += [rect("top_band",0,0,W,58+variant*3,accent),
              _txt("headline",120,104,930,h,62,light,800,"center"),
              _txt("sub",170,195,830,s,24,light,500,"center"),
              _txt("web",300,278,570,"www.yourcompany.com",20,accent,600,"center")]
    elif macro == 3:
        bh=55+variant*4
        o += [rect("bottom_band",0,H-bh,W,bh,accent),
              circle("logo",135,120,58,light),
              _txt("headline",240,70,820,h,58,light,800),
              _txt("sub",240,158,820,s,24,light,500),
              _txt("web",240,260,620,"www.yourcompany.com",20,accent,600)]
    elif macro == 4:
        cut=420+shift
        o += [polygon("diag",[(0,0),(cut,0),(cut-150,H),(0,H)],accent),
              _txt("left_title",55,105,280,"YOUR\nBRAND",50,brand,800,"center"),
              _txt("headline",cut+15,72,W-cut-65,h,54,light,800),
              _txt("sub",cut+15,160,W-cut-65,s,22,light,500),
              _txt("web",cut+15,268,500,"www.yourcompany.com",20,accent,600)]
    elif macro == 5:
        cut=700-shift
        o += [polygon("diag_right",[(cut,0),(W,0),(W,H),(cut+150,H)],accent),
              _txt("headline",70,72,560,h,56,light,800),
              _txt("sub",70,160,560,s,22,light,500),
              _txt("right_title",W-330,115,250,"YOUR\nBRAND",46,brand,800,"center"),
              _txt("web",70,270,500,"www.yourcompany.com",20,accent,600)]
    elif macro == 6:
        inset=38+variant*5
        o += [rect("frame",inset,inset,W-2*inset,H-2*inset,"rgba(0,0,0,0)",stroke=accent,sw=7),
              _txt("headline",160,82,850,h,60,light,800,"center"),
              _txt("sub",190,172,790,s,23,accent,600,"center"),
              _txt("web",300,266,570,"www.yourcompany.com",20,light,500,"center")]
    elif macro == 7:
        o += [circle("big_circle",170+shift,190,120,accent),
              _txt("logo",85+shift,145,170,"LOGO",40,brand,800,"center"),
              _txt("headline",360,78,730,h,58,light,800),
              _txt("sub",360,165,730,s,23,light,500),
              _txt("web",360,270,570,"www.yourcompany.com",20,accent,600)]
    elif macro == 8:
        o += [circle("c1",105+shift,85,42,accent), circle("c2",1035-shift,290,58,accent),
              circle("c3",930,82+variant*7,18,light),
              _txt("headline",190,80,790,h,62,light,800,"center"),
              _txt("sub",230,178,710,s,23,accent,600,"center"),
              _txt("web",300,270,570,"www.yourcompany.com",20,light,500,"center")]
    elif macro == 9:
        o += [rect("card",115+shift,55,W-230-2*shift,270,light),
              _txt("headline",185+shift,95,W-370-2*shift,h,54,brand,800,"center"),
              line("rule",260+shift,172,W-260-shift,172,accent,5),
              _txt("sub",185+shift,195,W-370-2*shift,s,21,brand,500,"center"),
              _txt("web",300,270,570,"www.yourcompany.com",19,accent,600,"center")]
    elif macro == 10:
        o += [rect("bar1",0,0,90+variant*7,H,accent),
              rect("bar2",115+variant*8,0,18,H,light),
              _txt("headline",190,75,850,h,60,light,800),
              _txt("sub",190,165,850,s,23,accent,600),
              _txt("web",190,272,600,"www.yourcompany.com",20,light,500)]
    elif macro == 11:
        o += [rect("bar_right",W-(90+variant*7),0,90+variant*7,H,accent),
              rect("thin_right",W-(140+variant*8),0,18,H,light),
              _txt("headline",90,75,850,h,60,light,800),
              _txt("sub",90,165,850,s,23,accent,600),
              _txt("web",90,272,600,"www.yourcompany.com",20,light,500)]
    elif macro == 12:
        y=70+variant*4
        o += [polygon("corner1",[(0,0),(280+shift,0),(0,190+variant*5)],accent),
              polygon("corner2",[(W,H),(W-280-shift,H),(W,H-190-variant*5)],accent),
              _txt("headline",180,y,810,h,60,light,800,"center"),
              _txt("sub",210,y+92,750,s,23,light,500,"center"),
              _txt("web",300,270,570,"www.yourcompany.com",20,accent,600,"center")]
    elif macro == 13:
        o += [polygon("chevron",[(0,0),(310+shift,0),(470+shift,H/2),(310+shift,H),(0,H)],accent),
              _txt("logo",70,145,220,"LOGO",42,brand,800,"center"),
              _txt("headline",520,72,570,h,55,light,800),
              _txt("sub",520,158,570,s,22,light,500),
              _txt("web",520,270,500,"www.yourcompany.com",20,accent,600)]
    elif macro == 14:
        mid=585+(variant-5)*18
        o += [rect("half",0,0,mid,H,accent),
              _txt("headline",55,92,mid-110,h,52,brand,800,"center"),
              _txt("right_title",mid+55,82,W-mid-110,"YOUR MESSAGE",48,light,800,"center"),
              _txt("sub",mid+55,165,W-mid-110,s,21,light,500,"center"),
              _txt("web",mid+55,270,W-mid-110,"www.yourcompany.com",19,accent,600,"center")]
    elif macro == 15:
        o += [rect("stripe_top",0,0,W,38+variant*2,accent),
              rect("stripe_bottom",0,H-(38+variant*2),W,38+variant*2,accent),
              circle("mark",585,105,35,light),
              _txt("headline",160,150,850,h,55,light,800,"center"),
              _txt("sub",190,220,790,s,22,accent,600,"center"),
              _txt("web",300,275,570,"www.yourcompany.com",19,light,500,"center")]
    elif macro == 16:
        o += [polygon("mountain1",[(0,H),(260+shift,90),(520+shift,H)],accent),
              polygon("mountain2",[(390,H),(690-shift,130),(960,H)],light,opacity=.18),
              _txt("headline",590,65,500,h,54,light,800,"center"),
              _txt("sub",590,155,500,s,21,light,500,"center"),
              _txt("web",590,270,500,"www.yourcompany.com",19,accent,600,"center")]
    elif macro == 17:
        o += [rect("label",70,65,310+shift,250,accent),
              _txt("label_text",95,125,260+shift,"YOUR\nBRAND",46,brand,800,"center"),
              _txt("headline",470+shift,72,W-530-shift,h,54,light,800),
              _txt("sub",470+shift,160,W-530-shift,s,21,light,500),
              _txt("web",470+shift,270,500,"www.yourcompany.com",19,accent,600)]
    elif macro == 18:
        o += [line("l1",70,70,W-70,70,accent,7), line("l2",70,H-70,W-70,H-70,accent,7),
              circle("dot1",105+shift,70,15,light), circle("dot2",W-105-shift,H-70,15,light),
              _txt("headline",160,105,850,h,58,light,800,"center"),
              _txt("sub",190,190,790,s,22,accent,600,"center"),
              _txt("web",300,252,570,"www.yourcompany.com",19,light,500,"center")]
    else:
        o += [polygon("ribbon",[(0,75),(780-shift,75),(880-shift,190),(780-shift,305),(0,305)],accent),
              _txt("headline",65,105,650,h,54,brand,800),
              _txt("sub",65,185,650,s,21,brand,500),
              circle("logo",1000,190,72,light),
              _txt("logo_text",935,165,130,"LOGO",34,brand,800,"center")]
    return o

def _object_bounds(obj):
    typ=obj.get("type")
    if typ=="polygon":
        pts=obj.get("points") or []
        xs=[float(p["x"]) for p in pts]; ys=[float(p["y"]) for p in pts]
        return min(xs),min(ys),max(xs),max(ys)
    if typ=="line":
        return min(obj["x1"],obj["x2"]),min(obj["y1"],obj["y2"]),max(obj["x1"],obj["x2"]),max(obj["y1"],obj["y2"])
    left=float(obj.get("left",0) or 0); top=float(obj.get("top",0) or 0)
    if typ=="circle":
        d=float(obj.get("radius",0) or 0)*2
        return left,top,left+d,top+d
    width=float(obj.get("width",0) or 0)
    if typ=="textbox":
        # Conservative height. Fabric wraps if necessary.
        lines=max(1,len(str(obj.get("text","")).split("\n")))
        fs=float(obj.get("fontSize",20) or 20)
        height=fs*float(obj.get("lineHeight",1.05) or 1.05)*lines*1.18
    else:
        height=float(obj.get("height",0) or 0)
    return left,top,left+width,top+height

def validate_objects(objects):
    bad=[]
    for obj in objects:
        if obj.get("id")=="background": continue
        l,t,r,b=_object_bounds(obj)
        if l < 0 or t < 0 or r > W or b > H:
            bad.append(f'{obj.get("id","object")}: ({l:.0f},{t:.0f})-({r:.0f},{b:.0f})')
    if bad:
        raise CommandError("Generated artwork exceeds canvas: "+"; ".join(bad))

def build_template(product, idx, width_in, height_in, surface_name):
    # Distinct palette rotation + distinct composition index.
    brand, light, accent = PALETTES[idx % len(PALETTES)]
    objects1 = build_unique_objects(idx, brand, accent, light)
    # Page 2 is NOT a mirror. It uses a separate composition and rotated palette.
    b2,l2,a2 = PALETTES[(idx+2) % len(PALETTES)]
    objects2 = build_unique_objects(idx+100, b2, a2, l2)
    validate_objects(objects1); validate_objects(objects2)

    page1={"name":"Outside Left Half Wall","background":brand,
           "physical":{"widthIn":width_in,"heightIn":height_in},"objects":objects1}
    page2={"name":"Outside Right Half Wall","background":b2,
           "physical":{"widthIn":width_in,"heightIn":height_in},"objects":objects2}
    return {
        "version":2,"templateType":"editable-master","reconstructed":True,
        "generator":GENERATOR,
        "designName":f"Canopy Side Wall Design {idx+1:03d}",
        "document":{"width":W,"height":H,"profile":"canopy",
                    "physical":{"widthIn":width_in,"heightIn":height_in},"unit":"in"},
        "pageCount":2,"pages":[copy.deepcopy(page1),copy.deepcopy(page2)],
        "adminPages":[copy.deepcopy(page1),copy.deepcopy(page2)],
        "editable":True,"editorNative":True,"editorSchema":"fabric-primitives-v1",
        "surface":surface_name,
        "source":{"type":"original-editor-native-vector-composition",
                  "note":"Two-page editable side-wall master; independent compositions; no flattened artwork."}
    }

def preview_svg(objects):
    import html

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    for o in objects:
        t=o.get("type")
        if t=="rect":
            out.append(f'<rect x="{o["left"]}" y="{o["top"]}" width="{o["width"]}" height="{o["height"]}" fill="{o.get("fill","#fff")}"/>')
        elif t=="circle":
            r=o["radius"]
            out.append(f'<circle cx="{o["left"]+r}" cy="{o["top"]+r}" r="{r}" fill="{o.get("fill","#fff")}"/>')
        elif t=="textbox":
            x=o["left"] + (o.get("width",0)/2 if o.get("textAlign")=="center" else 0)
            anchor="middle" if o.get("textAlign")=="center" else "start"
            y=o["top"]+o.get("fontSize",20)
            for n,line in enumerate(str(o.get("text","")).split("\n")):
                out.append(
                    f'<text x="{x}" y="{y+n*o.get("fontSize",20)*1.1}" text-anchor="{anchor}" '
                    f'font-family="Arial" font-size="{o.get("fontSize",20)}" font-weight="{o.get("fontWeight",400)}" '
                    f'fill="{o.get("fill","#111")}">{html.escape(line)}</text>'
                )
    out.append("</svg>")
    return "".join(out)

class Command(BaseCommand):
    help = "Create 100 editable templates for Custom Canopy Tent Side Wall (10x10), using Admin inch dimensions."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int)
        parser.add_argument("--product-name", default="Custom Canopy Tent Side Wall (10’x10′)")
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--width-in", type=float)
        parser.add_argument("--height-in", type=float)
        parser.add_argument("--surface", default="Side Wall")
        parser.add_argument("--replace-generated", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        try:
            if opts.get("product_id"):
                product = Product.objects.get(pk=opts["product_id"])
            else:
                product = (
                    Product.objects.filter(name__iexact=opts["product_name"], is_active=True).order_by("id").first()
                    or Product.objects.filter(name__icontains="Custom Canopy Tent Side Wall", is_active=True).order_by("id").first()
                )
                if not product:
                    raise Product.DoesNotExist
        except Product.DoesNotExist:
            raise CommandError("Active Custom Canopy Tent Side Wall product not found. Pass --product-id ID.")

        from designer.models import ProductPrintSurface
        active_surfaces=list(
            ProductPrintSurface.objects.filter(product=product,is_active=True).order_by("sort_order","id")
        )

        # Explicit CLI values are allowed for a one-off build, otherwise read Admin.
        width_in = float(opts["width_in"] or 0)
        height_in = float(opts["height_in"] or 0)
        if width_in<=0 or height_in<=0:
            preferred=next(
                (x for x in active_surfaces if "half wall" in str(x.label or "").lower()
                 or "side wall" in str(x.label or "").lower()),
                active_surfaces[0] if active_surfaces else None
            )
            width_in=float(getattr(preferred,"print_width_in",0) or getattr(product,"print_width_in",0) or 0)
            height_in=float(getattr(preferred,"print_height_in",0) or getattr(product,"print_height_in",0) or 0)

        if width_in<=0 or height_in<=0:
            raise CommandError(
                "Configure side-wall print width/height in Django Admin first (or pass --width-in/--height-in). "
                "This template command will not guess ruler dimensions."
            )

        count=max(1,min(100,opts["count"]))
        built=[]
        for idx in range(count):
            data=build_template(product,idx,width_in,height_in,opts["surface"])
            built.append((f"Canopy Side Wall {idx+1:03d} · {opts['surface']}",data))

        self.stdout.write(
            f"{product.id} · {product.name}: {width_in:g} × {height_in:g} in · "
            f"{opts['surface']} · {count} editable templates · 2 pages each"
        )
        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run OK. Database unchanged."))
            return

        with transaction.atomic():
            # Template generation must never rewrite Admin ruler configuration.
            if opts["replace_generated"]:
                DesignTemplate.objects.filter(
                    product=product,
                    json_data__generator__in=[
                        "zenvibe-canopy-sidewall-100-v1",
                        "zenvibe-canopy-sidewall-100-v2-safe",
                        "zenvibe-canopy-sidewall-100-v3-unique",
                    ],
                ).delete()

            for name,data in built:
                obj,_=DesignTemplate.objects.get_or_create(product=product,name=name)
                obj.json_data=data
                obj.is_active=True
                svg=preview_svg(data["pages"][0]["objects"]).encode("utf-8")
                obj.preview.save(
                    f"canopy_editable_{product.id}_{name.split()[2]}.svg",
                    ContentFile(svg),
                    save=False
                )
                obj.save()

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(built)} editable 2-page canopy side-wall templates for {product.name}."
        ))
