"""Original luxury print-face artwork for configured Zenvibe products.

Designs are editor-native Fabric objects. They do NOT include a rectangular
product image, photography placeholders, or UI changes. Each product's ADMIN
print surface and percentage print area are authoritative. Distinct vector
motifs, asymmetric layouts and typography are validated before writing.
No network calls, deletions or modifications to customer saved designs.

    python manage.py seed_luxury_print_face_templates --product-id 16 --dry-run
    python manage.py seed_luxury_print_face_templates --product-id 16 --apply
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from html import escape

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import Product, DesignTemplate

GENERATOR = "zenvibe-print-face-luxury-original-v1"
COUNT = 100

# Colours are deliberate editorial systems, not a template generator that
# counts a colour swap as a different design.
PALETTES = [
    ("#16272B", "#D4B77D", "#F2EBD9"), ("#24212A", "#D5B17C", "#FAEEE3"),
    ("#153D43", "#CFA778", "#F1F2E7"), ("#283C32", "#DBC298", "#FCF6E9"),
    ("#473335", "#D9AA91", "#F4E7DD"), ("#263149", "#B8C9D9", "#FCF3E0"),
    ("#443328", "#E3B77F", "#FCF2DE"), ("#282D30", "#C1AD93", "#F4EEE4"),
    ("#382B45", "#CAB5D8", "#FAF0E9"), ("#1C4241", "#C6B183", "#FFF8E9"),
    ("#544038", "#F1C9A2", "#FCF5E7"), ("#123A50", "#A9CDD9", "#F3E6CD"),
    ("#3B3F33", "#D9BD86", "#FCF7EA"), ("#4D3046", "#D6A9C5", "#F8EEDF"),
    ("#23362C", "#E0C69F", "#F9F0DC"), ("#28222F", "#D3A679", "#FCF0DD"),
    ("#5B3334", "#E3B4B4", "#FFF1E8"), ("#214B51", "#B2D4D2", "#F5F1E3"),
    ("#313B4B", "#E3C19A", "#F4F5EE"), ("#45382F", "#CEBB9C", "#FAF1E2"),
]
CONCEPTS = [
    ("ATELIER", "OBJECTS OF DESIRE", "Beautifully considered"),
    ("MAISON", "THE ART OF LIVING", "Signature collection"),
    ("FORMA", "BEYOND ORDINARY", "Made with purpose"),
    ("VERDANT", "NATURAL ELEGANCE", "Inspired by nature"),
    ("NOVA", "A NEW PERSPECTIVE", "A brighter tomorrow"),
    ("ORIGIN", "SIMPLY EXCEPTIONAL", "Crafted with care"),
    ("LUMIÈRE", "LET THERE BE LIGHT", "An elegant statement"),
    ("MERIDIAN", "EXPLORE MORE", "Your next chapter"),
    ("ARCO", "MODERN HERITAGE", "Timeless by design"),
    ("COUTURE", "THE NEW EDIT", "Distinctive details"),
    ("VINTAGE", "TIMELESS BEAUTY", "Made to be admired"),
    ("TERRAZZA", "SAVOUR THE MOMENT", "An inspired experience"),
    ("GALLERY", "LIVE IN COLOUR", "Creative expression"),
    ("SOLSTICE", "A LITTLE MAGIC", "Moments that matter"),
    ("STUDIO 8", "DESIGN IN MOTION", "Built for what is next"),
    ("HORIZON", "A BETTER VIEW", "Go beyond the expected"),
    ("MONARCH", "A MARK OF QUALITY", "The finer things"),
    ("OCEANA", "FEEL THE FLOW", "Inspired by the coast"),
    ("BLOOM", "GROW BEAUTIFULLY", "Thoughtfully created"),
    ("SIGNATURE", "BE REMEMBERED", "Your identity, refined"),
]
EDITIONS = ["Modernist", "Editorial", "Artisan", "Heritage", "Contemporary"]


def family_for(product):
    """Opt-in by physical product family, not by an arbitrary product ID."""
    name = (product.name or "").lower()
    if any(x in name for x in (
        "frame only", "aluminum canopy frame", "blank replacement", "stand only",
        "empty frame", "hardware", "mounting kit", "replacement part",
    )):
        return ""
    if any(x in name for x in (
        "feather flag", "teardrop flag", "tear drop flag", "pop out banner",
        "canopy", "back wall", "award", "trophy", "medal", "coaster",
        "pen set", "gift set", "notebook pen", "stationery set",
    )):
        return ""
    if (any(x in name for x in ("stylus", "marker", "highlighter")) or
        re.search(r"\bpens?\b",name)):
        return "pens"
    if any(x in name for x in ("tumbler", "mug", "drinkware", "water bottle", "travel bottle", "flask")):
        return "drinkware"
    if any(x in name for x in (
        "t-shirt", "t shirt", "hoodie", "polo", "shirt", "jacket", "apron",
        "hat", "cap", "sweatshirt", "vest", "jersey",
    )):
        return "apparel"
    if any(x in name for x in ("tote", "bag", "pouch", "backpack", "drawstring")):
        return "bags"
    if any(x in name for x in ("rectangle flag", "vinyl banner", "mesh banner",
                                "roll up banner", "roll-up banner", "rollup banner")):
        return "flat-display"
    if any(x in name for x in ("table runner", "table cover", "table skirt", "table throw")):
        return "fabric-panel"
    if any(x in name for x in ("notepad", "journal", "stationery gift", "gift box")):
        return "stationery"
    return ""


@dataclass(frozen=True)
class Surface:
    label: str
    width_in: float
    height_in: float
    workspace_width_in: float
    workspace_height_in: float
    area: tuple


def surfaces_for(product):
    """Read physical dimensions and printable fraction from Admin only."""
    surfaces = list(product.print_surfaces.filter(is_active=True).order_by("sort_order", "id"))
    areas = list(product.print_areas.order_by("sort_order", "id"))
    if not surfaces:
        wi = float(product.print_width_in or 0)
        hi = float(product.print_height_in or 0)
        if not (wi > 0 and hi > 0):
            raise CommandError("Missing Admin print dimensions")
        surfaces = [None]

    output = []
    for surface in surfaces:
        wi = float(surface.print_width_in if surface else product.print_width_in or 0)
        hi = float(surface.print_height_in if surface else product.print_height_in or 0)
        if wi <= 0 or hi <= 0:
            raise CommandError("Missing physical dimensions on a print surface")
        ww = float(
            (surface.workspace_width_in if surface else None)
            or product.workspace_width_in or wi
        )
        wh = float(
            (surface.workspace_height_in if surface else None)
            or product.workspace_height_in or hi
        )
        if ww <= 0 or wh <= 0:
            raise CommandError("Invalid Admin workspace dimensions")
        candidates = [a for a in areas if (
            a.surface_id in (None, surface.pk if surface else None)
        )]
        # A photo-specific area is not an artboard print guide unless it is
        # the only area. Prefer main-photo placement for the normal editor.
        candidates.sort(key=lambda a: (a.product_image_id is not None, a.sort_order, a.pk))
        area = candidates[0] if candidates else None
        if area is None:
            # On a shaped product, an unspecified print rectangle is dangerous.
            # A flat banner has a full bleed printing canvas.
            if family_for(product) not in ("flat-display", "fabric-panel"):
                raise CommandError("Configure a Product Print Area before designing this product")
            bounds = (.0, .0, 1.0, 1.0)
        else:
            bounds = tuple(float(v) / 100 for v in (
                area.left, area.top, area.width, area.height
            ))
            x, y, w, h = bounds
            if not (0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0
                    and x + w <= 1.001 and y + h <= 1.001):
                raise CommandError("Invalid Admin print-area percentages")
        output.append(Surface(
            surface.label if surface else "Print Face",
            wi, hi, ww, wh, bounds
        ))
    if len(output) > 12:
        raise CommandError("More than 12 print surfaces: confirm correct page setup in Admin")
    return output


def size_of(surface):
    ratio = surface.workspace_width_in / surface.workspace_height_in
    if not 1/8 <= ratio <= 8:
        raise CommandError("Extreme print-workspace ratio; configure a wider Admin workspace and an inset print area")
    if ratio >= 1:
        return 1200, round(1200 / ratio)
    return round(1200 * ratio), 1200


def box_for(surface, width, height):
    x, y, w, h = surface.area
    left = width * x
    top = height * y
    aw = width * w
    ah = height * h
    # Artwork is deliberately inside the safe part of the printing face.
    inset = min(aw, ah) * .06
    box = (left+inset, top+inset, aw-2*inset, ah-2*inset)
    if box[2] < 45 or box[3] < 22:
        raise CommandError("Printable face is too small for legible editable artwork")
    return box


def object_factory():
    serial = 0
    def make(kind, name, x, y, w, h, fill,
             opacity=1, angle=0, editable=True, **kwargs):
        nonlocal serial
        serial += 1
        obj = dict(
            id="lux-%03d" % serial, type=kind, name=name,
            left=round(x,3), top=round(y,3),
            width=round(w,3), height=round(h,3),
            fill=fill, opacity=opacity, angle=angle,
            scaleX=1, scaleY=1,
            customerEditable=editable, locked=not editable,
            originX="left", originY="top",
        )
        obj.update(kwargs)
        return obj
    return make


def motif(style, edition, region, colours, make):
    """20 genuinely distinct vector grammars; decorative zone only."""
    x,y,w,h=region
    dark,metal,paper=colours
    ink = metal if (style+edition)%3 else paper
    out=[]
    # Fractional geometry makes every direction fit the product-specific region.
    def tile(px,py,pw,ph,colour=ink,opacity=.9,angle=0,tag="Vector ornament"):
        out.append(make("rect",tag,x+w*px,y+h*py,w*pw,h*ph,colour,
                        opacity=opacity,angle=angle))
    def orb(px,py,r,colour=ink,opacity=.85,tag="Round ornament"):
        radius=min(w,h)*r
        out.append(make("circle",tag,x+w*px-radius,y+h*py-radius,
                        2*radius,2*radius,colour,opacity=opacity,
                        radius=radius))
    def oval(px,py,rx,ry,colour=ink,opacity=.8,angle=0):
        rx0=w*rx; ry0=h*ry
        out.append(make("ellipse","Editable floral or geometric petal",
                        x+w*px-rx0,y+h*py-ry0,rx0*2,ry0*2,
                        colour,opacity=opacity,angle=angle,rx=rx0,ry=ry0))

    n=edition+3
    if style==0:  # Architectural columns
        for j in range(n):
            tile(.10+j*.72/n,.12,.038+.1/n,.74 if j%2 else .52,opacity=.8)
    elif style==1:  # Floating halo rings
        for j in range(n):
            r=.30-j*.042
            if r<=.04: break
            orb(.50,.50,r,ink,opacity=.12)
        orb(.50,.50,.06,paper)
    elif style==2:  # Botanical branch
        tile(.48,.08,.025,.80,opacity=.72)
        for j in range(n+1):
            px=.31 if j%2 else .60
            oval(px,.16+j*.65/n,.15,.072)
    elif style==3:  # Deco diamond tiles
        for j in range(n):
            tile(.16+j*.58/n,.30,.09,.27,opacity=.7 if j%2 else .95)
    elif style==4:  # Sunrise
        orb(.48,.53,.24,ink,opacity=.34)
        for j in range(n+2):
            a=math.pi*j/(n+1)
            tile(.48+.34*math.cos(a),.48+.34*math.sin(a),.018,.15,ink,.8)
    elif style==5:  # Wave pattern
        for j in range(n):
            for q in range(5):
                orb(.16+q*.17,.2+j*.57/n,.013+.012*((q+j)%3),opacity=.65)
    elif style==6:  # Mosaic
        for j in range(n):
            for q in range(3):
                tile(.18+q*.22,.12+j*.73/n,.14,.12,ink,
                     opacity=.22+((j+q)%3)*.24)
    elif style==7:  # Star cluster
        for j in range(n+7):
            a=j*2.399
            orb(.5+.34*math.cos(a),.5+.34*math.sin(a),
                .014+(j%3)*.012,paper if j%3==0 else ink)
    elif style==8:  # Bespoke monogram mark
        tile(.24,.20,.52,.10,ink,.85)
        tile(.44,.19,.11,.59,ink,.8)
        tile(.27,.71,.50,.095,ink,.66)
    elif style==9:  # Layered petals
        for j in range(5+edition):
            a=j*2*math.pi/(5+edition)
            oval(.5+.19*math.cos(a),.5+.19*math.sin(a),
                 .125,.10,ink,.48)
        orb(.5,.5,.11,paper,.9)
    elif style==10:  # Minimal gallery border
        tile(.15,.14,.72,.018)
        tile(.15,.78,.72,.018)
        tile(.15,.14,.018,.65)
        tile(.85,.14,.018,.65)
        orb(.50,.46,.13,paper,.75)
    elif style==11:  # Optical bands
        for j in range(n+2):
            tile(.12+j*.64/(n+1),.15,.042,.70,
                 paper if j%2 else ink,.52+j*.04)
    elif style==12:  # Celestial constellation
        coords=[(.18,.28),(.45,.16),(.73,.30),(.34,.54),(.76,.76),(.18,.76)]
        for j,(px,py) in enumerate(coords):
            orb(px,py,.02+(j%3)*.013)
        for j in range(3+edition):
            tile(.20+j*.14,.44,.09,.012,ink,.35)
    elif style==13:  # Art nouveau vines
        for j in range(n):
            oval(.26+j*.11,.40+j*.045,.09,.18,ink,.46)
    elif style==14:  # Mountain silhouettes
        for j in range(n+1):
            tile(.13+j*.13,.25+((j*3)%5)*.11,.06,.55-((j*3)%5)*.09,
                 ink,.35+j*.06)
    elif style==15:  # Luxe jewellery
        for j in range(n):
            orb(.23+j*.54/max(1,n-1),.50,.065,ink,.35+j*.1)
        oval(.5,.5,.16,.27,paper,.24)
    elif style==16:  # Abstract stacked postcards
        for j in range(n):
            tile(.18+j*.035,.20+j*.035,.45,.46,
                 ink,.18+(j%3)*.13)
    elif style==17:  # Monochrome crescent
        orb(.48,.48,.28,ink,.7)
        orb(.60,.40,.22,dark,.96)
        orb(.64,.66,.045,paper,.95)
    elif style==18:  # Floral garden blocks
        for j in range(n):
            oval(.17+j*.66/n,.35+(j%2)*.24,.075,.20,
                 ink,.52)
        tile(.1,.84,.8,.025,paper,.5)
    else:  # Textile/foil crosshatch
        for j in range(n):
            tile(.14+j*.66/n,.20,.025,.59,ink,.5)
            tile(.16,.20+j*.58/n,.67,.025,paper,.5)
    return out


def typography(concept, edition, region, colours, make, compact=False):
    x,y,w,h=region
    dark,metal,paper=colours
    word,headline,subtitle=CONCEPTS[concept]
    # Compact print faces carry only a deliberate identity wordmark; tiny
    # subtitle text on pens/labels would be unreadable in physical printing.
    texts=[(word if not compact else word.split()[0], 0.04, .08, .92, .19, True)]
    if not compact:
        texts += [(headline, .04, .39, .92, .26, True),
                  (subtitle, .04, .78, .92, .14, False)]
    output=[]
    for idx,(label,bx,by,bw,bh,bold) in enumerate(texts):
        xx=x+w*bx; yy=y+h*by
        ww=w*bw; hh=h*bh
        # Bounding-box fit is more conservative than browser SVG text metrics.
        # No wraps; visual preview and live editable Textbox agree on one line.
        max_by_width=ww/(max(1,len(label))* (.72 if bold else .63))
        size=max(6,min(hh*.72,max_by_width,h*.19))
        if size<7.5:
            raise CommandError("The configured print face cannot fit legible editable copy")
        output.append(make(
            "textbox",
            ("Brand wordmark","Editable headline","Editable supporting copy")[idx],
            xx,yy,ww,hh,dark if idx in (0,1) else metal,
            fontSize=round(size,2),fontFamily="Arial" if idx==0 else "Georgia",
            fontWeight="700" if bold else "400",text=label,
            lineHeight=1.1,textAlign="left",
        ))
    return output


def layout_for(index, bounds):
    """Five structural arrangements, selected independently of colour."""
    x,y,w,h=bounds
    mode=index//20
    ratio=w/h
    if ratio>=2.7:
        art=(x+.025*w,y+.10*h,w*.23,h*.80)
        copy=(x+.31*w,y+.10*h,w*.65,h*.82)
        compact=ratio>5.5 or h<100
    elif ratio>=1.05:
        if mode in (1,3):
            art=(x+.59*w,y+.12*h,w*.37,h*.74)
            copy=(x+.04*w,y+.12*h,w*.51,h*.74)
        else:
            art=(x+.04*w,y+.12*h,w*.37,h*.74)
            copy=(x+.44*w,y+.12*h,w*.52,h*.74)
        compact=False
    elif ratio>=.70:
        if mode in (1,4):
            art=(x+.62*w,y+.11*h,w*.32,h*.52)
            copy=(x+.06*w,y+.18*h,w*.48,h*.65)
        else:
            art=(x+.16*w,y+.07*h,w*.68,h*.38)
            copy=(x+.11*w,y+.53*h,w*.78,h*.40)
        compact=False
    else:
        art=(x+.14*w,y+.07*h,w*.72,h*.33)
        copy=(x+.13*w,y+.50*h,w*.74,h*.39)
        compact=ratio<.26
    # New edition changes actual object placement, not only the palette.
    if mode==2:
        ax,ay,aw,ah=art
        art=(ax+aw*.04,ay+ah*.06,aw*.88,ah*.86)
    elif mode==3:
        cx,cy,cw,ch=copy
        copy=(cx+cw*.035,cy+ch*.01,cw*.90,ch*.93)
    elif mode==4:
        ax,ay,aw,ah=art
        art=(ax+aw*.07,ay+ah*.09,aw*.84,ah*.82)
    return art,copy,compact


def object_bounds(obj):
    x=float(obj.get("left",0)); y=float(obj.get("top",0))
    if obj["type"]=="circle":
        side=2*float(obj.get("radius",0))
        return x,y,side,side
    if obj["type"]=="ellipse":
        return x,y,2*float(obj["rx"]),2*float(obj["ry"])
    return x,y,float(obj.get("width",0)),float(obj.get("height",0))


def intersects(a,b):
    x,y,w,h=a
    X,Y,W,H=b
    return (min(x+w,X+W)-max(x,X)>1 and
            min(y+h,Y+H)-max(y,Y)>1)


def make_page(index, surface, page_index, family):
    width,height=size_of(surface)
    region=box_for(surface,width,height)
    art_region,copy_region,compact=layout_for(index,region)
    concept=(index*7+page_index*3)%len(CONCEPTS)
    style=index%20
    edition=index//20
    colors=PALETTES[(index*3+edition*5+page_index)%len(PALETTES)]
    mk=object_factory()
    motif_objects=motif(style,edition,art_region,colors,mk)
    copy_objects=typography(concept,edition,copy_region,colors,mk,compact=compact)
    safe=(region[0],region[1],region[2],region[3])
    for obj in motif_objects+copy_objects:
        x,y,w,h=object_bounds(obj)
        # All decorative marks are inside the dedicated art region, all copy
        # inside the typography region, with extra product-safe margins.
        if not (x>=safe[0]-1 and y>=safe[1]-1 and
                x+w<=safe[0]+safe[2]+1 and y+h<=safe[1]+safe[3]+1):
            raise CommandError("Generated object crosses the Admin safe print area")
    for obj in copy_objects:
        a=object_bounds(obj)
        for other in copy_objects:
            if other is not obj and intersects(a,object_bounds(other)):
                raise CommandError("Generated text overlaps another text object")
        for deco in motif_objects:
            if intersects(a,object_bounds(deco)):
                raise CommandError("Generated typography overlaps vector artwork")
    page=dict(
        name=surface.label,objects=motif_objects+copy_objects,
        width=width,height=height,editorCoordinates=True,
        editorWidth=width,editorHeight=height,
        background="rgba(0,0,0,0)",
        physical={"widthIn":surface.width_in,"heightIn":surface.height_in,"unit":"in"},
    )
    return page


def svg_for(page):
    w=int(page["width"]);h=int(page["height"])
    bits=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
          f'viewBox="0 0 {w} {h}">']
    for o in page["objects"]:
        kind=o["type"]
        fill=escape(str(o.get("fill") or "none"),quote=True)
        alpha=float(o.get("opacity",1))
        x=float(o["left"]);y=float(o["top"])
        ww=float(o.get("width",0));hh=float(o.get("height",0))
        if kind=="rect":
            bits.append(f'<rect x="{x:g}" y="{y:g}" width="{ww:g}" height="{hh:g}" '
                        f'fill="{fill}" opacity="{alpha:g}" />')
        elif kind=="circle":
            radius=float(o["radius"])
            bits.append(f'<circle cx="{x+radius:g}" cy="{y+radius:g}" r="{radius:g}" '
                        f'fill="{fill}" opacity="{alpha:g}" />')
        elif kind=="ellipse":
            rx=float(o["rx"]); ry=float(o["ry"])
            bits.append(f'<ellipse cx="{x+rx:g}" cy="{y+ry:g}" rx="{rx:g}" ry="{ry:g}" '
                        f'fill="{fill}" opacity="{alpha:g}" />')
        elif kind=="textbox":
            label=escape(str(o["text"]))
            size=float(o["fontSize"])
            font=escape(str(o["fontFamily"]),quote=True)
            weight=escape(str(o["fontWeight"]),quote=True)
            bits.append(f'<text x="{x:g}" y="{y+size:g}" font-family="{font}" '
                        f'font-size="{size:g}" font-weight="{weight}" fill="{fill}">'
                        f'{label}</text>')
    bits.append("</svg>")
    return "".join(bits)


class Command(BaseCommand):
    help="Create 100 original luxury editable print-face compositions for one configured product."

    def add_arguments(self, parser):
        parser.add_argument("--product-id",type=int,required=True)
        parser.add_argument("--count",type=int,default=COUNT)
        mode=parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run",action="store_true")
        mode.add_argument("--apply",action="store_true")

    def handle(self,*args,**opts):
        product=Product.objects.filter(pk=opts["product_id"],is_active=True).first()
        if not product:
            raise CommandError("Active product not found")
        family=family_for(product)
        if not family:
            raise CommandError("No verified print-face design family for this product")
        count=opts["count"]
        if not 1<=count<=100:
            raise CommandError("Count must be 1..100")
        surfaces=surfaces_for(product)
        generated=list(DesignTemplate.objects.filter(
            product=product,json_data__generator=GENERATOR).order_by("pk"))
        # Never mix an arbitrary existing legacy library with new geometry.
        all_existing=DesignTemplate.objects.filter(product=product).count()
        if all_existing!=len(generated):
            raise CommandError("Existing templates from another generator: preserve them and review mapping")
        designs=[]
        keys=set()
        for index in range(count):
            pages=[make_page(index,s,j,family) for j,s in enumerate(surfaces)]
            key=hashlib.sha256(json.dumps([
                [(o["type"],o["left"],o["top"],o.get("width"),o.get("height"),
                  o.get("radius"),o.get("text")) for o in p["objects"]]
                for p in pages
            ],sort_keys=True).encode()).hexdigest()
            if key in keys:
                raise CommandError("Duplicate composition detected at %03d"%(index+1))
            keys.add(key)
            concept=CONCEPTS[(index*7)%20][0]
            data=dict(
                version=3,generator=GENERATOR,
                designName=f"{family.title()} Luxury {index+1:03d} · {concept} · {EDITIONS[index//20]}",
                templateType="editable-master",editorNative=True,
                editable=True,constrainToPrintArea=True,
                showProductMockup=True,lockProductMockup=True,
                pageCount=len(pages),
                document={"width":pages[0]["width"],"height":pages[0]["height"]},
                pages=pages,adminPages=pages,
                designFamily=family,compositionKey=key,
                source={"type":"original-vector-print-face","artworkOnly":True},
            )
            designs.append((data,svg_for(pages[0])))
        self.stdout.write(
            f"{product.pk} {product.name}: validated {len(designs)} unique editable "
            f"{family} compositions, {len(surfaces)} Admin surfaces each"
        )
        if opts["dry_run"]:
            self.stdout.write("Dry run: no database or customer design changes")
            return
        with transaction.atomic():
            for i,(data,svg) in enumerate(designs):
                t=next((o for o in generated if o.name==data["designName"]),None)
                if t is None:
                    t=DesignTemplate(product=product,name=data["designName"])
                t.json_data=data
                t.is_active=True
                t.preview.save(
                    f"luxury-face-{product.pk}-{i+1:03d}.svg",
                    ContentFile(svg.encode("utf-8")),save=False
                )
                t.save()
        self.stdout.write(self.style.SUCCESS(
            f"Installed {count} unique native-vector templates without deleting any existing rows."
        ))
