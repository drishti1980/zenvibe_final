"""Generate a restrained, editable umbrella print library for Product 205.

Run:
  python manage.py build_luxury_umbrella_library
  python manage.py build_luxury_umbrella_library --apply

Creates 100 standalone SVG artworks and manifest under umbrella_artworks/luxury.
The umbrella's seven product colours and locked mockup are not modified.
Artwork occupies a bounded upper canopy region; branding is handled by the importer.
SVG is a replaceable image layer, while headline/subtitle remain editable text.
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
# One colour system per creative direction; no random shapes or rainbow palette.
COLLECTIONS = (
    ("Executive", "#D7B77B", "#EEE7DC", "YOUR COMPANY", "Est. 2026"),
    ("Heritage", "#C7A87B", "#F4EEE4", "THE HERITAGE CO.", "Crafted with care"),
    ("Botanical", "#B6C9AC", "#F2E8D6", "BOTANICAL HOUSE", "Naturally refined"),
    ("Wedding", "#E5C5B6", "#F7E9E0", "FOREVER & ALWAYS", "Your special day"),
    ("Hospitality", "#D5BC91", "#F3E8D2", "THE GRAND HOTEL", "A warm welcome"),
    ("Real Estate", "#B9C9D2", "#E7EEF1", "PREMIER ESTATES", "Exceptional living"),
    ("Golf", "#9BB9A0", "#E3ECE1", "THE GOLF CLUB", "Since 1985"),
    ("Travel", "#A9C6CF", "#E9EFF0", "THE JOURNEY", "Beyond the ordinary"),
    ("Fashion", "#C5B7AF", "#EFE7E2", "MAISON", "Limited edition"),
    ("Events", "#D4BDA1", "#F1E7DA", "THE OCCASION", "Memorable moments"),
)
NAMES = (
    "Monogram Frame", "Corner Botanical", "Art Deco Border",
    "Signature Diagonal", "Fine-Line Emblem", "Heritage Ribbon",
    "Architectural Lines", "Botanical Arch", "Minimal Medallion",
    "Editorial Border",
)

def path(d, stroke, width=5, fill="none"):
    return f'<path d="{d}" stroke="{stroke}" stroke-width="{width}" fill="{fill}" stroke-linecap="round" stroke-linejoin="round"/>'

def circle(x,y,r,stroke,width=5,fill="none"):
    return f'<circle cx="{x}" cy="{y}" r="{r}" stroke="{stroke}" stroke-width="{width}" fill="{fill}"/>'

def line(x,y,xx,yy,stroke,width=5):
    return f'<line x1="{x}" y1="{y}" x2="{xx}" y2="{yy}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round"/>'

def leaf(x,y,scale,stroke):
    return path(f"M{x} {y} q{-25*scale} {-55*scale} {8*scale} {-100*scale} q{45*scale} {38*scale} {-8*scale} {100*scale}",stroke,3)

def render(index):
    family, variant = divmod(index,10)
    theme, gold, ivory, headline, tagline = COLLECTIONS[family]
    # Entire motif sits above the lower editable text panel (y<535).
    # No artwork near the umbrella's centre hub (around x340,y350).
    motif=[]
    if variant==0:
        motif += [circle(340,260,145,gold,8),circle(340,260,129,ivory,3)]
        for dx in (-120,120):
            motif.append(line(340+dx,150,340+dx,370,gold,2))
    elif variant==1:
        motif += [path("M105 500 Q150 350 120 180",gold,6),
                  path("M575 500 Q530 350 560 180",gold,6)]
        for j in range(4):
            motif += [leaf(115+j*8,420-j*77,.65,gold),
                      leaf(565-j*8,420-j*77,.65,gold)]
    elif variant==2:
        motif += [path("M100 130 H580 V515 H100 Z",gold,8),
                  path("M117 147 H563 V498 H117 Z",ivory,2)]
        for j in range(4):
            motif += [line(110+j*24,130,110,130+j*24,gold,3),
                      line(570-j*24,515,570,515-j*24,gold,3)]
    elif variant==3:
        motif += [path("M90 475 L470 95",gold,12),
                  path("M145 505 L525 125",ivory,5),
                  path("M230 525 L565 190",gold,3)]
    elif variant==4:
        motif += [circle(340,250,120,gold,8),
                  circle(340,250,103,ivory,2),
                  path("M340 103 V145 M340 355 V397 M193 250 H235 M445 250 H487",gold,5)]
        for j in range(6):
            a=j*math.pi/3
            motif.append(circle(round(340+137*math.cos(a),2),
                                round(250+137*math.sin(a),2),6,gold,2,gold))
    elif variant==5:
        motif += [path("M120 180 Q340 85 560 180",gold,8),
                  path("M120 195 Q340 100 560 195",ivory,3),
                  path("M120 430 Q340 525 560 430",gold,8)]
        for j in range(5):
            motif.append(line(165+j*85,165,165+j*85,210,gold,3))
    elif variant==6:
        for j in range(4):
            motif += [line(100,160+j*83,255,160+j*83,gold,3),
                      line(425,160+j*83,580,160+j*83,gold,3)]
        motif += [path("M245 125 L245 470 M435 125 L435 470",ivory,4)]
    elif variant==7:
        motif += [path("M175 510 V265 Q175 105 340 105 Q505 105 505 265 V510",gold,8),
                  path("M193 500 V265 Q193 124 340 124 Q487 124 487 265 V500",ivory,3)]
        for j in range(3):
            motif += [leaf(205,425-j*80,.55,gold),
                      leaf(475,425-j*80,.55,gold)]
    elif variant==8:
        motif += [circle(340,245,118,gold,8),
                  path("M240 245 H440 M340 145 V345",ivory,3),
                  circle(340,245,95,ivory,3)]
        motif += [line(165,425,515,425,gold,4),
                  line(215,440,465,440,ivory,2)]
    else:
        motif += [path("M105 145 H575 M105 160 H575",gold,5),
                  path("M105 475 H575 M105 490 H575",gold,5)]
        for j in range(3):
            motif += [line(125+j*18,185,125+j*18,450,ivory,2),
                      line(555-j*18,185,555-j*18,450,ivory,2)]
    # Controlled theme-specific detail, outside central branding region.
    if family in (2,3):
        for j in range(3):
            motif.append(leaf(90+j*14,455-j*90,.35,ivory))
    if family in (0,1,8):
        motif.append(line(240,530,440,530,gold,3))
    if family in (4,5,9):
        motif.append(path("M250 520 H430",ivory,3))
    if family in (6,7):
        motif.append(circle(340,90,13,gold,3))
    # SVG contains decoration only; real branding remains separately editable.
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="680" height="730" '
            'viewBox="0 0 680 730"><title>'
            +escape(theme+" — "+NAMES[variant])+'</title>'
            +'<g opacity="0.95">'+''.join(motif)+'</g></svg>')

class Command(BaseCommand):
    help = "Build 100 luxury umbrella artwork files; optionally import to Product 205."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--product-id", type=int, default=205)

    def handle(self, *args, **opts):
        ROOT.mkdir(parents=True, exist_ok=True)
        manifest=[]
        for index in range(100):
            family,variant=divmod(index,10)
            theme,gold,ivory,headline,tagline=COLLECTIONS[family]
            filename=f"luxury-{index+1:03d}.svg"
            (ROOT/filename).write_text(render(index),encoding="utf-8")
            manifest.append({
                "name":f"{theme} — {NAMES[variant]}",
                "artwork":filename,
                "headline":headline,
                "subtitle":tagline,
            })
        manifest_path=ROOT/"manifest.json"
        manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",
                                 encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Generated {len(manifest)} luxury SVGs: {manifest_path}"))
        if opts["apply"]:
            call_command("import_umbrella_artworks",
                         product_id=opts["product_id"],
                         manifest=str(manifest_path),apply=True)
