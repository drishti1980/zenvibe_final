"""Zenvibe coaster collection v5: 100 deterministic editable vector compositions.

Fabric-compatible objects. Shared 1000x1000 artwork supports circle and square.
All decoration stays in a circular safe radius of 360; background full bleed.
No third-party libraries required.
"""
from __future__ import annotations
import math
import random

INKS = ['#183B35','#1B3451','#482B40','#563A2E','#263F44','#34314E','#355044','#593E4E','#283B5B','#4E4235']
PAPERS = ['#F7F1E7','#F0F5F2','#FFF4ED','#F5EDE2','#F2F5F3','#F4F0F8','#F6F0DE','#F9EDEB','#EAF1F6','#F4EDE4']
ACCENTS = ['#C69B57','#8AAEB0','#D38A76','#B89465','#6A9C97','#B59BD0','#BBA45B','#D19C9D','#8BA7CF','#A98C68']
LABELS = ['BOTANICAL','ART DECO','MOSAIC','TERRAZZO','FLORAL','MARITIME','FOLK ART','HERITAGE','ABSTRACT','ORNAMENT']

def safe_artwork(product, index):
    if not 0 <= index < 100:
        raise ValueError('index must be 0..99')
    family = index // 10  # ten distinct art families
    composition = index % 10  # ten distinct compositions in each family
    rng = random.Random(770001 + index * 9187)
    ink, paper, accent = INKS[family], PAPERS[family], ACCENTS[family]
    obj = []
    def add(name, typ, **kwargs):
        data = dict(id=name, name=name.replace('_',' ').title(), type=typ,
                    left=0, top=0, scaleX=1, scaleY=1, angle=0,
                    opacity=1, selectable=True, evented=True, customerEditable=True)
        data.update(kwargs)
        obj.append(data)
    def circle(name,x,y,r,fill,stroke=None,sw=0):
        add(name,'circle',left=x-r,top=y-r,radius=r,fill=fill,stroke=stroke,strokeWidth=sw)
    def ellipse(name,x,y,rx,ry,fill,ang=0):
        add(name,'ellipse',left=x-rx,top=y-ry,rx=rx,ry=ry,fill=fill,
            angle=ang,stroke=None,strokeWidth=0)
    def rect(name,x,y,w,h,fill):
        add(name,'rect',left=x,top=y,width=w,height=h,fill=fill,stroke=None,strokeWidth=0)
    def line(name,x1,y1,x2,y2,color,width=3):
        add(name,'line',left=x1,top=y1,x1=x1,y1=y1,x2=x2,y2=y2,
            stroke=color,strokeWidth=width,fill=None)
    def text(name,content,x,y,w,size,color,weight='700'):
        add(name,'textbox',left=x,top=y,width=w,text=content,fontFamily='Georgia',
            fontSize=size,fontWeight=weight,textAlign='center',lineHeight=1.12,
            fill=color,stroke=None,strokeWidth=0)
    def flower(name,x,y,r,petals=8):
        for k in range(petals):
            a=2*math.pi*k/petals
            ellipse(f'{name}_petal_{k}',x+math.cos(a)*r*.52,
                    y+math.sin(a)*r*.52,r*.21,r*.39,
                    accent if k%2 else ink,math.degrees(a)+90)
        circle(f'{name}_centre',x,y,r*.16,paper)
    def leaf(name,x,y,a,s=1):
        a=math.radians(a)
        ex=x+math.cos(a)*45*s;ey=y+math.sin(a)*45*s
        line(f'{name}_stem',x,y,ex,ey,ink,3)
        for k in range(3):
            p=(k+1)/4
            xx=x+(ex-x)*p;yy=y+(ey-y)*p
            ellipse(f'{name}_leaf_{k}_a',xx-9*s,yy-9*s,8*s,16*s,accent,math.degrees(a)-30)
            ellipse(f'{name}_leaf_{k}_b',xx+9*s,yy+9*s,8*s,16*s,ink,math.degrees(a)+30)
    def polar(cx,cy,r,a):
        a=math.radians(a)
        return cx+r*math.cos(a),cy+r*math.sin(a)
    def inside(x,y,margin=15):
        return math.hypot(x-500,y-500)<355-margin
    rect('full_bleed_background',0,0,1000,1000,paper)
    # Ten families with varied motif placement. Every index changes actual
    # geometry (scale, count, distribution, rotation and arrangement).
    count=8+composition*2
    rotation=(composition*17)%360
    if family==0:  # Botanical engraving
        for j in range(count):
            a=rotation+j*360/count
            x,y=polar(500,500,270+(j%3)*22,a)
            leaf(f'botanical_{j}',x,y,a+180,.8+(j%4)*.13)
        for j in range(6+composition):
            a=rotation+j*360/(6+composition)
            x,y=polar(500,500,338,a)
            circle(f'botanical_berry_{j}',x,y,5+(j%3),accent)
    elif family==1:  # Art Deco arches and sunbursts
        for j in range(count):
            a=rotation+j*360/count
            x1,y1=polar(500,500,225,a);x2,y2=polar(500,500,330,a)
            line(f'deco_ray_{j}',x1,y1,x2,y2,ink,3+(j%3))
            x,y=polar(500,500,332,a)
            circle(f'deco_tip_{j}',x,y,7,accent)
        for j in range(2+composition%4):
            circle(f'deco_ring_{j}',500,500,285+j*16,'transparent',accent,2)
    elif family==2:  # Handcut mosaic tesserae
        for j in range(70+composition*11):
            a=rng.uniform(0,360);r=rng.uniform(220,341)
            x,y=polar(500,500,r,a)
            if j%4==0: circle(f'mosaic_disc_{j}',x,y,rng.randint(7,16),ink)
            else: ellipse(f'mosaic_tile_{j}',x,y,rng.randint(6,15),rng.randint(8,19),accent if j%3 else ink,rng.randrange(180))
    elif family==3:  # Terrazzo fragments, different density and stone size
        for j in range(65+composition*15):
            a=rng.uniform(0,360);r=rng.uniform(225,346)
            x,y=polar(500,500,r,a)
            if j%5==0:circle(f'stone_{j}',x,y,rng.randint(6,17),ink)
            else:ellipse(f'chip_{j}',x,y,rng.randint(6,21),rng.randint(10,26),accent if j%2 else ink,rng.randrange(180))
    elif family==4:  # Flower garland, petals
        for j in range(count):
            a=rotation+j*360/count
            x,y=polar(500,500,292,a)
            flower(f'floral_{j}',x,y,36+(j%3)*9,6+(j%3)*2)
    elif family==5:  # Maritime shells and wave segments
        for j in range(count):
            a=rotation+j*360/count
            x,y=polar(500,500,285,a)
            for k in range(5):
                px,py=polar(x,y,10+k*7,a+90)
                ellipse(f'shell_{j}_{k}',px,py,6+k,12+k,ink if k%2 else accent,a)
        for j in range(12+composition*2):
            a=rotation+j*360/(12+composition*2)
            x,y=polar(500,500,347,a)
            circle(f'pearl_{j}',x,y,4,accent)
    elif family==6:  # Folk-art flowers and hand-painted leaves
        for j in range(count):
            a=rotation+j*360/count
            x,y=polar(500,500,290,a)
            if j%2: flower(f'folk_flower_{j}',x,y,43,5)
            else:leaf(f'folk_leaf_{j}',x,y,a+180,1.0)
    elif family==7:  # Heritage filigree wreath
        for ring in range(2+composition%3):
            n=14+ring*6+composition
            for j in range(n):
                a=rotation+j*360/n
                x,y=polar(500,500,245+ring*39,a)
                ellipse(f'filigree_{ring}_{j}',x,y,7+ring*2,16+ring*3,accent if j%2 else ink,a+90)
    elif family==8:  # Organic abstract paper cut-outs
        for j in range(38+composition*7):
            a=rng.uniform(0,360);r=rng.uniform(225,339)
            x,y=polar(500,500,r,a)
            if j%6==0:circle(f'abstract_disc_{j}',x,y,rng.randint(9,28),ink)
            else:ellipse(f'abstract_form_{j}',x,y,rng.randint(8,23),rng.randint(17,42),accent if j%3 else ink,rng.randrange(180))
    else:  # Ornament radial medallions
        for j in range(count):
            a=rotation+j*360/count
            x,y=polar(500,500,290,a)
            circle(f'ornament_disc_{j}',x,y,21+(j%3)*3,accent)
            circle(f'ornament_cut_{j}',x,y,9,paper)
            x2,y2=polar(500,500,339,a)
            ellipse(f'ornament_tip_{j}',x2,y2,7,15,ink,a)
    # Distinct layout treatments. All essential type is within 190px radius.
    plaque=paper
    if composition in (0,3,6,9):
        circle('central_plaque',500,500,206,plaque,accent,4)
        circle('plaque_inset',500,500,193,'transparent',ink,2)
    elif composition in (1,4,7):
        rect('central_plaque',298,411,404,178,plaque)
        line('plaque_top',328,414,672,414,accent,5)
        line('plaque_bottom',328,585,672,585,accent,5)
    else:
        circle('central_plaque',500,500,210,plaque)
        for j in range(6):
            x,y=polar(500,500,198,rotation+j*60)
            circle(f'plaque_bead_{j}',x,y,5,accent)
    text('brand','YOUR BRAND',316,454,368,53,ink)
    line('brand_rule',395,523,605,523,accent,4)
    text('collection',LABELS[family],338,549,324,21,ink)
    return obj
