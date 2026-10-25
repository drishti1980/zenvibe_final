"""Umbrella artwork library v2: safe, editable, theme-specific compositions.

The product photograph/canopy is owned by the editor; this module supplies
transparent vector overlays, not a replacement umbrella image.
"""
from __future__ import annotations
import math

THEMES = [
 ("Corporate Identity", "#155EAD", "#FFFFFF", "YOUR LOGO", "BUILD YOUR BRAND"),
 ("Wedding Celebration", "#B45377", "#FFF4E6", "OUR DAY", "FOREVER TOGETHER"),
 ("Birthday Party", "#7C3AED", "#FDE047", "CELEBRATE", "HAPPY BIRTHDAY"),
 ("Festival & Events", "#EA580C", "#FDE68A", "LIVE EVENTS", "MAKE MEMORIES"),
 ("Sports & Teams", "#047857", "#FFFFFF", "TEAM SPIRIT", "PLAY TO WIN"),
 ("Travel & Adventure", "#0284C7", "#FEF3C7", "EXPLORE", "THE WORLD AWAITS"),
 ("Botanical Garden", "#166534", "#F9A8D4", "BLOOM", "GROW WITH US"),
 ("Luxury Monogram", "#B68B45", "#FFFFFF", "YOUR BRAND", "SIGNATURE EDITION"),
 ("Photo Memories", "#DB2777", "#FFFFFF", "YOUR PHOTO", "MEMORIES FOREVER"),
 ("Community & Charity", "#0D9488", "#FEF08A", "TOGETHER", "MAKE A DIFFERENCE"),
]
COMPOSITIONS = [
 "top-banner", "bottom-banner", "left-emblem", "right-emblem",
 "twin-corners", "radial-dots", "botanical-sides", "confetti-arc",
 "split-panels", "editorial-badge",
]
CX,CY=525,500

def build_umbrella_v2(product, idx, rect, circle, text, line):
    """Return native Fabric primitives; decoration never intersects branding.

    10 distinct themes x 10 structural layouts. Brand text and all decorations
    are individually editable. Photo slots are editable labeled placeholders,
    not fabricated photographs.
    """
    theme=idx//10
    layout=idx%10
    title,primary,secondary,brand,tag=THEMES[theme]
    w,h=1050,1000
    out=[]
    used=[]
    def reserve(x,y,ww,hh):
        used.append((x,y,x+ww,y+hh))
    def overlaps(x,y,ww,hh):
        return any(x < x2+18 and x+ww > x1-18 and y < y2+18 and y+hh > y1-18
                   for x1,y1,x2,y2 in used)
    # Restrict decorations to the octagonal canopy's conservative interior.
    def safe(x,y,r=0):
        dx=abs(x-CX);dy=abs(y-CY)
        return (dx+r < 320 and dy+r < 310 and dx+dy+2*r < 460)
    def dot(key,x,y,r,color):
        if safe(x,y,r) and not overlaps(x-r,y-r,2*r,2*r):
            out.append(circle(key,x,y,r,color))
    def bar(key,x,y,ww,hh,color):
        if all(safe(px,py) for px,py in [(x,y),(x+ww,y),(x,y+hh),(x+ww,y+hh)]) and not overlaps(x,y,ww,hh):
            out.append(rect(key,x,y,ww,hh,color))
    # Ten structurally distinct positions, with generous non-overlap margins.
    positions=[
        (365,295,320,78),(365,610,320,78),(395,365,260,90),
        (395,540,260,90),(355,445,340,90),(370,380,310,90),
        (370,480,310,90),(370,335,310,90),(365,555,320,90),
        (365,430,320,90),
    ]
    x,y,ww,hh=positions[layout]
    reserve(x-14,y-18,ww+28,hh+96)
    # High-contrast editable brand label with a backing plaque.
    out.append(rect("brand_plaque",x-10,y-8,ww+20,hh+18,primary))
    out.append(text("brand",x+12,y+7,ww-24,brand,29,secondary,"800","center"))
    out.append(text("tagline",x+12,y+48,ww-24,tag,15,secondary,"600","center"))
    # Different decorative geometry and positioning per composition.
    anchors=[
      [(285,570),(760,570),(315,710),(730,710)],
      [(295,310),(750,310),(325,220),(715,220)],
      [(650,290),(690,620),(740,480)],
      [(310,290),(345,650),(270,480)],
      [(280,305),(765,685),(350,250),(700,735)],
      [(285,300),(755,310),(300,690),(755,690)],
      [(280,300),(745,310),(280,690),(745,690)],
      [(300,620),(745,615),(525,715)],
      [(295,290),(755,290),(300,715),(750,715)],
      [(290,290),(750,290),(290,710),(750,710)],
    ][layout]
    for j,(ax,ay) in enumerate(anchors):
        if theme==6:  # Botanical leaves / flowers
            dot(f"petal_{j}_a",ax-18,ay,15,secondary)
            dot(f"petal_{j}_b",ax+18,ay,15,secondary)
            dot(f"petal_{j}_c",ax,ay-18,15,secondary)
            dot(f"petal_{j}_d",ax,ay+18,15,secondary)
            dot(f"flower_{j}",ax,ay,10,primary)
        elif theme==2 or theme==3:  # Events / birthday
            dot(f"confetti_{j}",ax,ay,13,secondary)
            dot(f"confetti_alt_{j}",ax+35,ay-23,8,primary)
        elif theme==4:  # Sport: concentric ball marks
            dot(f"sport_outer_{j}",ax,ay,27,secondary)
            dot(f"sport_core_{j}",ax,ay,16,primary)
        elif theme==5:  # Travel: compass markers
            dot(f"compass_{j}",ax,ay,24,secondary)
            dot(f"compass_core_{j}",ax,ay,8,primary)
        elif theme==1:  # Wedding pearls
            dot(f"pearl_{j}",ax,ay,23,secondary)
            dot(f"pearl_center_{j}",ax,ay,9,primary)
        elif theme==8:  # Photo placeholders
            if safe(ax,ay,35) and not overlaps(ax-36,ay-30,72,60):
                out.append(rect(f"photo_slot_{j}",ax-36,ay-30,72,60,secondary,primary,3))
                out.append(text(f"photo_label_{j}",ax-32,ay-8,64,"PHOTO",12,primary,"700"))
        elif theme==7:  # Gold luxury seals
            dot(f"lux_seal_{j}",ax,ay,29,primary)
            dot(f"lux_core_{j}",ax,ay,18,secondary)
        elif theme==9:  # Community / charity
            dot(f"community_{j}",ax,ay,24,secondary)
            dot(f"community_center_{j}",ax,ay,10,primary)
        else:  # Corporate identity
            bar(f"identity_mark_{j}",ax-20,ay-15,40,30,secondary)
    # Add a small theme identifier only where it has its own clear region.
    foot_y=750 if y < 500 else 250
    if not overlaps(405,foot_y,240,34) and safe(525,foot_y+15,120):
        out.append(text("collection_caption",405,foot_y,240,title.upper(),17,secondary,"700"))
    for i,obj in enumerate(out):
        obj["id"]=f"umbrella_{idx+1:03d}_{i:03d}"
        obj["customerEditable"]=True
        obj["selectable"]=True
        obj["evented"]=True
    return w,h,out
