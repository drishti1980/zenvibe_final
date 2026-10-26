"""Original luxury coaster vector artwork. Every motif remains individually editable in Fabric."""
from __future__ import annotations
import math
import random

PALETTES = [
 ("#F4EDE1","#173D35","#B58C51"),("#F7F2E8","#273B60","#BC9456"),
 ("#F5EDE7","#713F4B","#C49C72"),("#F1EEE8","#2D3432","#B89A6C"),
 ("#E9F0EB","#255B55","#C4A16D"),("#F8F0E5","#65412E","#C09B67"),
 ("#F1EEF3","#403653","#AD8CBB"),("#F3EDE2","#2D5265","#B5A079"),
 ("#F7F2E7","#68533A","#C8A875"),("#E9F0F0","#31515D","#BD9C6A")]
NAMES=["BOTANICAL HOUSE","ATELIER NO. 8","HERITAGE FLORAL","THE GARDEN",
       "COASTAL CERAMIC","ARTISAN STUDIO","ROYAL ORNAMENT","MODERN HEIRLOOM",
       "THE MONOGRAM","SIGNATURE COLLECTION"]
def safe_artwork(product,index):
    if not 0 <= index < 100: raise ValueError("index must be 0..99")
    # Once curated SVGs are installed, never fall back to recycled procedural art.
    from .coaster_curated_svg import ART_DIR, load_curated_artwork
    if ART_DIR.is_dir():
        return load_curated_artwork(index)
    theme=index%10
    variation=index//10
    paper,ink,gold=PALETTES[(theme+variation*3)%10]
    rng=random.Random(90037+index*7919)
    objects=[]
    def add(key,kind,**kw):
        obj=dict(id=f"lux{index}_{key}",name=key.replace("_"," ").title(),
                 type=kind,left=0,top=0,scaleX=1,scaleY=1,angle=0,
                 opacity=1,selectable=True,evented=True,customerEditable=True)
        obj.update(kw);objects.append(obj)
    def path(key,d,color,stroke=None,sw=0):
        add(key,"path",path=d,fill=color,stroke=stroke,strokeWidth=sw,
            strokeLineCap="round",strokeLineJoin="round")
    def disk(key,x,y,r,color,outline=None,sw=0):
        add(key,"circle",left=x-r,top=y-r,radius=r,fill=color,
            stroke=outline,strokeWidth=sw)
    def oval(key,x,y,rx,ry,color,angle=0):
        add(key,"ellipse",left=x-rx,top=y-ry,rx=rx,ry=ry,angle=angle,fill=color)
    def txt(key,value,x,y,w,size,color,font="Georgia",weight="normal",spacing=1):
        add(key,"textbox",left=x,top=y,width=w,text=value,fontFamily=font,
            fontSize=size,fontWeight=weight,charSpacing=spacing,textAlign="center",
            lineHeight=1.12,fill=color)
    def polar(r,a,cx=500,cy=500):
        a=math.radians(a);return cx+r*math.cos(a),cy+r*math.sin(a)
    def line(key,x,y,xx,yy,color,width=2):
        path(key,f"M {x:.2f} {y:.2f} L {xx:.2f} {yy:.2f}","",color,width)
    def petal(key,x,y,size,angle,color):
        a=math.radians(angle);u=(math.cos(a),math.sin(a));v=(-u[1],u[0])
        def p(t,s):return f"{x+u[0]*t+v[0]*s:.2f} {y+u[1]*t+v[1]*s:.2f}"
        d=f"M {p(0,0)} Q {p(size*.52,-size*.48)} {p(size,0)} Q {p(size*.52,size*.48)} {p(0,0)} Z"
        path(key,d,color)
    def flower(key,x,y,r,n=7,rot=0):
        for k in range(n):
            petal(f"{key}_petal{k}",x,y,r,rot+k*360/n,ink if k%3==0 else gold)
        disk(key+"_pistil",x,y,r*.13,paper)
        disk(key+"_seed",x,y,r*.055,ink)
    def branch(key,x,y,length,angle,leaves=5):
        a=math.radians(angle)
        ex=x+math.cos(a)*length;ey=y+math.sin(a)*length
        line(key+"_stem",x,y,ex,ey,ink,2.5)
        for k in range(leaves):
            t=(k+1)/(leaves+1);bx=x+(ex-x)*t;by=y+(ey-y)*t
            petal(f"{key}_leaf{k}a",bx,by,length*.19,angle+55,gold)
            petal(f"{key}_leaf{k}b",bx,by,length*.19,angle-55,ink)
    def frame(key,r,steps=1):
        for k in range(steps):
            disk(f"{key}_{k}",500,500,r-k*10,"transparent",
                 gold if k%2==0 else ink,2 if k else 3)
    def medallion(key,x,y,r):
        disk(key+"_outer",x,y,r,ink)
        disk(key+"_inner",x,y,r*.84,paper)
        for j in range(8):
            px,py=polar(r*.68,j*45,x,y)
            petal(f"{key}_orn{j}",px,py,r*.28,j*45,gold)
        disk(key+"_core",x,y,r*.2,ink)
    def flourish(key,x,y,s,flip=1):
        # Bezier filigree; not a ring or scattered dot
        path(key,f"M {x-130*s:.1f} {y:.1f} C {x-72*s:.1f} {y-45*s*flip:.1f} {x-36*s:.1f} {y+42*s*flip:.1f} {x:.1f} {y:.1f} C {x+34*s:.1f} {y-35*s*flip:.1f} {x+83*s:.1f} {y+26*s*flip:.1f} {x+130*s:.1f} {y:.1f}","transparent",gold,3)
        for k in range(4):
            petal(f"{key}_bud{k}",x+(k-1.5)*45*s,y+(18 if k%2 else -18)*s,21*s,90 if k%2 else 270,ink)
    add("canvas_paper","rect",left=0,top=0,width=1000,height=1000,fill=paper)
    # V7: 100 separate compositions: 25 distinct subjects, four layouts each.
    # No ring/dot template families. Text hierarchy varies by subject/layout.
    # The individual decorative pieces are editable Fabric objects.
    SUBJECTS = [
        ("WILD IRIS","BOTANICAL ATELIER","floral"),("THE VOW","WEDDING COLLECTION","ribbon"),
        ("MIDNIGHT JAZZ","THE LOUNGE","music"),("CASA AZUL","CERAMIC STUDIO","tile"),
        ("GOLDEN HOUR","THE COAST","sun"),("THE ORCHARD","HARVEST HOUSE","fruit"),
        ("NORTH STAR","THE EXPLORER","star"),("FLEUR DE LIS","MAISON ROYALE","fleur"),
        ("THE COFFEE CLUB","EST. 2026","coffee"),("THE OLIVE GROVE","MEDITERRANEAN","olive"),
        ("NO. 27","ART DECO EDITION","deco"),("THE PALM HOUSE","TROPICAL BOTANICS","palm"),
        ("LOVE LETTER","A CELEBRATION","heart"),("THE GARDEN PARTY","SUMMER EDITION","butterfly"),
        ("SAIL AWAY","THE MARINA","sail"),("THE BEEKEEPER","HONEY & CO.","bee"),
        ("MOUNTAIN AIR","WILDERNESS CLUB","mountain"),("THE PEONY","FLORAL SOCIETY","peony"),
        ("VINTAGE CELLAR","RESERVE COLLECTION","grape"),("THE ARTIST","CREATIVE STUDIO","brush"),
        ("THE HIGHLANDS","HERITAGE EDITION","thistle"),("THE MOON ROOM","NIGHT COLLECTION","moon"),
        ("LITTLE PARIS","CAFE SOCIETY","tower"),("THE KEEPSAKE","FOREVER & ALWAYS","key"),
        ("WILD MEADOW","NATURE COLLECTION","daisy"),
    ]
    subject = index % 25
    layout = index // 25
    heading, caption, motif = SUBJECTS[subject]
    # Each subject has its own background and contrast pairing.
    paper, ink, gold = PALETTES[(subject*7+layout*3)%10]
    objects.clear()
    add("canvas_paper","rect",left=0,top=0,width=1000,height=1000,fill=paper)
    def bez(k, pts, color=ink, sw=4):
        path(k,"M "+pts,"transparent",color,sw)
    def flower_at(k,x,y,r,n=7):
        for t in range(n):
            a=t*360/n
            petal(f"{k}_petal{t}",x,y,r,a,gold if t%2 else ink)
        disk(k+"_center",x,y,r*.13,paper,ink,2)
    def motif_at(k,x,y,s):
        if motif in ("floral","peony","daisy"):
            flower_at(k,x,y,85*s,9 if motif=="peony" else 7)
            for j in range(3):
                branch(f"{k}_stem{j}",x+(j-1)*30*s,y+35*s,85*s,70+j*20,4)
        elif motif in ("olive","palm","thistle"):
            for j in range(4):
                branch(f"{k}_branch{j}",x-80*s+j*53*s,y+70*s,160*s,230+j*24,7)
            if motif=="thistle": flower_at(k+"_head",x,y-50*s,70*s,11)
        elif motif in ("tile","deco","fleur"):
            for j in range(6):
                a=j*60
                px,py=x+110*s*math.cos(math.radians(a)),y+110*s*math.sin(math.radians(a))
                petal(f"{k}_tile{j}",px,py,100*s,a+90,ink if j%2 else gold)
            disk(k+"_center",x,y,30*s,gold)
        elif motif in ("sun","star","moon"):
            if motif=="moon":
                disk(k+"_moon",x,y,105*s,ink)
                disk(k+"_cutout",x+42*s,y-24*s,94*s,paper)
            else:
                disk(k+"_core",x,y,65*s,gold)
            for j in range(12 if motif=="sun" else 8):
                a=j*(30 if motif=="sun" else 45)
                px=x+95*s*math.cos(math.radians(a));py=y+95*s*math.sin(math.radians(a))
                qx=x+150*s*math.cos(math.radians(a));qy=y+150*s*math.sin(math.radians(a))
                line(f"{k}_ray{j}",px,py,qx,qy,ink,3)
        elif motif in ("fruit","grape"):
            for j in range(9):
                px=x+((j%3)-1)*48*s;py=y+(j//3-1)*50*s
                disk(f"{k}_fruit{j}",px,py,29*s,ink if j%2 else gold)
            branch(k+"_leaf",x-40*s,y-105*s,120*s,315,6)
        elif motif in ("coffee","bee"):
            if motif=="coffee":
                disk(k+"_saucer",x,y+50*s,100*s,gold)
                disk(k+"_cup",x,y+40*s,77*s,paper,ink,8)
                for j in range(3):
                    bez(f"{k}_steam{j}",f"{x-45*s+j*40*s:.1f} {y-55*s:.1f} Q {x-70*s+j*40*s:.1f} {y-110*s:.1f} {x-35*s+j*40*s:.1f} {y-145*s:.1f}",ink,5)
            else:
                oval(k+"_body",x,y,36*s,70*s,ink)
                for j in (-1,1):
                    oval(f"{k}_wing{j}",x+j*62*s,y-36*s,59*s,37*s,gold,j*25)
                for j in range(4):
                    line(f"{k}_stripe{j}",x-25*s,y-35*s+j*23*s,x+25*s,y-35*s+j*23*s,paper,5)
        elif motif in ("mountain","sail","tower"):
            if motif=="mountain":
                for j in range(3):
                    dx=(j-1)*95*s
                    path(f"{k}_peak{j}",f"M {x+dx-110*s:.1f} {y+100*s:.1f} L {x+dx:.1f} {y-115*s:.1f} L {x+dx+110*s:.1f} {y+100*s:.1f} Z",gold if j==1 else ink)
            elif motif=="sail":
                path(k+"_sail",f"M {x:.1f} {y-160*s:.1f} L {x:.1f} {y+90*s:.1f} L {x+120*s:.1f} {y+90*s:.1f} Z",gold)
                line(k+"_mast",x,y-170*s,x,y+130*s,ink,7)
                bez(k+"_hull",f"{x-135*s:.1f} {y+115*s:.1f} Q {x:.1f} {y+190*s:.1f} {x+145*s:.1f} {y+115*s:.1f}",ink,10)
            else:
                for j in range(4):
                    yy=y-120*s+j*68*s
                    line(f"{k}_floor{j}",x-(70-j*12)*s,yy,x+(70-j*12)*s,yy,ink,9)
                line(k+"_towerleft",x-72*s,y+145*s,x-24*s,y-145*s,gold,8)
                line(k+"_towerright",x+72*s,y+145*s,x+24*s,y-145*s,gold,8)
        elif motif in ("ribbon","heart","key"):
            if motif=="heart":
                path(k+"_heart",f"M {x:.1f} {y+115*s:.1f} C {x-240*s:.1f} {y-20*s:.1f} {x-100*s:.1f} {y-180*s:.1f} {x:.1f} {y-80*s:.1f} C {x+100*s:.1f} {y-180*s:.1f} {x+240*s:.1f} {y-20*s:.1f} {x:.1f} {y+115*s:.1f} Z",gold)
            elif motif=="key":
                disk(k+"_bow",x-70*s,y-45*s,67*s,"transparent",ink,11)
                line(k+"_shaft",x-20*s,y+3*s,x+140*s,y+140*s,gold,16)
                line(k+"_tooth",x+110*s,y+115*s,x+150*s,y+65*s,ink,11)
            else:
                for j in range(5):
                    bez(f"{k}_ribbon{j}",f"{x-145*s:.1f} {y+(j-2)*25*s:.1f} C {x-40*s:.1f} {y-115*s+j*12*s:.1f} {x+45*s:.1f} {y+120*s-j*12*s:.1f} {x+145*s:.1f} {y+(j-2)*25*s:.1f}",gold if j%2 else ink,5)
        elif motif in ("butterfly","music","brush"):
            if motif=="butterfly":
                for side in (-1,1):
                    oval(f"{k}_wing{side}a",x+side*70*s,y-55*s,72*s,93*s,gold,side*25)
                    oval(f"{k}_wing{side}b",x+side*65*s,y+50*s,56*s,64*s,ink,side*20)
                oval(k+"_body",x,y,12*s,105*s,ink)
            elif motif=="music":
                for j in range(3):
                    dx=(j-1)*90*s
                    disk(f"{k}_note{j}",x+dx,y+75*s,29*s,ink)
                    line(f"{k}_staff{j}",x+dx+25*s,y+75*s,x+dx+25*s,y-115*s,gold,8)
            else:
                for j in range(5):
                    a=j*36
                    petal(f"{k}_stroke{j}",x-85*s+j*42*s,y-30*s,160*s,a,gold if j%2 else ink)
        else:
            flower_at(k,x,y,90*s,8)
    # Each index has its OWN art direction: large-format geometric backgrounds,
    # alternating asymmetric blocks, botanical panels and engraved linework.
    # These are part of the artwork, not palette-only duplicates.
    def panel(k, points, color):
        d="M "+" L ".join(f"{px:.1f} {py:.1f}" for px,py in points)+" Z"
        path(k,d,color)
    def pattern_at(k,mode):
        # Each design uses a distinct deterministic composition, not a reused icon.
        phase=(index*137.508)%360
        if mode==0:  # hand-engraved radiating foliage
            for j in range(13+index%9):
                a=phase+j*360/(13+index%9)
                x,y=polar(265,a)
                branch(f"{k}_leaf{j}",x,y,85+(index%4)*12,a+125,5)
        elif mode==1:  # ceramic interlaced diamond tessellation
            for j in range(6):
                for h in range(6):
                    x=210+j*116+((h%2)*35);y=208+h*116
                    if (j*7+h*3+index)%4==0:
                        r=29+((j+h+index)%4)*9
                        panel(f"{k}_tile{j}_{h}",[(x,y-r),(x+r,y),(x,y+r),(x-r,y)],gold if j%2 else ink)
        elif mode==2:  # layered sun-and-sand abstract
            for j in range(7):
                x=230+j*92
                y=390+math.sin((j+index)*.75)*140
                panel(f"{k}_facet{j}",[(x-80,900),(x-80,y),(x+95,y-105),(x+95,900)],
                      gold if j%2 else ink)
        elif mode==3:  # vintage etching / corner engraving
            for j,(x,y) in enumerate(((280,290),(720,290),(280,710),(720,710))):
                flower_at(f"{k}_engraved{j}",x,y,58+(index%5)*6,8+(index%4))
                branch(f"{k}_branch{j}",x,y,120,j*90+index%35,7)
        elif mode==4:  # architectural arch repeat
            for j in range(5):
                x=235+j*132
                bez(f"{k}_arch{j}",f"{x-57} 760 Q {x-57} {160+(index%7)*8} {x} 240 Q {x+57} {160+(index%7)*8} {x+57} 760",gold,4)
        elif mode==5:  # dynamic botanical sweep
            for j in range(11):
                a=195+j*14+(index%5)*2
                x,y=polar(305,a)
                branch(f"{k}_sweep{j}",x,y,105+(j%4)*12,a+100,6)
        elif mode==6:  # ornate linear fan
            for j in range(27):
                a=200+j*5+(index%11)
                x,y=polar(120,a,500,730)
                xx,yy=polar(550,a,500,730)
                line(f"{k}_fan{j}",x,y,xx,yy,gold if j%3 else ink,2)
        elif mode==7:  # oversized floral wallpaper
            for j in range(7):
                x=260+(j%3)*230+((index*17+j*13)%55)
                y=260+(j//3)*230
                flower_at(f"{k}_wallflower{j}",x,y,80+(j*index)%35,9)
        elif mode==8:  # rippling illustrated contour lines
            for j in range(15):
                yy=200+j*42
                bez(f"{k}_wave{j}",f"145 {yy} C 320 {yy-110-index%30} 520 {yy+115+index%35} 855 {yy}",gold if j%3 else ink,3)
        else:  # illustrated celestial field
            for j in range(17):
                a=(j*137.508+index*29)%360
                r=155+((j*67+index*13)%220)
                x,y=polar(r,a)
                if j%3:
                    disk(f"{k}_star{j}",x,y,5+(j%4)*3,gold)
                else:
                    for t in range(4):
                        aa=t*90
                        xx,yy=polar(23,aa,x,y)
                        line(f"{k}_cross{j}_{t}",x,y,xx,yy,ink,3)
    # No two template indexes share this combination of geometry and placement.
    pattern_at("signature_surface", (index*7+index//10)%10)
    # ART-FIRST gallery: no mandatory text, brand badges or edition numbers.
    # 100 compositions are mapped to 100 distinct subject/geometry combinations.
    # Artwork is built from editable Fabric shapes rather than a flattened image.
    # Each card has a full-surface composition and can optionally receive text
    # from the customer in the editor.
    def fill_art(k,mode):
        if mode==0:  # botanical woodcut, asymmetric foliage
            for j in range(17):
                a=18+j*21+index*3
                x,y=polar(180+(j%4)*52,a)
                branch(f"{k}_foliage{j}",x,y,95+(j%3)*19,a+115,5+(j%3))
            for j in range(5):
                a=45+j*72+index*4
                x,y=polar(190,a)
                flower_at(f"{k}_flower{j}",x,y,55+(j%2)*22,9)
        elif mode==1:  # densely layered decorative ceramic mandala
            for ring in range(3):
                n=12+ring*8+(index%3)*4
                radius=95+ring*104
                for j in range(n):
                    a=j*360/n+(index*11)%360
                    x,y=polar(radius,a)
                    petal(f"{k}_mandala{ring}_{j}",x,y,52+ring*9,a+90,
                          gold if (j+ring)%3 else ink)
            disk(k+"_jewel",500,500,57,ink)
            disk(k+"_jewel_inset",500,500,31,gold)
        elif mode==2:  # bold stained glass, interlocking colour fields
            for j in range(14):
                a=j*360/14+index*7
                x,y=polar(330,a)
                xx,yy=polar(95,a+12)
                panel(f"{k}_glass{j}",[(500,500),(xx,yy),(x,y)],
                      ink if j%3==0 else gold)
            for j in range(8):
                a=j*45
                x,y=polar(220,a)
                disk(f"{k}_glass_center{j}",x,y,28,paper,ink,5)
        elif mode==3:  # landscape illustration with multiple horizon layers
            disk(k+"_sun",650,320,100,gold)
            for j in range(8):
                yy=420+j*64
                coords=[(110,900),(110,yy+30*math.sin(j+index))]
                for t in range(10):
                    x=120+t*82
                    y=yy+math.sin(t*.9+j*.7+index*.13)*55
                    coords.append((x,y))
                coords.append((890,900))
                panel(f"{k}_landscape{j}",coords,ink if j%2 else gold)
        elif mode==4:  # full-bleed floral textile
            for j in range(14):
                a=j*137.508+index*19
                r=65+(j*73)%285
                x,y=polar(r,a)
                flower_at(f"{k}_textile{j}",x,y,49+(j*13)%39,7+j%4)
                branch(f"{k}_textile_leaf{j}",x,y,73,a+75,4)
        elif mode==5:  # wood engraved concentric tree and branches
            for j in range(24):
                a=j*15+index*3
                x,y=polar(65,a)
                branch(f"{k}_tree{j}",x,y,250,a,6)
            disk(k+"_trunk",500,500,43,ink)
            for j in range(5):
                a=j*72
                x,y=polar(250,a)
                flower_at(f"{k}_tree_bloom{j}",x,y,42,7)
        elif mode==6:  # abstract terrazzo / resin fragments
            for j in range(48):
                a=(j*137.508+index*17)%360
                r=25+(j*79+index*9)%350
                x,y=polar(r,a)
                size=14+(j*11+index)%35
                panel(f"{k}_resin{j}",[(x-size,y-size*.3),(x+size*.4,y-size),
                      (x+size,y+size*.6),(x-size*.6,y+size)],
                      ink if j%4==0 else gold)
        elif mode==7:  # Japanese-inspired wave and fan illustration
            for j in range(13):
                y=205+j*48
                bez(f"{k}_wave{j}",f"115 {y} C 280 {y-135-index%40} 415 {y+135} 545 {y} C 680 {y-115} 770 {y+105} 885 {y}",ink if j%3==0 else gold,5)
            disk(k+"_rising_sun",500,365,97,gold)
        elif mode==8:  # ornate geometric wood lattice
            for j in range(9):
                for h in range(9):
                    x=220+j*70;y=220+h*70
                    if (x-500)**2+(y-500)**2>345**2:continue
                    r=23+((j+h+index)%3)*6
                    panel(f"{k}_lattice{j}_{h}",[(x,y-r),(x+r,y),(x,y+r),(x-r,y)],
                          ink if (j+h)%3==0 else gold)
                    disk(f"{k}_lattice_center{j}_{h}",x,y,4,paper)
        else:  # paisley / folk art
            for j in range(11):
                a=j*360/11+index*5
                x,y=polar(240,a)
                petal(f"{k}_paisley{j}",x,y,155,a+25,ink if j%2 else gold)
                petal(f"{k}_paisley_inset{j}",x,y,103,a+25,paper)
                flower_at(f"{k}_paisley_bud{j}",x,y,35,7)
    # Main artwork is the focus; no small repeated centre icons.
    # Unique 100-way pairing: primary and secondary treatments vary by index.
    primary = index % 10
    secondary = (index // 10 + (index % 10)*3) % 10
    fill_art("primary",primary)
    # Secondary overlays add detail without turning every template into
    # the same centre label. Use sparingly to preserve visual hierarchy.
    if index % 4 == 0:
        for j in range(5):
            a=(j*72+index*17)%360
            x,y=polar(315,a)
            flower_at(f"accent_bloom{j}",x,y,35,7)
    elif index % 4 == 1:
        for j in range(7):
            a=(j*360/7+index*9)%360
            x,y=polar(312,a)
            petal(f"accent_engraving{j}",x,y,62,a+90,ink)
    elif index % 4 == 2:
        for j in range(9):
            a=(j*40+index*13)%360
            x,y=polar(320,a)
            panel(f"accent_mosaic{j}",[(x,y-18),(x+18,y),(x,y+18),(x-18,y)],gold)
    else:
        for j in range(7):
            a=(j*360/7+index*11)%360
            x,y=polar(285,a)
            branch(f"accent_vine{j}",x,y,60,a+125,4)
    return objects
