"""Create 100 distinct umbrella-panel artworks for Product 205.

Unlike the legacy 10-layout generator, each numbered artwork uses its own
deterministic composition. These are original vector illustrations, not
licensed photographs or hand-art-directed print-ready designs.

python manage.py build_luxury_umbrella_library
python manage.py build_luxury_umbrella_library --apply
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

ROOT = Path(settings.BASE_DIR) / "umbrella_artworks" / "luxury"
THEMES = [
    ("Executive", "YOUR COMPANY", "Signature collection", "#D6BC8D", "#F4EBDD"),
    ("Heritage", "HERITAGE STUDIO", "Crafted to last", "#E2C9A2", "#F5EEE3"),
    ("Botanical", "BOTANICAL HOUSE", "Nature inspired", "#B7D1AF", "#E6F0E1"),
    ("Wedding", "FOREVER & ALWAYS", "Celebrate love", "#EAC5C7", "#FAEAE8"),
    ("Hospitality", "GRAND HOTEL", "Exceptional hospitality", "#E3C19B", "#FFF0D9"),
    ("Property", "PREMIER ESTATES", "A new perspective", "#B4CAD6", "#EDF3F6"),
    ("Golf", "THE GOLF CLUB", "Tradition and excellence", "#B5CBAF", "#E9F1E3"),
    ("Travel", "WANDER MORE", "Discover the world", "#B3D1DA", "#EFF6F5"),
    ("Fashion", "MAISON", "Modern elegance", "#D6C2B8", "#F5ECE8"),
    ("Events", "THE OCCASION", "Make it memorable", "#E2C49E", "#F8ECDC"),
]
# Each ID has its own composition DNA, rather than reusing a template 10 times.
def artwork(n):
    family = n // 10
    name, headline, subtitle, accent, light = THEMES[family]
    seed = n + 1
    # Varied, deterministic editorial composition: orientation, focal region,
    # sweep curvature, silhouette, repetition count and accent placement.
    orientation = (seed * 7) % 11
    center_x = 170 + (seed * 137) % 330
    center_y = 175 + (seed * 71) % 225
    radius = 65 + (seed * 31) % 88
    sweep = 80 + (seed * 47) % 190
    count = 3 + (seed * 13) % 8
    elements = []
    def line(x1,y1,x2,y2,col,width=4):
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{width}" stroke-linecap="round"/>'
    def curve(d,col,width=4,fill="none"):
        return f'<path d="{d}" stroke="{col}" stroke-width="{width}" fill="{fill}" stroke-linecap="round" stroke-linejoin="round"/>'
    def disk(x,y,r,col):
        return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>'
    def ellipse(x,y,rx,ry,col):
        return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{col}"/>'
    # Ten distinctive illustration vocabularies, each with ten unique
    # focal structures and spatial arrangements, not recoloured copies.
    if family == 0:  # corporate architectural strokes
        for j in range(count):
            x = 85 + (seed*37+j*71)%505
            y = 120 + (seed*29+j*41)%320
            elements.append(curve(f"M{x} {y} l{40+j*5} {-24-j*6} l{36+j*3} {24+j*6}", accent, 5))
        elements.append(curve(f"M90 485 Q{center_x} {center_y} 590 485",light,7))
    elif family == 1:  # engraved heritage botanical ornaments
        for j in range(count):
            x = 105 + j*(475/max(count-1,1))
            y = 175 + ((j*seed*19)%235)
            elements.append(curve(f"M{x:.1f} 510 Q{x-55:.1f} {y:.1f} {x:.1f} {y-45:.1f}",accent,3))
            elements.append(ellipse(round(x+13,1),round(y-28,1),16+j%3*5,9,light))
    elif family == 2:  # botanical silhouettes and leaf sprays
        for j in range(count):
            x=90+(j*seed*17+35*j)%490
            y=160+(j*seed*23)%320
            elements.append(curve(f"M{x} {y+100} Q{x-35} {y+25} {x+20} {y}",accent,4))
            elements.append(curve(f"M{x+20} {y} Q{x-48} {y-16} {x-14} {y+47} Q{x+32} {y+24} {x+20} {y}Z",light,2,accent))
    elif family == 3:  # elegant floral petal wreath compositions
        for j in range(count):
            angle=2*math.pi*j/count+orientation*.15
            x=center_x+math.cos(angle)*radius
            y=center_y+math.sin(angle)*radius*.8
            elements.append(ellipse(round(x,1),round(y,1),18+(j%3)*7,36+(j%2)*10,accent if j%2 else light))
        elements.append(disk(center_x,center_y,17,light))
    elif family == 4:  # grand hotel deco fan arches
        for j in range(count):
            x=110+j*(460/max(count-1,1))
            top=140+(seed*j*11)%140
            elements.append(curve(f"M{x:.1f} 500 V{top} Q{x+28:.1f} {top-45} {x+55:.1f} {top}",accent,3))
        elements.append(line(105,515,575,515,light,6))
    elif family == 5:  # modern architecture skylines
        for j in range(count):
            x=95+j*(480/count)
            height=80+(seed*31+j*53)%220
            elements.append(curve(f"M{x:.1f} 510 V{510-height:.1f} H{x+480/count-9:.1f} V510",accent,5))
            if j%2==0:
                elements.append(line(round(x+11,1),round(510-height+25,1),round(x+11,1),485,light,2))
    elif family == 6:  # sweeping golf fairways and landscape bands
        for j in range(count):
            y=185+j*35
            x=95+(j*seed*13)%160
            elements.append(curve(f"M65 {y} Q{x} {y-sweep/3:.1f} 335 {y+25} T615 {y-10}",accent if j%2 else light,4))
        elements.append(disk(500,175,18,light))
    elif family == 7:  # travel topographic contours
        for j in range(count):
            y=125+j*(340/count)
            shift=(seed*23+j*31)%135
            elements.append(curve(f"M65 {y:.1f} C{140+shift} {y-75:.1f} {250-shift/2:.1f} {y+85:.1f} 350 {y:.1f} S{535+shift/3:.1f} {y-55:.1f} 615 {y:.1f}",accent if j%3 else light,3))
    elif family == 8:  # high fashion editorial bands
        for j in range(count):
            x=100+j*(470/count)
            offset=(seed*17+j*19)%120
            elements.append(curve(f"M{x:.1f} 115 L{x+offset:.1f} 500",accent if j%2 else light,5 if j%3 else 9))
        elements.append(curve(f"M95 475 Q{center_x} 405 585 475",light,3))
    else:  # celebration ribbons and cascading loops
        for j in range(count):
            x=100+j*(480/max(count-1,1))
            offset=(seed*11+j*29)%110
            elements.append(curve(f"M{x:.1f} 100 C{x+offset:.1f} 195 {x-offset:.1f} 295 {x+offset/3:.1f} 450",accent if j%2 else light,4))
    # All SVG imagery is restricted to a generous interior print region,
    # avoiding the lower branding lockup and clipping outside the canopy.
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="680" height="730" viewBox="0 0 680 730">'
            '<title>'+escape(name+' '+str(seed))+'</title>'
            '<defs><clipPath id="print"><path d="M90 95 L590 95 L610 470 Q340 570 70 470Z"/></clipPath></defs>'
            '<g clip-path="url(#print)">'+''.join(elements)+'</g></svg>')

class Command(BaseCommand):
    help = "Generate 100 distinct original vector umbrella print compositions."
    def add_arguments(self, parser):
        parser.add_argument("--apply",action="store_true")
        parser.add_argument("--product-id",type=int,default=205)
    def handle(self,*args,**options):
        ROOT.mkdir(parents=True,exist_ok=True)
        manifest=[]
        for n in range(100):
            name,headline,subtitle,_,_=THEMES[n//10]
            filename=f"luxury-{n+1:03d}.svg"
            (ROOT/filename).write_text(artwork(n),encoding="utf-8")
            manifest.append({"name":f"{name} Original Composition {n+1:03d}",
                             "artwork":filename,"headline":headline,
                             "subtitle":subtitle})
        target=ROOT/"manifest.json"
        target.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Created 100 SVG compositions and {target}"))
        if options["apply"]:
            call_command("import_umbrella_artworks",product_id=options["product_id"],
                         manifest=str(target),apply=True)
