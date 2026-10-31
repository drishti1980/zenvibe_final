"""Install 100 original editable teardrop compositions for Zenvibe product 89.

Dry run:
    python manage.py install_luxury_teardrop_flags --product-id 89 --dry-run
Apply (backs up the current JSON first):
    python manage.py install_luxury_teardrop_flags --product-id 89 --apply

The die-cut mask is enforced by editor.js / universal-export.js.
These templates contain editor-native vectors and text, not flattened flyers.
"""
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import DesignTemplate, Product
from designer.management.commands.seed_flyer_templates_v2 import (
    rect, circle, ellipse, line, polygon, textbox, object_to_svg, structural_signature,
)

W, H = 600, 1400
GENERATOR = "zenvibe-teardrop-luxury-100-v1"
DIE = [
    (.08,.995),(.08,.43),(.10,.31),(.17,.20),(.28,.12),
    (.42,.065),(.59,.035),(.75,.04),(.88,.09),(.97,.17),
    (.985,.26),(.955,.34),(.89,.44),(.79,.56),(.67,.69),
    (.53,.81),(.37,.92),
]

# Twenty different editorial concepts, with five artwork architectures each.
CONCEPTS = [
    ("Atelier Noir","MAKE AN IMPACT","Design that stands apart"),
    ("Heritage Gold","THE SIGNATURE","Made for distinction"),
    ("Coastal Escape","FIND YOUR WAVE","Explore something new"),
    ("Botanical House","NATURAL BEAUTY","A little more extraordinary"),
    ("Modern Gallery","BOLD IDEAS","Created to be remembered"),
    ("The Grand Edit","THE MAIN EVENT","Experience the exceptional"),
    ("Urban Form","BUILT TO INSPIRE","Space for better ideas"),
    ("Evening Society","AFTER DARK","An unforgettable night"),
    ("Luxury Living","LIVE BEAUTIFULLY","Details make the difference"),
    ("Studio Bloom","FRESH PERSPECTIVE","Crafted with intention"),
    ("Voyage Club","GO FURTHER","Adventure begins here"),
    ("Prime Coffee","BREWED TO PERFECTION","Artisan made, every day"),
    ("Wellness Co","FEEL YOUR BEST","Your moment to shine"),
    ("Art of Motion","MOVE WITH PURPOSE","Find your own rhythm"),
    ("Tech Horizon","NEXT GENERATION","Tomorrow starts here"),
    ("Meridian Events","BE THERE","Make this moment count"),
    ("The Collection","LIMITED EDITION","Designed just for you"),
    ("Ocean Atelier","BLUE HORIZONS","An inspired destination"),
    ("Royal Studio","TIMELESS STYLE","Elegance in every detail"),
    ("Wildflower Co","GROW TOGETHER","A celebration of nature"),
]
PALETTES = [
    ("#10272C","#F0D6AA","#C49A54"),
    ("#17191E","#F6F0E4","#CAAA73"),
    ("#143F50","#F7F0DB","#C5B29B"),
    ("#1D4538","#F9F2E4","#D6AF6D"),
    ("#212442","#F7E6C5","#AFC8D3"),
    ("#521D31","#FBE8DD","#D4B073"),
    ("#122D39","#F3F4E8","#C3A66F"),
    ("#211D2B","#F7E9D1","#D5A85D"),
    ("#374A43","#F8EEDC","#BDA474"),
    ("#593C3A","#FDF0DE","#E4AF81"),
    ("#17354A","#F7EDE5","#D7A966"),
    ("#492F25","#FFF3DF","#C89D72"),
    ("#2A4840","#F9EEE1","#A9C5A7"),
    ("#283044","#F7EEDB","#D99C78"),
    ("#18273B","#F0F2E7","#A5C3D8"),
    ("#503747","#F7E9E3","#B9A0C4"),
    ("#292D32","#FAF5E8","#D5B77B"),
    ("#16425A","#ECF4F1","#CCAF81"),
    ("#342D3B","#FFF3E6","#C7AA82"),
    ("#3D4E3D","#F6EDDA","#D5B18C"),
]
MOODS = ("Signature","Editorial","Contemporary","Boutique","Collector")

def add_text(objects, label, x, y, width, size, color, *, bold=False, font="Georgia", align="left", tag="Copy"):
    obj = textbox(
        label, x, y, width, size, color,
        family=font, weight="700" if bold else "400",
        align=align, line_height=1.12, name=tag
    )
    obj["height"] = min(H-y-20, size * (2.65 if "\n" in label else 1.55))
    obj["customerEditable"] = True
    objects.append(obj)
    return obj

def add_decor(objects, concept, variant, dark, light, metallic):
    """Twenty vector art directions with varying structural geometry.

    Decoration lives in the large top / right / lower-edge bands. All important
    editable lettering is positioned later in a dedicated unobstructed region.
    """
    k = concept
    shift = 12 * variant
    if k == 0:  # architectural diagonal
        objects.extend([
            polygon([(0,0),(600,0),(600,195+shift),(70,610+shift)],metallic,name="Architectural foil"),
            polygon([(0,0),(465,0),(0,650+shift)],dark,name="Deep overlay"),
        ])
    elif k == 1:  # framed oval / vintage seal
        for j in range(3+variant):
            objects.append(ellipse(390,300+j*12,180-j*18,245-j*20,"transparent",stroke=metallic,sw=3,name="Heritage frame"))
    elif k == 2:  # ocean bands
        for j in range(5+variant):
            y=160+j*48
            pts=[(x,y+math.sin(x/75+j*.8)*26) for x in range(0,601,60)]
            for p,q in zip(pts,pts[1:]):
                objects.append(line(*p,*q,metallic,sw=4,opacity=.78,name="Ocean current"))
    elif k == 3:  # leaf clusters
        for j in range(6+variant):
            xx=350+(j%3)*70
            yy=190+(j//3)*80
            objects.append(ellipse(xx,yy,28+(j%2)*8,65,metallic,angle=25 if j%2 else -25,name="Botanical foliage"))
    elif k == 4:  # structured grid
        for j in range(3+variant):
            objects.append(rect(345+j*35,155+j*25,75,210,metallic if j%2 else light,opacity=.25,name="Gallery column"))
        objects.append(circle(445,280,95,metallic,opacity=.65,name="Gallery disc"))
    elif k == 5:  # spotlight discs
        for j in range(4+variant):
            objects.append(circle(430,260,150-j*20,"transparent",stroke=metallic,sw=5,name="Festival halo"))
    elif k == 6:  # city silhouette
        for j in range(6+variant):
            x=250+j*48
            hh=100+((j*43+variant*17)%170)
            objects.append(rect(x,270-hh,37,hh,metallic,opacity=.5,name="City tower"))
    elif k == 7:  # stars and threads
        for j in range(10+variant*3):
            a=j*2.399
            cx=370+math.sin(a)*180
            cy=255+math.cos(a)*150
            objects.append(circle(cx,cy,3+(j%4)*2,metallic,name="Night star"))
    elif k == 8:  # art nouveau rays
        for j in range(9+variant):
            a=(j/(8+variant))*math.pi*.75
            objects.append(line(420,230,420+math.cos(a)*190,230+math.sin(a)*190,metallic,sw=3,name="Sunburst ray"))
    elif k == 9:  # floral petals
        for j in range(9+variant):
            a=j*2*math.pi/(9+variant)
            cx=430+math.cos(a)*85
            cy=245+math.sin(a)*85
            objects.append(ellipse(cx,cy,24,50,light if j%2 else metallic,angle=j*24,name="Bloom petal"))
        objects.append(circle(430,245,30,metallic,name="Bloom center"))
    elif k == 10:  # travel topographic lines
        for j in range(6+variant):
            objects.append(ellipse(405,230,180-j*16,230-j*18,"transparent",stroke=metallic,sw=3,opacity=.6,name="Topographic line"))
    elif k == 11:  # coffee crest
        objects.append(circle(420,220,95,light,name="Coffee medallion"))
        objects.append(circle(420,220,76,dark,name="Coffee center"))
        for j in range(5+variant):
            objects.append(ellipse(335+j*30,330,9,17,metallic,angle=j*18,name="Coffee bean"))
    elif k == 12:  # soft wellness arcs
        for j in range(4+variant):
            objects.append(ellipse(420,255,170-j*25,250-j*30,"transparent",stroke=light,sw=5,opacity=.55,name="Wellness arch"))
    elif k == 13:  # motion swashes
        for j in range(4+variant):
            yy=100+j*56
            objects.append(polygon([(180,yy),(550,yy+40),(550,yy+57),(180,yy+17)],metallic if j%2 else light,opacity=.35,name="Motion ribbon"))
    elif k == 14:  # circuit traces
        for j in range(4+variant):
            y=110+j*55
            objects.append(line(300,y,495,y,metallic,sw=3,name="Circuit trace"))
            objects.append(circle(495,y,7,light,name="Circuit node"))
    elif k == 15:  # concert equaliser
        for j in range(6+variant):
            height=50+((j*37+variant*29)%145)
            objects.append(rect(265+j*42,300-height,20,height,metallic,opacity=.65,name="Music equaliser"))
    elif k == 16:  # fashion repeating bands
        for j in range(5+variant):
            objects.append(polygon([(250+j*48,60),(275+j*48,60),(510+j*22,375),(490+j*22,375)],metallic if j%2 else light,opacity=.55,name="Fashion band"))
    elif k == 17:  # horizon layers
        for j in range(5+variant):
            y=180+j*42
            objects.append(polygon([(220,y+80),(365,y-45),(510,y+80)],metallic if j%2 else light,opacity=.26,name="Mountain layer"))
    elif k == 18:  # foil diamonds
        for j in range(4+variant):
            x=270+j*56
            objects.append(polygon([(x,135),(x+32,205),(x,275),(x-32,205)],metallic,opacity=.35+(j%3)*.15,name="Luxe diamond"))
    else:  # fine meadow stems
        for j in range(5+variant):
            x=310+j*40
            objects.append(line(x,360,x+25,170,metallic,sw=3,name="Garden stem"))
            objects.append(ellipse(x+25,185,16,44,light if j%2 else metallic,angle=j*14,name="Garden leaf"))


def build(index, side=0):
    concept=index//5
    variant=index%5
    title,headline,sub=CONCEPTS[concept]
    bg,ink,gold=PALETTES[(concept+variant*7)%20]
    if side:
        # Reverse side uses related, complementary graphic treatment.
        gold,ink=ink,gold
    objects=[rect(0,0,W,H,bg,name="Printable fabric artwork")]
    objects[0].update({"customerEditable": False, "selectable": False,
                       "evented": False, "locked": True})
    add_decor(objects,concept,variant,bg,ink,gold)
    # Full-bleed background of the SAME colour clears the letterpress field.
    # It is deliberately not an inset white card. Decoration is confined to
    # the art-led header and cannot cross any editable headline.
    panel=rect(0,320,W,H-320,bg,name="Open typography field")
    panel.update({"customerEditable":False,"selectable":False,"evented":False,"locked":True})
    objects.append(panel)
    objects.append(line(100,320,520,320,gold,sw=3,opacity=.75,name="Foil divider"))
    for j in range(variant+1):
        x=96+j*20
        objects.append(line(x,1140,x+12,1220+variant*7,gold,sw=2,
                            opacity=.45,name="Tail signature"))
    # Every text band has fixed safe spacing and is inside the narrowing die.
    layouts=[
        (150,450,57,715,910),
        (145,465,52,725,918),
        (156,475,54,735,925),
        (140,485,50,745,930),
        (165,490,53,755,938),
    ]
    x,hy,size,sy,oy=layouts[variant]
    headline_text=headline if side==0 else ("DISCOVER MORE" if concept%2==0 else "YOUR MOMENT")
    brand_text=title.upper() if side==0 else "BE PART OF IT"
    add_text(objects,brand_text,155,355,310,22,ink,bold=True,font="Arial",tag="Editable brand")
    add_text(objects,headline_text,x,hy,370,size,ink,bold=True,font="Georgia",tag="Editable headline")
    add_text(objects,sub,135,sy,330,23,ink,tag="Editable supporting copy")
    add_text(objects,"EXPLORE  •  TODAY",116,oy,245,21,gold,bold=True,font="Arial",tag="Editable call to action")
    add_text(objects,"YOUR LOGO HERE",105,1090,215,15,ink,bold=True,font="Arial",tag="Editable logo label")

    texts=[o for o in objects if o.get("type") in ("text","textbox")]
    for left,right in zip(texts,texts[1:]):
        box_bottom=float(left["top"])+float(left["height"])
        if box_bottom > float(right["top"])-9:
            raise ValueError("Text collision at design %d (%s and %s)" %
                             (index+1,left["name"],right["name"]))
        if float(left["left"])<0 or float(left["left"])+float(left["width"])>W:
            raise ValueError("Text outside source canvas")
    page={"name":"Front" if side==0 else "Back","width":W,"height":H,
          "objects":objects}
    return page

def preview_svg(page):
    points=" ".join("%.2f,%.2f"%(x*W,y*H) for x,y in DIE)
    body="\n".join(object_to_svg(o) for o in page["objects"])
    return ('<svg xmlns="http://www.w3.org/2000/svg" '
            'width="%d" height="%d" viewBox="0 0 %d %d">'
            '<defs><clipPath id="fabric-die"><polygon points="%s"/></clipPath></defs>'
            '<g clip-path="url(#fabric-die)">%s</g></svg>')%(W,H,W,H,points,body)

class Command(BaseCommand):
    help="Build 100 editable two-sided luxury flag compositions, backed up in place."
    def add_arguments(self,parser):
        parser.add_argument("--product-id",type=int,default=89)
        parser.add_argument("--dry-run",action="store_true")
        parser.add_argument("--apply",action="store_true")
    def handle(self,*args,**opts):
        if opts["dry_run"]==opts["apply"]:
            raise CommandError("Select exactly one of --dry-run and --apply.")
        product=Product.objects.filter(pk=opts["product_id"]).first()
        if product is None:
            raise CommandError("Product does not exist.")
        if "teardrop" not in product.name.lower() and "tear drop" not in product.name.lower():
            raise CommandError("Refusing to install flag artwork on a non-teardrop product.")
        existing=list(DesignTemplate.objects.filter(product=product,is_active=True).order_by("pk"))
        if len(existing)>100:
            raise CommandError("Found %d active designs; resolve the extra designs before updating." % len(existing))
        built=[]
        signatures=set()
        for n in range(100):
            front=build(n,0)
            back=build(n,1)
            signature=structural_signature(front["objects"])
            if signature in signatures:
                raise CommandError("Repeated geometry at design %03d"%(n+1))
            signatures.add(signature)
            title=CONCEPTS[n//5][0]
            data={"version":3,"generator":GENERATOR,
                  "templateType":"editable-master","document":{"width":W,"height":H},
                  "width":W,"height":H,"pages":[front,back],
                  "adminPages":[front,back],"pageCount":2,
                  "printShape":"teardrop","constrainToPrintArea":True,
                  "editable":True,"compositionKey":"flag-%03d"%(n+1)}
            built.append((title,data,preview_svg(front)))
        self.stdout.write("Verified 100 unique structure signatures; 2 editable pages each.")
        self.stdout.write("Existing active templates: %d; will reuse IDs and add %d rows."%
                          (len(existing),100-len(existing)))
        if opts["dry_run"]:
            self.stdout.write("Dry run only; database unchanged.")
            return
        backup=Path(settings.BASE_DIR)/"template_backups"
        backup.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
        file=backup/("teardrop-before-luxury-%s.json"%stamp)
        file.write_text(json.dumps([
            {"id":t.pk,"name":t.name,"json_data":t.json_data,
             "preview":str(t.preview.name) if t.preview else ""}
            for t in existing
        ],indent=2,default=str),encoding="utf-8")
        with transaction.atomic():
            for index,(title,data,svg) in enumerate(built):
                if index<len(existing):
                    template=existing[index]
                else:
                    template=DesignTemplate(product=product,is_active=True)
                template.name="Luxury Teardrop %03d — %s · %s"%(
                    index+1,title,MOODS[index%5]
                )
                template.json_data=data
                template.is_active=True
                template.preview.save("luxury-teardrop-%03d.svg"%(index+1),
                                      ContentFile(svg.encode("utf-8")),save=False)
                template.save()
        self.stdout.write(self.style.SUCCESS(
            "Applied 100 shape-aware templates without deleting designs. Backup: %s"%file
        ))
