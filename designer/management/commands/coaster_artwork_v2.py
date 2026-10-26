"""Generate themed, editable SVG artwork for coaster product 415.

No external artwork API, no image flattening, no modifications to other products.
Use: python manage.py coaster_artwork_v2 --generate
Then: python manage.py apply_coaster_artwork --product-id 415 --dry-run
"""
from __future__ import annotations
import math
import random
from pathlib import Path
from xml.sax.saxutils import escape
from django.conf import settings
from django.core.management.base import BaseCommand

ROOT = Path(settings.BASE_DIR) / "designer" / "coaster_artworks"
PALETTES = [
    ("#F7F0E4","#274A3C","#D9A65A","#A9BFA4"),("#FFF4ED","#883E4D","#DB8B8A","#E7BDAC"),
    ("#F1EDE5","#263D54","#C69D59","#B6C6D1"),("#FBF2D5","#395A49","#D58C45","#C8D8AD"),
    ("#F2E9F1","#513A62","#C39DBF","#B6C7E1"),("#E9F4F3","#1C6170","#E4AC7E","#7EB7BC"),
    ("#F8F0E9","#763C30","#E3AE82","#B2B46D"),("#F2F1E8","#343E31","#B0A37E","#C7D5BE"),
    ("#F7E9DC","#6D4C6C","#D8A3A8","#BFAFCB"),("#E7EEF2","#1C425C","#DBA458","#87A9B8"),
]
NAMES = [
    "Botanical Atelier","Wildflower Meadow","Coastal Escape","Sunrise Horizon",
    "Art Deco Salon","Citrus Market","Japanese Garden","Mediterranean Tile",
    "Celestial Nights","Vintage Apothecary","Tropical Paradise","Autumn Harvest",
    "Modern Gallery","Desert Bloom","Ocean Waves","Country Cottage",
    "Heritage Monogram","Parisian Cafe","Winter Evergreen","Abstract Museum",
]
def path(d, fill, stroke="none", sw=0):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def circle(x,y,r,fill,stroke="none",sw=0):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def line(x,y,xx,yy,color,sw=5):
    return f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{xx:.2f}" y2="{yy:.2f}" stroke="{color}" stroke-width="{sw}"/>'
def text(x,y,s,size,color,weight="normal"):
    return f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Georgia" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(s)}</text>'
def ellipse(x,y,rx,ry,fill):
    return f'<ellipse cx="{x:.2f}" cy="{y:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" fill="{fill}"/>'
def artwork(i):
    family=i//5
    variant=i%5
    rng=random.Random(7719+i*901)
    bg,ink,accent,soft=PALETTES[(family+variant)%len(PALETTES)]
    pieces=[f'<rect width="1000" height="1000" fill="{bg}"/>']
    def flower(x,y,r,color):
        for a in range(0,360,60):
            q=math.radians(a)
            pieces.append(ellipse(x+math.cos(q)*r*.67,y+math.sin(q)*r*.67,r*.36,r*.36,color))
        pieces.append(circle(x,y,r*.28,accent))
    def leaf(x,y,ang,scale=1):
        dx=math.cos(ang)*110*scale;dy=math.sin(ang)*110*scale
        pieces.append(line(x,y,x+dx,y+dy,ink,4))
        for t in (.25,.48,.72):
            xx=x+dx*t;yy=y+dy*t
            for side in (-1,1):
                ax=xx+math.cos(ang+side*1.0)*46*scale
                ay=yy+math.sin(ang+side*1.0)*46*scale
                pieces.append(ellipse(ax,ay,25*scale,12*scale,soft))
    if family in (0,1,6,13,15,18):
        for k in range(9+variant*2):
            a=k*2.39996+variant*.2
            rad=320+(k%3)*55
            x=500+math.cos(a)*rad;y=500+math.sin(a)*rad
            if k%3==0: flower(x,y,55+(k%3)*9,accent)
            else: leaf(x,y,a+2,1.0+(k%2)*.3)
        if family==18:
            for k in range(12):pieces.append(circle(100+k*72,130,4,ink))
    elif family in (2,3,14):
        for k in range(7):
            y=160+k*115
            amp=24+k*9
            d="M 0 "+str(y)
            for x in range(0,1001,80):
                d+=f" L {x} {y+math.sin(x/105+k*.75)*amp:.1f}"
            pieces.append(path(d,"none", [soft,ink,accent][k%3],12+k*2))
        pieces.append(circle(760,260,90+variant*12,accent))
        if family==2:
            for k in range(8):pieces.append(ellipse(120+k*115,790+(k%2)*30,35,10,soft))
    elif family in (4,7,16):
        for k in range(4+variant):
            inset=48+k*40
            pieces.append(f'<rect x="{inset}" y="{inset}" width="{1000-2*inset}" height="{1000-2*inset}" rx="{(family==7)*24}" fill="none" stroke="{accent if k%2 else ink}" stroke-width="{5 if k else 12}"/>')
        for k in range(12):
            a=k*math.pi/6
            x=500+math.cos(a)*330;y=500+math.sin(a)*330
            pieces.append(circle(x,y,12+variant*2,accent))
        if family==7:
            for x in (180,820):
                for y in (180,820):flower(x,y,58,soft)
    elif family in (5,11):
        for k in range(10+variant):
            a=k*2.39996
            x=500+math.cos(a)*340;y=500+math.sin(a)*340
            r=40+(k%3)*18
            pieces.append(circle(x,y,r,accent))
            pieces.append(circle(x-10,y-12,r*.58,bg))
            leaf(x+r,y,a+.7,.5)
    elif family in (8,9,17):
        for k in range(70+variant*10):
            x=rng.randrange(70,930);y=rng.randrange(70,930)
            if family==8:pieces.append(circle(x,y,rng.randrange(2,8),accent))
            elif family==9:pieces.append(line(x,y,x+15,y+18,soft,3))
            else:pieces.append(circle(x,y,rng.randrange(3,11),soft))
        pieces.append(circle(500,445,220,"none",ink,5))
        if family==8:pieces.append(circle(500,430,120,accent))
    elif family==10:
        for k in range(12):
            x=80+(k%4)*270;y=120+(k//4)*320
            leaf(x,y,1.1+k*.7,1.5)
            flower(x+75,y+85,42,accent)
    elif family==12:
        for k in range(6+variant):
            x=rng.randrange(40,750);y=rng.randrange(50,780)
            w=rng.randrange(100,280);h=rng.randrange(90,250)
            pieces.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{soft if k%2 else accent}" opacity="0.7"/>')
        pieces.append(circle(730,290,130,bg,ink,7))
    elif family==19:
        for k in range(14):
            a=k*math.pi/7
            x=500+math.cos(a)*270;y=500+math.sin(a)*270
            pieces.append(path(f"M 500 500 L {x:.1f} {y:.1f} L {500+math.cos(a+.15)*330:.1f} {500+math.sin(a+.15)*330:.1f} Z",soft if k%2 else accent))
        pieces.append(circle(500,500,185,bg))
    # The lettering is SVG text, not pixels, and stays editable in Fabric.
    labels=[
        ("THE BOTANICAL","COLLECTION"),("WILDFLOWER","STUDIO"),("COASTAL","RETREAT"),
        ("GOLDEN","HOUR"),("MAISON","DECO"),("CITRUS &","SUNSHINE"),
        ("ZEN","GARDEN"),("CASA","MEDITERRANEA"),("MOONLIGHT","SOCIAL"),
        ("HERITAGE","APOTHECARY"),("TROPICAL","ESCAPE"),("HARVEST","MARKET"),
        ("FORM &","COLOUR"),("DESERT","BLOOM"),("OCEAN","CLUB"),
        ("THE","COTTAGE"),("THE","MONOGRAM"),("CAFE","PARISIEN"),
        ("EVERGREEN","HOUSE"),("MODERN","MUSE"),
    ]
    title,subtitle=labels[family]
    # A solid central label provides legibility without a repetitive outer medallion.
    if family not in (12,19):
        pieces.append(f'<rect x="210" y="375" width="580" height="245" rx="12" fill="{bg}" stroke="{ink}" stroke-width="3"/>')
    pieces.append(text(500,470,title,56 if len(title)<13 else 43,ink,"bold"))
    pieces.append(text(500,548,subtitle,35,ink))
    pieces.append(line(350,573,650,573,accent,5))
    return '<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">\n'+"\n".join(pieces)+"\n</svg>\n"

class Command(BaseCommand):
    help="Generate 100 themed, editable SVG coasters (20 visual families, five variants each)."
    def add_arguments(self,parser):
        parser.add_argument("--generate",action="store_true")
    def handle(self,*args,**opts):
        if not opts["generate"]:
            self.stdout.write("Pass --generate to write the 100 SVGs.")
            return
        ROOT.mkdir(parents=True,exist_ok=True)
        for i in range(100):
            (ROOT/f"{i+1:03d}.svg").write_text(artwork(i),encoding="utf-8")
        self.stdout.write(self.style.SUCCESS("Generated 100 SVGs in 20 themed families; no database changes."))
