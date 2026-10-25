"""
ZenVibe Business Cards V2 — 200 editable JSON/SVG masters
=========================================================
Creates 100 Standard + 100 Premium business-card templates.

Design rule:
- NO colour-only duplicates.
- Each template receives a different layout DNA: composition, logo treatment,
  typography hierarchy, contact arrangement, vector motif, front/back structure.
- All text/shapes/lines/paths are separate editable Fabric-compatible objects.
- No flattened design artwork is used.
- SVG front/back files are generated from the same editable vector layer data.

Install:
  designer/management/commands/seed_business_card_templates_v2.py

Run:
  python manage.py seed_business_card_templates_v2 \
      --standard-product-id 216 --premium-product-id 1 --dry-run

Then:
  python manage.py seed_business_card_templates_v2 \
      --standard-product-id 216 --premium-product-id 1 --replace-generated
"""
from __future__ import annotations

import hashlib
import html
import json
import math
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from designer.models import DesignTemplate, Product

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = ImageDraw = ImageFont = None

PREFIX_STANDARD = "ZV2 Standard Business Card"
PREFIX_PREMIUM = "ZV2 Premium Business Card"
GENERATOR_ID = "zenvibe-business-card-v2-unique"
DEFAULT_W, DEFAULT_H = 1050, 600

# -----------------------------------------------------------------------------
# Editable Fabric layer helpers
# -----------------------------------------------------------------------------
def txt(i, value, x, y, size, fill, *, font="Montserrat", weight="normal",
        width=None, align="left", spacing=0, angle=0, name="Text"):
    return {
        "id": i, "type": "textbox" if width else "text", "text": value,
        "left": round(x,2), "top": round(y,2), "width": round(width,2) if width else None,
        "fontSize": round(size,2), "font": font, "fontWeight": weight,
        "fontStyle": "normal", "underline": False, "textAlign": align,
        "charSpacing": spacing, "lineHeight": 1.12, "fill": fill, "angle": angle,
        "opacity": 1, "name": name, "fieldType": "template-text",
        "customerEditable": True, "locked": False, "scaleX": 1, "scaleY": 1,
        "originX": "left", "originY": "top",
    }

def rect(i,x,y,w,h,fill,*,rx=0,stroke=None,sw=0,angle=0,opacity=1,name="Shape"):
    return {"id":i,"type":"rect","left":round(x,2),"top":round(y,2),"width":round(w,2),
            "height":round(h,2),"rx":rx,"ry":rx,"fill":fill,"stroke":stroke,"strokeWidth":sw,
            "angle":angle,"opacity":opacity,"name":name,"fieldType":"template-shape",
            "customerEditable":True,"locked":False,"scaleX":1,"scaleY":1,
            "originX":"left","originY":"top"}

def circle(i,x,y,r,fill,*,stroke=None,sw=0,opacity=1,name="Circle"):
    return {"id":i,"type":"circle","left":round(x,2),"top":round(y,2),"radius":round(r,2),
            "fill":fill,"stroke":stroke,"strokeWidth":sw,"opacity":opacity,"name":name,
            "fieldType":"template-shape","customerEditable":True,"locked":False,"scaleX":1,"scaleY":1,
            "originX":"left","originY":"top"}

def line(i,x1,y1,x2,y2,color,*,sw=3,dash=None,name="Line"):
    return {"id":i,"type":"line","left":0,"top":0,"points":[x1,y1,x2,y2],"stroke":color,
            "strokeWidth":sw,"strokeDashArray":dash,"fill":None,"opacity":1,"name":name,
            "fieldType":"template-shape","customerEditable":True,"locked":False,"scaleX":1,"scaleY":1,
            "originX":"left","originY":"top"}

def path(i,d,fill,*,stroke=None,sw=0,opacity=1,name="Vector Artwork"):
    return {"id":i,"type":"path","left":0,"top":0,"path":d,"fill":fill,"stroke":stroke,
            "strokeWidth":sw,"opacity":opacity,"name":name,"fieldType":"template-artwork",
            "customerEditable":True,"locked":False,"scaleX":1,"scaleY":1,
            "originX":"left","originY":"top"}

# -----------------------------------------------------------------------------
# Design systems
# -----------------------------------------------------------------------------
STANDARD_PALETTES = [
    ("#FFFFFF","#111827","#2563EB","#EAF2FF"), ("#FAFAF9","#1C1917","#0F766E","#DDF7F1"),
    ("#FFFFFF","#18181B","#E11D48","#FFE8EF"), ("#F8FAFC","#0F172A","#7C3AED","#EEE9FF"),
    ("#FFFDF7","#292524","#EA580C","#FFF0E4"), ("#F7FBFF","#082F49","#0891B2","#DDF7FC"),
    ("#FFFFFF","#1F2937","#16A34A","#E7F8EC"), ("#FCFBFF","#27272A","#9333EA","#F3E8FF"),
    ("#FAFAFA","#171717","#D97706","#FEF3C7"), ("#F9FAFB","#111827","#0E7490","#CFFAFE"),
]
PREMIUM_PALETTES = [
    ("#0A0A0B","#F6F0E4","#C9A45C","#171719"), ("#F5EFE4","#1B1B1B","#A47B3D","#E8DDCA"),
    ("#071B17","#F4EFE4","#C5A66A","#123027"), ("#151A26","#F7F1E5","#D2B77C","#242D42"),
    ("#3A0C17","#FFF5E8","#D6B06A","#541626"), ("#0F1A24","#F3EEE6","#B9A274","#1C2D3B"),
    ("#EDE7DC","#20201E","#8F6A3D","#D9CFBF"), ("#16120F","#F4E9D8","#B68A4C","#2A211A"),
    ("#13221A","#F8F2E8","#C8A96A","#233B2D"), ("#F6F3ED","#161616","#9B7A49","#E7DFD1"),
]
STD_FONTS = [("Montserrat","Montserrat"),("Poppins","Inter"),("Inter","Montserrat"),("Raleway","Lato"),("Oswald","Montserrat"),("DM Sans","Inter"),("Nunito Sans","Montserrat"),("Work Sans","Inter"),("Roboto","Poppins"),("Manrope","Inter")]
PREM_FONTS = [("Playfair Display","Montserrat"),("Cormorant Garamond","Inter"),("Bodoni Moda","Montserrat"),("DM Serif Display","Lato"),("Libre Baskerville","Montserrat"),("Cinzel","Inter"),("Lora","Montserrat"),("Prata","Inter"),("EB Garamond","Montserrat"),("Merriweather","Inter")]

STD_NAMES = [
"Blue Axis","Nordic Split","Studio Grid","Signal Stripe","Clear Margin","Metro Block","Creative Arc","Pixel Office","Modern Ledger","Cobalt Frame",
"Teal Corner","Mono Contact","Ribbon Edge","Smart Column","Civic Line","Urban Stack","Digital Wave","Fresh Geometry","Clean Offset","Bright Marker",
"Slate Band","Consultant Grid","Agency Slice","Minimal Capsule","Tech Orbit","White Space","Linked Blocks","Professional Curve","Architect Rule","Focus Bar",
"Skyline","Diagonal Office","Modern Ticket","Precision Dot","Linear Brand","Creative Window","Business Pulse","Contour Card","Sharp Corner","Bold Initial",
"Navy Portal","Mint Logic","Rose Accent","Indigo Slice","Orange Shift","Cyan Blueprint","Green Signal","Violet Studio","Amber Office","Ocean Rule",
"Vertical Identity","Side Label","Top Rail","Bottom Rail","Split Identity","Corner Badge","Offset Circle","Floating Panel","Data Grid","Modern Capsule",
"Double Column","Slim Sidebar","Wide Stripe","Micro Pattern","Contact Rail","Logo Window","Name First","Title First","Editorial Office","Rounded Block",
"Geometric Cross","Modular Tile","Framed Signal","Cut Corner","Parallel Lines","Half Tone","Swiss Grid","Creative Dot","Corporate Arch","Modern Hex",
"Fine Grid","Dynamic Slash","Open Frame","Soft Circle","Type Stack","Logo Halo","Minimal Steps","Network Line","Studio Angle","Cardinal Block",
"Quarter Panel","Centre Mark","Left Anchor","Right Anchor","Top Accent","Bottom Accent","Dual Tone","Clean Geometry","Modern Crest","Pure Type"
]
PREM_NAMES = [
"Noir Atelier","Ivory House","Emerald Reserve","Midnight Gilt","Burgundy Salon","Heritage Line","Maison Black","Champagne Frame","Private Studio","Velvet Edge",
"Monogram Society","Gilded Column","Executive Crest","Quiet Luxury","Gallery Serif","Estate Mark","Silk Border","Obsidian Card","Pearl Atelier","Bronze House",
"Deco Arch","Fine Foil","Luxe Signature","Imperial Grid","Tailored Black","Gold Horizon","Velvet Monogram","Ivory Crest","Emerald Salon","Midnight Maison",
"Burgundy Atelier","Heritage Seal","Private Reserve","Gallery Frame","Signature Estate","Noir Column","Champagne Arch","Executive Line","Quiet Serif","Silk Monogram",
"Obsidian Crest","Pearl House","Bronze Atelier","Deco Reserve","Fine Border","Luxe Estate","Imperial Maison","Tailored Gilt","Gold Society","Velvet House",
"Ivory Reserve","Emerald Heritage","Midnight Crest","Burgundy Frame","Noir Signature","Champagne Estate","Private Monogram","Gallery House","Executive Atelier","Quiet Frame",
"Silk Reserve","Obsidian Maison","Pearl Crest","Bronze Signature","Deco Estate","Fine Society","Luxe Arch","Imperial House","Tailored Reserve","Gold Atelier",
"Velvet Crest","Ivory Signature","Emerald Estate","Midnight Society","Burgundy Maison","Heritage Arch","Private House","Gallery Reserve","Executive Monogram","Quiet Estate",
"Silk Atelier","Obsidian Frame","Pearl Society","Bronze Crest","Deco House","Fine Maison","Luxe Reserve","Imperial Signature","Tailored Estate","Gold Crest",
"Velvet Society","Ivory Maison","Emerald Frame","Midnight Reserve","Burgundy Crest","Heritage Estate","Private Signature","Gallery Monogram","Executive House","Quiet Atelier"
]

# 20 structural archetypes. Each of five variants changes geometry, hierarchy,
# motif and back-side construction — not merely the palette.
def build_design(kind:str, index:int, W:int, H:int):
    premium = kind == "premium"
    pal = (PREMIUM_PALETTES if premium else STANDARD_PALETTES)[index % 10]
    bg, ink, accent, soft = pal
    ff_head, ff_body = (PREM_FONTS if premium else STD_FONTS)[index % 10]
    family, variant = divmod(index, 5)
    uid = lambda s: f"{kind}-{index+1:03d}-{s}"
    name = (PREM_NAMES if premium else STD_NAMES)[index]
    front=[]; back=[]

    # shared sample copy, intentionally fully editable
    person = ["ALEX MORGAN","JORDAN LEE","TAYLOR REED","CASEY BLAKE","MORGAN HAYES"][variant]
    role = ["CREATIVE DIRECTOR","BRAND STRATEGIST","ARCHITECT","CONSULTANT","FOUNDER"][variant]
    initials = "".join(x[0] for x in person.split())
    contact = ["+61 400 123 456","hello@yourbrand.com","yourbrand.com"]

    # ---------- 20 genuinely different composition archetypes ----------
    if family == 0:  # asymmetric sidebar
        sw=[190,235,275,320,360][variant]
        front += [rect(uid('side'),0,0,sw,H,accent), txt(uid('logo'),initials,60,65,68,bg,font=ff_head,weight='bold'),
                  txt(uid('name'),person,sw+70,150,48,ink,font=ff_head,weight='bold'),txt(uid('role'),role,sw+70,215,20,accent,font=ff_body,spacing=120),
                  line(uid('rule'),sw+70,270,W-75,270,accent,sw=2)]
        y=330
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,sw+70,y+j*52,21,ink,font=ff_body))
        back += [rect(uid('bside'),W-sw,0,sw,H,accent),txt(uid('blogo'),initials,95,195,110,ink,font=ff_head,weight='bold'),txt(uid('bbrand'),'YOUR BRAND',95,330,24,accent,font=ff_body,spacing=220)]
    elif family == 1:  # diagonal slash
        x=[560,610,660,710,760][variant]
        front += [path(uid('slash'),f"M {x} 0 L {W} 0 L {W} {H} L {x-170} {H} Z",accent),
                  txt(uid('name'),person,80,120,50,ink,font=ff_head,weight='bold'),txt(uid('role'),role,82,190,20,accent,font=ff_body,spacing=140),
                  txt(uid('mono'),initials,x+30,210,100,bg,font=ff_head,weight='bold')]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,80,330+j*46,20,ink,font=ff_body))
        back += [path(uid('bslash'),f"M 0 0 L {W*.42} 0 L {W*.62} {H} L 0 {H} Z",accent),txt(uid('bname'),'YOUR BRAND',W*.57,250,36,ink,font=ff_head,weight='bold')]
    elif family == 2:  # framed centre
        m=[44,58,72,86,100][variant]
        front += [rect(uid('frame'),m,m,W-2*m,H-2*m,'transparent',stroke=accent,sw=3),circle(uid('seal'),W/2-48,105,48,accent),
                  txt(uid('sealtext'),initials,W/2-31,122,30,bg,font=ff_head,weight='bold'),txt(uid('name'),person,0,245,46,ink,font=ff_head,weight='bold',width=W,align='center'),
                  txt(uid('role'),role,0,310,19,accent,font=ff_body,width=W,align='center',spacing=130)]
        front += [txt(uid('mail'),contact[1],0,425,18,ink,font=ff_body,width=W,align='center'),txt(uid('web'),contact[2],0,458,18,ink,font=ff_body,width=W,align='center')]
        back += [rect(uid('bframe'),m,m,W-2*m,H-2*m,ink),txt(uid('blogo'),'YOUR\nBRAND',0,190,62,bg,font=ff_head,weight='bold',width=W,align='center')]
    elif family == 3:  # top stripe / editorial
        hh=[80,105,130,155,180][variant]
        front += [rect(uid('top'),0,0,W,hh,accent),txt(uid('brand'),'YOUR BRAND',70,hh/2-15,24,bg,font=ff_body,weight='bold',spacing=160),
                  txt(uid('name'),person,70,200,56,ink,font=ff_head,weight='bold'),txt(uid('role'),role,72,272,20,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,72,390+j*40,18,ink,font=ff_body))
        back += [rect(uid('btop'),0,0,W,H,accent),txt(uid('bmono'),initials,70,150,170,bg,font=ff_head,weight='bold'),line(uid('br'),70,365,W-80,365,bg,sw=2)]
    elif family == 4:  # circular orbit
        r=[105,125,145,165,185][variant]
        front += [circle(uid('orb1'),85,95,r,soft),circle(uid('orb2'),115,125,r*.66,'transparent',stroke=accent,sw=4),
                  txt(uid('mono'),initials,145,180,54,accent,font=ff_head,weight='bold'),txt(uid('name'),person,500,135,48,ink,font=ff_head,weight='bold'),
                  txt(uid('role'),role,500,202,19,accent,font=ff_body,spacing=100)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,500,330+j*45,19,ink,font=ff_body))
        back += [circle(uid('borb'),W/2-r,H/2-r,r,accent),txt(uid('bmono'),initials,W/2-70,H/2-45,76,bg,font=ff_head,weight='bold')]
    elif family == 5:  # vertical typography
        front += [txt(uid('vert'),'YOUR BRAND',45,515,24,accent,font=ff_body,spacing=180,angle=-90),line(uid('vl'),105,60,105,540,accent,sw=3),
                  txt(uid('name'),person,180,130,62,ink,font=ff_head,weight='bold',width=720),txt(uid('role'),role,185,225,20,accent,font=ff_body,spacing=130)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,185,360+j*44,19,ink,font=ff_body))
        back += [txt(uid('bv'),'YOUR BRAND',0,245,55,bg if premium else ink,font=ff_head,weight='bold',width=W,align='center'),rect(uid('bb'),0,0,35,H,accent)]
    elif family == 6:  # modular tiles
        sizes=[(300,210),(340,180),(250,250),(380,145),(285,225)][variant]
        a,b=sizes
        front += [rect(uid('tile1'),0,0,a,b,accent),rect(uid('tile2'),W-a,H-b,a,b,soft),txt(uid('mono'),initials,65,55,70,bg,font=ff_head,weight='bold'),
                  txt(uid('name'),person,a+55,100,47,ink,font=ff_head,weight='bold'),txt(uid('role'),role,a+58,166,18,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,95,385+j*45,19,ink,font=ff_body))
        back += [rect(uid('bt1'),0,0,W*.48,H,accent),rect(uid('bt2'),W*.48,0,W*.52,H,ink),txt(uid('bmono'),initials,140,225,85,bg,font=ff_head,weight='bold')]
    elif family == 7:  # nested corner lines
        off=[35,50,65,80,95][variant]
        front += [line(uid('l1'),off,off,W*.42,off,accent,sw=4),line(uid('l2'),off,off,off,H*.42,accent,sw=4),
                  line(uid('l3'),W-off,H-off,W*.58,H-off,accent,sw=4),line(uid('l4'),W-off,H-off,W-off,H*.58,accent,sw=4),
                  txt(uid('name'),person,110,160,56,ink,font=ff_head,weight='bold'),txt(uid('role'),role,112,235,19,accent,font=ff_body,spacing=120)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,112,365+j*42,18,ink,font=ff_body))
        back += [txt(uid('blogo'),initials,0,180,140,accent,font=ff_head,weight='bold',width=W,align='center'),txt(uid('brand'),'YOUR BRAND',0,345,22,ink,font=ff_body,width=W,align='center',spacing=200)]
    elif family == 8:  # centre divider two-column
        dx=[430,475,525,575,620][variant]
        front += [line(uid('div'),dx,70,dx,530,accent,sw=2),txt(uid('mono'),initials,95,175,105,accent,font=ff_head,weight='bold'),
                  txt(uid('brand'),'YOUR BRAND',95,315,22,ink,font=ff_body,spacing=180),txt(uid('name'),person,dx+60,135,46,ink,font=ff_head,weight='bold'),txt(uid('role'),role,dx+62,200,18,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,dx+62,335+j*48,18,ink,font=ff_body))
        back += [rect(uid('bl'),0,0,dx,H,ink),rect(uid('br'),dx,0,W-dx,H,accent),txt(uid('bmono'),initials,dx-105,235,80,bg,font=ff_head,weight='bold')]
    elif family == 9:  # stepped blocks
        step=[70,90,110,130,150][variant]
        front += [rect(uid('s1'),0,0,W*.34,step,accent),rect(uid('s2'),0,step,W*.24,step,soft),rect(uid('s3'),0,step*2,W*.14,step,accent),
                  txt(uid('name'),person,430,110,50,ink,font=ff_head,weight='bold'),txt(uid('role'),role,432,180,19,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,432,335+j*45,18,ink,font=ff_body))
        back += [rect(uid('bs1'),0,0,W,H,ink),rect(uid('bs2'),0,H-120,W*.7,120,accent),txt(uid('bbrand'),'YOUR BRAND',75,205,54,bg,font=ff_head,weight='bold')]
    elif family == 10:  # capsule identity
        ww=[330,380,430,480,530][variant]
        front += [rect(uid('cap'),65,70,ww,92,accent,rx=46),txt(uid('brand'),'YOUR BRAND',105,98,23,bg,font=ff_body,weight='bold',spacing=90),
                  txt(uid('name'),person,68,240,54,ink,font=ff_head,weight='bold'),txt(uid('role'),role,70,310,19,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,620,250+j*50,18,ink,font=ff_body))
        back += [rect(uid('bcap'),W*.23,H*.36,W*.54,120,accent,rx=60),txt(uid('bbrand'),'YOUR BRAND',0,H*.36+38,28,bg,font=ff_head,weight='bold',width=W,align='center')]
    elif family == 11:  # architectural blueprint
        g=[55,65,75,85,95][variant]
        for x in range(g,W,g*2): front.append(line(uid(f'gx{x}'),x,0,x,H,soft,sw=1))
        for y in range(g,H,g*2): front.append(line(uid(f'gy{y}'),0,y,W,y,soft,sw=1))
        front += [rect(uid('box'),70,70,W-140,H-140,'transparent',stroke=accent,sw=2),txt(uid('name'),person,115,135,48,ink,font=ff_head,weight='bold'),txt(uid('role'),role,118,205,18,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,118,385+j*40,17,ink,font=ff_body))
        back += [line(uid('bd1'),70,70,W-70,H-70,accent,sw=2),line(uid('bd2'),W-70,70,70,H-70,accent,sw=2),txt(uid('bmono'),initials,0,245,70,ink,font=ff_head,weight='bold',width=W,align='center')]
    elif family == 12:  # wave / contour paths
        amp=[35,50,65,80,95][variant]
        d=f"M 0 {H*.25} C {W*.25} {H*.25-amp}, {W*.5} {H*.25+amp}, {W} {H*.25} L {W} 0 L 0 0 Z"
        front += [path(uid('wave'),d,accent),txt(uid('brand'),'YOUR BRAND',70,70,24,bg,font=ff_body,weight='bold',spacing=140),txt(uid('name'),person,75,300,52,ink,font=ff_head,weight='bold'),txt(uid('role'),role,78,370,19,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,650,315+j*45,18,ink,font=ff_body))
        back += [path(uid('bwave'),f"M 0 {H} C {W*.3} {H-amp*2}, {W*.7} {H+amp}, {W} {H-amp} L {W} 0 L 0 0 Z",ink),txt(uid('bbrand'),'YOUR BRAND',0,250,42,bg,font=ff_head,weight='bold',width=W,align='center')]
    elif family == 13:  # large initial crop
        fs=[280,320,360,400,440][variant]
        front += [txt(uid('giant'),initials[0],-20,-75,fs,soft,font=ff_head,weight='bold'),txt(uid('name'),person,430,120,50,ink,font=ff_head,weight='bold'),txt(uid('role'),role,433,190,18,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,433,340+j*44,18,ink,font=ff_body))
        back += [txt(uid('bgiant'),initials[-1],W-330,-90,400,soft,font=ff_head,weight='bold'),txt(uid('brand'),'YOUR BRAND',75,250,44,accent,font=ff_head,weight='bold')]
    elif family == 14:  # central band
        bh=[110,135,160,185,210][variant]
        front += [rect(uid('band'),0,H/2-bh/2,W,bh,accent),txt(uid('name'),person,70,H/2-40,50,bg,font=ff_head,weight='bold'),txt(uid('role'),role,72,H/2+25,18,bg,font=ff_body,spacing=110)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,70,70+j*38,17,ink,font=ff_body))
        back += [rect(uid('bband'),0,0,W,H,accent),rect(uid('bin'),75,75,W-150,H-150,'transparent',stroke=bg,sw=2),txt(uid('blogo'),initials,0,220,100,bg,font=ff_head,weight='bold',width=W,align='center')]
    elif family == 15:  # quarter circle crop
        r=[180,220,260,300,340][variant]
        front += [circle(uid('q'),-r*.45,-r*.45,r,accent),txt(uid('mono'),initials,45,55,64,bg,font=ff_head,weight='bold'),txt(uid('name'),person,400,135,50,ink,font=ff_head,weight='bold'),txt(uid('role'),role,403,205,18,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,403,350+j*45,18,ink,font=ff_body))
        back += [circle(uid('bq'),W-r*.55,H-r*.55,r,accent),txt(uid('brand'),'YOUR BRAND',75,235,46,ink,font=ff_head,weight='bold')]
    elif family == 16:  # swiss typographic grid
        front += [txt(uid('index'),f"0{variant+1}",70,65,20,accent,font=ff_body,weight='bold'),line(uid('hr'),70,105,W-70,105,ink,sw=2),
                  txt(uid('name'),person,70,145,72,ink,font=ff_head,weight='bold',width=800),txt(uid('role'),role,73,255,18,accent,font=ff_body,spacing=160)]
        front += [txt(uid('phone'),contact[0],70,450,17,ink,font=ff_body),txt(uid('mail'),contact[1],390,450,17,ink,font=ff_body),txt(uid('web'),contact[2],760,450,17,ink,font=ff_body)]
        back += [line(uid('bv'),W*.5,70,W*.5,H-70,accent,sw=2),txt(uid('bname'),'YOUR',110,170,65,ink,font=ff_head,weight='bold'),txt(uid('bname2'),'BRAND',560,300,65,accent,font=ff_head,weight='bold')]
    elif family == 17:  # cut corner polygon
        cut=[90,120,150,180,210][variant]
        d=f"M 0 0 L {W-cut} 0 L {W} {cut} L {W} {H} L 0 {H} Z"
        front += [path(uid('panel'),d,soft),path(uid('corner'),f"M {W-cut} 0 L {W} 0 L {W} {cut} Z",accent),txt(uid('name'),person,85,155,52,ink,font=ff_head,weight='bold'),txt(uid('role'),role,88,225,18,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,88,370+j*43,18,ink,font=ff_body))
        back += [path(uid('bpanel'),f"M 0 0 L {cut} 0 L 0 {cut} Z",accent),txt(uid('bbrand'),'YOUR BRAND',0,250,52,ink,font=ff_head,weight='bold',width=W,align='center')]
    elif family == 18:  # parallel ribbons
        gap=[24,32,40,48,56][variant]
        for k in range(4): front.append(rect(uid(f'r{k}'),0,70+k*gap,W*.32,12,accent if k%2==0 else soft))
        front += [txt(uid('name'),person,420,120,54,ink,font=ff_head,weight='bold'),txt(uid('role'),role,423,195,18,accent,font=ff_body)]
        for j,c in enumerate(contact): front.append(txt(uid(f'c{j}'),c,423,350+j*44,18,ink,font=ff_body))
        back += [rect(uid('bbar1'),0,H*.35,W,18,accent),rect(uid('bbar2'),0,H*.65,W,18,accent),txt(uid('bmono'),initials,0,225,90,ink,font=ff_head,weight='bold',width=W,align='center')]
    else:  # family 19: pure type / signature
        size=[54,60,66,72,78][variant]
        front += [txt(uid('brand'),'YOUR BRAND',75,75,20,accent,font=ff_body,weight='bold',spacing=220),txt(uid('name'),person,75,210,size,ink,font=ff_head,weight='bold'),
                  txt(uid('role'),role,78,295,18,accent,font=ff_body,spacing=120),line(uid('sig'),75,355,350,355,accent,sw=2)]
        front += [txt(uid('phone'),contact[0],650,190,17,ink,font=ff_body),txt(uid('mail'),contact[1],650,245,17,ink,font=ff_body),txt(uid('web'),contact[2],650,300,17,ink,font=ff_body)]
        back += [txt(uid('quote'),'MAKE YOUR MARK.',0,225,58,ink,font=ff_head,weight='bold',width=W,align='center'),line(uid('bline'),W*.35,330,W*.65,330,accent,sw=3)]

    # Matte/glossy finish cue is metadata + subtle vector styling only; still fully editable.
    finish = "Gloss-inspired" if index % 2 else "Matte-inspired"
    if premium and index % 3 == 0:
        # add editable fine-foil line, never a raster effect
        front.append(line(uid('foil'),70,H-55,W-70,H-55,accent,sw=1))
    return name, finish, bg, front, back, {"head":ff_head,"body":ff_body,"palette":pal,"family":family,"variant":variant}

# -----------------------------------------------------------------------------
# Validation + SVG
# -----------------------------------------------------------------------------
def structure_signature(front, back):
    def sig(objects):
        return [(o.get('type'),round(float(o.get('left',0))/25),round(float(o.get('top',0))/25),
                 round(float(o.get('width') or o.get('radius') or 0)/25),round(float(o.get('height') or 0)/25),
                 o.get('font',''),round(float(o.get('fontSize') or 0)/4)) for o in objects]
    return hashlib.sha1(json.dumps([sig(front),sig(back)],sort_keys=True).encode()).hexdigest()

def fabric_json(product, kind, index, name, finish, bg, front, back, dna):
    return {
        "version": 3,
        "generator": GENERATOR_ID,
        "reconstructed": True,
        "templateType": "editable-master",
        "businessCardCollection": kind,
        "finishStyle": finish,
        "designDNA": dna,
        "document": {"width": int(product.width or DEFAULT_W), "height": int(product.height or DEFAULT_H),
                     "physical": "3.5 x 2 in", "unit": "in"},
        "pages": [{"label":"Front","background":bg,"objects":front},
                  {"label":"Back","background":bg,"objects":back}],
        "adminPages": [{"label":"Front","background":bg,"objects":front},
                       {"label":"Back","background":bg,"objects":back}],
        "meta": {"name":name,"allLayersEditable":True,"flattenedArtwork":False},
    }

def esc(v): return html.escape(str(v),quote=True)
def page_svg(page,W,H):
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',f'<rect width="100%" height="100%" fill="{esc(page.get("background","#fff"))}"/>']
    for o in page.get('objects',[]):
        t=o.get('type'); fill=o.get('fill') or 'none'; stroke=o.get('stroke') or 'none'; sw=o.get('strokeWidth',0); op=o.get('opacity',1)
        if t in ('text','textbox','i-text'):
            anchor={'left':'start','center':'middle','right':'end'}.get(o.get('textAlign'),'start'); x=o.get('left',0); w=o.get('width') or 0
            if anchor=='middle': x+=w/2
            elif anchor=='end': x+=w
            out.append(f'<text x="{x}" y="{o.get("top",0)+o.get("fontSize",20)}" font-family="{esc(o.get("font","Arial"))}" font-size="{o.get("fontSize",20)}" font-weight="{esc(o.get("fontWeight","normal"))}" fill="{esc(fill)}" opacity="{op}" text-anchor="{anchor}">{esc(o.get("text",""))}</text>')
        elif t=='rect': out.append(f'<rect x="{o.get("left",0)}" y="{o.get("top",0)}" width="{o.get("width",0)}" height="{o.get("height",0)}" rx="{o.get("rx",0)}" fill="{esc(fill)}" stroke="{esc(stroke)}" stroke-width="{sw}" opacity="{op}"/>')
        elif t=='circle': out.append(f'<circle cx="{o.get("left",0)+o.get("radius",0)}" cy="{o.get("top",0)+o.get("radius",0)}" r="{o.get("radius",0)}" fill="{esc(fill)}" stroke="{esc(stroke)}" stroke-width="{sw}" opacity="{op}"/>')
        elif t=='line':
            p=o.get('points',[0,0,0,0]); out.append(f'<line x1="{p[0]}" y1="{p[1]}" x2="{p[2]}" y2="{p[3]}" stroke="{esc(stroke)}" stroke-width="{sw}" opacity="{op}"/>')
        elif t=='path': out.append(f'<path d="{esc(o.get("path",""))}" fill="{esc(fill)}" stroke="{esc(stroke)}" stroke-width="{sw}" opacity="{op}"/>')
    out.append('</svg>'); return ''.join(out)

def simple_preview(payload,W,H):
    if Image is None: return None
    page=payload['pages'][0]; im=Image.new('RGB',(W,H),page['background']); d=ImageDraw.Draw(im)
    for o in page['objects']:
        fill=o.get('fill')
        if not fill or fill=='transparent': continue
        try:
            if o['type']=='rect': d.rectangle((o['left'],o['top'],o['left']+o['width'],o['top']+o['height']),fill=fill)
            elif o['type']=='circle': d.ellipse((o['left'],o['top'],o['left']+2*o['radius'],o['top']+2*o['radius']),fill=fill)
            elif o['type']=='line': d.line(o['points'],fill=o.get('stroke') or fill,width=max(1,int(o.get('strokeWidth',1))))
        except Exception: pass
    import io
    b=io.BytesIO(); im.resize((525,300)).save(b,format='PNG'); return b.getvalue()

class Command(BaseCommand):
    help = "Generate 100 unique Standard + 100 unique Premium editable JSON/SVG business cards."

    def add_arguments(self,p):
        p.add_argument('--standard-product-id',type=int,required=True)
        p.add_argument('--premium-product-id',type=int,required=True)
        p.add_argument('--count',type=int,default=100)
        p.add_argument('--replace-generated',action='store_true')
        p.add_argument('--dry-run',action='store_true')
        p.add_argument('--premium-only',action='store_true',help='Only generate Premium Business Cards; leave Standard templates unchanged.')

    def handle(self,*args,**opts):
        count=opts['count']
        if count<1 or count>100: raise CommandError('--count must be 1..100')
        try:
            std=Product.objects.get(pk=opts['standard_product_id']); prem=Product.objects.get(pk=opts['premium_product_id'])
        except Product.DoesNotExist as e: raise CommandError(str(e))
        if opts['replace_generated'] and not opts['dry_run']:
            q=DesignTemplate.objects.filter(product=prem,name__startswith=PREFIX_PREMIUM)
            if not opts['premium_only']:
                q=q | DesignTemplate.objects.filter(product=std,name__startswith=PREFIX_STANDARD)
            deleted=q.count(); q.delete(); self.stdout.write(f'Deleted {deleted} previous V2 generated templates.')

        total=0; signatures=set(); export_root=Path(settings.BASE_DIR)/'generated_business_card_svg_v2'
        if not opts['dry_run']: export_root.mkdir(parents=True,exist_ok=True)
        targets=[('premium',prem,PREFIX_PREMIUM)] if opts['premium_only'] else [('standard',std,PREFIX_STANDARD),('premium',prem,PREFIX_PREMIUM)]
        for kind,product,prefix in targets:
            W=int(product.width or DEFAULT_W); H=int(product.height or DEFAULT_H)
            for i in range(count):
                # Standard and Premium share the same canonical 100-design library.
                # Product-specific pricing and finish are configured on Product, not artwork.
                design_name,finish,bg,front,back,dna=build_design('standard',i,W,H)
                sig=structure_signature(front,back)
                if (kind,sig) in signatures: raise CommandError(f'Duplicate structure detected: {kind} {i+1}')
                signatures.add((kind,sig))
                full_name=f'{prefix} {i+1:03d} · {design_name} · {finish}'
                payload=fabric_json(product,kind,i,full_name,finish,bg,front,back,dna)
                payload['sharedDesignLibrary']='zenvibe-business-cards-canonical-100'
                payload['sharedDesignIndex']=i+1
                if not all(p['objects'] for p in payload['pages']): raise CommandError(f'Empty page {full_name}')
                if opts['dry_run']:
                    self.stdout.write(f'DRY RUN {kind:8s} {i+1:03d}: {full_name}')
                else:
                    obj,_=DesignTemplate.objects.update_or_create(product=product,name=full_name,defaults={'json_data':payload,'is_active':True})
                    preview=simple_preview(payload,W,H)
                    if preview:
                        obj.preview.save(f'zv2-business-card-{kind}-{i+1:03d}.png',ContentFile(preview),save=False); obj.save(update_fields=['preview','updated_at'])
                    folder=export_root/kind/f'{i+1:03d}-{design_name.lower().replace(" ","-")}'
                    folder.mkdir(parents=True,exist_ok=True)
                    (folder/'front.svg').write_text(page_svg(payload['pages'][0],W,H),encoding='utf-8')
                    (folder/'back.svg').write_text(page_svg(payload['pages'][1],W,H),encoding='utf-8')
                    (folder/'template.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
                total+=1
        self.stdout.write(self.style.SUCCESS((f'Dry run complete. {total} unique editable templates validated; database unchanged.' if opts['dry_run'] else f'Created/updated {total} editable templates. SVG/JSON exports: {export_root}')))
