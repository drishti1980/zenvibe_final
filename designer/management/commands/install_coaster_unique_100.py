"""Replace coaster gallery with 90 distinct illustrated layouts and 10 photo designs.

Usage:
 python manage.py install_coaster_unique_100 --product-id 415 --dry-run
 python manage.py install_coaster_unique_100 --product-id 415 --apply

Photo assets are sourced from the existing calendar photo catalog, not from
calendar preview screenshots. Downloaded photos are cached locally.
"""
import base64
import hashlib
import io
import math
import random
from pathlib import Path
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageDraw, ImageOps

from designer.models import DesignTemplate
from designer.management.commands.seed_calendar_editable_templates import PHOTO_URLS

SIZE=1000
PALETTES=[
 ("#F8E9D4","#244E4A","#D48E64"),("#12243D","#E6B86C","#8CC7D8"),
 ("#F4E5E4","#754B5B","#C58493"),("#E8EFE8","#426C5A","#C5A16C"),
 ("#FAEFD9","#5D5480","#D98C53"),("#172D35","#C2D7D1","#E4A76D"),
 ("#F3F2EA","#355F87","#E5B3A0"),("#4B292F","#E8C8B1","#CE8163"),
 ("#F0DDBD","#375047","#A7664D"),("#E6E8F3","#4D5586","#D99B7D"),
]
FAMILIES=[
 "Botanical Silhouette","Radiant Mandala","Art Deco","Ocean Currents",
 "Floral Meadow","Terrazzo","Geometric Mosaic","Mountain Layers",
 "Woodgrain","Abstract Brush","Star Map","Tropical Leaves",
 "Scallop Pattern","Minimal Line Art","Petal Kaleidoscope",
 "Marble Veins","Sun and Moon","Ceramic Tiles",
]
PHOTO_TITLES=["Alpine Lake","Forest Light","Wildflower Field","Night Sky",
              "Sunlit Woodland","Mountain Peaks","Autumn Walk","Waterfall",
              "Golden Sunset","Ocean Horizon"]
assert len(FAMILIES)==18

def rgb(c):
    return tuple(bytes.fromhex(c.lstrip("#")))
def point(cx,cy,r,a):
    return (int(cx+math.cos(a)*r),int(cy+math.sin(a)*r))
def motif(draw,family,variant,fg,accent,rng):
    # All decorative objects remain outside the central 560x260 title area.
    # Five distinctly constructed compositions per family, not five recolors.
    phase=variant*.37
    if family==0: # botanical: branching corner stems
        for corner in range(2+variant):
            x=80 if corner%2==0 else 920
            y=100+corner*170
            for j in range(5+variant):
                yy=y+j*30
                dx=(1 if x<500 else -1)*(35+18*(j%3))
                draw.line((x,yy,x+dx,yy-22),fill=fg,width=5)
                draw.ellipse((x+dx-23,yy-45,x+dx+20,yy-13),fill=accent)
    elif family==1: # radial petals, changing petal count and ring geometry
        n=9+variant*4
        for j in range(n):
            a=math.tau*j/n+phase
            x,y=point(500,500,355,a)
            rr=13+variant*3
            draw.ellipse((x-rr,y-rr*2,x+rr,y+rr*2),outline=fg,width=5)
            x2,y2=point(500,500,440,a)
            draw.ellipse((x2-7,y2-7,x2+7,y2+7),fill=accent)
    elif family==2: # art deco corner fans
        for cx,cy in [(0,0),(1000,1000),(0,1000),(1000,0)][:2+variant%3]:
            for j in range(9+variant*3):
                a=(j/float(8+variant*3))*math.pi/2
                sx=1 if cx==0 else -1;sy=1 if cy==0 else -1
                draw.line((cx,cy,cx+sx*math.cos(a)*(200+variant*28),
                           cy+sy*math.sin(a)*(200+variant*28)),fill=fg,width=3)
    elif family==3: # ocean wave bands at top/bottom
        for band in range(3+variant):
            for y0 in [100+band*32,810+band*32]:
                pts=[(x,int(y0+18*math.sin(x/65+phase+band))) for x in range(0,1001,6)]
                draw.line(pts,fill=fg if band%2 else accent,width=5)
    elif family==4: # meadow flowers at edges
        for j in range(8+variant*3):
            a=math.tau*j/(8+variant*3)+phase
            x,y=point(500,500,380+40*(j%2),a)
            for k in range(6):
                xx,yy=point(x,y,19+variant*2,k*math.tau/6)
                draw.ellipse((xx-12,yy-12,xx+12,yy+12),fill=accent)
            draw.ellipse((x-9,y-9,x+9,y+9),fill=fg)
    elif family==5: # terrazzo flecks, excluding center
        for j in range(80+variant*35):
            x=rng.randrange(70,930);y=rng.randrange(70,930)
            if 230<x<770 and 335<y<665:continue
            rr=rng.randrange(5,13+variant*4)
            draw.polygon([(x-rr,y),(x,y-rr),(x+rr,y+rr),(x-rr,y+rr)],fill=fg if j%3 else accent)
    elif family==6: # geometric mosaic along the perimeter
        for j in range(14+variant*4):
            a=math.tau*j/(14+variant*4)+phase
            x,y=point(500,500,410,a)
            r=20+variant*3
            draw.polygon([point(x,y,r,a+k*math.tau/(3+variant%4)) for k in range(3+variant%4)],outline=fg,width=5)
    elif family==7: # mountain horizons, top and bottom
        for row in range(2+variant):
            for base in (185,835):
                coords=[(0,base)]
                for x in range(0,1001,75):
                    coords.append((x,base-45-rng.randrange(20,90)))
                coords.append((1000,base))
                draw.line(coords,fill=fg if row%2 else accent,width=3)
    elif family==8: # woodgrain, offset elliptical arcs
        for j in range(12+variant*5):
            y=60+j*(880/(12+variant*5))
            coords=[(x,int(y+12*math.sin(x/(70+variant*11)+j*.45))) for x in range(0,1001,7)]
            coords=[p for p in coords if not (220<p[0]<780 and 320<p[1]<680)]
            # Separate line segments to avoid bridging the central title zone.
            for segment in ([(x,yy) for x,yy in coords if x<220],[(x,yy) for x,yy in coords if x>780]):
                if len(segment)>1:draw.line(segment,fill=fg,width=2)
    elif family==9: # abstract broad strokes
        for j in range(10+variant*3):
            a=rng.random()*math.tau
            x,y=point(500,500,rng.randint(340,455),a)
            r=17+variant*4
            draw.arc((x-r*2,y-r*2,x+r*2,y+r*2),rng.randrange(360),rng.randrange(360,720),fill=fg if j%2 else accent,width=8)
    elif family==10: # constellation stars
        for j in range(35+variant*12):
            a=rng.random()*math.tau
            x,y=point(500,500,rng.randint(330,465),a)
            r=3+((j+variant)%7)
            draw.line((x-r,y,x+r,y),fill=accent,width=2)
            draw.line((x,y-r,x,y+r),fill=fg,width=2)
    elif family==11: # long tropical leaf blades
        for j in range(5+variant*2):
            a=j*math.tau/(5+variant*2)+phase
            x,y=point(500,500,430,a)
            for k in range(6):
                xx,yy=point(x,y,18+k*13,a+math.pi)
                draw.ellipse((xx-15,yy-26,xx+15,yy+26),fill=fg if k%2 else accent)
    elif family==12: # scalloped outer ring
        for j in range(22+variant*7):
            a=j*math.tau/(22+variant*7)
            x,y=point(500,500,425,a)
            r=15+variant*2
            draw.arc((x-r,y-r,x+r,y+r),0,300,fill=fg,width=4)
    elif family==13: # continuous fine line arcs
        for j in range(5+variant*3):
            r=300+j*15
            draw.arc((500-r,500-r,500+r,500+r),20+variant*17,160+variant*17,fill=fg,width=2)
            draw.arc((500-r,500-r,500+r,500+r),200+variant*17,340+variant*17,fill=accent,width=2)
    elif family==14: # radial nested petals
        for j in range(6+variant*3):
            a=j*math.tau/(6+variant*3)
            x,y=point(500,500,400,a)
            for rr in range(12,55,12):
                draw.ellipse((x-rr,y-rr,x+rr,y+rr),outline=accent if rr%3 else fg,width=3)
    elif family==15: # marble curves confined to edges
        for j in range(7+variant*3):
            x0=30+j*83
            coords=[(int(x0+45*math.sin(y/90+j+phase)),y) for y in range(0,1001,8)]
            for side in ([(x,y) for x,y in coords if y<300],[(x,y) for x,y in coords if y>700]):
                if len(side)>1:draw.line(side,fill=fg if j%2 else accent,width=3)
    elif family==16: # sun moon phases
        for j in range(7+variant*2):
            a=j*math.tau/(7+variant*2)
            x,y=point(500,500,400,a)
            r=14+variant*3
            draw.ellipse((x-r,y-r,x+r,y+r),outline=fg,width=4)
            if j%2:draw.arc((x-r+6,y-r,x+r+6,y+r),80,280,fill=accent,width=4)
    else: # ceramic tile lattice border
        n=8+variant*2
        for j in range(n):
            x=70+j*(860/n)
            for y in (90,870):
                draw.rounded_rectangle((x,y,x+28+variant*2,y+28+variant*2),radius=5,outline=fg,width=3)
        for j in range(n):
            y=70+j*(860/n)
            for x in (90,870):
                draw.ellipse((x,y,x+23,y+23),fill=accent)

def make_illustration(i):
    family=i//5
    variant=i%5
    bg,fg,accent=PALETTES[(i*7+family)%len(PALETTES)]
    # Further deterministic palette tint makes the collection varied, while
    # uniqueness is in the composition, not solely its palette.
    im=Image.new("RGB",(SIZE,SIZE),rgb(bg))
    d=ImageDraw.Draw(im)
    rng=random.Random(20261028+i*9901)
    motif(d,family,variant,rgb(fg),rgb(accent),rng)
    # A restrained concentric border frames artwork without crossing text.
    margin=48+variant*8
    d.ellipse((margin,margin,1000-margin,1000-margin),outline=rgb(accent),width=3)
    return im,FAMILIES[family]+" "+str(variant+1),fg

def image_data(im):
    out=io.BytesIO()
    im.save(out,format="PNG",optimize=True)
    raw=out.getvalue()
    return raw,"data:image/png;base64,"+base64.b64encode(raw).decode("ascii")

def text_obj(label,fg):
    return {"id":"coaster-editable-title","type":"textbox","left":245,"top":422,
            "width":510,"height":160,"text":label,"fontFamily":"Georgia",
            "fontSize":52,"fontWeight":"normal","fill":fg,
            "textAlign":"center","originX":"left","originY":"top",
            "selectable":True,"evented":True,"customerEditable":True}

def photo_image(index,cache):
    cache.mkdir(parents=True,exist_ok=True)
    path=cache/("photo-%02d.jpg"%(index+1))
    if not path.exists():
        url=PHOTO_URLS[index]
        try:
            with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=15) as res:
                payload=res.read(12*1024*1024)
            im=Image.open(io.BytesIO(payload));im.verify()
            path.write_bytes(payload)
        except Exception as e:
            raise CommandError("Could not download photo %d; supply a cached photo at %s: %s"%(index+1,path,e))
    with Image.open(path) as source:
        return ImageOps.fit(source.convert("RGB"),(SIZE,SIZE),method=Image.Resampling.LANCZOS)

class Command(BaseCommand):
    help="Install 90 composition-distinct coaster artworks plus 10 different photo artworks."
    def add_arguments(self,parser):
        parser.add_argument("--product-id",type=int,default=415)
        parser.add_argument("--dry-run",action="store_true")
        parser.add_argument("--apply",action="store_true")
        parser.add_argument("--photo-dir",default="")
    def handle(self,*args,**opts):
        if opts["apply"]==opts["dry_run"]:
            raise CommandError("Choose exactly one of --apply or --dry-run")
        templates=list(DesignTemplate.objects.filter(product_id=opts["product_id"],is_active=True).order_by("pk"))
        if len(templates)!=100:
            raise CommandError("Expected exactly 100 active coaster templates; found %d"%len(templates))
        if len(PHOTO_URLS)<10:
            raise CommandError("Calendar photo catalog has fewer than ten images")
        cache=Path(opts["photo_dir"]) if opts["photo_dir"] else Path(settings.BASE_DIR)/"coaster_photo_cache"
        self.stdout.write("90 illustrated compositions + 10 different photos; 100 existing template IDs preserved.")
        if opts["dry_run"]:
            return
        prepared=[]
        signatures=set()
        for i,t in enumerate(templates):
            if i<90:
                im,title,ink=make_illustration(i)
                objects_title=[text_obj("YOUR TEXT",ink)]
                name="%03d | %s"%(i+1,title)
            else:
                im=photo_image(i-90,cache)
                objects_title=[] # Photo stays unobscured; user adds editable text.
                name="%03d | Photo - %s"%(i+1,PHOTO_TITLES[i-90])
            # Verify no exact duplicate artwork bytes enter the collection.
            raw,url=image_data(im)
            digest=hashlib.sha256(raw).hexdigest()
            if digest in signatures:
                raise CommandError("Duplicate artwork detected at %s"%name)
            signatures.add(digest)
            artwork={"id":"coaster-artwork","type":"image","left":0,"top":0,
                     "width":1000,"height":1000,"scaleX":1,"scaleY":1,
                     "src":url,"selectable":True,"evented":True,"customerEditable":True}
            page={"width":1000,"height":1000,"objects":[artwork]+objects_title}
            data=dict(t.json_data or {})
            data.update({"width":1000,"height":1000,"pages":[page],
                         "adminPages":[{"width":1000,"height":1000,"objects":[dict(o) for o in page["objects"]]}],
                         "generator":"zenvibe-coaster-unique-100-v1",
                         "artworkComposition":i+1,"constrainToPrintArea":True})
            # Gallery is a circular coaster preview; retain the full square
            # source in JSON so square selection is not pre-clipped.
            preview=im.convert("RGBA")
            alpha=Image.new("L",(SIZE,SIZE),0)
            ImageDraw.Draw(alpha).ellipse((0,0,SIZE-1,SIZE-1),fill=255)
            preview.putalpha(alpha)
            preview_raw,_=image_data(preview)
            prepared.append((t,name,data,preview_raw))
        # Complete all image preparation before any database writes.
        with transaction.atomic():
            for t,name,data,raw in prepared:
                t.name=name
                t.json_data=data
                t.preview.save("coaster-unique-%03d-%s.png"%(data["artworkComposition"],t.pk),
                               ContentFile(raw),save=False)
                t.save(update_fields=["name","json_data","preview"])
        self.stdout.write(self.style.SUCCESS("Installed 100 artworks; no reused source image or repeated composition index."))
