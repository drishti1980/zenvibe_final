"""Install 100 editable coaster artworks based on the supplied 24-design reference.

Artwork is reconstructed as native editable Fabric objects; photo/watercolor
descriptions are NOT claimed to be actual photos or watercolor textures.
Existing template IDs and product mappings are preserved.
"""
from __future__ import annotations

import copy
import io
import math
from PIL import Image, ImageDraw
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product
from .seed_calendar_editable_templates import rect, txt, circle
from .rebuild_coaster_previews import render

# The 24 categories and copy are taken from the supplied coaster artwork JSON.
SPECS = [
 ("Marble Luxury", "ZV", "", "#F4EFE8", "#B8893A", "#DCC9AD", "monogram"),
 ("Botanical", "BOTANICAL", "HOUSE", "#F3E8DC", "#5A3E2B", "#A78866", "botanical"),
 ("Watercolor", "Good", "Vibes", "#F6DCD4", "#8A5A36", "#D4A94F", "watercolor"),
 ("Tropical", "TROPICAL", "PARADISE", "#F5EEDC", "#1F4A33", "#C9A24A", "tropical"),
 ("Floral", "BLOOM", "WHERE YOU ARE PLANTED", "#FBF1E6", "#C9776E", "#E8908A", "floral"),
 ("Modern", "ZEN", "LIVING", "#0F1E33", "#D4B26A", "#967747", "branches"),
 ("Coastal", "Ocean", "Breeze", "#E9D6B8", "#183F45", "#1E9AA6", "coastal"),
 ("Terrazzo", "GOOD FOOD", "GOOD MOOD", "#F3E6D3", "#A8743E", "#C08552", "terrazzo"),
 ("Minimal", "SIMPLE", "MOMENTS", "#4B5E3C", "#E8D9B0", "#A9B88E", "minimal"),
 ("Photo Theme", "Coffee", "ALWAYS A GOOD IDEA", "#3A2618", "#FFFFFF", "#B99068", "coffee"),
 ("Classic", "HOME", "SWEET HOME", "#F6F1E7", "#1F3F94", "#7D9BC5", "delft"),
 ("Wood Theme", "ZV", "", "#8A4B26", "#5A2E14", "#B07B4F", "wood"),
 ("Abstract", "STAY", "POSITIVE", "#F5E9DA", "#C9A06A", "#2E3B33", "abstract"),
 ("Marble Dark", "LUXURY", "LIVING", "#141414", "#D4B26A", "#C9A24A", "darkmarble"),
 ("Floral", "BE KIND", "TO YOURSELF", "#FBE4E2", "#C9605A", "#E8A09A", "cherry"),
 ("Botanical", "NATURAL", "LIFE", "#E9EDE4", "#3E4A3E", "#7A8F7A", "eucalyptus"),
 ("Photo Theme", "Adventure", "AWAITS", "#8E9A9E", "#24383C", "#DCE1DD", "mountain"),
 ("Gold Accent", "GRATEFUL", "TODAY ALWAYS", "#FBF6EC", "#B8893A", "#C9A24A", "goldleaf"),
 ("Artistic", "CREATE", "BEAUTIFUL THINGS", "#F3E6D6", "#3A3A3A", "#B8573A", "artistic"),
 ("Elegant", "LOVE", "LAUGH LIVE", "#F2EBDF", "#7A6A58", "#5E7A6A", "elegant"),
 ("Photo Theme", "Good", "Times", "#E07A2A", "#1C1C1C", "#F6CB75", "sunset"),
 ("Mandala", "BALANCE", "", "#0E0E0E", "#C9A24A", "#A78648", "mandala"),
 ("Floral", "FLOWERS", "MAKE PEOPLE HAPPIER", "#F7F5F0", "#2E3A5A", "#2E4FA0", "blueflowers"),
 ("Minimal", "BEAUTY", "IN SIMPLICITY", "#F5F0E6", "#5A5A4A", "#5E7A4A", "olive"),
]

def editable(o):
    o.update(selectable=True, evented=True, customerEditable=True)
    return o

def ellipse(key,x,y,rx,ry,fill,angle=0):
    return editable(dict(id=key,type="ellipse",left=round(x,2),top=round(y,2),
                         rx=round(rx,2),ry=round(ry,2),fill=fill,angle=angle))

def make_artwork(index):
    # Cycle all 24 references before using any reference a second time.
    spec_index = index % len(SPECS)
    variation = index // len(SPECS)  # 0..4
    category,title,subtitle,bg,ink,accent,style = SPECS[spec_index]
    o=[rect("background",0,0,1000,1000,bg)]
    def add(item):o.append(item)
    def disk(key,x,y,r,color):add(circle(key,x-r,y-r,r,color))
    def ring(key,r,color,width=3):
        add(editable(dict(id=key,type="circle",left=500-r,top=500-r,
                          radius=r,fill="transparent",stroke=color,strokeWidth=width)))
    def text(key,value,x,y,width,size,color=None,font="Cinzel",weight="500"):
        if not value:return
        # Center-aligned textboxes, positioned inside the print-safe central zone.
        lines=value.split("\n")
        for j,line in enumerate(lines):
            add(txt(key+"-"+str(j),x,y+j*size*1.22,width,line,size,
                    color or ink,"center",weight,font))
    def flower(key,x,y,r=35,color=None):
        for j in range(6):
            a=math.tau*j/6
            add(ellipse(key+"-petal-"+str(j),x+math.cos(a)*r-17,
                        y+math.sin(a)*r-29,17,29,color or accent,math.degrees(a)))
        disk(key+"-centre",x,y,13,ink)
    def leaf(key,x,y,s=1):
        add(ellipse(key,x,y,20*s,57*s,accent,36))
    def sprig(key,x,y,flip=1):
        add(rect(key+"-stem",x,y,4,220,ink))
        for j in range(5):
            leaf(key+"-"+str(j),x+(-65 if j%2 else 12)*flip,y+j*40,0.8)
    def heading(y=390,size=70,font="Cinzel",width=760,x=120):
        text("title",title,x,y,width,size,ink,font,"600")
    def sub(y=520,size=31,font="Montserrat",width=720,x=140):
        text("subtitle",subtitle,x,y,width,size,ink,font,"400")

    if style=="monogram":
        # Gold-veined marble interpreted as editable fine-line ornament.
        for j in range(7):
            add(rect("vein-"+str(j),140+j*95,160+(j%3)*105,3,120+(j%2)*90,accent))
        disk("translucent-medallion",500,500,260,"#FFF9F0")
        ring("medallion-ring",270,accent,4)
        heading(365,205,"Cormorant Garamond")
    elif style=="botanical":
        ring("fine-ring",398,accent,3)
        sprig("left",185,285);sprig("right",810,285,-1)
        text("pretitle","THE",260,332,480,34,ink)
        heading(435,73);sub(555,33)
    elif style=="watercolor":
        for j in range(8):
            disk("wash-"+str(j),190+(j%4)*210,240+(j//4)*430,100+(j%3)*23,
                 "#F0BEBB" if j%2 else "#EECAC4")
        text("script-one",title,160,280,680,170,ink,"Great Vibes")
        text("script-two",subtitle,160,500,680,170,ink,"Great Vibes")
    elif style=="tropical":
        for j in range(5):
            leaf("palm-left-"+str(j),80+j*35,180+j*75,1.7)
            leaf("palm-right-"+str(j),780+j*27,170+j*82,1.7)
        ring("tropical-ring",390,accent)
        heading(430,75);sub(540,30)
    elif style in ("floral","cherry","blueflowers"):
        for j,(x,y) in enumerate(((180,240),(810,240),(165,750),(825,745),(500,135))):
            flower("blossom-"+str(j),x,y,43 if style!="cherry" else 30)
        heading(405,83)
        sub(535,28)
    elif style=="branches":
        sprig("gold-left",160,260);sprig("gold-right",830,260,-1)
        heading(390,115);sub(535,40)
    elif style=="coastal":
        disk("sun",740,250,105,"#F1C178")
        for j in range(4):
            for k in range(5):
                add(ellipse("surf-%d-%d"%(j,k),-85+k*230,540+j*75,155,50,
                            accent if j%2 else "#76BCC1"))
        text("coast-one",title,160,305,680,125,ink,"Great Vibes")
        text("coast-two",subtitle,160,450,680,125,ink,"Great Vibes")
    elif style=="terrazzo":
        for j in range(28):
            a=j*math.tau/28
            radius=395+(j%3)*12
            x=500+math.cos(a)*radius;y=500+math.sin(a)*radius
            disk("chip-"+str(j),x,y,9+(j%3)*7,accent if j%2 else ink)
        heading(370,66);sub(490,59)
    elif style=="minimal":
        sprig("sage",200,315)
        text("minimal-title",title,365,390,475,70)
        text("minimal-subtitle",subtitle,365,495,475,54)
    elif style=="coffee":
        disk("coffee-cup",655,330,175,"#E9D9C7")
        disk("espresso",655,330,137,"#694329")
        disk("latte-heart",650,315,49,"#E8D5B7")
        for j in range(7):
            add(ellipse("bean-"+str(j),90+j*100,720+(j%2)*25,17,31,accent,j*14))
        text("coffee-script",title,125,350,750,150,ink,"Great Vibes")
        sub(560,29)
    elif style=="delft":
        ring("blue-ring",385,ink,5)
        for j in range(12):
            a=j*math.tau/12
            flower("delft-"+str(j),500+math.cos(a)*350,
                   500+math.sin(a)*350,24,accent)
        heading(395,90);sub(535,57)
    elif style=="wood":
        for j in range(12):
            add(rect("grain-"+str(j),75+j*75,100,3,800,accent))
        ring("engraved",235,ink,6)
        heading(365,185,"Cormorant Garamond")
    elif style in ("abstract","artistic"):
        disk("blob-one",140,180,220,accent)
        disk("blob-two",830,810,220,"#6E7A5A")
        disk("blob-three",800,130,95,ink)
        heading(380,88);sub(510,48)
    elif style=="darkmarble":
        for j in range(8):
            add(rect("gold-vein-"+str(j),125+j*100,110+(j%2)*105,3,220,accent))
        ring("gold-round-frame",355,accent,4)
        heading(390,88);sub(525,48)
    elif style=="eucalyptus":
        sprig("euca-left",165,260);sprig("euca-right",835,260,-1)
        ring("sage-round-frame",355,accent,3)
        heading(410,73);sub(520,48)
    elif style=="mountain":
        disk("mist-sun",720,255,95,"#E5DED1")
        for j in range(5):
            add(ellipse("mountain-"+str(j),-200+j*200,515+j*45,280,200,
                        "#536F72" if j%2 else "#718D8E"))
        text("mountain-script",title,110,300,780,115,ink,"Great Vibes")
        sub(465,40)
    elif style in ("goldleaf","elegant","olive"):
        ring("luxury-ring",380,accent,3)
        sprig("vine-left",185,270);sprig("vine-right",820,270,-1)
        heading(380,77);sub(505,41)
    elif style=="sunset":
        disk("setting-sun",500,450,245,"#F6CB75")
        for j in range(6):
            add(rect("sunset-horizon-"+str(j),100,665+j*27,800,12,
                     "#8C4C42" if j%2 else "#B45B3C"))
        text("sunset-script",title,180,305,640,130,ink,"Great Vibes")
        text("sunset-subtitle",subtitle,180,460,640,125,ink,"Great Vibes")
    elif style=="mandala":
        ring("lotus-ring",325,accent,4)
        for j in range(16):
            a=j*math.tau/16
            add(ellipse("lotus-"+str(j),465+math.cos(a)*255,
                        465+math.sin(a)*255,32,76,accent,math.degrees(a)))
        heading(655,66)
    else:
        ring("olive-ring",380,accent,3)
        sprig("olive-left",180,290)
        heading(390,80);sub(520,45)

    # Variants alter small finishing details while retaining each reference's art direction.
    if variation==1:
        ring("variant-fine-border",460,accent,2)
    elif variation==2:
        add(rect("variant-rule",355,770,290,3,accent))
    elif variation==3:
        for x in (275,725):
            disk("variant-dot-"+str(x),x,790,9,accent)
    elif variation==4:
        ring("variant-inner-hairline",440,ink,2)
    for ob in o:
        if ob.get("type") == "textbox":
            key=ob.get("id","")
            if key.startswith(("title-","minimal-title-","coffee-script-","coast-one-","coast-two-","script-one-","script-two-","sunset-script-","sunset-subtitle-","mountain-script-")):
                ob["fontSize"]=max(100,float(ob.get("fontSize",70)))
            elif key.startswith(("subtitle-","minimal-subtitle-")):
                ob["fontSize"]=max(45,float(ob.get("fontSize",30)))
    return o,category

class Command(BaseCommand):
    help="Replace 100 existing coaster artworks using 24 supplied design directions."
    def add_arguments(self,parser):
        parser.add_argument("--product-id",type=int,default=415)
        parser.add_argument("--shape",choices=("circle","square"),default="circle")
        parser.add_argument("--dry-run",action="store_true")
        parser.add_argument("--apply",action="store_true")
    def handle(self,*args,**opts):
        if opts["dry_run"]==opts["apply"]:
            raise CommandError("Choose exactly one of --dry-run or --apply")
        if not Product.objects.filter(pk=opts["product_id"]).exists():
            raise CommandError("Coaster product does not exist")
        templates=list(DesignTemplate.objects.filter(
            product_id=opts["product_id"],is_active=True).order_by("id"))
        if len(templates)!=100:
            raise CommandError("Expected 100 active coaster templates; found %s"%len(templates))
        prepared=[]
        for i,t in enumerate(templates):
            if not isinstance(t.json_data,dict) or not t.json_data.get("pages"):
                raise CommandError("Invalid editable pages on template %s"%t.pk)
            objects,category=make_artwork(i)
            data=copy.deepcopy(t.json_data)
            for page in data["pages"]:
                page["objects"]=copy.deepcopy(objects)
            for page in data.get("adminPages",[]):
                page["objects"]=copy.deepcopy(objects)
            data["generator"]="zenvibe-coaster-reference-24-v2"
            data["artworkCategory"]=category
            data["artworkReferenceIndex"]=i%24+1
            image=render(objects,opts["shape"])
            if opts["shape"]=="circle":
                rgba=image.convert("RGBA")
                mask=Image.new("L",rgba.size,0)
                ImageDraw.Draw(mask).ellipse((1,1,rgba.width-2,rgba.height-2),fill=255)
                rgba.putalpha(mask)
                image=rgba
            buffer=io.BytesIO()
            image.save(buffer,format="PNG",optimize=True)
            prepared.append((t,data,buffer.getvalue(),category))
        self.stdout.write("Validated %d designs across 24 reference themes"%len(prepared))
        if opts["dry_run"]:
            self.stdout.write("Dry run: no changes made")
            return
        with transaction.atomic():
            for i,(t,data,png,category) in enumerate(prepared):
                t.json_data=data
                t.name=("%03d | %s"%(i+1,category))[:140]
                t.preview.save("coaster-elegant-v2-%s-%03d.png"%(t.pk,i+1),
                               ContentFile(png),save=False)
                t.save(update_fields=["json_data","name","preview"])
        self.stdout.write(self.style.SUCCESS("Installed 100 reference-inspired editable coasters"))
