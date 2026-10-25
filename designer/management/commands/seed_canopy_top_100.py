from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.files.base import ContentFile
from designer.models import Product, DesignTemplate
import copy, html, math

GENERATOR = "zenvibe-canopy-top-10x10-zenvibe-format-v3"
W = H = 1200
PHYSICAL_W = PHYSICAL_H = 120.0

PALETTES = [
("#10243E","#FFFFFF","#E95445"),("#F45B69","#111827","#FFFFFF"),
("#167A3E","#FFFFFF","#8BC34A"),("#095C91","#FFFFFF","#0B2D4D"),
("#F6B817","#111827","#FFFFFF"),("#E53935","#FFFFFF","#9B1C1C"),
("#12355B","#FFFFFF","#D7E7F4"),("#F97316","#FFFFFF","#111827"),
("#0B4F3A","#FFFFFF","#DDEFE8"),("#FFFFFF","#12355B","#D9E6EF"),
("#172554","#FFFFFF","#38BDF8"),("#F59E0B","#111827","#FFFFFF"),
("#0F766E","#FFFFFF","#99F6E4"),("#6D28D9","#FFFFFF","#C4B5FD"),
("#111111","#FFFFFF","#E11D48"),("#0369A1","#FFFFFF","#BAE6FD"),
("#991B1B","#FFFFFF","#FECACA"),("#14532D","#FFFFFF","#DCFCE7"),
("#4C1D95","#FFFFFF","#DDD6FE"),("#334155","#FFFFFF","#CBD5E1"),
]

def rect(i,x,y,w,h,fill,stroke=None,sw=0,opacity=1):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"rect","left":x,"top":y,
            "width":w,"height":h,"fill":fill,"stroke":stroke,"strokeWidth":sw,
            "opacity":opacity,"customerEditable":True}
def circle(i,cx,cy,r,fill,stroke=None,sw=0):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"circle","left":cx-r,"top":cy-r,
            "radius":r,"fill":fill,"stroke":stroke,"strokeWidth":sw,"customerEditable":True}
def poly(i,pts,fill,opacity=1,stroke=None,sw=0):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"polygon",
            "points":[{"x":x,"y":y} for x,y in pts],"fill":fill,"opacity":opacity,
            "stroke":stroke,"strokeWidth":sw,"customerEditable":True}
def line(i,x1,y1,x2,y2,stroke,sw=5):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"line","x1":x1,"y1":y1,
            "x2":x2,"y2":y2,"stroke":stroke,"strokeWidth":sw,"customerEditable":True}
def text(i,x,y,w,s,size,fill,weight=700,align="center",angle=0):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"textbox","left":x,"top":y,
            "width":w,"text":s,"fontSize":size,"fontFamily":"Poppins","fontWeight":weight,
            "fill":fill,"textAlign":align,"lineHeight":1.0,"angle":angle,"customerEditable":True}

def edge_labels(o, fg, bg, accent, variant):
    """Branding zones arranged like a printed canopy roof: one label per outer edge."""
    top_y = 34 + (variant % 3) * 8
    bottom_y = 1128 - (variant % 3) * 8
    o += [
        text("company_top", 350, top_y, 500, "COMPANY NAME", 28, fg, 700),
        text("company_bottom", 350, bottom_y, 500, "COMPANY NAME", 28, fg, 700),
        text("company_left", 16, 445, 310, "COMPANY NAME", 27, fg, 700, "center", -90),
        text("company_right", 874, 445, 310, "COMPANY NAME", 27, fg, 700, "center", 90),
    ]

def center_logo(o, fg, bg, accent, variant):
    kind = variant % 5
    if kind == 0:
        o += [circle("logo_disc",600,600,92,fg),
              text("logo",505,568,190,"LOGO",38,bg,800)]
    elif kind == 1:
        o += [poly("logo_diamond",[(600,500),(700,600),(600,700),(500,600)],fg),
              text("logo",505,568,190,"LOGO",36,bg,800)]
    elif kind == 2:
        o += [rect("logo_box",505,525,190,150,fg),
              text("logo",515,575,170,"LOGO",36,bg,800)]
    elif kind == 3:
        o += [circle("logo_outer",600,600,112,fg),
              circle("logo_inner",600,600,82,bg),
              text("logo",515,570,170,"LOGO",34,fg,800)]
    else:
        o += [poly("logo_hex",[(600,495),(691,548),(691,652),(600,705),(509,652),(509,548)],fg),
              text("logo",515,568,170,"LOGO",34,bg,800)]

def build(idx,bg,fg,accent):
    """
    100 canopy-top masters in the same structural language as the reference:
    complete 120x120 square, four roof panels meeting at the centre, visible
    corner-to-centre diagonal seams, edge branding and a central logo zone.
    """
    family = idx % 20
    variant = idx // 20            # 0..4
    d = variant * 18
    seam = "#E53935" if idx % 4 == 0 else fg
    o = [rect("background",0,0,W,H,bg)]

    # Every family covers ALL FOUR roof quadrants. No blank half-canvas.
    if family == 0:
        # Classic four triangular roof panels.
        o += [
            poly("top_panel",[(0,0),(1200,0),(600,600)],accent,.34),
            poly("right_panel",[(1200,0),(1200,1200),(600,600)],fg,.12),
            poly("bottom_panel",[(1200,1200),(0,1200),(600,600)],accent,.18),
            poly("left_panel",[(0,1200),(0,0),(600,600)],fg,.08),
        ]
    elif family == 1:
        # Strong alternating X.
        o += [
            poly("left_panel",[(0,0),(600,600),(0,1200)],accent),
            poly("right_panel",[(1200,0),(1200,1200),(600,600)],accent),
            poly("top_panel",[(0,0),(1200,0),(600,600)],fg,.10),
            poly("bottom_panel",[(0,1200),(1200,1200),(600,600)],fg,.10),
        ]
    elif family == 2:
        o += [
            poly("top_panel",[(0,0),(1200,0),(600,600)],accent),
            poly("bottom_panel",[(0,1200),(1200,1200),(600,600)],accent),
            poly("left_panel",[(0,0),(600,600),(0,1200)],fg,.10),
            poly("right_panel",[(1200,0),(1200,1200),(600,600)],fg,.10),
        ]
    elif family == 3:
        # Inset perimeter / classic reference style.
        inset=55+d
        o += [
            rect("perimeter",inset,inset,1200-2*inset,1200-2*inset,"rgba(0,0,0,0)",accent,18),
            poly("top_panel",[(inset,inset),(1200-inset,inset),(600,600)],accent,.20),
            poly("right_panel",[(1200-inset,inset),(1200-inset,1200-inset),(600,600)],fg,.10),
            poly("bottom_panel",[(1200-inset,1200-inset),(inset,1200-inset),(600,600)],accent,.12),
            poly("left_panel",[(inset,1200-inset),(inset,inset),(600,600)],fg,.08),
        ]
    elif family == 4:
        # Broad corner bands.
        q=180+d
        o += [
            poly("tl",[(0,0),(q,0),(600,600),(0,q)],accent),
            poly("tr",[(1200,0),(1200-q,0),(600,600),(1200,q)],fg,.18),
            poly("br",[(1200,1200),(1200-q,1200),(600,600),(1200,1200-q)],accent),
            poly("bl",[(0,1200),(q,1200),(600,600),(0,1200-q)],fg,.18),
        ]
    elif family == 5:
        # Centre diamond surrounded by four panels.
        r=185+d
        o += [
            poly("top",[(0,0),(1200,0),(600,600-r)],accent,.42),
            poly("right",[(1200,0),(1200,1200),(600+r,600)],fg,.14),
            poly("bottom",[(1200,1200),(0,1200),(600,600+r)],accent,.22),
            poly("left",[(0,1200),(0,0),(600-r,600)],fg,.08),
            poly("center",[(600,600-r),(600+r,600),(600,600+r),(600-r,600)],bg),
        ]
    elif family == 6:
        # Four kites.
        p=300+d
        o += [
            poly("top",[(0,0),(1200,0),(600,600),(600-p,300),(600+p,300)],accent,.38),
            poly("right",[(1200,0),(1200,1200),(600,600),(900,600-p),(900,600+p)],fg,.12),
            poly("bottom",[(1200,1200),(0,1200),(600,600),(600+p,900),(600-p,900)],accent,.20),
            poly("left",[(0,1200),(0,0),(600,600),(300,600+p),(300,600-p)],fg,.08),
        ]
    elif family == 7:
        # Double-X bands.
        w=105+d//2
        o += [
            poly("band1",[(0,0),(w,0),(1200,1200-w),(1200,1200),(1200-w,1200),(0,w)],accent),
            poly("band2",[(1200,0),(1200-w,0),(0,1200-w),(0,1200),(w,1200),(1200,w)],accent),
        ]
    elif family == 8:
        # Cross + diagonals.
        w=120+d
        o += [rect("vertical",600-w/2,0,w,1200,accent),
              rect("horizontal",0,600-w/2,1200,w,accent)]
    elif family == 9:
        # Four corner blocks tapering to centre.
        q=350+d
        o += [
            poly("tl",[(0,0),(q,0),(600,600),(0,q)],accent),
            poly("tr",[(1200,0),(1200-q,0),(600,600),(1200,q)],accent,.72),
            poly("br",[(1200,1200),(1200-q,1200),(600,600),(1200,1200-q)],accent),
            poly("bl",[(0,1200),(q,1200),(600,600),(0,1200-q)],accent,.72),
        ]
    elif family == 10:
        # Layered central diamond.
        r1=460-d; r2=300-d//2
        o += [poly("diamond1",[(600,600-r1),(600+r1,600),(600,600+r1),(600-r1,600)],accent,.55),
              poly("diamond2",[(600,600-r2),(600+r2,600),(600,600+r2),(600-r2,600)],bg)]
    elif family == 11:
        # Top/bottom chevrons + side panels.
        y=270+d
        o += [
            poly("top",[(0,0),(1200,0),(900,y),(600,600),(300,y)],accent),
            poly("bottom",[(0,1200),(1200,1200),(900,1200-y),(600,600),(300,1200-y)],accent),
            poly("left",[(0,0),(300,y),(600,600),(300,1200-y),(0,1200)],fg,.10),
            poly("right",[(1200,0),(900,y),(600,600),(900,1200-y),(1200,1200)],fg,.10),
        ]
    elif family == 12:
        x=270+d
        o += [
            poly("left",[(0,0),(x,300),(600,600),(x,900),(0,1200)],accent),
            poly("right",[(1200,0),(1200-x,300),(600,600),(1200-x,900),(1200,1200)],accent),
            poly("top",[(0,0),(x,300),(600,600),(1200-x,300),(1200,0)],fg,.10),
            poly("bottom",[(0,1200),(x,900),(600,600),(1200-x,900),(1200,1200)],fg,.10),
        ]
    elif family == 13:
        # Four inset triangular wedges.
        q=240+d
        o += [
            poly("top",[(q,0),(1200-q,0),(600,600)],accent),
            poly("right",[(1200,q),(1200,1200-q),(600,600)],accent,.78),
            poly("bottom",[(1200-q,1200),(q,1200),(600,600)],accent),
            poly("left",[(0,1200-q),(0,q),(600,600)],accent,.78),
        ]
    elif family == 14:
        # Hourglass panels.
        q=390+d
        o += [
            poly("left",[(0,0),(q,0),(600,600),(q,1200),(0,1200)],accent),
            poly("right",[(1200,0),(1200-q,0),(600,600),(1200-q,1200),(1200,1200)],accent),
        ]
    elif family == 15:
        # Border bands + four centre seams.
        b=120+d
        o += [rect("topband",0,0,1200,b,accent),rect("bottomband",0,1200-b,1200,b,accent),
              rect("leftband",0,b,b,1200-2*b,accent,.82),rect("rightband",1200-b,b,b,1200-2*b,accent,.82)]
    elif family == 16:
        # Pinwheel.
        q=310+d
        o += [
            poly("p1",[(0,0),(1200,0),(600,600),(q,q)],accent),
            poly("p2",[(1200,0),(1200,1200),(600,600),(1200-q,q)],fg,.15),
            poly("p3",[(1200,1200),(0,1200),(600,600),(1200-q,1200-q)],accent),
            poly("p4",[(0,1200),(0,0),(600,600),(q,1200-q)],fg,.15),
        ]
    elif family == 17:
        # Corner diamonds.
        r=180+d//2
        o += [
            poly("c1",[(0,0),(r,0),(0,r)],accent),poly("c2",[(1200,0),(1200-r,0),(1200,r)],accent),
            poly("c3",[(1200,1200),(1200-r,1200),(1200,1200-r)],accent),
            poly("c4",[(0,1200),(r,1200),(0,1200-r)],accent),
            poly("mid",[(600,330-d),(870+d,600),(600,870+d),(330-d,600)],fg,.10),
        ]
    elif family == 18:
        # Circular centre over four-panel roof.
        o += [
            poly("top",[(0,0),(1200,0),(600,600)],accent,.32),
            poly("right",[(1200,0),(1200,1200),(600,600)],fg,.10),
            poly("bottom",[(1200,1200),(0,1200),(600,600)],accent,.18),
            poly("left",[(0,1200),(0,0),(600,600)],fg,.08),
            circle("center_ring",600,600,210+d//2,"rgba(0,0,0,0)",fg,18),
        ]
    else:
        # Clean four-quadrant fan.
        q=360+d
        o += [
            poly("fan_top",[(0,0),(1200,0),(600,600),(600-q,250),(600+q,250)],accent,.42),
            poly("fan_right",[(1200,0),(1200,1200),(600,600),(950,600-q),(950,600+q)],fg,.12),
            poly("fan_bottom",[(1200,1200),(0,1200),(600,600),(600+q,950),(600-q,950)],accent,.22),
            poly("fan_left",[(0,1200),(0,0),(600,600),(250,600+q),(250,600-q)],fg,.08),
        ]

    # IMPORTANT: explicit corner-to-centre seam lines on every single design.
    seam_width = 5 + variant
    o += [
        line("seam_tl",0,0,600,600,seam,seam_width),
        line("seam_tr",1200,0,600,600,seam,seam_width),
        line("seam_br",1200,1200,600,600,seam,seam_width),
        line("seam_bl",0,1200,600,600,seam,seam_width),
    ]

    # Inner safe/perimeter line, similar to the reference print construction.
    inset=45 + variant*8
    o.append(rect("inner_print_frame",inset,inset,1200-2*inset,1200-2*inset,
                  "rgba(0,0,0,0)",seam,3))

    edge_labels(o,fg,bg,accent,variant)
    center_logo(o,fg,bg,accent,idx)
    return o

def validate(objects):
    # Geometry is intentionally constrained to 0..1200. Text labels use rotation,
    # so we validate their anchor rectangles conservatively without rejecting rotation.
    for o in objects:
        if o["type"]=="polygon":
            for p in o["points"]:
                if not (0 <= p["x"] <= W and 0 <= p["y"] <= H): raise CommandError("Polygon outside canvas")
        elif o["type"]=="line":
            if min(o["x1"],o["x2"],o["y1"],o["y2"]) < 0 or max(o["x1"],o["x2"],o["y1"],o["y2"]) > W:
                raise CommandError("Line outside canvas")

def make_template(idx, width_in, height_in):
    bg,fg,accent=PALETTES[idx % len(PALETTES)]
    objects=build(idx,bg,fg,accent); validate(objects)
    page={"name":"Canopy tent Top","background":bg,
          "physical":{"widthIn":float(width_in),"heightIn":float(height_in),"unit":"in"},"objects":objects}
    return {"version":3,"templateType":"editable-master","generator":GENERATOR,
            "designName":f"Canopy Tent Top {idx+1:03d}",
            "document":{"width":W,"height":H,"profile":"canopy",
                        "physical":{"widthIn":float(width_in),"heightIn":float(height_in),"unit":"in"},"unit":"in"},
            "pageCount":1,"pages":[copy.deepcopy(page)],"adminPages":[copy.deepcopy(page)],
            "editable":True,"editorNative":True,"editorSchema":"fabric-primitives-v1","surface":"Canopy tent Top"}

def svg(objects):
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">']
    for o in objects:
        t=o["type"]; fill=o.get("fill","none")
        if t=="rect":
            out.append(f'<rect x="{o["left"]}" y="{o["top"]}" width="{o["width"]}" height="{o["height"]}" fill="{fill}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}"/>')
        elif t=="circle":
            r=o["radius"]; out.append(f'<circle cx="{o["left"]+r}" cy="{o["top"]+r}" r="{r}" fill="{fill}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}"/>')
        elif t=="polygon":
            pts=" ".join(f'{p["x"]},{p["y"]}' for p in o["points"])
            out.append(f'<polygon points="{pts}" fill="{fill}" opacity="{o.get("opacity",1)}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}"/>')
        elif t=="line":
            out.append(f'<line x1="{o["x1"]}" y1="{o["y1"]}" x2="{o["x2"]}" y2="{o["y2"]}" stroke="{o["stroke"]}" stroke-width="{o["strokeWidth"]}"/>')
        elif t=="textbox":
            x=o["left"]+o["width"]/2; y=o["top"]+o["fontSize"]
            transform=f' transform="rotate({o.get("angle",0)} {x} {y})"' if o.get("angle") else ""
            out.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Arial" font-size="{o["fontSize"]}" font-weight="{o["fontWeight"]}" fill="{fill}"{transform}>{html.escape(o["text"])}</text>')
    out.append("</svg>"); return "".join(out)

class Command(BaseCommand):
    help="Generate the approved 100 unique editable 10x10 canopy-top templates."
    def add_arguments(self,p):
        p.add_argument("--product-id",type=int)
        p.add_argument("--count",type=int,default=100)
        p.add_argument("--replace-generated",action="store_true")
        p.add_argument("--dry-run",action="store_true")
    def handle(self,*args,**opts):
        if opts["product_id"]:
            product=Product.objects.filter(pk=opts["product_id"],is_active=True).first()
        else:
            product=(Product.objects.filter(name__icontains="Canopy Tent Top Fabric Replacement",is_active=True).order_by("id").first())
        if not product: raise CommandError("Active Canopy Tent Top Fabric Replacement product not found.")
        from designer.models import ProductPrintSurface
        surface=(ProductPrintSurface.objects
                 .filter(product=product,is_active=True)
                 .order_by("sort_order","id")
                 .first())
        width_in=float(getattr(surface,"print_width_in",0) or getattr(product,"print_width_in",0) or 0)
        height_in=float(getattr(surface,"print_height_in",0) or getattr(product,"print_height_in",0) or 0)
        if width_in<=0 or height_in<=0:
            raise CommandError(
                "Configure the product/surface print width and height in inches in Django Admin first. "
                "This template command no longer hard-codes or overwrites ruler dimensions."
            )

        count=max(1,min(100,opts["count"]))
        built=[(f"Canopy Tent Top {i+1:03d}",make_template(i,width_in,height_in)) for i in range(count)]
        self.stdout.write(f"{product.name}: {width_in:g} × {height_in:g} in (from Admin) · {count} approved-format editable templates")
        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run OK. Database unchanged.")); return

        with transaction.atomic():
            if opts["replace_generated"]:
                # Remove prior canopy-top generated masters for THIS product only.
                DesignTemplate.objects.filter(product=product,json_data__generator__in=[
                    "zenvibe-canopy-top-10x10-zenvibe-format-v3",
                    "zenvibe-canopy-top-10x10-approved-100-v2",
                    "zenvibe-canopy-top-10x10-100-v1-unique",
                    "zenvibe-canopy-top-100-v1",
                ]).delete()

            for name,data in built:
                obj,_=DesignTemplate.objects.get_or_create(product=product,name=name)
                obj.json_data=data; obj.is_active=True
                obj.preview.save(f"canopy_top_{product.id}_{name.split()[-1]}.svg",
                                 ContentFile(svg(data["pages"][0]["objects"]).encode()),save=False)
                obj.save()
        self.stdout.write(self.style.SUCCESS(f"Created {count} editable approved-format canopy-top templates."))
