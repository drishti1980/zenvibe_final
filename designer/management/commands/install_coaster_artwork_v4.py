"""Generate textured, illustration-led coaster templates with editable type.

Run: python manage.py install_coaster_artwork_v4 --product-id 415 --apply
No external image APIs, websites, or network requests. Artwork is embedded as
a replaceable Fabric image layer, while text remains native editable textboxes.
"""
import base64
import copy
import io
import math
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate
from .install_coaster_reference_100 import SPECS

SIZE=800
PALETTES=[
("#f5efe5","#b98a51","#74513d"),("#f4ead9","#85664b","#463a2e"),
("#f8e1d9","#dc9a92","#754c3c"),("#f7eedb","#1e5849","#bd9156"),
("#fff2e9","#ce877f","#715244"),("#0d2235","#c99c53","#f0d6a1"),
("#e7f0e9","#238c9a","#164f62"),("#f5e8d5","#ba8a66","#694a39"),
("#405638","#b3c29c","#f3ead3"),("#3b251c","#c18e60","#fff5e5"),
("#faf4e9","#32539a","#172e61"),("#965d38","#61371f","#e9bf85"),
("#f4e9d8","#be7957","#425d4e"),("#15191e","#bf8a51","#e8c68b"),
("#f9e5e2","#c77973","#6b4b47"),("#e9f0e8","#6c927f","#40594c"),
("#c7d1d0","#6a8b89","#253d44"),("#fff6e8","#c3a06c","#6e523c"),
("#f3e5d5","#c07656","#43534c"),("#f4eee3","#9c876e","#4d6755"),
("#eaa26a","#a84f37","#392b34"),("#10151d","#cba463","#ead3a2"),
("#f5f2e9","#688db6","#283f65"),("#f5f1e5","#779071","#485943")
]

def font(size,serif=True):
    names=(["DejaVuSerif.ttf","C:/Windows/Fonts/georgia.ttf"] if serif
           else ["DejaVuSans.ttf","C:/Windows/Fonts/arial.ttf"])
    for name in names:
        try:return ImageFont.truetype(name,size)
        except OSError:pass
    return ImageFont.load_default()

def rgba(hexcolor,alpha=255):
    from PIL import ImageColor
    return (*ImageColor.getrgb(hexcolor),alpha)

def generate(index):
    theme,title,subtitle,*_=SPECS[index%24]
    bg,accent,ink=PALETTES[index%24]
    rng=random.Random(2049+index*71)
    im=Image.new("RGBA",(SIZE,SIZE),rgba(bg))
    d=ImageDraw.Draw(im,"RGBA")
    style=index%24
    # Fine paper / stone grain, kept subtle so type remains legible.
    for _ in range(14000):
        x=rng.randrange(SIZE);y=rng.randrange(SIZE)
        c=(255,255,255,rng.randrange(2,18)) if rng.random()<.55 else (54,41,27,rng.randrange(1,12))
        d.point((x,y),fill=c)
    def ellipse(x,y,rx,ry,color,width=0):
        d.ellipse((x-rx,y-ry,x+rx,y+ry),fill=None if width else color,
                  outline=color if width else None,width=width)
    def branch(x,y,angle,length,color,depth=4):
        if depth<1:return
        x2=x+math.cos(angle)*length;y2=y+math.sin(angle)*length
        d.line((x,y,x2,y2),fill=rgba(color,220),width=max(2,depth*2))
        for sign in (-1,1):
            a=angle+sign*.7
            px=x2+math.cos(a)*length*.42;py=y2+math.sin(a)*length*.42
            ellipse(px,py,12+depth*2,25+depth*3,rgba(accent,185))
        branch(x2,y2,angle+rng.uniform(-.28,.28),length*.73,color,depth-1)
    def flower(x,y,r,color):
        for k in range(6):
            a=k*math.tau/6
            ellipse(x+math.cos(a)*r*.72,y+math.sin(a)*r*.72,r*.46,r*.46,rgba(color,190))
        ellipse(x,y,r*.28,r*.28,rgba(accent,240))
    def arc_ring(radius,color,width=3):
        d.ellipse((400-radius,400-radius,400+radius,400+radius),outline=rgba(color,210),width=width)
    def wave(y,color):
        points=[(x,y+math.sin(x*.016+rng.random()*.15)*24+math.sin(x*.033)*9) for x in range(-20,821,4)]
        d.polygon(points+[(820,820),(-20,820)],fill=rgba(color,170))
    if style in (0,13,19):
        # Layered marble veins, luminous cream or black stone.
        for _ in range(18):
            x0=rng.randrange(-200,800);y0=rng.randrange(-200,800)
            points=[(x0+t*14,y0+t*8+math.sin(t*.34)*26) for t in range(55)]
            d.line(points,fill=rgba(accent,rng.randint(85,190)),width=rng.randint(1,4),joint="curve")
        arc_ring(282,accent,3)
    elif style in (1,3,4,5,14,15,17,22,23):
        arc_ring(326,accent,2)
        for k in range(6):
            a=k*math.tau/6+rng.uniform(-.15,.15)
            x=400+math.cos(a)*330;y=400+math.sin(a)*330
            branch(x,y,a+math.pi+rng.uniform(-.4,.4),75,ink,3)
            if style in (4,14,22):flower(x,y,30,accent)
        if style in (3,5):
            for k in range(4):
                a=k*math.pi/2+.3
                x=400+math.cos(a)*340;y=400+math.sin(a)*340
                for j in range(5):
                    branch(x+j*8,y+j*7,a+math.pi,85,accent,2)
    elif style==2:
        # Layered translucent watercolor washes.
        layer=Image.new("RGBA",im.size,(0,0,0,0));ld=ImageDraw.Draw(layer,"RGBA")
        for _ in range(70):
            x=rng.randint(-100,900);y=rng.randint(-100,900);r=rng.randint(45,160)
            ld.ellipse((x-r,y-r,x+r,y+r),fill=rgba(accent,rng.randint(9,25)))
        layer=layer.filter(ImageFilter.GaussianBlur(26))
        im=Image.alpha_composite(im,layer);d=ImageDraw.Draw(im,"RGBA")
        for _ in range(140):ellipse(rng.randint(40,760),rng.randint(40,760),rng.randint(1,3),2,rgba(accent,170))
    elif style in (6,16,20):
        # Layered coastal / mountain landscape.
        if style==20:
            ellipse(575,280,150,150,rgba("#f7c076",210))
            for k in range(5):wave(510+k*53,["#d98d60","#c77758","#aa6251","#8d5360","#674b57"][k])
        elif style==6:
            for k in range(5):wave(310+k*105,["#c2e2de","#79c6ca","#2f9caa","#207a91","#165c74"][k])
        else:
            ellipse(585,230,90,90,rgba("#f9eee0",180))
            for k in range(5):
                y=440+k*66
                pts=[(0,800),(0,y)]
                pts += [(x,y+math.sin(x*.009+k)*70+math.sin(x*.021)*26) for x in range(0,801,8)]
                pts.append((800,800))
                d.polygon(pts,fill=rgba(["#a8b9b4","#839d99","#678b84","#466b64","#294b49"][k],215))
    elif style==7:
        for _ in range(180):
            a=rng.random()*math.tau;r=rng.uniform(290,385)
            x=400+math.cos(a)*r;y=400+math.sin(a)*r
            ellipse(x,y,rng.randint(5,19),rng.randint(5,20),rgba(rng.choice([accent,ink,"#e4c4a6","#d1a38a"]),rng.randint(120,220)))
    elif style==8:
        for j in range(5):
            branch(100+j*22,680-j*55,-1.15,125,accent,3)
    elif style==9:
        # Illustrated overhead latte and coffee beans in the upper corner.
        ellipse(620,225,120,120,rgba("#ead8c2"))
        ellipse(620,225,93,93,rgba("#7a4d30"))
        for j in range(6):
            a=j*math.tau/6
            ellipse(620+math.cos(a)*35,225+math.sin(a)*35,18,31,rgba("#f2dec3",210))
        for j in range(16):
            a=rng.uniform(0,math.tau);r=rng.uniform(315,380)
            ellipse(400+math.cos(a)*r,400+math.sin(a)*r,10,17,rgba(accent,220))
    elif style==10:
        arc_ring(317,ink,3)
        for k in range(10):
            a=k*math.tau/10
            flower(400+math.cos(a)*314,400+math.sin(a)*314,33,accent)
    elif style==11:
        for j in range(90):
            y=25+j*9
            d.arc((-300,y-95,1100,y+95),0,180,fill=rgba(accent,rng.randint(25,90)),width=rng.randint(1,3))
        arc_ring(235,ink,4)
    elif style in (12,18):
        for k in range(9):
            a=k*math.tau/9
            x=400+math.cos(a)*355;y=400+math.sin(a)*355
            ellipse(x,y,rng.randint(70,140),rng.randint(50,120),rgba(rng.choice([accent,ink,"#d7b58d"]),100))
        for k in range(5):branch(rng.randint(40,760),rng.choice([75,720]),-math.pi/2,65,ink,2)
    elif style==21:
        arc_ring(330,accent,2)
        for ring in range(3):
            n=12+ring*8
            radius=100+ring*91
            for k in range(n):
                a=k*math.tau/n
                x=400+math.cos(a)*radius;y=400+math.sin(a)*radius
                ellipse(x,y,19+ring*5,30+ring*8,rgba(accent,150),3)
        flower(400,400,38,accent)
        # Clear the center for readable editable lettering.
        d.ellipse((248,248,552,552),fill=rgba(bg,250))
    # Reserve a central text zone. A translucent center medallion separates
    # type from ornamental illustrations, except for scenic designs.
    if style not in (6,16,20,21,9,8,11):
        d.rounded_rectangle((178,313,622,514),radius=65,
                            fill=rgba(bg,226))
        if style in (0,13,19):d.rounded_rectangle((181,316,619,511),radius=64,outline=rgba(accent,185),width=2)
    return im,title,subtitle,ink,bg,theme

def layout_text(title,subtitle,color):
    # Predict actual text width with the same font used for preview.
    lines=[title]+([subtitle] if subtitle else [])
    result=[]
    font_sizes=[]
    for j,value in enumerate(lines):
        target=465 if j==0 else 480
        size=76 if j==0 else 34
        ft=font(size,True)
        while ft.getbbox(value)[2]-ft.getbbox(value)[0]>target and size>23:
            size-=2;ft=font(size,True)
        font_sizes.append(size)
    heights=[round(s*1.25) for s in font_sizes]
    top=round(400-sum(heights)/2)
    for j,value in enumerate(lines):
        size=font_sizes[j]
        result.append({"id":f"artwork-text-{j}","type":"textbox",
            "left":205,"top":top,"width":590,"text":value,
            "fontSize":round(size*1.25),"fontFamily":"Georgia",
            "fontWeight":"400","fill":color,"textAlign":"center",
            "selectable":True,"evented":True,"customerEditable":True})
        top+=round(heights[j]*1.25)
    return result

class Command(BaseCommand):
    help="Install 100 richly illustrated coaster artworks, keeping editable text."
    def add_arguments(self,parser):
        parser.add_argument("--product-id",type=int,default=415)
        parser.add_argument("--dry-run",action="store_true")
        parser.add_argument("--apply",action="store_true")
    def handle(self,*args,**opts):
        if opts["dry_run"]==opts["apply"]:raise CommandError("Choose --dry-run or --apply")
        qs=list(DesignTemplate.objects.filter(product_id=opts["product_id"],is_active=True).order_by("pk"))
        if len(qs)!=100:raise CommandError(f"Expected 100 active templates, found {len(qs)}")
        prepared=[]
        for i,t in enumerate(qs):
            image,title,subtitle,ink,bg,theme=generate(i)
            image=image.resize((1000,1000),Image.Resampling.LANCZOS)
            buffer=io.BytesIO();image.save(buffer,"PNG",optimize=True)
            data_url="data:image/png;base64,"+base64.b64encode(buffer.getvalue()).decode("ascii")
            # Background is replaceable in the editor. The type stays native Fabric.
            obj={"id":"illustrated-artwork","type":"image","left":0,"top":0,
                 "width":1000,"height":1000,"scaleX":1,"scaleY":1,
                 "src":data_url,"selectable":True,"evented":True,"customerEditable":True}
            texts=layout_text(title,subtitle,ink)
            data=copy.deepcopy(t.json_data or {})
            data["width"]=1000;data["height"]=1000
            data["generator"]="zenvibe-coaster-artwork-v5-canvas"
            data["artworkCategory"]=theme
            data["pages"]=[{"width":1000,"height":1000,"objects":[obj]+texts}]
            data["adminPages"]=copy.deepcopy(data["pages"])
            # Gallery preview is composited from the same background and text.
            preview=image.resize((800,800),Image.Resampling.LANCZOS);d=ImageDraw.Draw(preview)
            for ob in texts:
                ft=font(round(ob["fontSize"]*.8),True)
                value=ob["text"];bbox=d.textbbox((0,0),value,font=ft)
                x=400-(bbox[2]-bbox[0])/2;y=ob["top"]*.8
                d.text((x,y),value,font=ft,fill=ink)
            mask=Image.new("L",(800,800),0)
            ImageDraw.Draw(mask).ellipse((0,0,799,799),fill=255)
            preview.putalpha(mask)
            out=io.BytesIO();preview.save(out,"PNG",optimize=True)
            prepared.append((t,data,out.getvalue(),theme))
        self.stdout.write(f"Prepared {len(prepared)} themed artwork templates")
        if opts["dry_run"]:return
        with transaction.atomic():
            for i,(t,data,png,theme) in enumerate(prepared):
                t.json_data=data
                t.name=f"{i+1:03d} | {theme}"
                t.preview.save(f"coaster-artwork-v5-{t.pk}.png",ContentFile(png),save=False)
                t.save(update_fields=["json_data","name","preview"])
        self.stdout.write(self.style.SUCCESS("Installed 100 artwork-led coaster templates"))
