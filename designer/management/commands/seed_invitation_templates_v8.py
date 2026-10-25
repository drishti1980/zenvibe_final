from __future__ import annotations

import copy
import hashlib
import io
import json
import math
from html import escape
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import DesignTemplate, Product

try:
    import cairosvg
except Exception:
    cairosvg = None

W, H = 750, 1050
GENERATOR_ID = "zenvibe-invitation-v8-100-distinct-couture"
MEDIA_DIR = "generated_invitation_templates_v8"
VERSION = 8

# Original design directions informed by public luxury/elegant invitation trends:
# botanical florals, watercolor-like layered petals, gold linework, arches,
# chinoiserie, art-deco, monograms, Indian-inspired ornament, pearl/lace frames,
# editorial typography, dark jewel tones, photo windows, celestial and garden themes.

EVENTS = [
    ("Wedding", "OLIVIA & ETHAN", "Together with their families", "SATURDAY · 18 OCTOBER 2026", "THE GLASSHOUSE · MELBOURNE"),
    ("Engagement", "AMELIA & NOAH", "Celebrate our engagement", "FRIDAY · 06 NOVEMBER 2026", "THE TERRACE · GEELONG"),
    ("Birthday", "SOPHIA TURNS 30", "Dinner · Drinks · Dancing", "SATURDAY · 24 OCTOBER 2026", "THE GARDEN ROOM · 7:00 PM"),
    ("Baby Shower", "BABY IN BLOOM", "Honouring Sarah & baby", "SUNDAY · 08 NOVEMBER 2026", "WILLOW HOUSE · 2:00 PM"),
    ("Anniversary", "25 YEARS", "Celebrating Mia & Daniel", "SATURDAY · 14 NOVEMBER 2026", "GRAND BALLROOM · 6:30 PM"),
    ("Graduation", "CLASS OF 2026", "Celebrate William's graduation", "FRIDAY · 20 NOVEMBER 2026", "HARBOUR HALL · 6:00 PM"),
    ("Corporate", "AN EVENING WITH ZENVIBE", "Client appreciation reception", "THURSDAY · 29 OCTOBER 2026", "WATERFRONT PAVILION · 6:00 PM"),
    ("Housewarming", "NEW HOME · NEW MEMORIES", "Come celebrate with us", "SUNDAY · 15 NOVEMBER 2026", "18 GARDEN AVENUE · 3:00 PM"),
    ("Kids", "MILA TURNS FIVE", "Cake · Games · Big smiles", "SUNDAY · 22 NOVEMBER 2026", "RAINBOW ROOM · 1:00 PM"),
    ("Festive", "A FESTIVE SOIRÉE", "Celebrate the season with us", "SATURDAY · 12 DECEMBER 2026", "THE ORANGERIE · 6:30 PM"),
]

PALETTES = [
    ("Ivory Champagne", "#fffaf0", "#1d1d1d", "#c79b45", "#ead9b3", "#ffffff", "#7d9a7a"),
    ("Emerald Gold", "#123f35", "#fff9ef", "#d2ad61", "#2d6657", "#f7efd9", "#8fb58b"),
    ("Midnight Sapphire", "#101d43", "#fffaf4", "#d9b25e", "#243f7a", "#eef2ff", "#8aa0ce"),
    ("Burgundy Rose", "#6b1734", "#fff7f4", "#d5a18d", "#9c4860", "#f7d9de", "#6f9170"),
    ("Orchid Plum", "#45205a", "#fff8fd", "#e0b6e6", "#77438a", "#f4ddf4", "#9b85ad"),
    ("Aqua Champagne", "#0b777a", "#fffdf8", "#e2c06d", "#42aaa8", "#dff6f4", "#6e9c83"),
    ("Cobalt Coral", "#234a9f", "#fff8f4", "#ff806f", "#5b78c8", "#ffe1da", "#6e9a7a"),
    ("Fuchsia Gold", "#9f1f68", "#fff8f4", "#d9b663", "#cf4b91", "#faddeb", "#6d9276"),
    ("Forest Antique", "#1d4c36", "#fffaf0", "#b9944e", "#538169", "#e6efe5", "#8aac7c"),
    ("Terracotta Cream", "#b76148", "#fff8ef", "#efb06a", "#db8b73", "#f9e0d3", "#7f9970"),
    ("Black Pearl", "#111111", "#fbf7ed", "#d0c19b", "#333333", "#f1ece1", "#8f9b7c"),
    ("Peacock Teal", "#004c56", "#fffaf5", "#d5a84c", "#16818a", "#dff2f0", "#91ad7b"),
    ("Lavender Silver", "#74558a", "#fff9ff", "#d7d0e7", "#9d83ae", "#eee5f4", "#8ea084"),
    ("Sunset Peach", "#ef715f", "#fff9f3", "#f1c05e", "#f39a82", "#ffe2d5", "#87a276"),
    ("Mint Emerald", "#e1f6ed", "#13372f", "#2b8a72", "#91d0b8", "#ffffff", "#5f9071"),
    ("Royal Aubergine", "#32143f", "#fff8f1", "#dfb25c", "#5d2b70", "#f0ddef", "#8c9f77"),
    ("Azure White", "#eaf5ff", "#183754", "#3e8ed0", "#a8d5f5", "#ffffff", "#6e9479"),
    ("Blush Burgundy", "#fff0f0", "#6c2030", "#be7980", "#e9c2c6", "#ffffff", "#6f9275"),
    ("Lemon Navy", "#fff4a8", "#19284a", "#e4b740", "#f4dd6a", "#fffbea", "#7e9d75"),
    ("Teal Magenta", "#073c42", "#fff7fb", "#df3d8e", "#176e73", "#ffd9ea", "#82a06f"),
]

FONTS = [
    ("Cormorant Garamond", "Montserrat"),
    ("Playfair Display", "DM Sans"),
    ("Cinzel", "Montserrat"),
    ("Libre Baskerville", "DM Sans"),
    ("DM Serif Display", "Montserrat"),
    ("Georgia", "DM Sans"),
]

DESIGN_NAMES = [
    "Ivory Peony Atelier", "Emerald Rose Conservatory", "Midnight Orchid Gold", "Blush Magnolia Silk", "Burgundy Garden Estate",
    "Champagne Camellia Crest", "Sapphire Botanical Arch", "Rosewater Peony Wreath", "Black Gold Orchid Gala", "Lavender Floral Cameo",
    "Pearl Jasmine Lace", "Forest Wildflower Manor", "Aqua Lotus Pavilion", "Ruby Dahlia Ballroom", "Cobalt Hydrangea Gallery",
    "Ivory Olive Monogram", "Fuchsia Rose Editorial", "Terracotta Garden Vow", "Teal Magnolia Luxe", "Navy Pearl Botanical",
    "Champagne Wildflower Gate", "Emerald Orchid Chinoiserie", "Blush Peony Ribbon", "Aubergine Floral Cathedral", "Azure Jasmine Window",
    "Burgundy Vintage Rose", "Ivory Gold Fern", "Peacock Dahlia Crest", "Lavender Wisteria Arch", "Midnight Celestial Bloom",
    "Rose Gold Camellia", "Forest Magnolia Estate", "Pearl Orchid Border", "Ruby Botanical Frame", "Aqua Hydrangea Garden",
    "Cobalt Rose Deco", "Ivory Peony Cascade", "Emerald Jasmine Oval", "Blush Orchid Halo", "Black Pearl Florentine",
    "Champagne Lotus Mandala", "Navy Magnolia Conservatory", "Terracotta Rose Scroll", "Plum Wisteria Gallery", "Mint Wildflower Garden",
    "Ivory Floral Filigree", "Fuchsia Peony Luxe", "Sapphire Orchid Court", "Burgundy Jasmine Manor", "Pearl Magnolia Ribbon",
    "Rose Gold Camellia Duo", "Emerald Rose Cameo", "Azure Peony Ballroom", "Aubergine Orchid Wreath", "Champagne Garden Arch",
    "Blush Magnolia Terrace", "Forest Camellia Oval", "Cobalt Botanical Gate", "Ivory Dahlia Atelier", "Ruby Peony Scroll",
    "Pearl Jasmine Cathedral", "Peacock Orchid Crest", "Lavender Rose Conservatory", "Midnight Camellia Deco", "Terracotta Magnolia Garden",
    "Gold Leaf Peony Estate", "Aqua Jasmine Halo", "Burgundy Orchid Court", "Ivory Rose Chinoiserie", "Emerald Magnolia Lace",
    "Blush Wildflower Ribbon", "Sapphire Dahlia Frame", "Pearl Orchid Gallery", "Plum Botanical Arch", "Champagne Peony Mandala",
    "Cobalt Orchid Gilded", "Ivory Botanical Ballroom", "Blush Magnolia Cameo", "Midnight Wildflower Gold", "Champagne Rose Finale",
    "Emerald Peony Salon", "Ruby Camellia Theatre", "Pearl Hydrangea House", "Navy Jasmine Pavilion", "Rosewater Dahlia Suite",
    "Aqua Orchid Society", "Forest Peony Hall", "Ivory Magnolia Court", "Fuchsia Botanical Salon", "Black Gold Rose Room",
    "Lavender Jasmine Estate", "Cobalt Peony Gallery", "Terracotta Orchid Manor", "Champagne Magnolia House", "Emerald Wildflower Court",
    "Pearl Rose Ballroom", "Ruby Orchid Atelier", "Ivory Camellia Hall", "Midnight Magnolia Palace", "Blush Peony Finale",
]


def uid(prefix: str, *parts) -> str:
    return prefix + "_" + "_".join(str(p).replace(" ", "_") for p in parts)


def rect(i, x, y, w, h, fill, stroke=None, sw=0, rx=0, opacity=1, editable=True):
    return {"id": i, "name": i.replace("_", " ").title(), "type": "rect", "left": round(x,2), "top": round(y,2), "width": round(w,2), "height": round(h,2), "fill": fill, "stroke": stroke, "strokeWidth": sw, "rx": rx, "ry": rx, "opacity": opacity, "customerEditable": editable}


def circle(i, x, y, r, fill, stroke=None, sw=0, opacity=1, editable=True):
    return {"id": i, "name": i.replace("_", " ").title(), "type": "circle", "left": round(x-r,2), "top": round(y-r,2), "radius": round(r,2), "fill": fill, "stroke": stroke, "strokeWidth": sw, "opacity": opacity, "customerEditable": editable}


def ellipse(i, x, y, rx, ry, fill, stroke=None, sw=0, angle=0, opacity=1, editable=True):
    return {"id": i, "name": i.replace("_", " ").title(), "type": "ellipse", "left": round(x-rx,2), "top": round(y-ry,2), "rx": round(rx,2), "ry": round(ry,2), "fill": fill, "stroke": stroke, "strokeWidth": sw, "angle": angle, "opacity": opacity, "customerEditable": editable}


def line(i, x1, y1, x2, y2, stroke, sw=2, opacity=1, dash=None, editable=True):
    d = {"id": i, "name": i.replace("_", " ").title(), "type": "line", "left": 0, "top": 0, "points": [round(x1,2), round(y1,2), round(x2,2), round(y2,2)], "stroke": stroke, "strokeWidth": sw, "fill": None, "opacity": opacity, "customerEditable": editable}
    if dash:
        d["strokeDashArray"] = dash
    return d


def path(i, d, fill="transparent", stroke=None, sw=0, opacity=1, angle=0, editable=True):
    return {"id": i, "name": i.replace("_", " ").title(), "type": "path", "left": 0, "top": 0, "path": d, "fill": fill, "stroke": stroke, "strokeWidth": sw, "opacity": opacity, "angle": angle, "customerEditable": editable}


def textbox(i, x, y, text, fs, fill, width=560, align="center", font="Playfair Display", weight=400, lh=1.15, italic=False, spacing=0):
    # IMPORTANT: editor-native text object. No SVG text overlay, no raster text.
    return {
        "id": i, "name": i.replace("_", " ").title(), "type": "textbox",
        "left": round(x,2), "top": round(y,2), "width": round(width,2),
        "text": text, "fontSize": fs, "font": font, "fontFamily": font,
        "fontWeight": weight, "fontStyle": "italic" if italic else "normal",
        "fill": fill, "textAlign": align, "charSpacing": spacing,
        "lineHeight": lh, "customerEditable": True, "locked": False,
        "fieldType": "invitation-text", "manualReplacement": True,
    }


def petal(i, cx, cy, length, width, color, angle=0, opacity=.88):
    # A petal is an editable bezier path in absolute document coordinates.
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    tipx, tipy = cx + ux*length, cy + uy*length
    p1x, p1y = cx + vx*width, cy + vy*width
    p2x, p2y = cx - vx*width, cy - vy*width
    c1x, c1y = cx + ux*length*.52 + vx*width*1.05, cy + uy*length*.52 + vy*width*1.05
    c2x, c2y = cx + ux*length*.92 + vx*width*.35, cy + uy*length*.92 + vy*width*.35
    c3x, c3y = cx + ux*length*.92 - vx*width*.35, cy + uy*length*.92 - vy*width*.35
    c4x, c4y = cx + ux*length*.52 - vx*width*1.05, cy + uy*length*.52 - vy*width*1.05
    d = f"M {p1x:.1f} {p1y:.1f} C {c1x:.1f} {c1y:.1f} {c2x:.1f} {c2y:.1f} {tipx:.1f} {tipy:.1f} C {c3x:.1f} {c3y:.1f} {c4x:.1f} {c4y:.1f} {p2x:.1f} {p2y:.1f} Q {cx:.1f} {cy:.1f} {p1x:.1f} {p1y:.1f} Z"
    return path(i, d, fill=color, opacity=opacity)


def leaf(i, cx, cy, length, width, color, angle=0, opacity=.9, stroke=None):
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    sx, sy = cx - ux*length*.5, cy - uy*length*.5
    tx, ty = cx + ux*length*.5, cy + uy*length*.5
    c1x, c1y = cx + vx*width, cy + vy*width
    c2x, c2y = cx - vx*width, cy - vy*width
    d = f"M {sx:.1f} {sy:.1f} Q {c1x:.1f} {c1y:.1f} {tx:.1f} {ty:.1f} Q {c2x:.1f} {c2y:.1f} {sx:.1f} {sy:.1f} Z"
    return path(i, d, fill=color, stroke=stroke, sw=.7 if stroke else 0, opacity=opacity)


def flower(prefix, cx, cy, scale, petal_color, inner_color, kind="peony", rot=0):
    o=[]
    if kind == "orchid":
        counts=[5,3]
        radii=[36,18]
        widths=[13,9]
    elif kind == "dahlia":
        counts=[14,10,6]
        radii=[30,21,12]
        widths=[7,6,5]
    elif kind == "magnolia":
        counts=[7,5]
        radii=[34,20]
        widths=[14,11]
    elif kind == "rose":
        counts=[12,8,5]
        radii=[28,18,10]
        widths=[8,7,5]
    else: # peony / camellia
        counts=[12,9,6]
        radii=[32,21,12]
        widths=[9,8,6]
    for ring,(count,rad,wid) in enumerate(zip(counts,radii,widths)):
        for j in range(count):
            ang = rot + j*(360/count) + ring*9
            opacity = .58 + ring*.14
            o.append(petal(uid(prefix,"petal",ring,j),cx,cy,rad*scale,wid*scale,petal_color,ang,opacity))
    o.append(circle(uid(prefix,"center"),cx,cy,5.5*scale,inner_color,opacity=.95))
    for j in range(8):
        a=math.radians(j*45)
        o.append(circle(uid(prefix,"stamen",j),cx+math.cos(a)*8*scale,cy+math.sin(a)*8*scale,1.6*scale,inner_color,opacity=.9))
    return o


def foliage_spray(prefix, cx, cy, length, color, accent, angle=0, density=7, flip=1):
    o=[]
    a=math.radians(angle)
    ux,uy=math.cos(a),math.sin(a)
    vx,vy=-uy,ux
    sx,sy=cx-ux*length*.5,cy-uy*length*.5
    ex,ey=cx+ux*length*.5,cy+uy*length*.5
    o.append(line(uid(prefix,"stem"),sx,sy,ex,ey,accent,1.3,.75))
    for j in range(density):
        t=(j+1)/(density+1)
        bx,by=sx+(ex-sx)*t,sy+(ey-sy)*t
        side=1 if j%2==0 else -1
        side*=flip
        lx,ly=bx+vx*17*side,by+vy*17*side
        o.append(leaf(uid(prefix,"leaf",j),lx,ly,34,11,color,angle+side*48,.88,accent))
        if j%3==1:
            o.append(circle(uid(prefix,"berry",j),bx+vx*29*side,by+vy*29*side,3.3,accent,opacity=.88))
    return o


def floral_cluster(prefix, cx, cy, palette, seed=0, scale=1.0, mirror=False):
    _,bg,dark,gold,soft,white,green=palette
    colors=[soft,white,"#f7c7d7","#f0d8b4","#d9c4ef", "#f2a8b9"]
    kinds=["peony","rose","magnolia","orchid","dahlia"]
    o=[]
    direction=-1 if mirror else 1
    o += foliage_spray(uid(prefix,"sprayA"),cx-50*direction,cy+8,140*scale,green,gold,24*direction,7,direction)
    o += foliage_spray(uid(prefix,"sprayB"),cx+50*direction,cy+10,125*scale,green,gold,154*direction,6,-direction)
    placements=[(-34,-8,1.02),(10,-18,.88),(43,10,.72),(-5,29,.62)]
    for k,(dx,dy,sc) in enumerate(placements):
        color=colors[(seed+k)%len(colors)]
        o += flower(uid(prefix,"flower",k),cx+dx*scale,cy+dy*scale,sc*scale,color,gold,kinds[(seed+k)%len(kinds)],seed*13+k*17)
    for j in range(8):
        a=math.radians(seed*19+j*45)
        px=cx+math.cos(a)*(74+j%3*9)*scale
        py=cy+math.sin(a)*(58+j%2*10)*scale
        o.append(petal(uid(prefix,"loose",j),px,py,15*scale,5*scale,colors[(seed+j+2)%len(colors)],seed*17+j*31,.62))
    return o


def gold_filagree(prefix, palette, variant=0):
    _,bg,dark,gold,soft,white,green=palette
    o=[]
    # corner curls and delicate gold rules
    corners=[(54,54,1,1),(W-54,54,-1,1),(54,H-54,1,-1),(W-54,H-54,-1,-1)]
    for c,(x,y,sx,sy) in enumerate(corners):
        d=f"M {x:.1f} {y:.1f} C {x+sx*55:.1f} {y:.1f} {x+sx*76:.1f} {y+sy*24:.1f} {x+sx*80:.1f} {y+sy*62:.1f} C {x+sx*82:.1f} {y+sy*88:.1f} {x+sx*60:.1f} {y+sy*102:.1f} {x+sx*42:.1f} {y+sy*78:.1f}"
        o.append(path(uid(prefix,"curl",c),d,stroke=gold,sw=1.6,opacity=.85))
        o.append(circle(uid(prefix,"dot",c),x+sx*90,y+sy*90,2.4,gold,opacity=.8))
    return o


def luxury_frame(prefix,palette,kind="double"):
    _,bg,dark,gold,soft,white,green=palette
    o=[]
    if kind=="arch":
        o.append(path(uid(prefix,"arch1"),"M 105 910 L 105 355 C 105 155 645 155 645 355 L 645 910",stroke=gold,sw=2.0,opacity=.9))
        o.append(path(uid(prefix,"arch2"),"M 122 892 L 122 365 C 122 182 628 182 628 365 L 628 892",stroke=soft,sw=1.2,opacity=.85))
    elif kind=="oval":
        o.append(ellipse(uid(prefix,"oval1"),375,520,280,405,"transparent",gold,2.0,opacity=.9))
        o.append(ellipse(uid(prefix,"oval2"),375,520,263,387,"transparent",soft,1.2,opacity=.8))
    elif kind=="deco":
        o.append(rect(uid(prefix,"outer"),52,52,646,946,"transparent",gold,2.0))
        o.append(rect(uid(prefix,"inner"),68,68,614,914,"transparent",gold,1.0,opacity=.65))
        for x in (92,658):
            o.append(line(uid(prefix,"v",x),x,92,x,958,gold,1,.65))
        for y in (132,918):
            o.append(line(uid(prefix,"h",y),92,y,658,y,gold,1,.65))
    elif kind=="lace":
        o.append(rect(uid(prefix,"base"),56,56,638,938,"transparent",gold,1.4,opacity=.8))
        for x in range(76,676,24):
            o.append(circle(uid(prefix,"topdot",x),x,68,3.2,gold,opacity=.75))
            o.append(circle(uid(prefix,"botdot",x),x,982,3.2,gold,opacity=.75))
        for y in range(92,960,28):
            o.append(circle(uid(prefix,"ldot",y),68,y,3.2,gold,opacity=.75))
            o.append(circle(uid(prefix,"rdot",y),682,y,3.2,gold,opacity=.75))
    else:
        o.append(rect(uid(prefix,"outer"),52,52,646,946,"transparent",gold,2.0,rx=2))
        o.append(rect(uid(prefix,"inner"),66,66,618,918,"transparent",soft,1.0,rx=2,opacity=.75))
    o += gold_filagree(uid(prefix,"filagree"),palette)
    return o


def watercolor_wash(prefix,palette,variant=0):
    _,bg,dark,gold,soft,white,green=palette
    o=[]
    # translucent editable ellipses emulate watercolor without raster imagery
    blobs=[(115,170,130,80,soft,.13,-18),(620,230,140,95,green,.10,22),(150,850,150,90,gold,.08,12),(600,860,170,95,soft,.12,-15)]
    for j,(x,y,rx,ry,c,op,a) in enumerate(blobs):
        o.append(ellipse(uid(prefix,j),x,y,rx,ry,c,angle=a,opacity=op))
    return o


def gloss_layers(prefix,palette,variant=0):
    _,bg,dark,gold,soft,white,green=palette
    return [
        path(uid(prefix,"shine1"),"M 420 0 L 610 0 L 270 1050 L 95 1050 Z",fill=white,opacity=.035,editable=False),
        ellipse(uid(prefix,"shine2"),180,140,160,95,white,opacity=.025,editable=False),
        line(uid(prefix,"micro"),110,946,640,946,gold,.7,.45),
    ]


def monogram(prefix,palette,letters="O & E",y=160):
    _,bg,dark,gold,soft,white,green=palette
    o=[]
    o.append(circle(uid(prefix,"ring1"),375,y,48,"transparent",gold,1.8,.9))
    o.append(circle(uid(prefix,"ring2"),375,y,40,"transparent",soft,1,.7))
    o.append(textbox(uid(prefix,"letters"),330,y-17,letters,20,dark,90,"center","Cinzel",700,1.0,False,60))
    return o


def photo_window(prefix,palette,shape="arch"):
    _,bg,dark,gold,soft,white,green=palette
    o=[]
    if shape=="arch":
        o.append(path(uid(prefix,"window"),"M 180 500 L 180 270 C 180 120 570 120 570 270 L 570 500 Z",fill=soft,stroke=gold,sw=2,opacity=.32))
    else:
        o.append(rect(uid(prefix,"window"),170,140,410,300,soft,gold,2,18,.26))
    o.append(textbox(uid(prefix,"label"),230,290,"ADD YOUR PHOTO",12,dark,290,"center","Montserrat",700,1,False,100))
    return o


def front_page(idx,palette,event):
    """Build one of 100 materially different front compositions.

    V8 deliberately does NOT use colour changes as the differentiator.  The
    template index selects both a macro layout (10 choices) and a botanical /
    ornament system (10 choices), giving 100 geometry combinations.  Each
    combination changes artwork placement, frame treatment, text block shape,
    rules, monogram/photo treatment and decorative density.
    """
    pname,bg,dark,gold,soft,white,green=palette
    title_font,body_font=FONTS[(idx*3 + idx//10)%len(FONTS)]
    macro=idx//10          # 0..9: overall information architecture
    botanical=idx%10       # 0..9: artwork system
    dark_mode = idx in {1,8,10,14,19,22,27,31,35,39,42,48,51,58,61,67,70,76,82,88,91,95,99}
    base=dark if dark_mode else bg
    fg=bg if dark_mode else dark
    p=(pname,base,fg,gold,soft,white,green)
    o=[rect("background",0,0,W,H,base,editable=False)]

    # Background treatment varies structurally, not only by palette.
    bgmode=(macro+botanical)%6
    if bgmode==0:
        o += watercolor_wash("wash",p,idx)
    elif bgmode==1:
        o.append(ellipse("wash_a",120,170,175,115,soft,angle=-22,opacity=.10,editable=False))
        o.append(ellipse("wash_b",650,860,210,135,green,angle=18,opacity=.08,editable=False))
    elif bgmode==2:
        o.append(path("paper_wave","M 0 760 C 170 690 260 845 420 770 C 560 705 640 735 750 680 L 750 1050 L 0 1050 Z",fill=soft,opacity=.10,editable=False))
    elif bgmode==3:
        o.append(rect("inner_tone",42,42,666,966,white,opacity=.035,editable=False))
    elif bgmode==4:
        o.append(ellipse("halo",375,470,315,430,soft,opacity=.055,editable=False))
    else:
        o.append(path("diagonal_tone","M 0 0 L 245 0 L 0 640 Z",fill=soft,opacity=.10,editable=False))
        o.append(path("diagonal_tone_2","M 750 1050 L 505 1050 L 750 410 Z",fill=green,opacity=.07,editable=False))

    # Frame choice is intentionally de-correlated from colour and macro.
    frame_kind=["double","arch","oval","deco","lace","arch","double","oval","lace","deco"][(idx*7+macro)%10]
    o += luxury_frame("frame",p,frame_kind)

    # ------------------------------------------------------------------
    # BOTANICAL / ORNAMENT SYSTEM: ten genuinely different art structures
    # ------------------------------------------------------------------
    if botanical==0:  # asymmetrical couture corners
        o += floral_cluster("flora_tl",118,145,p,idx,.92)
        o += floral_cluster("flora_br",632,900,p,idx+7,1.02,True)
        o += foliage_spray("bridge_tl",160,245,250,green,gold,55,8)
        o += foliage_spray("bridge_br",590,800,270,green,gold,235,8,-1)
    elif botanical==1:  # abundant top canopy + falling petals
        for k,x in enumerate((95,225,375,525,655)):
            o += floral_cluster(uid("canopy",k),x,108+(k%2)*22,p,idx+k,.55,k%2==1)
        for k in range(13):
            x=95+(k*47)%570; y=220+(k*61)%265
            o.append(petal(uid("falling",k),x,y,13+(k%3)*3,4.5,soft,20+k*29,.42))
    elif botanical==2:  # vertical botanical columns
        o += foliage_spray("column_l1",78,500,760,green,gold,90,15)
        o += foliage_spray("column_l2",112,510,620,green,gold,90,12,-1)
        o += foliage_spray("column_r1",672,500,760,green,gold,90,15,-1)
        o += foliage_spray("column_r2",638,510,620,green,gold,90,12)
        for k,y in enumerate((180,390,610,825)):
            o += flower(uid("column_flower_l",k),92,y,.43,soft,gold,["rose","orchid","dahlia","magnolia"][k],k*24)
            o += flower(uid("column_flower_r",k),658,H-y,.40,white,gold,["magnolia","dahlia","orchid","rose"][k],k*31)
    elif botanical==3:  # full lower garden, no top flowers
        for k,(x,y,sc) in enumerate(((65,930,.62),(180,900,.76),(305,940,.68),(430,905,.82),(555,938,.68),(675,900,.62))):
            o += floral_cluster(uid("garden",k),x,y,p,idx+k,sc,k%2==1)
        o += foliage_spray("garden_rise_l",110,760,310,green,gold,70,9)
        o += foliage_spray("garden_rise_r",640,760,310,green,gold,110,9,-1)
    elif botanical==4:  # large floral wreath / crest
        for k,a in enumerate(range(0,360,30)):
            x=375+math.cos(math.radians(a))*250
            y=500+math.sin(math.radians(a))*355
            if k%3==0:
                o += flower(uid("wreath_flower",k),x,y,.42,soft,gold,["peony","rose","orchid","dahlia"][k%4],a)
            else:
                o.append(leaf(uid("wreath_leaf",k),x,y,52,15,green,a+90,.78,gold))
        o += monogram("wreath_mono",p,(event[1][:1]+" · "+event[1][-1:]),180)
    elif botanical==5:  # chinoiserie flowering branches
        o += foliage_spray("branch_left",135,490,770,green,gold,70,15)
        o += foliage_spray("branch_right",620,560,680,green,gold,112,14,-1)
        pts=[(105,175),(180,285),(125,430),(205,655),(625,220),(575,350),(655,535),(565,760)]
        for k,(x,y) in enumerate(pts):
            o += flower(uid("branch_bloom",k),x,y,.40+(k%3)*.06,[soft,white,"#f4c8d5"][k%3],gold,["orchid","magnolia","rose"][k%3],k*33)
    elif botanical==6:  # floral arch / garden gate
        o += foliage_spray("arch_left",150,505,700,green,gold,88,14)
        o += foliage_spray("arch_right",600,505,700,green,gold,92,14,-1)
        for k,a in enumerate((205,225,245,265,285,305,325,345)):
            x=375+math.cos(math.radians(a))*260
            y=360+math.sin(math.radians(a))*225
            o += flower(uid("arch_bloom",k),x,y,.46,soft,gold,["rose","peony","magnolia","orchid"][k%4],a)
    elif botanical==7:  # sparse editorial ikebana
        o += foliage_spray("ikebana_main",205,650,720,green,gold,70,12)
        o += foliage_spray("ikebana_cross",545,340,460,green,gold,145,9,-1)
        o += flower("ikebana_hero",170,245,1.02,soft,gold,"magnolia",-18)
        o += flower("ikebana_small",570,735,.62,white,gold,"orchid",35)
        for k in range(7):
            o.append(petal(uid("ikebana_loose",k),520+k*21,170+k*47,18,6,soft,45+k*18,.48))
    elif botanical==8:  # deco floral corners + geometric fan
        for k,(x,y,mir) in enumerate(((95,120,False),(655,120,True),(95,930,True),(655,930,False))):
            o += floral_cluster(uid("deco_corner",k),x,y,p,idx+k,.48,mir)
        for k in range(7):
            inset=115+k*15
            o.append(line(uid("deco_top",k),inset,210,W-inset,210,gold,.8,.30+k*.05))
        o.append(path("deco_diamond","M 375 118 L 430 175 L 375 232 L 320 175 Z",fill="transparent",stroke=gold,sw=1.4,opacity=.72))
    else:  # botanical mandala / lotus petals
        for ring,(rad,count,plen) in enumerate(((92,10,28),(160,14,24),(235,18,19),(310,22,15))):
            for k in range(count):
                a=k*360/count + ring*7
                x=375+math.cos(math.radians(a))*rad
                y=505+math.sin(math.radians(a))*rad*1.25
                o.append(petal(uid("lotus",ring,k),x,y,plen,7 if ring<2 else 5.5,soft,a+90,.28+ring*.08))
        o += floral_cluster("lotus_crown",375,120,p,idx,.62)

    # ------------------------------------------------------------------
    # MACRO LAYOUT: ten different typography / information architectures
    # ------------------------------------------------------------------
    kicker=event[0].upper()
    title=event[1]
    subtitle=event[2]
    date=event[3]
    venue=event[4]
    if macro==0:  # classic centered editorial
        y=330
        o += [textbox("kicker",120,y,kicker,12,gold,510,"center",body_font,700,1,False,170),
              textbox("title",90,y+62,title,48 if len(title)<20 else 39,fg,570,"center",title_font,700,1.04,False,28),
              textbox("subtitle",120,y+145,subtitle,18,fg,510,"center",title_font,400,1.2,True,10),
              line("rule",265,y+212,485,y+212,gold,1.3,.8),
              textbox("date",120,y+248,date,14,fg,510,"center",body_font,700,1.2,False,55),
              textbox("venue",120,y+296,venue,13,fg,510,"center",body_font,500,1.2,False,28)]
    elif macro==1:  # left-aligned fashion editorial
        o += [textbox("kicker",245,300,kicker,11,gold,400,"left",body_font,700,1,False,180),
              textbox("title",245,350,title,52 if len(title)<18 else 40,fg,390,"left",title_font,700,1.0,False,18),
              line("rule",245,500,560,500,gold,1.2,.75),
              textbox("subtitle",245,535,subtitle,17,fg,390,"left",title_font,400,1.25,True),
              textbox("date",245,635,date,13,fg,390,"left",body_font,700,1.3,False,35),
              textbox("venue",245,700,venue,12,fg,390,"left",body_font,500,1.35)]
    elif macro==2:  # oversized title, minimal details
        o += [textbox("kicker",110,265,kicker,11,gold,530,"center",body_font,700,1,False,220),
              textbox("title",70,335,title,62 if len(title)<17 else 45,fg,610,"center",title_font,700,.95,False,8),
              textbox("subtitle",140,500,subtitle.upper(),12,gold,470,"center",body_font,600,1.2,False,95),
              textbox("date",110,610,date,16,fg,530,"center",body_font,700,1.2,False,50),
              textbox("venue",110,662,venue,13,fg,530,"center",body_font,500,1.3,False,25)]
    elif macro==3:  # monogram + formal centered block
        o += monogram("macro_mono",p,(title[:1]+" & "+title[-1:]),275)
        o += [textbox("kicker",110,360,kicker,11,gold,530,"center",body_font,700,1,False,160),
              textbox("title",100,415,title,43,fg,550,"center",title_font,700,1.05),
              textbox("subtitle",120,492,subtitle,17,fg,510,"center",title_font,400,1.2,True),
              line("rule",290,560,460,560,gold,1.2,.8),
              textbox("date",120,600,date,14,fg,510,"center",body_font,700,1.2,False,55),
              textbox("venue",120,650,venue,13,fg,510,"center",body_font,500,1.3)]
    elif macro==4:  # split panel / asymmetric
        o.append(rect("text_panel",285,245,390,535,white,opacity=.055,editable=False))
        o.append(line("panel_rule",285,245,285,780,gold,2,.7))
        o += [textbox("kicker",330,300,kicker,11,gold,300,"left",body_font,700,1,False,160),
              textbox("title",330,355,title,43 if len(title)<18 else 34,fg,300,"left",title_font,700,1.05),
              textbox("subtitle",330,485,subtitle,16,fg,300,"left",title_font,400,1.25,True),
              textbox("date",330,590,date,13,fg,300,"left",body_font,700,1.3,False,30),
              textbox("venue",330,650,venue,12,fg,300,"left",body_font,500,1.35)]
    elif macro==5:  # circular seal composition
        o.append(ellipse("seal_outer",375,515,235,310,"transparent",gold,1.5,opacity=.72))
        o.append(ellipse("seal_inner",375,515,215,290,"transparent",soft,1.0,opacity=.60))
        o += [textbox("kicker",145,355,kicker,11,gold,460,"center",body_font,700,1,False,190),
              textbox("title",125,420,title,44 if len(title)<18 else 35,fg,500,"center",title_font,700,1.02),
              textbox("subtitle",155,520,subtitle,16,fg,440,"center",title_font,400,1.25,True),
              textbox("date",145,625,date,13,fg,460,"center",body_font,700,1.3,False,40),
              textbox("venue",145,680,venue,12,fg,460,"center",body_font,500,1.3)]
    elif macro==6:  # photo/editorial card
        o += photo_window("macro_photo",p,"arch" if botanical%2==0 else "rect")
        o += [textbox("kicker",120,525,kicker,11,gold,510,"center",body_font,700,1,False,180),
              textbox("title",95,575,title,40 if len(title)<18 else 33,fg,560,"center",title_font,700,1.05),
              textbox("date",120,690,date,13,fg,510,"center",body_font,700,1.3,False,45),
              textbox("venue",120,740,venue,12,fg,510,"center",body_font,500,1.3)]
    elif macro==7:  # tall invitation column
        o.append(rect("column_panel",210,205,330,650,white,opacity=.045,editable=False))
        o += [textbox("kicker",235,270,kicker,10,gold,280,"center",body_font,700,1,False,220),
              textbox("title",230,340,title,38 if len(title)<18 else 31,fg,290,"center",title_font,700,1.0),
              line("rule1",300,475,450,475,gold,1,.7),
              textbox("subtitle",235,510,subtitle,15,fg,280,"center",title_font,400,1.3,True),
              textbox("date",235,620,date,12,fg,280,"center",body_font,700,1.35,False,25),
              textbox("venue",235,680,venue,11,fg,280,"center",body_font,500,1.35)]
    elif macro==8:  # diagonal modern luxury
        o.append(path("slash_panel","M 145 275 L 620 210 L 605 745 L 130 810 Z",fill=white,opacity=.045,stroke=gold,sw=1.0))
        o += [textbox("kicker",175,325,kicker,11,gold,400,"left",body_font,700,1,False,170),
              textbox("title",170,385,title,47 if len(title)<18 else 36,fg,410,"left",title_font,700,1.0),
              textbox("subtitle",170,520,subtitle,16,fg,410,"left",title_font,400,1.25,True),
              line("rule",170,600,480,560,gold,1.2,.65),
              textbox("date",190,640,date,13,fg,390,"left",body_font,700,1.3,False,35),
              textbox("venue",195,700,venue,12,fg,380,"left",body_font,500,1.3)]
    else:  # formal stacked blocks with generous white space
        o += [textbox("kicker",110,245,kicker,10,gold,530,"center",body_font,700,1,False,240),
              line("top_rule",300,300,450,300,gold,1,.7),
              textbox("title",90,350,title,50 if len(title)<18 else 39,fg,570,"center",title_font,700,1.0),
              textbox("subtitle",130,475,subtitle,16,fg,490,"center",title_font,400,1.25,True),
              textbox("date",120,620,date,13,fg,510,"center",body_font,700,1.3,False,55),
              textbox("venue",120,675,venue,12,fg,510,"center",body_font,500,1.3,False,25),
              line("bottom_rule",300,755,450,755,gold,1,.7)]

    # RSVP location changes by macro so the lower portion is not repeated.
    if macro in {1,4,8}:
        o.append(textbox("rsvp",245 if macro==1 else 330 if macro==4 else 190,820 if macro!=8 else 790,
                         "RSVP · 04XX XXX XXX · hello@example.com",10,gold,390 if macro==1 else 300 if macro==4 else 390,
                         "left",body_font,600,1.2,False,18))
    else:
        o.append(textbox("rsvp",145,840,"RSVP · 04XX XXX XXX · hello@example.com",10,gold,460,"center",body_font,600,1.2,False,22))

    # Unique deterministic couture details. The number and placement differ for every index.
    o += couture_details("couture",p,idx)
    extra_count=3+(idx%8)
    for j in range(extra_count):
        x=105+((idx*53+j*83)%540); y=105+((idx*71+j*127)%820)
        if j%2:
            o.append(circle(uid("signature_pearl",idx,j),x,y,1.4+(idx+j)%3*.45,gold,opacity=.34))
        else:
            o.append(petal(uid("signature_petal",idx,j),x,y,10+(idx+j)%7,3.8,soft,(idx*17+j*41)%360,.30))
    o += gloss_layers("gloss",p,idx)
    return o

def details_page(idx,palette,event):
    pname,bg,dark,gold,soft,white,green=palette
    title_font,body_font=FONTS[(idx+2)%len(FONTS)]
    dark_mode=idx%4==1
    base=dark if dark_mode else bg
    fg=bg if dark_mode else dark
    p=(pname,base,fg,gold,soft,white,green)
    o=[rect("details_background",0,0,W,H,base,editable=False)]
    o += watercolor_wash("details_wash",p,idx+2)
    o += luxury_frame("details_frame",p,["double","arch","oval","lace"][(idx//3)%4])
    o += floral_cluster("details_top",375,125,p,idx,.72)
    o += floral_cluster("details_bottom_left",120,910,p,idx+4,.55)
    o += floral_cluster("details_bottom_right",630,910,p,idx+7,.55,True)
    o += [
        textbox("details_kicker",110,245,"THE DETAILS",12,gold,530,"center",body_font,700,1,False,160),
        textbox("details_title",110,292,event[1],36,fg,530,"center",title_font,700,1.1),
        line("details_rule1",250,380,500,380,gold,1.3,.75),
        textbox("ceremony_h",110,425,"CEREMONY",12,gold,530,"center",body_font,700,1,False,120),
        textbox("ceremony",110,458,"4:00 PM\nThe Glasshouse Garden\n18 Celebration Avenue · Victoria",17,fg,530,"center",body_font,500,1.42),
        textbox("reception_h",110,595,"RECEPTION",12,gold,530,"center",body_font,700,1,False,120),
        textbox("reception",110,628,"5:30 PM\nCocktails · Dinner · Dancing\nGrand Ballroom",17,fg,530,"center",body_font,500,1.42),
        textbox("notes_h",110,770,"DRESS & NOTES",12,gold,530,"center",body_font,700,1,False,120),
        textbox("notes",110,805,"Cocktail attire · Parking available\nPlease arrive 15 minutes early",15,fg,530,"center",body_font,500,1.4),
    ]
    o += couture_details("details_couture",p,idx+17)
    o += gloss_layers("details_gloss",p,idx)
    return o


def rsvp_page(idx,palette,event):
    pname,bg,dark,gold,soft,white,green=palette
    title_font,body_font=FONTS[(idx+4)%len(FONTS)]
    dark_mode=idx%3==0
    base=dark if dark_mode else bg
    fg=bg if dark_mode else dark
    p=(pname,base,fg,gold,soft,white,green)
    o=[rect("rsvp_background",0,0,W,H,base,editable=False)]
    o += watercolor_wash("rsvp_wash",p,idx+3)
    o += luxury_frame("rsvp_frame",p,["oval","arch","double","lace"][(idx//4)%4])
    o += floral_cluster("rsvp_top",375,130,p,idx,.72)
    o += floral_cluster("rsvp_bottom",375,920,p,idx+5,.70,True)
    o += [
        textbox("rsvp_kicker",110,280,"KINDLY REPLY",12,gold,530,"center",body_font,700,1,False,160),
        textbox("rsvp_title",110,328,"RSVP",54,fg,530,"center",title_font,700,1.0),
        textbox("rsvp_date",110,420,"Please respond by 10 October 2026",16,fg,530,"center",body_font,500,1.25),
        line("rsvp_rule",245,478,505,478,gold,1.4,.8),
        textbox("rsvp_name",145,540,"Guest name  ______________________________",15,fg,460,"left",body_font,500,1.2),
        textbox("rsvp_attend",145,606,"□ Joyfully accepts    □ Regretfully declines",15,fg,460,"left",body_font,500,1.2),
        textbox("rsvp_diet",145,672,"Dietary requirements  ____________________",15,fg,460,"left",body_font,500,1.2),
        textbox("rsvp_contact",110,790,"04XX XXX XXX\nhello@example.com\nwww.example.com/rsvp",15,gold,530,"center",body_font,650,1.45),
    ]
    o += couture_details("rsvp_couture",p,idx+31)
    o += gloss_layers("rsvp_gloss",p,idx)
    return o


def structured_event(event):
    """Portable semantic event payload kept beside the visual Fabric document."""
    event_type, title, host_line, date_line, venue_line = event
    return {
        "title": event_type + " Celebration" if event_type != "Wedding" else "Wedding Celebration",
        "host": title,
        "date": "2026-10-15",
        "time": "16:00",
        "location": {
            "venue": venue_line.split(" · ")[0].title(),
            "address": "123 Heritage Way, Melbourne VIC",
            "map_link": "https://example.com",
        },
        "dress_code": "Formal Attire",
        "rsvp_deadline": "2026-09-20",
        "message": "We look forward to celebrating with you!",
        "display": {"host_line": host_line, "date_line": date_line, "venue_line": venue_line},
    }


def couture_details(prefix, palette, idx):
    """Small editable finishing details: foil specks, pearl dots and fine rules."""
    _,bg,dark,gold,soft,white,green=palette
    o=[]
    # Fine inset rules give a clean stationery/letterpress feel.
    o.append(rect(uid(prefix,"hairline"),78,78,W-156,H-156,"transparent",gold,.65,opacity=.42))
    # Editable foil/pearl points; deterministic, no raster texture.
    for j in range(18):
        x=98 + ((j*97 + idx*31) % 554)
        y=105 + ((j*151 + idx*43) % 820)
        r=1.1 + (j%3)*.45
        o.append(circle(uid(prefix,"foil",j),x,y,r,gold,opacity=.28 + (j%4)*.08))
    # Delicate corner petals.
    for j,(x,y,a) in enumerate([(90,90,45),(660,90,135),(90,960,-45),(660,960,-135)]):
        o.append(petal(uid(prefix,"cornerpetal",j),x,y,17,5.5,soft,a,.38))
    return o


def page_count_for(idx):
    if idx < 34:
        return 1
    if idx < 67:
        return 2
    return 3


def build_template(idx, product):
    palette=PALETTES[idx%len(PALETTES)]
    event=EVENTS[(idx*7 + idx//8)%len(EVENTS)]
    count=page_count_for(idx)
    pages=[{"name":"Invitation","background":palette[1],"objects":front_page(idx,palette,event)}]
    if count>=2:
        pages.append({"name":"Details","background":palette[1],"objects":details_page(idx,palette,event)})
    if count>=3:
        pages.append({"name":"RSVP","background":palette[1],"objects":rsvp_page(idx,palette,event)})
    finish=["High-Gloss","Pearlescent","Gold-Foil Look","Soft-Touch","Satin-Lustre"][idx%5]
    design_name=DESIGN_NAMES[idx]
    name=f"ZV7 Invitation {idx+1:03d} · {design_name} · {count} Page{'s' if count>1 else ''} · {finish}"
    physical_w=float(getattr(product,"print_width_in",0) or 5)
    physical_h=float(getattr(product,"print_height_in",0) or 7)
    data={
        "version":VERSION,
        "templateType":"editable-master",
        "reconstructed":True,
        "generator":GENERATOR_ID,
        "composition_key": f"macro-{idx//10:02d}-art-{idx%10:02d}",
        "designName":design_name,
        "eventType":event[0],
        "event": structured_event(event),
        "finish":finish,
        "pageCount":count,
        "document":{"width":W,"height":H,"profile":"invitation-5x7","physical":{"widthIn":physical_w,"heightIn":physical_h}},
        "pages":copy.deepcopy(pages),
        "adminPages":copy.deepcopy(pages),
        "editable":True,
        "editorNative":True,
        "editorSchema":"fabric-primitives-v1",
        "luxuryFloralLibrary":True,
        "luxuryFloralLibraryVersion":VERSION,
        "designCode":f"zv7-inv-{idx+1:03d}",
        "source":{"type":"original-editor-native-vector-composition","note":"All visible invitation text is stored as Fabric textbox JSON objects. Floral artwork is composed from editable Fabric path/circle/ellipse/line objects. A semantic event JSON payload is stored beside the visual document. SVG is generated only as a sidecar/preview; it is never used as the editor master."},
    }
    return name,data,pages


def object_to_svg(o):
    typ=o.get("type")
    op=o.get("opacity",1)
    if typ=="rect":
        return f'<rect x="{o["left"]}" y="{o["top"]}" width="{o["width"]}" height="{o["height"]}" rx="{o.get("rx",0)}" fill="{o.get("fill","none")}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{op}"/>'
    if typ=="circle":
        r=o["radius"]; return f'<circle cx="{o["left"]+r}" cy="{o["top"]+r}" r="{r}" fill="{o.get("fill","none")}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{op}"/>'
    if typ=="ellipse":
        rx,ry=o["rx"],o["ry"]; cx=o["left"]+rx; cy=o["top"]+ry
        transform=f' transform="rotate({o.get("angle",0)} {cx} {cy})"' if o.get("angle") else ""
        return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{o.get("fill","none")}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{op}"{transform}/>'
    if typ=="line":
        x1,y1,x2,y2=o["points"]; return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{o.get("stroke","#000")}" stroke-width="{o.get("strokeWidth",1)}" opacity="{op}"/>'
    if typ=="path":
        return f'<path d="{escape(str(o.get("path","")), quote=True)}" fill="{o.get("fill","none")}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{op}"/>'
    if typ in {"text","textbox","i-text"}:
        text=escape(str(o.get("text","")))
        x=o.get("left",0); y=o.get("top",0)+o.get("fontSize",16)
        anchor="middle" if o.get("textAlign")=="center" else "start"
        if anchor=="middle": x += o.get("width",0)/2
        lines=text.split("\n")
        tsp=[]
        for n,t in enumerate(lines):
            tsp.append(f'<tspan x="{x}" dy="{0 if n==0 else o.get("fontSize",16)*o.get("lineHeight",1.2)}">{t}</tspan>')
        return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{escape(str(o.get("fontFamily") or o.get("font") or "Arial"))}" font-size="{o.get("fontSize",16)}" font-weight="{o.get("fontWeight",400)}" font-style="{o.get("fontStyle","normal")}" fill="{o.get("fill","#111")}" opacity="{op}">{"".join(tsp)}</text>'
    return ""


def svg_page(objects):
    body="".join(object_to_svg(o) for o in objects)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{body}</svg>'


def structure_signature(pages):
    # Geometry/type signature, deliberately ignoring literal text/colors.
    clean=[]
    for p in pages:
        arr=[]
        for o in p["objects"]:
            arr.append({
                "type":o.get("type"),"left":round(float(o.get("left",0)),1),"top":round(float(o.get("top",0)),1),
                "width":round(float(o.get("width",0) or 0),1),"height":round(float(o.get("height",0) or 0),1),
                "radius":round(float(o.get("radius",0) or 0),1),"rx":round(float(o.get("rx",0) or 0),1),"ry":round(float(o.get("ry",0) or 0),1),
                "path":hashlib.sha1(str(o.get("path","")).encode()).hexdigest()[:10] if o.get("path") else "",
                "points":o.get("points"),"fontSize":o.get("fontSize"),"textWidth":o.get("width") if o.get("type") in {"textbox","text","i-text"} else None,
            })
        clean.append(arr)
    return hashlib.sha256(json.dumps(clean,sort_keys=True).encode()).hexdigest()


def validate_editor_native(data):
    assert data.get("templateType")=="editable-master"
    assert data.get("reconstructed") is True
    assert data.get("pages")
    for page in data["pages"]:
        objects=page.get("objects") or []
        bad = [o for o in objects if not isinstance(o, dict)]
        if bad:
            raise ValueError(f"Page contains non-object entries: {[repr(x)[:80] for x in bad[:5]]}")
        texts=[o for o in objects if o.get("type") in {"text","textbox","i-text"}]
        if len(texts) < 5:
            raise ValueError("Page does not contain enough editable text objects")
        for t in texts:
            if t.get("customerEditable") is not True:
                raise ValueError("Text object is not customerEditable")
            if not t.get("text"):
                raise ValueError("Editable text is empty")
        forbidden=[o for o in objects if o.get("type") in {"image","group"} or o.get("exactVisualMaster") or o.get("backgroundAsset")]
        if forbidden:
            raise ValueError("Template contains image/group/master objects; V6 must be editor-native JSON")


class Command(BaseCommand):
    help="Seed 100 editor-native luxury floral invitations. JSON is the editor master; SVG is preview/sidecar only."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, required=True)
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--replace-generated", action="store_true")

    def handle(self,*args,**opts):
        count=max(1,min(100,opts["count"]))
        try:
            product=Product.objects.get(pk=opts["product_id"])
        except Product.DoesNotExist:
            raise CommandError(f"Product {opts['product_id']} not found")

        built=[]; seen=set(); composition_keys=set()
        for idx in range(count):
            name,data,pages=build_template(idx,product)
            validate_editor_native(data)
            sig=structure_signature(pages)
            key=data["composition_key"]
            if key in composition_keys:
                raise CommandError(f"Composition-family duplicate detected at template {idx+1}: {name}")
            if sig in seen:
                raise CommandError(f"Structural duplicate detected at template {idx+1}: {name}")
            composition_keys.add(key)
            seen.add(sig)
            built.append((name,data,pages))

        self.stdout.write(self.style.SUCCESS(f"Validated {len(built)} editor-native invitations; unique structures: {len(seen)}"))
        self.stdout.write("Page split: 34 × 1-page, 33 × 2-page, 33 × 3-page (for count=100)")
        self.stdout.write("Master format: editable JSON Fabric primitives. SVG is preview/sidecar only.")

        if opts["dry_run"]:
            for i,(name,data,pages) in enumerate(built,1):
                if i<=5 or i>len(built)-3:
                    txt_count=sum(1 for p in pages for o in p["objects"] if o.get("type") in {"text","textbox","i-text"})
                    obj_count=sum(len(p["objects"]) for p in pages)
                    self.stdout.write(f"{i:03d}: {name} · objects={obj_count} · editable_text={txt_count}")
            self.stdout.write(self.style.SUCCESS("Dry run complete; database unchanged."))
            return

        base_dir=Path("media")/MEDIA_DIR/str(product.pk)
        base_dir.mkdir(parents=True,exist_ok=True)

        with transaction.atomic():
            if opts["replace_generated"]:
                old=DesignTemplate.objects.filter(product=product, json_data__generator__in=[
                    "zenvibe-invitation-v6-editor-native-couture",
                    "zenvibe-invitation-v7-100-distinct-couture",
                    GENERATOR_ID,
                ])
                self.stdout.write(f"Removing prior generated V6/V7/V8 invitation batches: {old.count()}")
                old.delete()

            for idx,(name,data,pages) in enumerate(built):
                svg_files=[]
                for pno,page in enumerate(pages,1):
                    svg=svg_page(page["objects"])
                    fn=f"invitation_v8_{idx+1:03d}_page_{pno}.svg"
                    (base_dir/fn).write_text(svg,encoding="utf-8")
                    svg_files.append(f"{MEDIA_DIR}/{product.pk}/{fn}")
                data["svgFiles"]=svg_files
                data["svgUsage"]="preview-sidecar-only"

                preview_svg=svg_page(pages[0]["objects"])
                if cairosvg is not None:
                    try:
                        preview_bytes=cairosvg.svg2png(bytestring=preview_svg.encode("utf-8"),output_width=W,output_height=H)
                        preview_name=f"invitation_v8_{idx+1:03d}.png"
                    except Exception:
                        preview_bytes=preview_svg.encode("utf-8")
                        preview_name=f"invitation_v8_{idx+1:03d}.svg"
                else:
                    preview_bytes=preview_svg.encode("utf-8")
                    preview_name=f"invitation_v8_{idx+1:03d}.svg"

                obj=DesignTemplate.objects.filter(product=product, name=name).first()
                if obj is None:
                    obj=DesignTemplate(product=product,name=name)
                obj.json_data=data
                obj.is_active=True
                obj.preview.save(preview_name,ContentFile(preview_bytes),save=False)
                obj.save()

        self.stdout.write(self.style.SUCCESS(f"Imported {len(built)} ZV8 invitation templates for product {product.pk}: {product.name}"))
        self.stdout.write("Open one in the editor and double-click any heading/name/date/venue textbox; it is JSON-native editable text, not an SVG/image master.")
