from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.files.base import ContentFile
from designer.models import Product, DesignTemplate
import json, copy

GENERATOR = "zenvibe-canopy-editable-v1"
W, H = 1200, 800

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

def build_objects(style, brand, accent, light):
    o = [rect("background",0,0,W,H,brand,editable=True)]
    if style == 0:
        o += [
            rect("accent_left",0,0,115,H,accent),
            rect("accent_bottom",115,700,W-115,100,light),
            textbox("brand_name",175,210,850,"YOUR BRAND",84,light,700),
            textbox("tagline",175,315,850,"MAKE YOUR EVENT STAND OUT",30,accent,600),
            textbox("website",175,645,850,"www.yourcompany.com",24,brand,600),
        ]
    elif style == 1:
        o += [
            rect("top_band",0,0,W,150,light),
            rect("bottom_band",0,650,W,150,accent),
            circle("logo_mark",600,330,95,accent),
            textbox("brand_name",180,450,840,"YOUR BRAND",72,light,700),
            textbox("tagline",180,545,840,"EVENTS • EXHIBITIONS • PROMOTIONS",25,light,500),
            textbox("website",180,705,840,"www.yourcompany.com",24,brand,700),
        ]
    elif style == 2:
        o += [
            rect("panel_left",0,0,430,H,accent),
            textbox("brand_name",65,190,300,"YOUR\nBRAND",72,brand,800),
            textbox("headline",500,205,610,"BIG IDEAS.\nBOLD PRESENCE.",58,light,700,align="left"),
            textbox("tagline",500,365,610,"Custom event branding that gets noticed.",27,light,400,align="left"),
            textbox("website",500,600,610,"www.yourcompany.com",24,accent,600,align="left"),
        ]
    elif style == 3:
        o += [
            rect("center_card",150,120,900,560,light),
            rect("center_rule",310,390,580,8,accent),
            textbox("brand_name",250,235,700,"YOUR BRAND",76,brand,800),
            textbox("tagline",250,335,700,"CREATE • CONNECT • GROW",28,accent,600),
            textbox("website",250,485,700,"www.yourcompany.com",25,brand,500),
            textbox("phone",250,535,700,"+1 000 000 0000",23,brand,500),
        ]
    else:
        o += [
            rect("stripe_1",0,0,W,95,accent),
            rect("stripe_2",0,705,W,95,light),
            textbox("brand_name",130,220,940,"YOUR BRAND",92,light,800),
            textbox("headline",130,340,940,"DESIGNED TO BE SEEN",39,accent,700),
            textbox("tagline",130,410,940,"Trade shows • Markets • Outdoor events",25,light,400),
            textbox("website",130,625,940,"www.yourcompany.com",24,brand,700),
        ]
    return o

def build_template(product, idx, width_in, height_in, surface_name):
    brand, light, accent = PALETTES[idx % len(PALETTES)]
    objects = build_objects(idx % 5, brand, accent, light)
    page = {
        "name": surface_name,
        "background": brand,
        "physical": {"widthIn": width_in, "heightIn": height_in},
        "objects": objects,
    }
    return {
        "version": 1,
        "templateType": "editable-master",
        "reconstructed": True,
        "generator": GENERATOR,
        "designName": f"Canopy Brand Layout {idx+1:02d}",
        "document": {
            "width": W,
            "height": H,
            "profile": "canopy",
            "physical": {"widthIn": width_in, "heightIn": height_in},
            "unit": "in",
        },
        "pageCount": 1,
        "pages": [copy.deepcopy(page)],
        "adminPages": [copy.deepcopy(page)],
        "editable": True,
        "editorNative": True,
        "editorSchema": "fabric-primitives-v1",
        "surface": surface_name,
        "source": {
            "type": "original-editor-native-vector-composition",
            "note": "Editable canopy layout built from Fabric primitives. No flattened artwork master."
        }
    }

def preview_svg(objects):
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
                    f'fill="{o.get("fill","#111")}">{line}</text>'
                )
    out.append("</svg>")
    return "".join(out)

class Command(BaseCommand):
    help = "Create editable ZenVibe-style canopy templates using inch-based physical dimensions."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, required=True)
        parser.add_argument("--count", type=int, default=5)
        parser.add_argument("--width-in", type=float)
        parser.add_argument("--height-in", type=float)
        parser.add_argument("--surface", default="Canopy")
        parser.add_argument("--replace-generated", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        try:
            product = Product.objects.get(pk=opts["product_id"])
        except Product.DoesNotExist:
            raise CommandError("Product not found")

        width_in = opts["width_in"] or float(product.print_width_in or 0)
        height_in = opts["height_in"] or float(product.print_height_in or 0)
        if width_in <= 0 or height_in <= 0:
            raise CommandError(
                "Set Print width/height in Admin first, or pass --width-in and --height-in. "
                "The command will not guess physical print dimensions."
            )

        count=max(1,min(20,opts["count"]))
        built=[]
        for idx in range(count):
            data=build_template(product,idx,width_in,height_in,opts["surface"])
            built.append((f"Canopy Editable {idx+1:02d} · {opts['surface']}",data))

        self.stdout.write(
            f"{product.id} · {product.name}: {width_in:g} × {height_in:g} in · "
            f"{opts['surface']} · {count} editable templates"
        )
        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run OK. Database unchanged."))
            return

        with transaction.atomic():
            if opts["replace_generated"]:
                DesignTemplate.objects.filter(
                    product=product, json_data__generator=GENERATOR
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
            f"Created {len(built)} editable canopy templates for {product.name}."
        ))
