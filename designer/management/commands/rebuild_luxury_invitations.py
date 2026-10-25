from __future__ import annotations

import copy
import hashlib
import io
import json
import os
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
GENERATOR_ID = "zenvibe-invitation-v4-luxury-floral"
MEDIA_DIR = "generated_invitation_templates_v4"

EVENTS = [
    ("Wedding", "OLIVIA & ETHAN", "Together with their families", "SATURDAY · 18 OCTOBER 2026", "THE GLASSHOUSE · MELBOURNE"),
    ("Engagement", "AMELIA & NOAH", "Celebrate our engagement", "FRIDAY · 06 NOVEMBER 2026", "THE TERRACE · GEELONG"),
    ("Birthday", "SOPHIA TURNS 30", "Dinner · Drinks · Dancing", "SATURDAY · 24 OCTOBER 2026", "THE GARDEN ROOM · 7:00 PM"),
    ("Baby Shower", "BABY IN BLOOM", "Honouring Sarah & baby", "SUNDAY · 08 NOVEMBER 2026", "WILLOW HOUSE · 2:00 PM"),
    ("Bridal Shower", "BRIDAL BRUNCH", "Showering Emma with love", "SUNDAY · 01 NOVEMBER 2026", "THE CONSERVATORY · 11:00 AM"),
    ("Anniversary", "25 YEARS", "Celebrating Mia & Daniel", "SATURDAY · 14 NOVEMBER 2026", "GRAND BALLROOM · 6:30 PM"),
    ("Graduation", "CLASS OF 2026", "Celebrate William's graduation", "FRIDAY · 20 NOVEMBER 2026", "HARBOUR HALL · 6:00 PM"),
    ("Corporate", "AN EVENING WITH ZENVIBE", "Client appreciation reception", "THURSDAY · 29 OCTOBER 2026", "WATERFRONT PAVILION · 6:00 PM"),
    ("Housewarming", "NEW HOME · NEW MEMORIES", "Come celebrate with us", "SUNDAY · 15 NOVEMBER 2026", "18 GARDEN AVENUE · 3:00 PM"),
    ("Kids", "MILA TURNS FIVE", "Cake · Games · Big smiles", "SUNDAY · 22 NOVEMBER 2026", "RAINBOW ROOM · 1:00 PM"),
]

PALETTES = [
    ("Ivory Gold", "#fffaf0", "#202020", "#c8a04a", "#efe0b8", "#ffffff"),
    ("Emerald Champagne", "#0d3b33", "#fffaf2", "#d1ae62", "#295e52", "#f9f2df"),
    ("Midnight Sapphire", "#101d4a", "#fffdf8", "#e6b95e", "#274383", "#eaf0ff"),
    ("Ruby Rose Gold", "#6f1737", "#fff8f6", "#d49a88", "#a94463", "#f8d7dd"),
    ("Orchid Plum", "#44205b", "#fff9ff", "#e3b7e8", "#743d8b", "#f3ddf5"),
    ("Aqua Gold", "#16a6a8", "#fffdfa", "#e7c369", "#55c9c5", "#dff7f6"),
    ("Cobalt Coral", "#2349a6", "#fffaf7", "#ff7b6c", "#5e7bd0", "#ffe4df"),
    ("Fuchsia Champagne", "#a91f6a", "#fffaf5", "#e1be74", "#d94993", "#fde0ee"),
    ("Forest Antique Gold", "#1e5037", "#fffaf0", "#b9954f", "#548465", "#e4f1e7"),
    ("Terracotta Cream", "#b85f46", "#fff9f1", "#f0b06a", "#dd8c72", "#f8e0d3"),
    ("Black Pearl", "#111111", "#fbf8ef", "#d3c49b", "#333333", "#f1eee6"),
    ("Peacock Teal", "#004b55", "#fffdf7", "#d9a84f", "#11808c", "#d9f1f1"),
    ("Lavender Silver", "#76558d", "#fffaff", "#d8d2e7", "#9f83b0", "#eee6f4"),
    ("Sunset Peach", "#f06f5f", "#fff9f4", "#f4c05d", "#f6977d", "#ffe2d5"),
    ("Mint Emerald", "#dff6ec", "#10372f", "#2a8b73", "#8fd0b8", "#ffffff"),
    ("Royal Aubergine", "#31133e", "#fffaf4", "#e0b35b", "#5d2b70", "#f0ddf2"),
    ("Azure White", "#e9f5ff", "#183756", "#3f8fd2", "#a8d6f8", "#ffffff"),
    ("Blush Burgundy", "#fff0f0", "#6f1f2f", "#c0767f", "#ecc3c8", "#ffffff"),
    ("Lemon Navy", "#fff4a8", "#18274b", "#e7b841", "#f8df67", "#fffbed"),
    ("Teal Magenta", "#073c42", "#fff8fb", "#e53d92", "#176e73", "#ffd9eb"),
]

FONTS = ["Cormorant Garamond", "Playfair Display", "Cinzel", "Libre Baskerville", "DM Serif Display", "Montserrat", "DM Sans", "Georgia"]

THEMES = [
    "watercolor_rose", "botanical_vine", "gold_leaf", "art_deco", "arabesque", "mandala", "lace", "double_arch",
    "oval_cameo", "ribbon", "celestial", "confetti", "rainbow_kids", "photo_window", "chinoiserie", "paisley",
    "marble", "terrazzo", "tropical", "vintage_rose", "winter_floral", "festive_luxe", "graduation_seal", "corporate_minimal",
    "peony_frame", "orchid_line", "sunflower", "eucalyptus", "wildflower", "magnolia", "lotus", "fern", "olive_branch",
    "geometric_fan", "moroccan_tile", "stained_glass", "royal_crest", "velvet_border", "foil_corner", "pearl_frame",
    "modern_wave", "color_block", "editorial_serif", "minimal_script", "gilded_column", "monogram_house", "garden_gate",
    "scallop_frame", "bow_luxe", "champagne_bubbles",
]

LAYOUTS = ["centered", "top_heavy", "bottom_heavy", "left_editorial", "split", "arch_center", "frame_center", "asymmetric", "seal_center", "column"]

DESIGN_NAMES = [
    "Rosewater Gold Garden", "Emerald Vine Romance", "Ivory Gilded Leaves", "Midnight Art Deco Gala", "Ruby Arabesque Estate",
    "Orchid Mandala Celebration", "Pearl Lace Invitation", "Sapphire Double Arch", "Blush Oval Cameo", "Champagne Ribbon House",
    "Celestial Navy Gold", "Bright Confetti Soiree", "Rainbow Birthday Joy", "Editorial Photo Window", "Blue Chinoiserie Garden",
    "Aubergine Paisley Court", "Marble Gold Atelier", "Coral Terrazzo Party", "Tropical Emerald Palm", "Vintage Rose Manor",
    "Winter Pearl Botanica", "Festive Jewel Luxe", "Graduation Gold Seal", "Corporate Ivory Minimal", "Peony Champagne Frame",
    "Orchid Fine Line", "Sunflower Summer", "Eucalyptus Sage", "Wildflower Meadow", "Magnolia Ivory",
    "Lotus Rose Gold", "Fern Forest", "Olive Branch Classic", "Geometric Fan Couture", "Moroccan Tile Gold",
    "Stained Glass Jewel", "Royal Crest Black Gold", "Velvet Burgundy Border", "Foil Corner Minimal", "Pearl Double Frame",
    "Modern Aqua Wave", "Cobalt Coral Block", "Editorial Serif Cream", "Minimal Script Blush", "Gilded Column Navy",
    "Monogram Estate Emerald", "Garden Gate Ivory", "Scallop Pink Pearl", "Luxury Bow Champagne", "Champagne Bubble Black",
    "Rosewater Botanical Arch", "Emerald Vine Column", "Gold Leaf Oval", "Deco Burgundy Frame", "Arabesque Sapphire",
    "Mandala Fuchsia Gold", "Lace Lavender Garden", "Double Arch Terracotta", "Cameo Mint Estate", "Ribbon Black Pearl",
    "Celestial Aubergine", "Confetti Cobalt", "Kids Pastel Rainbow", "Photo Blush Gallery", "Chinoiserie Peacock",
    "Paisley Emerald", "Marble Ruby Gold", "Terrazzo Aqua", "Tropical Sunset", "Vintage Rose Champagne",
    "Winter Sapphire Silver", "Festive Ruby Gold", "Graduation Navy Crest", "Corporate Teal Editorial", "Peony Blush Arch",
    "Orchid Plum Gallery", "Sunflower Navy", "Eucalyptus Ivory", "Wildflower Lavender", "Magnolia Emerald",
    "Lotus Midnight", "Fern Pearl", "Olive Branch Burgundy", "Geometric Gold Fan", "Moroccan Teal Tile",
    "Stained Glass Plum", "Royal Crest Emerald", "Velvet Black Gold", "Foil Corner Cobalt", "Pearl Frame Rose",
    "Modern Wave Magenta", "Color Block Lemon Navy", "Editorial Cream Gold", "Minimal Script Aqua", "Gilded Column Forest",
    "Monogram Ruby Estate", "Garden Gate Lavender", "Scallop Mint", "Bow Fuchsia Champagne", "Champagne Bubble Sapphire",
]


def rect(i, x, y, w, h, fill, opacity=1, angle=0, rx=0, stroke=None, sw=0):
    d = {"id": i, "name": i.replace("_", " ").title(), "type": "rect", "left": round(x,2), "top": round(y,2), "width": round(w,2), "height": round(h,2), "fill": fill, "opacity": opacity, "angle": angle, "rx": rx, "ry": rx, "customerEditable": True}
    if stroke: d.update(stroke=stroke, strokeWidth=sw or 2)
    return d

def circle(i, cx, cy, r, fill, opacity=1, stroke=None, sw=0):
    d={"id":i,"name":i.replace("_"," ").title(),"type":"circle","left":round(cx-r,2),"top":round(cy-r,2),"radius":round(r,2),"fill":fill,"opacity":opacity,"customerEditable":True}
    if stroke: d.update(stroke=stroke, strokeWidth=sw or 2)
    return d

def ellipse(i, cx, cy, rx, ry, fill, opacity=1, stroke=None, sw=0):
    d={"id":i,"name":i.replace("_"," ").title(),"type":"ellipse","left":round(cx-rx,2),"top":round(cy-ry,2),"rx":round(rx,2),"ry":round(ry,2),"fill":fill,"opacity":opacity,"customerEditable":True}
    if stroke: d.update(stroke=stroke, strokeWidth=sw or 2)
    return d

def line(i,x1,y1,x2,y2,stroke,sw=2,opacity=1):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"line","left":0,"top":0,"points":[x1,y1,x2,y2],"stroke":stroke,"strokeWidth":sw,"opacity":opacity,"fill":None,"customerEditable":True}

def polygon(i, pts, fill, opacity=1, stroke=None, sw=0):
    d={"id":i,"name":i.replace("_"," ").title(),"type":"polygon","left":0,"top":0,"points":pts,"fill":fill,"opacity":opacity,"customerEditable":True}
    if stroke: d.update(stroke=stroke, strokeWidth=sw or 2)
    return d

def path(i, svg_path, fill="transparent", stroke="#111", sw=2, opacity=1):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"path","left":0,"top":0,"path":svg_path,"fill":fill,"stroke":stroke,"strokeWidth":sw,"opacity":opacity,"customerEditable":True}

def txt(i,x,y,s,fs,fill,weight=400,width=None,align="left",font="Playfair Display",lh=1.15,italic=False):
    d={"id":i,"name":i.replace("_"," ").title(),"type":"text","left":round(x,2),"top":round(y,2),"text":s,"fontSize":fs,"font":font,"fontWeight":weight,"fill":fill,"textAlign":align,"lineHeight":lh,"customerEditable":True}
    if width is not None: d["width"]=round(width,2)
    if italic: d["fontStyle"]="italic"
    return d

def leaf(prefix,x,y,sx,sy,fill,angle=0,opacity=1):
    pts=[{"x":x,"y":y+sy/2},{"x":x+sx/2,"y":y},{"x":x+sx,"y":y+sy/2},{"x":x+sx/2,"y":y+sy}]
    d=polygon(prefix,pts,fill,opacity); d["angle"]=angle; return d

def flower(prefix,cx,cy,accent,soft,scale=1):
    out=[]
    for n,(dx,dy) in enumerate([(0,-24),(22,-7),(14,20),(-14,20),(-22,-7)]): out.append(circle(f"{prefix}_petal{n}",cx+dx*scale,cy+dy*scale,18*scale,soft,.88))
    out.append(circle(prefix+"_centre",cx,cy,9*scale,accent,1))
    return out

def vine(prefix,x1,y1,x2,y2,accent,soft,mirror=False):
    s=-1 if mirror else 1
    out=[path(prefix+"_stem",f"M {x1} {y1} C {x1+80*s} {y1+40}, {x2-70*s} {y2-60}, {x2} {y2}","transparent",accent,2,.7)]
    for n,t in enumerate([.18,.36,.55,.72,.88]):
        x=x1+(x2-x1)*t; y=y1+(y2-y1)*t
        out.append(leaf(f"{prefix}_leaf{n}",x,y,34*s if s>0 else 34,18,accent,(-25+12*n)*s,.78))
    return out

def arch(prefix,x,y,w,h,stroke,sw=3,fill="transparent"):
    p=f"M {x} {y+h} L {x} {y+h*0.42} C {x} {y}, {x+w} {y}, {x+w} {y+h*0.42} L {x+w} {y+h} Z"
    return path(prefix,p,fill,stroke,sw,1)

def title_block(event,dark,accent,y=330,layout="centered"):
    kind,title,kicker,date,venue=event
    if layout in ("left_editorial","column"):
        x=105; w=520; align="left"
    else:
        x=90; w=570; align="center"
    return [
        txt("kicker",x,y,kicker.upper(),17,accent,650,w,align,"Montserrat"),
        txt("headline",x,y+55,title,48,dark,700,w,align,"Cormorant Garamond",1.0),
        txt("date",x,y+190,date,19,dark,600,w,align,"DM Sans"),
        txt("venue",x,y+235,venue,17,dark,500,w,align,"DM Sans"),
        txt("rsvp",x,y+305,"RSVP · 04XX XXX XXX · hello@example.com",14,accent,650,w,align,"DM Sans"),
    ]

def motif_objects(theme, palette, idx):
    _,bg,dark,accent,soft,white=palette
    o=[]
    if theme=="watercolor_rose":
        o += [ellipse("wash1",120,120,150,95,soft,.38),ellipse("wash2",645,910,160,105,accent,.13)]
        o += flower("rose1",95,130,accent,soft,1.35)+flower("rose2",660,900,accent,soft,1.2)
        o += vine("vine1",45,170,230,350,accent,soft)+vine("vine2",705,870,520,690,accent,soft,True)
    elif theme=="botanical_vine":
        o += vine("lv",40,80,245,360,accent,soft)+vine("rv",710,970,500,690,accent,soft,True)
        o += [line("top_rule",130,90,620,90,accent,2,.8),line("bottom_rule",130,955,620,955,accent,2,.8)]
    elif theme=="gold_leaf":
        for n in range(8):
            o.append(leaf(f"gl{n}",55+n*45,70+n%2*18,42,20,accent,(-18+n*6),.9))
            o.append(leaf(f"gr{n}",650-n*40,930-n%2*18,42,20,accent,(18-n*5),.75))
    elif theme=="art_deco":
        o += [rect("deco_outer",45,45,660,960,"transparent",1,0,0,accent,3),rect("deco_inner",65,65,620,920,"transparent",1,0,0,soft,1)]
        for x in (110,640): o += [line(f"deco{x}a",x,45,x+70,135,accent,3),line(f"deco{x}b",x+70,135,x,225,accent,3)]
    elif theme=="arabesque":
        o += [path("arab1","M 70 180 C 160 80, 250 80, 330 170 C 410 260, 500 260, 680 120","transparent",accent,3,.8),path("arab2","M 70 870 C 180 980, 280 980, 360 880 C 450 770, 560 790, 680 930","transparent",accent,3,.8)]
        for cx,cy in [(110,140),(640,900),(620,155),(130,890)]: o+=flower(f"af{cx}",cx,cy,accent,soft,.65)
    elif theme=="mandala":
        for r,sw,op in [(210,3,.7),(165,2,.6),(120,2,.55),(72,2,.5)]: o.append(circle(f"mandala{r}",375,250,r,"transparent",op,accent,sw))
        for a,(cx,cy) in enumerate([(375,40),(560,120),(585,320),(375,460),(165,320),(190,120)]): o.append(ellipse(f"pet{a}",cx,cy,26,48,soft,.35,accent,2))
    elif theme=="lace":
        o += [rect("lace_frame",50,50,650,950,"transparent",1,0,22,accent,2)]
        for n in range(18):
            o.append(circle(f"lace_t{n}",70+n*36,65,7,soft,1,accent,1)); o.append(circle(f"lace_b{n}",70+n*36,985,7,soft,1,accent,1))
    elif theme=="double_arch":
        o += [arch("arch1",90,95,570,820,accent,4),arch("arch2",120,125,510,760,soft,2)]
    elif theme=="oval_cameo":
        o += [ellipse("oval1",375,360,245,300,"transparent",1,accent,3),ellipse("oval2",375,360,220,275,"transparent",1,soft,2)]
        o += flower("of1",180,170,accent,soft,.8)+flower("of2",570,565,accent,soft,.8)
    elif theme=="ribbon":
        o += [polygon("rib1",[{"x":0,"y":170},{"x":750,"y":70},{"x":750,"y":190},{"x":0,"y":290}],accent,.9),polygon("rib2",[{"x":0,"y":810},{"x":750,"y":720},{"x":750,"y":850},{"x":0,"y":940}],soft,.55)]
    elif theme=="celestial":
        o += [circle("moon",375,210,120,dark,1),circle("mooncut",420,175,120,bg,1)]
        for n,(x,y,r) in enumerate([(130,120,5),(610,145,4),(170,300,3),(620,320,5),(290,90,3),(510,80,4)]): o.append(circle(f"star{n}",x,y,r,accent,1))
    elif theme=="confetti":
        colors=[accent,soft,dark]
        for n in range(34):
            x=35+(n*73)%680; y=45+(n*97)%930
            if n%2:o.append(circle(f"cf{n}",x,y,4+n%5,colors[n%3],.75))
            else:o.append(rect(f"cf{n}",x,y,8,22,colors[n%3],.75,angle=(n*17)%70-35))
    elif theme=="rainbow_kids":
        for n,c in enumerate(["#ff6b6b","#ffd93d","#6bcb77","#4d96ff","#b983ff"]): o.append(arch(f"rain{n}",120+n*18,80+n*18,510-n*36,330-n*20,c,14))
        o += [circle("cloud1",160,310,55,"#ffffff",.95),circle("cloud2",205,300,42,"#ffffff",.95),circle("cloud3",595,315,58,"#ffffff",.95)]
    elif theme=="photo_window":
        o += [rect("photo",90,80,570,420,soft,.25,0,20,accent,3),txt("photo_label",90,270,"YOUR PHOTO",26,accent,700,570,"center","Montserrat")]
    elif theme=="chinoiserie":
        o += [rect("ch_frame",50,50,650,950,"transparent",1,0,8,accent,3)]
        o += vine("chv1",40,140,260,380,accent,soft)+vine("chv2",710,900,500,650,accent,soft,True)
        for cx,cy in [(120,190),(640,820),(595,190),(150,840)]: o+=flower(f"ch{cx}",cx,cy,accent,soft,.7)
    elif theme=="paisley":
        o += [path("pa1","M 70 220 C 180 80, 300 90, 250 240 C 220 330, 100 340, 120 440 C 175 365, 245 365, 285 430","transparent",accent,4,.8),path("pa2","M 680 830 C 560 980, 450 960, 495 810 C 525 700, 655 700, 625 605 C 585 670, 520 665, 470 610","transparent",accent,4,.8)]
    elif theme=="marble":
        for n in range(7): o.append(path(f"mar{n}",f"M {-50+n*110} {120+n*30} C {180+n*60} {30+n*45}, {420-n*35} {280+n*20}, {800-n*20} {160+n*60}","transparent",soft if n%2 else accent,3,.28))
    elif theme=="terrazzo":
        colors=[accent,soft,dark,"#ffffff"]
        for n in range(26):
            x=30+(n*101)%700;y=55+(n*137)%930
            o.append(polygon(f"tz{n}",[{"x":x,"y":y},{"x":x+18+n%12,"y":y+4},{"x":x+12,"y":y+22+n%9},{"x":x-4,"y":y+14}],colors[n%4],.35))
    elif theme=="tropical":
        for n,(x,y,a) in enumerate([(50,80,20),(115,110,-15),(625,830,165),(675,900,195),(80,900,-35)]): o.append(leaf(f"tp{n}",x,y,130,45,accent,a,.78))
    elif theme=="vintage_rose":
        o += [rect("vr1",45,45,660,960,"transparent",1,0,0,accent,2),rect("vr2",62,62,626,926,"transparent",1,0,0,soft,1)]
        o += flower("vrf1",90,110,accent,soft,1.1)+flower("vrf2",655,925,accent,soft,1.1)
    elif theme=="winter_floral":
        for n,(x,y) in enumerate([(110,120),(170,85),(600,120),(650,85),(120,920),(640,920)]):
            o += flower(f"wf{n}",x,y,"#cfd8e3","#ffffff",.8); o.append(leaf(f"wfl{n}",x+15,y+15,48,18,accent,20,.5))
    elif theme=="festive_luxe":
        o += [rect("fest_top",0,0,W,240,dark),rect("fest_bottom",0,880,W,170,dark),line("fest_gold",0,240,W,240,accent,6),line("fest_gold2",0,880,W,880,accent,6)]
        for n in range(12): o.append(circle(f"spark{n}",60+n*58,120+(n%3)*22,4+(n%4),accent,.9))
    elif theme=="graduation_seal":
        o += [circle("seal1",375,240,150,"transparent",1,accent,5),circle("seal2",375,240,120,"transparent",1,soft,3),txt("sealcap",250,205,"CLASS OF\n2026",44,dark,750,250,"center","Cinzel")]
    elif theme=="corporate_minimal":
        o += [rect("corp_bar",0,0,95,H,accent),line("corp_rule",130,155,650,155,dark,2,.5),line("corp_rule2",130,865,650,865,dark,2,.5)]
    elif theme=="peony_frame":
        o += flower("pf1",90,95,accent,soft,1.4)+flower("pf2",650,105,accent,soft,1.2)+flower("pf3",95,945,accent,soft,1.2)+flower("pf4",645,930,accent,soft,1.4)
    elif theme=="orchid_line":
        o += [path("orchstem","M 100 900 C 180 690, 100 500, 260 250","transparent",accent,3,.7),path("orchstem2","M 650 120 C 560 310, 650 500, 510 760","transparent",accent,3,.6)]
        for n,(x,y) in enumerate([(165,650),(210,520),(225,360),(580,300),(560,450),(535,610)]): o += flower(f"or{n}",x,y,accent,soft,.55)
    elif theme=="sunflower":
        for cx,cy in [(120,130),(640,900)]:
            for n in range(12): o.append(ellipse(f"sf{cx}_{n}",cx,cy,16,42,"#f4c542",.9))
            o.append(circle(f"sfc{cx}",cx,cy,22,"#7c4a20",1))
    elif theme=="eucalyptus":
        o += vine("eu1",40,100,270,380,accent,soft)+vine("eu2",710,900,480,670,accent,soft,True)
        for n in range(7): o.append(circle(f"eub{n}",80+n*90,85+n%2*18,8,soft,.9))
    elif theme=="wildflower":
        for n in range(16):
            x=55+n*43; h=50+(n%5)*22
            o.append(line(f"stem{n}",x,980,x,980-h,accent,2,.55)); o += flower(f"wflo{n}",x,980-h,accent,soft,.33)
    elif theme=="magnolia":
        o += flower("mag1",115,160,accent,"#fff6f2",1.55)+flower("mag2",610,860,accent,"#fff6f2",1.45)+vine("magv",55,185,250,390,accent,soft)
    elif theme=="lotus":
        for cy in [170,880]:
            for n,dx in enumerate([-90,-55,-20,20,55,90]): o.append(ellipse(f"lot{cy}_{n}",375+dx,cy,28,70,soft,.55,accent,2))
    elif theme=="fern":
        o += [line("fern1",80,80,250,380,accent,3,.7),line("fern2",670,970,500,680,accent,3,.7)]
        for n in range(10):
            o.append(leaf(f"fern1_{n}",95+n*13,105+n*24,45,14,accent,-35,.7)); o.append(leaf(f"fern2_{n}",610-n*13,885-n*20,45,14,accent,145,.7))
    elif theme=="olive_branch":
        o += vine("ol1",80,120,290,270,accent,soft)+vine("ol2",670,900,460,760,accent,soft,True)
        for n in range(8): o.append(ellipse(f"olive{n}",110+n*35,135+n*18,9,14,"#6e7f45",.8))
    elif theme=="geometric_fan":
        for n in range(9): o.append(polygon(f"fan{n}",[{"x":375,"y":80},{"x":40+n*84,"y":360},{"x":80+n*78,"y":390}],accent if n%2==0 else soft,.35))
    elif theme=="moroccan_tile":
        for row in range(5):
            for col in range(4):
                cx=95+col*185; cy=110+row*205
                o.append(polygon(f"mt{row}_{col}",[{"x":cx,"y":cy-36},{"x":cx+36,"y":cy},{"x":cx,"y":cy+36},{"x":cx-36,"y":cy}],"transparent",1,accent,2))
    elif theme=="stained_glass":
        colors=[accent,soft,"#d8f3dc","#ffd6e0"]
        for n in range(10): o.append(polygon(f"sg{n}",[{"x":n*75,"y":0},{"x":n*75+180,"y":0},{"x":n*75+80,"y":280},{"x":n*75-20,"y":220}],colors[n%4],.35))
    elif theme=="royal_crest":
        o += [circle("crest",375,210,100,"transparent",1,accent,5),txt("crest_m",305,150,"ZV",58,accent,700,140,"center","Cinzel"),line("crest_l",240,315,510,315,accent,2)]
    elif theme=="velvet_border":
        o += [rect("velvet_outer",0,0,W,H,dark),rect("velvet_inner",45,45,660,960,bg,1,0,10,accent,3)]
    elif theme=="foil_corner":
        o += [polygon("fc1",[{"x":0,"y":0},{"x":300,"y":0},{"x":0,"y":300}],accent,.9),polygon("fc2",[{"x":750,"y":1050},{"x":450,"y":1050},{"x":750,"y":750}],accent,.55)]
    elif theme=="pearl_frame":
        o += [rect("pf_outer",50,50,650,950,"transparent",1,0,16,accent,3)]
        for n in range(18): o.append(circle(f"pearl{n}",75+n*35,65,5,"#fff",1,accent,1))
    elif theme=="modern_wave":
        o += [path("wave1","M -20 170 C 160 40, 300 300, 770 120 L 770 0 L -20 0 Z",accent,accent,0,.35),path("wave2","M -20 910 C 180 760, 420 1030, 770 820 L 770 1050 L -20 1050 Z",soft,soft,0,.45)]
    elif theme=="color_block":
        o += [rect("cb1",0,0,240,H,accent),rect("cb2",240,0,120,H,soft,.8),rect("cb3",360,0,390,H,bg)]
    elif theme=="editorial_serif":
        o += [line("ed_top",80,125,670,125,accent,2),line("ed_mid",80,420,670,420,soft,2),txt("edition",85,90,"PRIVATE EDITION · 2026",13,accent,700,580,"center","Montserrat")]
    elif theme=="minimal_script":
        o += [ellipse("ms_blob",620,130,190,110,soft,.25),line("ms_rule",150,730,600,730,accent,2,.6)]
    elif theme=="gilded_column":
        o += [rect("gc_col",0,0,135,H,dark),rect("gc_gold",135,0,14,H,accent),txt("gc_mono",25,390,"Z\nE\nN",36,bg,700,80,"center","Cinzel")]
    elif theme=="monogram_house":
        o += [rect("mh_frame",65,70,620,910,"transparent",1,0,0,accent,2),circle("mh_c",375,220,85,"transparent",1,accent,3),txt("mh_t",315,175,"OE",46,accent,700,120,"center","Cinzel")]
    elif theme=="garden_gate":
        o += [arch("gg1",85,80,580,850,accent,3),arch("gg2",115,110,520,790,soft,2)]
        o += vine("ggv1",70,170,220,350,accent,soft)+vine("ggv2",680,850,530,650,accent,soft,True)
    elif theme=="scallop_frame":
        for n in range(12):
            o.append(circle(f"sc_t{n}",60+n*58,62,28,bg,1,accent,2)); o.append(circle(f"sc_b{n}",60+n*58,988,28,bg,1,accent,2))
        o += [line("sc_l",45,85,45,965,accent,2),line("sc_r",705,85,705,965,accent,2)]
    elif theme=="bow_luxe":
        o += [ellipse("bow_l",300,160,100,55,soft,.8,accent,2),ellipse("bow_r",450,160,100,55,soft,.8,accent,2),circle("bow_c",375,160,28,accent,1),polygon("tail1",[{"x":350,"y":180},{"x":300,"y":380},{"x":370,"y":300}],accent,.5),polygon("tail2",[{"x":400,"y":180},{"x":450,"y":380},{"x":380,"y":300}],accent,.5)]
    elif theme=="champagne_bubbles":
        for n in range(28):
            x=40+(n*89)%680; y=45+(n*131)%930; r=4+(n%7)*4
            o.append(circle(f"bub{n}",x,y,r,"transparent",.7,accent,1+(n%3)))
    return o

def layout_adjust(objects, layout, event, palette):
    _,bg,dark,accent,soft,white=palette
    if layout=="centered": return objects + title_block(event,dark,accent,330,"centered")
    if layout=="top_heavy": return objects + title_block(event,dark,accent,480,"centered")
    if layout=="bottom_heavy": return objects + title_block(event,dark,accent,210,"centered")
    if layout=="left_editorial": return objects + title_block(event,dark,accent,300,"left_editorial")
    if layout=="split":
        objects += [rect("split_panel",0,0,260,H,dark,.96),rect("split_rule",260,0,12,H,accent)]
        return objects + [txt("split_brand",55,470,event[0].upper(),22,bg,700,150,"center","Cinzel")] + title_block(event,dark,accent,300,"left_editorial")
    if layout=="arch_center": return objects + [arch("layout_arch",95,165,560,710,accent,2)] + title_block(event,dark,accent,330,"centered")
    if layout=="frame_center": return objects + [rect("layout_frame",75,120,600,810,"transparent",1,0,16,accent,2)] + title_block(event,dark,accent,340,"centered")
    if layout=="asymmetric": return objects + [ellipse("asym_blob",625,330,160,280,soft,.18),rect("asym_rule",95,250,460,6,accent)] + title_block(event,dark,accent,305,"left_editorial")
    if layout=="seal_center": return objects + [circle("layout_seal",375,245,95,"transparent",1,accent,3),txt("layout_seal_t",310,210,event[0][:2].upper(),40,accent,700,130,"center","Cinzel")] + title_block(event,dark,accent,390,"centered")
    return objects + [rect("col_bg",0,0,120,H,dark),rect("col_gold",120,0,10,H,accent)] + title_block(event,dark,accent,290,"left_editorial")

def front_page(idx, palette, event):
    _,bg,dark,accent,soft,white=palette
    theme=THEMES[idx%len(THEMES)]
    layout=LAYOUTS[(idx*3 + idx//10)%len(LAYOUTS)]
    objs=[rect("background",0,0,W,H,bg)]
    objs += motif_objects(theme,palette,idx)
    objs = layout_adjust(objs,layout,event,palette)
    # visual finish: editable only
    finish=idx%5
    if finish==0: objs += [rect("matte_wash",0,0,W,H,dark,.018)]
    elif finish==1: objs += [rect("gloss_sheen",520,-120,130,1320,"#ffffff",.045,18)]
    elif finish==2: objs += [line("foil_top",55,58,W-55,58,accent,3,.9),line("foil_bottom",55,H-58,W-55,H-58,accent,3,.9)]
    elif finish==3: objs += [rect("soft_touch",0,0,W,H,dark,.028)]
    else: objs += [ellipse("satin_glow",620,120,220,90,"#ffffff",.05)]
    return objs

def details_page(idx,palette,event):
    _,bg,dark,accent,soft,white=palette
    o=[rect("details_bg",0,0,W,H,bg)]
    theme=THEMES[idx%len(THEMES)]
    # reuse a reduced motif so page set feels coordinated, not duplicated
    o += motif_objects(theme,palette,idx)[0:6]
    o += [
        txt("details_title",95,135,"THE DETAILS",42,dark,700,560,"center","Cinzel"),
        line("details_rule",220,210,530,210,accent,2),
        txt("schedule_h",95,300,"SCHEDULE",14,accent,700,560,"center","Montserrat"),
        txt("schedule",95,345,"4:30 PM · Arrival\n5:00 PM · Ceremony / Welcome\n6:00 PM · Drinks & Celebration",20,dark,500,560,"center","DM Sans",1.45),
        txt("location_h",95,575,"LOCATION",14,accent,700,560,"center","Montserrat"),
        txt("location",95,620,event[4]+"\n123 Celebration Avenue · Victoria",18,dark,500,560,"center","DM Sans",1.4),
        txt("notes_h",95,800,"DRESS / NOTES",14,accent,700,560,"center","Montserrat"),
        txt("notes",95,840,"Dress code: Cocktail\nParking available on site",17,dark,500,560,"center","DM Sans",1.35),
    ]
    return o

def rsvp_page(idx,palette,event):
    _,bg,dark,accent,soft,white=palette
    darkbg = idx%2==0
    base=dark if darkbg else bg; fg=bg if darkbg else dark
    o=[rect("rsvp_bg",0,0,W,H,base),rect("rsvp_frame",55,55,640,940,"transparent",1,0,18,accent,3)]
    o += [
        txt("rsvp_kicker",100,165,"PLEASE REPLY",15,accent,700,550,"center","Montserrat"),
        txt("rsvp_title",100,225,"RSVP",58,fg,700,550,"center","Cinzel"),
        txt("rsvp_date",100,350,"Kindly respond by 10 October 2026",18,fg,500,550,"center","DM Sans"),
        txt("rsvp_name",120,485,"Guest name: __________________________",17,fg,500,510,"left","DM Sans"),
        txt("rsvp_attend",120,555,"□ Joyfully accepts      □ Regretfully declines",16,fg,500,510,"left","DM Sans"),
        txt("rsvp_diet",120,625,"Dietary requirements: __________________",16,fg,500,510,"left","DM Sans"),
        txt("rsvp_contact",100,760,"04XX XXX XXX\nhello@example.com\nwww.example.com/rsvp",17,accent,650,550,"center","DM Sans",1.45),
    ]
    o += motif_objects(THEMES[(idx+7)%len(THEMES)],palette,idx)[:4]
    return o

def object_to_svg(o):
    typ=o.get("type"); op=o.get("opacity",1); fill=o.get("fill","none")
    if fill in (None,"transparent"): fill="none"
    stroke=o.get("stroke","none"); sw=o.get("strokeWidth",0)
    if typ=="rect":
        return f'<rect x="{o.get("left",0)}" y="{o.get("top",0)}" width="{o.get("width",0)}" height="{o.get("height",0)}" rx="{o.get("rx",0)}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}" transform="rotate({o.get("angle",0)} {o.get("left",0)} {o.get("top",0)})" />'
    if typ=="circle":
        r=o.get("radius",0); cx=o.get("left",0)+r; cy=o.get("top",0)+r
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}" />'
    if typ=="ellipse":
        rx=o.get("rx",0);ry=o.get("ry",0);cx=o.get("left",0)+rx;cy=o.get("top",0)+ry
        return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}" />'
    if typ=="line":
        x1,y1,x2,y2=o.get("points",[0,0,0,0]); return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}" stroke-opacity="{op}" />'
    if typ=="polygon":
        pts=" ".join(f'{p["x"]},{p["y"]}' for p in o.get("points",[])); return f'<polygon points="{pts}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}" />'
    if typ=="path":
        return f'<path d="{escape(str(o.get("path","")))}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}" stroke-opacity="{op}" />'
    if typ in ("text","textbox"):
        x=o.get("left",0);y=o.get("top",0)+o.get("fontSize",20);fs=o.get("fontSize",20);ff=escape(str(o.get("font","Arial")));fw=o.get("fontWeight",400);ta=o.get("textAlign","left");anchor={"center":"middle","right":"end"}.get(ta,"start");width=o.get("width") or 0
        if anchor=="middle": x=x+width/2
        elif anchor=="end": x=x+width
        parts=str(o.get("text","")).split("\n"); lh=fs*o.get("lineHeight",1.15)
        tsp=[]
        for n,t in enumerate(parts): tsp.append(f'<tspan x="{x}" dy="{0 if n==0 else lh}">{escape(t)}</tspan>')
        return f'<text x="{x}" y="{y}" fill="{fill}" fill-opacity="{op}" font-family="{ff}" font-size="{fs}" font-weight="{fw}" text-anchor="{anchor}">{"".join(tsp)}</text>'
    return ""

def svg_page(objects):
    body="".join(object_to_svg(o) for o in objects)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{body}</svg>'

def signature(pages):
    norm=[]
    for p in pages:
        norm.append([{k:v for k,v in o.items() if k not in {"id","name"}} for o in p["objects"]])
    return hashlib.sha256(json.dumps(norm,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def page_count_for(idx):
    if idx < 34: return 1
    if idx < 67: return 2
    return 3

def build_template(idx, product):
    palette=PALETTES[idx%len(PALETTES)]
    event=EVENTS[(idx*3 + idx//10)%len(EVENTS)]
    count=page_count_for(idx)
    pages=[{"name":"Invitation","objects":front_page(idx,palette,event)}]

    # Protect layout-only safe panels from accidental customer movement.
    for _page in pages:
        for _obj in _page.get("objects", []):
            if _obj.get("id") == "content_safe_panel":
                _obj["customerEditable"] = False
                _obj["selectable"] = False
                _obj["evented"] = False
                _obj["locked"] = True
    if count>=2: pages.append({"name":"Details","objects":details_page(idx,palette,event)})
    if count>=3: pages.append({"name":"RSVP","objects":rsvp_page(idx,palette,event)})
    finish=["Matte","Gloss","Foil","Soft-Touch","Satin"][idx%5]
    name=f"Luxury Invitation {idx+1:03d} · {DESIGN_NAMES[idx]} · {count} Page{'s' if count>1 else ''} · {finish}"
    physical_w=float(getattr(product,"print_width_in",0) or 5)
    physical_h=float(getattr(product,"print_height_in",0) or 7)
    data={
        "version":4,"templateType":"editable-master","reconstructed":True,"generator":GENERATOR_ID,
        "designName":DESIGN_NAMES[idx],"eventType":event[0],"finish":finish,"pageCount":count,
        "document":{"width":W,"height":H,"profile":"invitation-card","physical":{"widthIn":physical_w,"heightIn":physical_h}},
        "pages":copy.deepcopy(pages),"adminPages":copy.deepcopy(pages),
        "source":{"type":"reference-driven-vector-reconstruction","note":"Original editable vector composition inspired by supplied marketplace screenshots; no raster artwork embedded."},
    }
    return name,data,pages


# =========================================================
# V4 LUXURY FLORAL OVERRIDES
# These functions intentionally override the lighter V3 builders above.
# All decoration is built from editable Fabric-compatible primitives.
# =========================================================

LUXURY_FLORAL_NAMES = [
    "Ivory Peony Atelier", "Emerald Rose Conservatory", "Midnight Orchid Gold", "Blush Magnolia Silk",
    "Burgundy Garden Estate", "Champagne Wildflower Veil", "Royal Blue Hydrangea", "Pearl Jasmine Lace",
    "Black Gold Rose Couture", "Sage Eucalyptus Romance", "Lavender Wisteria House", "Ruby Peony Nocturne",
    "Aqua Lotus Gilded", "Forest Fern & Rose", "Terracotta Dahlia Manor", "Plum Orchid Court",
    "Navy White Rose Gallery", "Mint Floral Cameo", "Fuchsia Bougainvillea", "Gold Botanical Cathedral",
    "Rosewater English Garden", "Emerald Magnolia Arch", "Sapphire Lily Ballroom", "Ivory Garden Gate",
    "Champagne Orchid Ribbon", "Burgundy Vintage Rose", "Black Pearl Camellia", "Blush Peony Monogram",
    "Teal Jasmine Pavilion", "Royal Aubergine Dahlia", "Cobalt Wildflower Editorial", "Sage Rosewater Wreath",
    "Ruby Magnolia Crest", "Navy Eucalyptus Foil", "Pearl Hydrangea Cloud", "Emerald Botanical Oval",
    "Lavender Rose Chinoiserie", "Champagne Garden Column", "Midnight Peony Frame", "Terracotta Wild Rose",
    "Ivory Orchid Cameo", "Forest Lily Arch", "Blush Jasmine Bow", "Aqua Magnolia Wave",
    "Burgundy Eucalyptus Manor", "Black Gold Botanical Crest", "Mint Peony Scallop", "Plum Wisteria Gate",
    "Navy Rose Deco", "Pearl Garden Filigree", "Rose Gold Camellia", "Emerald White Orchid",
    "Sapphire Wildflower Halo", "Champagne Dahlia Estate", "Ivory Fern & Peony", "Ruby Rose Cathedral",
    "Black Pearl Magnolia", "Blush Hydrangea Romance", "Teal Orchid Atelier", "Lavender Jasmine Court",
    "Forest Camellia Gold", "Navy Garden Ribbon", "Pearl Rosewater Wreath", "Terracotta Lily Gallery",
    "Emerald Dahlia Frame", "Aubergine Rose Veil", "Cobalt Magnolia Editorial", "Champagne Eucalyptus Cameo",
    "Ivory Wisteria Garden", "Ruby Orchid Ballroom", "Sage Peony Conservatory", "Black Gold Jasmine",
    "Blush Dahlia Ribbon", "Teal Wildflower Manor", "Navy Camellia Crest", "Pearl Magnolia Lace",
    "Emerald Rose Filigree", "Lavender Orchid Arch", "Terracotta Peony House", "Sapphire Jasmine Night",
    "Ivory Hydrangea Estate", "Burgundy Magnolia Gold", "Mint Rose Gallery", "Plum Camellia Court",
    "Aqua Eucalyptus Veil", "Black Pearl Peony", "Champagne Lily Pavilion", "Rosewater Orchid Garden",
    "Forest Wildflower Crest", "Navy Magnolia Cathedral", "Pearl Peony Atelier", "Ruby Jasmine Filigree",
    "Emerald Camellia Arch", "Lavender Dahlia Silk", "Terracotta Rose Estate", "Cobalt Orchid Gilded",
    "Ivory Botanical Ballroom", "Blush Magnolia Cameo", "Midnight Wildflower Gold", "Champagne Rose Finale",
]

FLOWER_KINDS = ["rose", "peony", "magnolia", "orchid", "dahlia", "camellia", "lily", "jasmine", "wildflower", "hydrangea"]
FRAME_KINDS = ["double", "filigree", "arch", "oval", "deco", "lace", "cathedral", "ribbon", "column", "scallop"]
COMPOSITIONS = ["corners", "top_garden", "bottom_garden", "left_bouquet", "right_bouquet", "wreath", "arch_garden", "diagonal", "border_garden", "floating_petals"]


def _rot(cx, cy, radius, deg):
    a = math.radians(deg)
    return cx + math.cos(a) * radius, cy + math.sin(a) * radius


def petal_path(prefix, cx, cy, length, width, angle, fill, stroke=None, opacity=.9):
    """Editable pointed petal made from an SVG cubic path."""
    ux, uy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    vx, vy = -uy, ux
    tipx, tipy = cx + ux * length, cy + uy * length
    c1x, c1y = cx + ux * length * .42 + vx * width, cy + uy * length * .42 + vy * width
    c2x, c2y = cx + ux * length * .82 + vx * width * .42, cy + uy * length * .82 + vy * width * .42
    c3x, c3y = cx + ux * length * .82 - vx * width * .42, cy + uy * length * .82 - vy * width * .42
    c4x, c4y = cx + ux * length * .42 - vx * width, cy + uy * length * .42 - vy * width
    d = f"M {cx:.2f} {cy:.2f} C {c1x:.2f} {c1y:.2f}, {c2x:.2f} {c2y:.2f}, {tipx:.2f} {tipy:.2f} C {c3x:.2f} {c3y:.2f}, {c4x:.2f} {c4y:.2f}, {cx:.2f} {cy:.2f} Z"
    return path(prefix, d, fill, stroke or fill, 1.2, opacity)


def luxury_rose(prefix, cx, cy, accent, soft, scale=1.0, dark=None):
    out=[]
    dark = dark or accent
    # outer petals
    for n in range(12):
        out.append(petal_path(f"{prefix}_outer_{n}", cx, cy, 48*scale, 18*scale, n*30-90, soft, dark, .82))
    for n in range(9):
        out.append(petal_path(f"{prefix}_mid_{n}", cx, cy, 34*scale, 15*scale, n*40-80, accent, dark, .76))
    for n in range(7):
        out.append(petal_path(f"{prefix}_inner_{n}", cx, cy, 21*scale, 10*scale, n*51-70, dark, dark, .68))
    out.append(circle(prefix+"_heart",cx,cy,8*scale,dark,.95))
    return out


def luxury_peony(prefix, cx, cy, accent, soft, scale=1.0):
    out=[]
    for ring,(cnt,length,width,opacity,color) in enumerate([
        (14,54,19,.74,soft),(12,42,18,.78,accent),(10,31,15,.82,soft),(8,22,11,.88,accent)
    ]):
        for n in range(cnt):
            out.append(petal_path(f"{prefix}_r{ring}_{n}",cx,cy,length*scale,width*scale,(360/cnt)*n-90+ring*9,color,accent,opacity))
    out.append(circle(prefix+"_centre",cx,cy,7*scale,accent,1))
    return out


def magnolia(prefix, cx, cy, accent, soft, scale=1.0):
    out=[]
    for n in range(8):
        out.append(petal_path(f"{prefix}_p{n}",cx,cy,58*scale,25*scale,n*45-90,"#fff9f5",accent,.96))
    for n in range(5):
        out.append(petal_path(f"{prefix}_i{n}",cx,cy,31*scale,13*scale,n*72-70,soft,accent,.86))
    out += [circle(prefix+"_c1",cx,cy,9*scale,accent,1),circle(prefix+"_c2",cx+2*scale,cy-2*scale,4*scale,"#f4cf70",1)]
    return out


def orchid(prefix, cx, cy, accent, soft, scale=1.0):
    out=[]
    for n,a in enumerate([-78,-22,22,78]): out.append(petal_path(f"{prefix}_wing{n}",cx,cy,50*scale,20*scale,a,soft,accent,.88))
    out += [petal_path(prefix+"_lip1",cx,cy,34*scale,18*scale,145,accent,accent,.92),petal_path(prefix+"_lip2",cx,cy,34*scale,18*scale,35,accent,accent,.92),circle(prefix+"_c",cx,cy,7*scale,"#f4cf70",1)]
    return out


def dahlia(prefix, cx, cy, accent, soft, scale=1.0):
    out=[]
    for ring in range(4):
        cnt=16-ring*2
        for n in range(cnt):
            out.append(petal_path(f"{prefix}_r{ring}_{n}",cx,cy,(48-ring*8)*scale,(10-ring)*scale,n*(360/cnt)-90+ring*7,soft if ring%2==0 else accent,accent,.8+ring*.04))
    out.append(circle(prefix+"_c",cx,cy,6*scale,accent,1))
    return out


def camellia(prefix,cx,cy,accent,soft,scale=1.0):
    return luxury_rose(prefix,cx,cy,accent,soft,scale*.92,dark=accent)


def lily(prefix,cx,cy,accent,soft,scale=1.0):
    out=[]
    for n in range(6): out.append(petal_path(f"{prefix}_p{n}",cx,cy,65*scale,18*scale,n*60-90,"#fffdfa",accent,.95))
    for n in range(5):
        ex,ey=_rot(cx,cy,38*scale,n*72-90)
        out.append(line(f"{prefix}_st{n}",cx,cy,ex,ey,accent,1.4,.75));out.append(circle(f"{prefix}_an{n}",ex,ey,3.5*scale,"#d59b45",1))
    return out


def jasmine(prefix,cx,cy,accent,soft,scale=1.0):
    out=[]
    for b in range(5):
        bx,by=_rot(cx,cy,20*scale,b*72)
        for n in range(5): out.append(petal_path(f"{prefix}_{b}_{n}",bx,by,18*scale,7*scale,n*72-90,"#fffdf7",accent,.96))
        out.append(circle(f"{prefix}_c{b}",bx,by,3*scale,accent,1))
    return out


def wildflower(prefix,cx,cy,accent,soft,scale=1.0):
    out=[]
    colors=[accent,soft,"#f2b6c6","#d7c6ff","#ffe09b"]
    for b in range(6):
        bx=cx+(b-2.5)*24*scale; by=cy+(b%2)*18*scale
        out.append(line(f"{prefix}_s{b}",bx,by+40*scale,bx,by,accent,1.2,.65))
        for n in range(5): out.append(petal_path(f"{prefix}_{b}_{n}",bx,by,16*scale,6*scale,n*72-90,colors[b%len(colors)],accent,.9))
        out.append(circle(f"{prefix}_c{b}",bx,by,3*scale,"#c78d35",1))
    return out


def hydrangea(prefix,cx,cy,accent,soft,scale=1.0):
    out=[]
    for r in range(3):
        cnt=8+r*4; rad=(12+r*17)*scale
        for n in range(cnt):
            bx,by=_rot(cx,cy,rad,n*(360/cnt)+r*11)
            for p in range(4): out.append(petal_path(f"{prefix}_{r}_{n}_{p}",bx,by,10*scale,4*scale,p*90-90,soft if (n+r)%2 else accent,accent,.72))
    return out


def flower_kind(kind,prefix,cx,cy,accent,soft,scale=1.0):
    return {
        "rose":luxury_rose,"peony":luxury_peony,"magnolia":magnolia,"orchid":orchid,"dahlia":dahlia,
        "camellia":camellia,"lily":lily,"jasmine":jasmine,"wildflower":wildflower,"hydrangea":hydrangea,
    }[kind](prefix,cx,cy,accent,soft,scale)


def luxe_leaf(prefix,x,y,length,width,angle,color,opacity=.78):
    return petal_path(prefix,x,y,length,width,angle,color,color,opacity)


def foliage_spray(prefix,x,y,length,angle,accent,soft,branches=7,mirror=False):
    out=[]
    ux,uy=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    ex,ey=x+ux*length,y+uy*length
    out.append(line(prefix+"_stem",x,y,ex,ey,accent,2,.62))
    for n in range(1,branches+1):
        t=n/(branches+1); bx=x+(ex-x)*t; by=y+(ey-y)*t
        side=-1 if (n%2==0) ^ mirror else 1
        out.append(luxe_leaf(f"{prefix}_leaf{n}",bx,by,30,11,angle+side*55,accent,.72))
        if n%3==0: out.append(circle(f"{prefix}_berry{n}",bx+side*8,by-4,4,soft,.85,accent,1))
    return out


def gold_filigree(prefix, x, y, w, h, accent, mirror=False):
    s=-1 if mirror else 1
    d1=f"M {x} {y+h} C {x+45*s} {y+h*.72}, {x+30*s} {y+h*.35}, {x+w*s} {y}"
    d2=f"M {x+5*s} {y+h*.75} C {x+55*s} {y+h*.58}, {x+5*s} {y+h*.32}, {x+w*.72*s} {y+h*.16}"
    out=[path(prefix+"_a",d1,"transparent",accent,2.4,.88),path(prefix+"_b",d2,"transparent",accent,1.4,.64)]
    for n in range(4):
        bx=x+(18+22*n)*s; by=y+h-(n+1)*h/5
        out.append(luxe_leaf(f"{prefix}_l{n}",bx,by,20,7,-55*s,accent,.66))
    return out


def luxury_frame(kind, palette, idx):
    _,bg,dark,accent,soft,white=palette
    o=[]

    if kind=="double":
        o += [
            rect("frame_outer",38,38,W-76,H-76,"transparent",1,0,20,accent,2.4),
            rect("frame_inner",54,54,W-108,H-108,"transparent",1,0,16,soft,1.1)
        ]

    elif kind=="filigree":
        o += [rect("frame_fine",52,52,W-104,H-104,"transparent",1,0,12,accent,1.3)]
        o += gold_filigree("tl",58,58,135,160,accent)
        o += gold_filigree("br",692,832,135,160,accent,True)

    elif kind=="arch":
        o += [
            arch("frame_arch1",72,88,606,840,accent,2.8),
            arch("frame_arch2",90,108,570,802,soft,1.3)
        ]

    elif kind=="oval":
        # True centred oval with equal margins.
        o += [
            ellipse("frame_oval1",375,520,255,390,"transparent",1,accent,2.6),
            ellipse("frame_oval2",375,520,238,370,"transparent",1,soft,1.2)
        ]

    elif kind=="deco":
        o += [
            rect("deco_outer",42,42,W-84,H-84,"transparent",1,0,0,accent,2.2),
            rect("deco_inner",60,60,W-120,H-120,"transparent",1,0,0,soft,1)
        ]
        for y in (128,922):
            o += [
                line(f"deco_l{y}",72,y,165,y,accent,1.8),
                line(f"deco_r{y}",585,y,678,y,accent,1.8),
            ]

    elif kind=="lace":
        o += [rect("lace_base",48,48,W-96,H-96,"transparent",1,0,26,accent,1.5)]
        for n in range(18):
            x=76+n*35
            o += [circle(f"lace_t{n}",x,62,5.5,bg,1,accent,1),circle(f"lace_b{n}",x,988,5.5,bg,1,accent,1)]

    elif kind=="cathedral":
        o += [
            arch("cat_outer",62,72,626,850,accent,2.8),
            arch("cat_inner",82,94,586,810,soft,1.35),
        ]

    elif kind=="ribbon":
        o += [
            rect("rib_frame",60,60,W-120,H-120,"transparent",1,0,14,accent,1.6),
            polygon("rib_top",[{"x":110,"y":72},{"x":640,"y":72},{"x":600,"y":108},{"x":150,"y":108}],accent,.14),
            polygon("rib_bottom",[{"x":110,"y":978},{"x":640,"y":978},{"x":600,"y":942},{"x":150,"y":942}],accent,.14),
        ]

    elif kind=="column":
        # Symmetric columns with equal width/margins.
        o += [
            rect("col_l",48,48,42,H-96,dark,.92),
            rect("col_l_gold",90,48,5,H-96,accent),
            rect("col_r",660,48,42,H-96,dark,.92),
            rect("col_r_gold",655,48,5,H-96,accent),
        ]

    else:
        o += [rect("sc_base",52,52,W-104,H-104,"transparent",1,0,26,accent,1.5)]
        for n in range(12):
            x=82+n*53
            o += [circle(f"sc_t{n}",x,64,15,bg,1,accent,1.1),circle(f"sc_b{n}",x,986,15,bg,1,accent,1.1)]

    return o

def floral_cluster(prefix,cx,cy,palette,idx,scale=1.0,mirror=False):
    _,bg,dark,accent,soft,white=palette
    kind=FLOWER_KINDS[idx%len(FLOWER_KINDS)]
    kind2=FLOWER_KINDS[(idx+3)%len(FLOWER_KINDS)]
    o=[]
    o += foliage_spray(prefix+"_spray1",cx,cy,145*scale,220 if mirror else -40,accent,soft,7,mirror)
    o += foliage_spray(prefix+"_spray2",cx,cy,120*scale,155 if mirror else 25,accent,soft,6,not mirror)
    o += flower_kind(kind,prefix+"_main",cx,cy,accent,soft,1.0*scale)
    o += flower_kind(kind2,prefix+"_side",cx+(58 if not mirror else -58)*scale,cy+38*scale,accent,soft,.62*scale)
    for n in range(5):
        px=cx+(-85+n*36)*(1 if not mirror else -1)*scale; py=cy+70*scale+(n%2)*15
        o.append(petal_path(f"{prefix}_loose{n}",px,py,17*scale,6*scale,-90+n*18,soft,accent,.55))
    return o


def composition_florals(composition,palette,idx):
    """
    Strictly aligned decorative compositions.
    Central copy area is kept visually clear and all heavy artwork is balanced
    around the page centre line x=375.
    """
    o=[]

    if composition=="corners":
        o += floral_cluster("tl",82,92,palette,idx,.48)
        o += floral_cluster("br",668,958,palette,idx+1,.48,True)

    elif composition=="top_garden":
        xs=[85,185,285,465,565,665]
        ss=[.34,.40,.44,.44,.40,.34]
        for n,(x,s) in enumerate(zip(xs,ss)):
            o += floral_cluster(f"top{n}",x,72,palette,idx+n,s,mirror=n>=3)

    elif composition=="bottom_garden":
        xs=[85,185,285,465,565,665]
        ss=[.34,.40,.44,.44,.40,.34]
        for n,(x,s) in enumerate(zip(xs,ss)):
            o += floral_cluster(f"bot{n}",x,978,palette,idx+n,s,mirror=n>=3)

    elif composition=="left_bouquet":
        # Balanced vertical bouquet fully outside the main text box.
        for n,(y,s) in enumerate([(180,.46),(525,.42),(870,.46)]):
            o += floral_cluster(f"left{n}",72,y,palette,idx+n*2,s)

    elif composition=="right_bouquet":
        for n,(y,s) in enumerate([(180,.46),(525,.42),(870,.46)]):
            o += floral_cluster(f"right{n}",678,y,palette,idx+n*2,s,True)

    elif composition=="wreath":
        # Symmetric top crown, not a central wreath.
        crown=[
            (215,125,.28),(270,92,.32),(330,74,.34),
            (420,74,.34),(480,92,.32),(535,125,.28)
        ]
        for n,(cx,cy,s) in enumerate(crown):
            o += flower_kind(FLOWER_KINDS[(idx+n)%len(FLOWER_KINDS)],f"wr{n}",cx,cy,palette[3],palette[4],s)

    elif composition=="arch_garden":
        left=[(82,185,.28),(66,350,.24),(64,525,.22),(72,700,.24),(96,865,.28)]
        right=[(668,185,.28),(684,350,.24),(686,525,.22),(678,700,.24),(654,865,.28)]
        for n,(x,y,s) in enumerate(left):
            o += flower_kind(FLOWER_KINDS[(idx+n)%len(FLOWER_KINDS)],f"agl{n}",x,y,palette[3],palette[4],s)
        for n,(x,y,s) in enumerate(right):
            o += flower_kind(FLOWER_KINDS[(idx+n+5)%len(FLOWER_KINDS)],f"agr{n}",x,y,palette[3],palette[4],s)

    elif composition=="diagonal":
        # Two balanced corner cascades. Nothing crosses the middle.
        left=[(58,105,.26),(100,155,.23),(135,205,.20)]
        right=[(615,845,.20),(650,900,.23),(692,955,.26)]
        for n,(x,y,s) in enumerate(left):
            o += floral_cluster(f"dgl{n}",x,y,palette,idx+n,s)
        for n,(x,y,s) in enumerate(right):
            o += floral_cluster(f"dgr{n}",x,y,palette,idx+n+3,s,True)

    elif composition=="border_garden":
        ys=[150,330,720,900]
        for n,y in enumerate(ys):
            o += flower_kind(FLOWER_KINDS[(idx+n)%len(FLOWER_KINDS)],f"bl{n}",58,y,palette[3],palette[4],.25)
            o += flower_kind(FLOWER_KINDS[(idx+n+3)%len(FLOWER_KINDS)],f"br{n}",692,y,palette[3],palette[4],.25)

    else:
        # Floating petals only in top and bottom bands.
        o += floral_cluster("float_a",82,110,palette,idx,.40)
        o += floral_cluster("float_b",668,940,palette,idx+2,.40,True)
        for n in range(18):
            band_top = n < 9
            m = n if band_top else n-9
            x=95+(m*70)%560
            y=(92+(m%3)*34) if band_top else (880+(m%3)*34)
            o.append(petal_path(f"fp{n}",x,y,9+(n%3)*2,3.5+(n%2),-65+(n*23)%130,palette[4],palette[3],.15+(n%3)*.05))

    return o

def rich_paper_background(palette,idx):
    _,bg,dark,accent,soft,white=palette
    o=[rect("background",0,0,W,H,bg)]
    # paper/watercolour depth built as editable translucent shapes
    o += [ellipse("wash_a",105,95,220,150,soft,.08),ellipse("wash_b",670,950,260,180,accent,.045)]
    if idx%3==0: o += [ellipse("wash_c",610,210,170,95,"#ffffff",.09),ellipse("wash_d",160,820,180,120,soft,.06)]
    if idx%4==0:
        for n in range(10): o.append(line(f"papergrain{n}",45,100+n*92,705,80+n*92,dark,.35,.035))
    return o



def _safe_font_size(value, preferred, max_width, font_family="DM Sans", minimum=12):
    """Conservative font fitting for both SVG previews and Fabric canvas."""
    value = str(value or "")
    longest = max((len(line) for line in value.split("\n")), default=1)
    family = str(font_family or "").lower()
    factor = 0.60 if any(
        x in family
        for x in ("cinzel", "serif", "playfair", "cormorant", "georgia", "baskerville")
    ) else 0.56
    estimated = longest * preferred * factor
    if estimated <= max_width:
        return preferred
    fitted = int(max_width / max(1, longest * factor))
    return max(minimum, min(preferred, fitted))


def _wrap_text_for_box(value, preferred_size, max_width, font_family, max_lines=2):
    """Wrap long display text into at most max_lines without cutting it off."""
    value = " ".join(str(value or "").split())
    if not value:
        return value, preferred_size

    family = str(font_family or "").lower()
    factor = 0.60 if any(
        x in family
        for x in ("cinzel", "serif", "playfair", "cormorant", "georgia", "baskerville")
    ) else 0.56

    # First see whether it already fits on one line.
    one_line_width = len(value) * preferred_size * factor
    if one_line_width <= max_width:
        return value, preferred_size

    words = value.split()
    best = None

    # Try a balanced 2-line split at every word boundary.
    if max_lines >= 2 and len(words) > 1:
        for split in range(1, len(words)):
            a = " ".join(words[:split])
            b = " ".join(words[split:])
            longest = max(len(a), len(b))
            fitted = int(max_width / max(1, longest * factor))
            score = (
                min(preferred_size, fitted),
                -abs(len(a) - len(b)),
            )
            if best is None or score > best[0]:
                best = (score, a + "\n" + b)

        if best:
            fs = max(24, min(preferred_size, best[0][0]))
            return best[1], fs

    # Last fallback: shrink one line.
    fs = max(22, _safe_font_size(value, preferred_size, max_width, font_family, 22))
    return value, fs


def safe_txt(
    i, x, y, value, preferred_size, fill, weight=400, width=None,
    align="left", font="Playfair Display", lh=1.15, italic=False,
    minimum=12, wrap=False, max_lines=2
):
    """
    Create editable text inside a fixed safe box.
    Headings can wrap to 2 lines; normal copy simply scales down.
    """
    box_width = float(width or (W - x - 40))
    value = str(value or "")

    if wrap:
        rendered, fs = _wrap_text_for_box(
            value, preferred_size, box_width, font, max_lines=max_lines
        )
    else:
        rendered = value
        fs = _safe_font_size(value, preferred_size, box_width, font, minimum)

    d = txt(i, x, y, rendered, fs, fill, weight, width, align, font, lh, italic)

    # Fabric must treat bounded text as a Textbox, not an IText.
    # Otherwise `width` does not constrain/wrap the string.
    if width is not None:
        d["type"] = "textbox"
        d["width"] = round(box_width, 2)
        d["splitByGrapheme"] = False

    return d


def luxury_title_block(event,palette,idx):
    kind,title,kicker,date,venue=event
    _,bg,dark,accent,soft,white=palette

    x=145
    box=460
    o=[]

    # Uniform hierarchy across all 100 templates.
    wrapped, fitted = _wrap_text_for_box(title, 46, box, "Cormorant Garamond", max_lines=2)
    headline_y = 382 - (18 if "\n" in wrapped else 0)

    o += [
        safe_txt("kicker",x,332,kicker.upper(),11.5,accent,700,box,"center","Montserrat",minimum=9),
        safe_txt("headline",x,headline_y,wrapped,fitted,dark,700,box,"center","Cormorant Garamond",1.02,minimum=24),
        line("title_rule",255,500,495,500,accent,1.4,.72),
        safe_txt("date",x,540,date,16,dark,650,box,"center","DM Sans",minimum=11),
        safe_txt("venue",x,588,venue,14,dark,500,box,"center","DM Sans",minimum=10),
        safe_txt("rsvp",x,648,"RSVP · 04XX XXX XXX · hello@example.com",11.5,accent,650,box,"center","DM Sans",minimum=9),
    ]
    return o

def glossy_finish(palette,idx):
    _,bg,dark,accent,soft,white=palette
    o=[]
    # metallic micro-lines + transparent diagonal sheen give a premium glossy preview
    o += [line("foil_micro_top",82,78,668,78,accent,1.2,.5),line("foil_micro_bottom",82,972,668,972,accent,1.2,.5)]
    if idx%2==0:
        o += [polygon("gloss_sweep",[{"x":500,"y":-80},{"x":650,"y":-80},{"x":260,"y":1130},{"x":110,"y":1130}],"#ffffff",.055)]
    else:
        o += [ellipse("satin_glow",600,160,240,110,"#ffffff",.065),ellipse("satin_glow2",130,870,180,85,"#ffffff",.04)]
    if idx%5==0:
        for n in range(12):
            x=105+n*49; o.append(circle(f"foil_spark{n}",x,104+(n%2)*8,2.2,accent,.75))
    return o


def front_page(idx,palette,event):
    composition=COMPOSITIONS[idx%len(COMPOSITIONS)]
    frame=FRAME_KINDS[(idx*3 + idx//7)%len(FRAME_KINDS)]
    o=rich_paper_background(palette,idx)
    o += luxury_frame(frame,palette,idx)
    o += composition_florals(composition,palette,idx)

    # Clean central information block. This enforces visual alignment even for
    # ornate compositions and long titles.
    _,bg,dark,accent,soft,white=palette
    panel = rect("content_safe_panel",122,282,506,420,bg,.965,0,22)
    panel["customerEditable"]=False
    panel["selectable"]=False
    panel["evented"]=False
    panel["locked"]=True
    o.append(panel)

    o += luxury_title_block(event,palette,idx)
    o += glossy_finish(palette,idx)
    return o

def details_page(idx,palette,event):
    _,bg,dark,accent,soft,white=palette
    o=rich_paper_background(palette,idx+11)
    o += luxury_frame(FRAME_KINDS[(idx+4)%len(FRAME_KINDS)],palette,idx)
    # coordinated but lighter floral identity
    o += floral_cluster("det_tl",95,115,palette,idx,.48)+floral_cluster("det_br",655,930,palette,idx+2,.5,True)
    o += [
        txt("details_title",105,145,"THE DETAILS",40,dark,700,540,"center","Cinzel"),
        txt("details_sub",105,205,"Everything you need for the celebration",15,accent,500,540,"center","Georgia",1.0,True),
        line("details_rule",265,252,485,252,accent,1.5,.7),
        txt("schedule_h",105,310,"ORDER OF EVENTS",12,accent,700,540,"center","Montserrat"),
        txt("schedule",105,350,"4:30 PM  ·  Guest arrival\n5:00 PM  ·  Ceremony / Welcome\n6:00 PM  ·  Drinks & Celebration",18,dark,500,540,"center","DM Sans",1.55),
        txt("location_h",105,585,"VENUE",12,accent,700,540,"center","Montserrat"),
        txt("location",105,625,event[4]+"\n123 Celebration Avenue · Victoria",17,dark,500,540,"center","DM Sans",1.45),
        txt("notes_h",105,790,"DRESS & NOTES",12,accent,700,540,"center","Montserrat"),
        txt("notes",105,827,"Cocktail attire · Parking available\nPlease arrive 15 minutes early",16,dark,500,540,"center","DM Sans",1.4),
    ]
    o += glossy_finish(palette,idx+1)
    return o


def rsvp_page(idx,palette,event):
    _,bg,dark,accent,soft,white=palette
    dark_mode=idx%3==0
    base=dark if dark_mode else bg; fg=bg if dark_mode else dark
    pp=("Custom",base,fg,accent,soft,white)
    o=[rect("rsvp_bg",0,0,W,H,base)]
    o += luxury_frame(FRAME_KINDS[(idx+7)%len(FRAME_KINDS)],pp,idx)
    o += floral_cluster("rsvp_top",375,120,pp,idx,.62)+floral_cluster("rsvp_bottom",375,920,pp,idx+3,.58,True)
    o += [
        txt("rsvp_kicker",110,270,"KINDLY REPLY",12,accent,700,530,"center","Montserrat"),
        txt("rsvp_title",110,318,"RSVP",56,fg,700,530,"center","Cinzel"),
        txt("rsvp_date",110,420,"Please respond by 10 October 2026",16,fg,500,530,"center","DM Sans"),
        line("rsvp_rule",245,470,505,470,accent,1.5,.75),
        txt("rsvp_name",145,535,"Guest name  ______________________________",16,fg,500,460,"left","DM Sans"),
        txt("rsvp_attend",145,600,"□ Joyfully accepts    □ Regretfully declines",15,fg,500,460,"left","DM Sans"),
        txt("rsvp_diet",145,665,"Dietary requirements  ____________________",15,fg,500,460,"left","DM Sans"),
        txt("rsvp_contact",110,770,"04XX XXX XXX\nhello@example.com\nwww.example.com/rsvp",16,accent,650,530,"center","DM Sans",1.5),
    ]
    o += glossy_finish(pp,idx+2)
    return o


def build_template(idx, product):
    palette=PALETTES[idx%len(PALETTES)]
    event=EVENTS[(idx*3 + idx//10)%len(EVENTS)]
    count=page_count_for(idx)
    pages=[{"name":"Invitation","objects":front_page(idx,palette,event)}]
    if count>=2: pages.append({"name":"Details","objects":details_page(idx,palette,event)})
    if count>=3: pages.append({"name":"RSVP","objects":rsvp_page(idx,palette,event)})
    finish=["High-Gloss","Pearlescent","Gold-Foil Look","Soft-Touch","Satin-Lustre"][idx%5]
    design_name=LUXURY_FLORAL_NAMES[idx]
    name=f"Luxury Invitation {idx+1:03d} · {design_name} · {count} Page{'s' if count>1 else ''} · {finish}"
    physical_w=float(getattr(product,"print_width_in",0) or 5)
    physical_h=float(getattr(product,"print_height_in",0) or 7)
    data={
        "version":4,
        "templateType":"editable-master",
        "reconstructed":True,
        "generator":GENERATOR_ID,
        "designName":design_name,
        "eventType":event[0],
        "finish":finish,
        "pageCount":count,
        "document":{"width":W,"height":H,"profile":"invitation-card","physical":{"widthIn":physical_w,"heightIn":physical_h}},
        "pages":copy.deepcopy(pages),
        "adminPages":copy.deepcopy(pages),
        "source":{"type":"original-luxury-vector-composition","note":"Editable floral/vector composition built from original petal, foliage, frame and typographic primitives; no third-party raster artwork embedded."},
        "editable":True,
        "luxuryFloralLibrary":True,
        "luxuryFloralLibraryVersion":4,
        "designCode":f"zv4-inv-{idx+1:03d}",
    }
    return name,data,pages

class Command(BaseCommand):
    help="Rebuild invitation library with 100 distinct luxury editable 1/2/3-page templates"
    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, required=True)
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--replace-generated", action="store_true")
    def handle(self,*args,**opts):
        count=max(1,min(100,opts["count"]))
        try: product=Product.objects.get(pk=opts["product_id"])
        except Product.DoesNotExist: raise CommandError(f"Product {opts['product_id']} not found")
        built=[]; seen=set()
        for idx in range(count):
            name,data,pages=build_template(idx,product)
            sig=signature(pages)
            if sig in seen: raise CommandError(f"Duplicate structure detected at {name}")
            seen.add(sig); built.append((name,data,pages))
            self.stdout.write(f"{'DRY RUN ' if opts['dry_run'] else ''}{idx+1:03d}: {name}")
        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. {len(built)} structurally unique editable JSON/SVG invitations validated; database unchanged.")); return
        with transaction.atomic():
            # FULL rebuild for the selected invitation product only.
            # Other products and their templates are never touched.
            existing_count = DesignTemplate.objects.filter(product=product).count()
            DesignTemplate.objects.filter(product=product).delete()
            self.stdout.write(f"Removed {existing_count} existing templates from product {product.pk}.")
            media_root=Path(getattr(__import__("django.conf").conf.settings,"MEDIA_ROOT"))
            base_dir=media_root/MEDIA_DIR/str(product.pk); base_dir.mkdir(parents=True,exist_ok=True)
            for idx,(name,data,pages) in enumerate(built):
                svg_files=[]
                for pno,page in enumerate(pages,1):
                    svg=svg_page(page["objects"])
                    fn=f"invitation_{idx+1:03d}_page_{pno}.svg"; (base_dir/fn).write_text(svg,encoding="utf-8")
                    svg_files.append(f"{MEDIA_DIR}/{product.pk}/{fn}")
                data["svgFiles"]=svg_files
                # Always create a real gallery preview.
                # Prefer PNG when CairoSVG is installed; otherwise save the generated
                # SVG itself to the preview field so <img src="..."> still renders.
                preview_svg = svg_page(pages[0]["objects"])
                preview_bytes = None
                preview_name = f"luxury_invitation_align5_{idx+1:03d}.svg"
                preview_content = ContentFile(preview_svg.encode("utf-8"))

                if cairosvg is not None:
                    try:
                        preview_bytes = cairosvg.svg2png(
                            bytestring=preview_svg.encode("utf-8"),
                            output_width=W,
                            output_height=H,
                        )
                    except Exception as exc:
                        self.stdout.write(
                            self.style.WARNING(
                                f"PNG preview failed for {idx+1:03d}; using SVG fallback: {exc}"
                            )
                        )

                if preview_bytes:
                    preview_name = f"luxury_invitation_align5_{idx+1:03d}.png"
                    preview_content = ContentFile(preview_bytes)

                obj, _ = DesignTemplate.objects.update_or_create(
                    product=product,
                    name=name,
                    defaults={"json_data":data, "is_active":True},
                )
                obj.preview.save(preview_name, preview_content, save=True)

                if not obj.preview:
                    raise CommandError(
                        f"Preview could not be saved for template {idx+1:03d}: {name}"
                    )
        self.stdout.write(self.style.SUCCESS(f"Imported {len(built)} editable invitation templates for product {product.pk}: {product.name}"))
