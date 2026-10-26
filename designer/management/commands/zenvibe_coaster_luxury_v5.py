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
    # Each family has a distinct visual architecture; the variations alter motif
    # geometry and placement, not just palette. The bleed background is full-size.
    if theme==0: # engraved botanical wreath
        n=7+variation
        for j in range(n):
            a=j*360/n+variation*8
            x,y=polar(298,a)
            branch(f"engraved_branch{j}",x,y,75,a+125,4+variation%3)
        frame("botanical_keyline",358,2)
    elif theme==1: # architectural art deco fan
        for sector in range(4+variation%3):
            angle=sector*360/(4+variation%3)+variation*6
            for j in range(9):
                a=angle-24+j*6
                x,y=polar(218,a);xx,yy=polar(345,a)
                line(f"fan{sector}_ray{j}",x,y,xx,yy,gold if j%2 else ink,2.7)
            x,y=polar(328,angle)
            medallion(f"fan{sector}_jewel",x,y,16)
        frame("deco_border",362,2)
    elif theme==2: # tile mosaic, actual interlocking diamonds
        for ring in range(3):
            n=16+ring*8+variation%4*4
            radius=226+ring*58
            for j in range(n):
                a=360*j/n+variation*7
                x,y=polar(radius,a)
                rr=11+ring*3
                path(f"tile{ring}_{j}",f"M {x:.1f} {y-rr:.1f} L {x+rr:.1f} {y:.1f} L {x:.1f} {y+rr:.1f} L {x-rr:.1f} {y:.1f} Z",ink if (j+ring)%3==0 else gold)
        frame("tile_border",364,1)
    elif theme==3: # oversized painted flowers, asymmetrical arrangement
        positions=[(265,280,80),(730,310,94),(285,720,76),(748,730,83)]
        for j,(x,y,r) in enumerate(positions):
            shift=variation*6*(1 if j%2 else -1)
            flower(f"painted_bloom{j}",x+shift,y-shift,r,7+(j+variation)%3,variation*13)
            branch(f"painted_sprig{j}",x+shift,y-shift,r*.9,45+j*90,4)
    elif theme==4: # blue-and-cream porcelain scrollwork
        frame("porcelain_rim",360,3)
        for j in range(6+variation%3):
            a=j*360/(6+variation%3)+variation*9
            x,y=polar(290,a)
            flower(f"porcelain_rosette{j}",x,y,49,6,a)
            branch(f"porcelain_vine{j}",x,y,68,a+145,4)
    elif theme==5: # intricate heritage engraving, corner clusters
        frame("engraving_frame",361,2)
        for j in range(4):
            a=45+j*90+variation*3
            x,y=polar(298,a)
            medallion(f"engraving_crest{j}",x,y,39)
            branch(f"engraving_scroll{j}",x,y,79,a+90,5)
        flourish("engraving_top",500,193,.65)
        flourish("engraving_bottom",500,807,.65,-1)
    elif theme==6: # ornate radial paisley-inspired petals
        n=8+variation%5
        for j in range(n):
            a=j*360/n+variation*11
            x,y=polar(226,a)
            petal(f"royal_outer{j}",x,y,117,a,gold)
            petal(f"royal_inlay{j}",x,y,86,a,ink)
            x2,y2=polar(334,a)
            disk(f"royal_pearl{j}",x2,y2,7,paper,ink,2)
        frame("royal_rim",362,1)
    elif theme==7: # folk art birds and flora, using editable silhouettes
        for j in range(4+variation%3):
            a=j*360/(4+variation%3)+variation*8
            x,y=polar(300,a)
            flower(f"folk_daisy{j}",x,y,49,8,a)
            branch(f"folk_vine{j}",x,y,82,a+165,5)
        for j in range(2):
            x=245+j*510;y=490+(-1)**j*42
            path(f"bird{j}",f"M {x-48} {y} Q {x-10} {y-58} {x+31} {y-4} Q {x+8} {y+41} {x-48} {y} Z",ink)
            petal(f"bird_wing{j}",x-2,y-4,46,25 if j else 155,gold)
            disk(f"bird_eye{j}",x+13,y-12,4,paper)
    elif theme==8: # refined monogram-style corner ornamentation
        frame("monogram_outline",362,2)
        for j in range(4):
            a=45+j*90
            x,y=polar(285,a)
            flourish(f"monogram_flourish{j}",x,y,.48,1 if j%2 else -1)
            medallion(f"monogram_seal{j}",x,y,24)
    else: # hand-drawn garden garland, detailed leaves and berries
        for j in range(12+variation):
            a=j*360/(12+variation)+variation*3
            x,y=polar(300,a)
            branch(f"garland_branch{j}",x,y,56,a+130,4)
            if j%3==0: flower(f"garland_flower{j}",x,y,40,6,a)
        frame("garland_keyline",360,1)
    # Type hierarchy is a deliberate editorial element, not a repeated central
    # badge. Different families use different brand treatments.
    if theme in (0,2,4,6,9):
        disk("ivory_letterpress_field",500,500,184,paper)
        txt("brand","YOUR BRAND",331,465,338,51,ink,weight="bold",spacing=65)
        txt("subtitle",NAMES[theme],335,543,330,19,gold,spacing=110)
        line("fine_rule",407,532,593,532,gold,2)
    elif theme in (1,5,8):
        add("architectural_label","rect",left=309,top=432,width=382,height=144,fill=paper)
        line("label_top",342,444,658,444,gold,3)
        txt("brand","YOUR BRAND",330,468,340,52,ink,weight="bold",spacing=55)
        txt("subtitle",NAMES[theme],343,543,314,18,gold,spacing=100)
    else:
        add("botanical_label","rect",left=312,top=435,width=376,height=139,fill=paper)
        txt("brand","YOUR BRAND",333,462,334,52,ink,weight="bold",spacing=60)
        flourish("label_flourish",500,542,.52)
    return objects
