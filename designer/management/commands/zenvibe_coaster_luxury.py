"""Editable luxury coaster vector designs, 100 variants."""
from __future__ import annotations
import math
import random

PALETTES = [
('#F7F1E7','#263E38','#B89457','#D8D0BE'),
('#122E2B','#F8F3E8','#C9A45D','#50796C'),
('#FCF7F2','#283C55','#D1A77E','#9AB7B1'),
('#182840','#F7EFD9','#D7B26E','#57718D'),
('#F2E4D5','#4E433E','#C1785D','#A7B6A2'),
('#1B262A','#FAF3E4','#C9A46E','#5D7C7A'),
('#F9E8E3','#4D394A','#C78696','#B9A6C8'),
('#F4F0E7','#173F45','#C6A475','#8CAFB0'),
('#F6F0DD','#504038','#A8805A','#94A17A'),
('#F3F5F0','#263D3B','#B9A76A','#8AADA5'),
]
NAMES=['Botanical Atelier','Art Deco','Terrazzo','Coastal','Marble Veins','Floral Garden','Mandala','Modern Abstract','Woodland','Geometric Mosaic']

def safe_artwork(product,index):
    """10 editable artwork families x 10 palette variants; 1000px artboard."""
    family=index%10
    variant=(index//10)%10
    bg,ink,gold,muted=PALETTES[variant]
    rnd=random.Random(index*7919+13)
    objects=[]
    def obj(name,kind,**kw):
        properties=dict(id=name,name=name.replace('_',' ').title(),type=kind,scaleX=1,scaleY=1,angle=0,opacity=1,selectable=True,evented=True,customerEditable=True)
        properties.update(kw)
        objects.append(properties)
    def rect(name,x,y,w,h,c):
        obj(name,'rect',left=x,top=y,width=w,height=h,fill=c,stroke=None,strokeWidth=0)
    def circ(name,x,y,r,c,stroke=None,sw=0):
        obj(name,'circle',left=x-r,top=y-r,radius=r,fill=c,stroke=stroke,strokeWidth=sw)
    def line(name,x1,y1,x2,y2,c,sw=3):
        obj(name,'line',left=x1,top=y1,x1=x1,y1=y1,x2=x2,y2=y2,stroke=c,strokeWidth=sw,fill=None)
    def ellipse(name,x,y,rx,ry,c,angle=0):
        obj(name,'ellipse',left=x-rx,top=y-ry,rx=rx,ry=ry,fill=c,stroke=None,strokeWidth=0,angle=angle)
    def text(name,s,x,y,w,size,color,weight='700',font='Georgia'):
        obj(name,'textbox',left=x,top=y,width=w,text=s,fontSize=size,fontFamily=font,fontWeight=weight,textAlign='center',lineHeight=1.12,fill=color,stroke=None,strokeWidth=0)
    rect('background',0,0,1000,1000,bg)
    def petal_cluster(prefix,x,y,scale=1,petals=6):
        for j in range(petals):
            a=2*math.pi*j/petals
            ellipse(f'{prefix}_petal_{j}',x+math.cos(a)*29*scale,y+math.sin(a)*29*scale,13*scale,26*scale,muted if j%2 else gold,math.degrees(a)+90)
        circ(prefix+'_centre',x,y,11*scale,ink)
    def leaf_branch(prefix,x,y,direction=1):
        line(prefix+'_stem',x,y,x+direction*95,y-170,ink,3)
        for j in range(5):
            px=x+direction*(15+j*16);py=y-30-j*28
            ellipse(f'{prefix}_leaf_a_{j}',px-13*direction,py,11,23,muted,-40*direction)
            ellipse(f'{prefix}_leaf_b_{j}',px+13*direction,py-8,11,23,gold,40*direction)
    # Reference-inspired artwork: saturated, full-area illustration with
    # a protected central brand zone. 10 distinct themes, each with 10
    # deterministic motif variations, rather than faint horizontal strokes.
    import colorsys
    variant_style = variant % 5
    def mix(a,b,t):
        aa=tuple(int(a.lstrip('#')[i:i+2],16) for i in (0,2,4))
        bb=tuple(int(b.lstrip('#')[i:i+2],16) for i in (0,2,4))
        return '#%02X%02X%02X'%tuple(round(u*(1-t)+v*t) for u,v in zip(aa,bb))
    vivid = [
        ('#103D35','#E9BD73','#E88A70','#F5D8A8'),
        ('#162F51','#A9D5E7','#E4A0B7','#F3E4C9'),
        ('#3B2447','#DDA9C8','#F2BF72','#E9E1C5'),
        ('#184C53','#F3C36D','#F08975','#E5E9C9'),
        ('#593B2F','#E7BA8E','#A8C1A1','#F7E8D3'),
        ('#253E2D','#D6C477','#D38D7A','#F1EAD5'),
        ('#283D63','#E5B87D','#A9BEDA','#F5EBDD'),
        ('#653D49','#E7C4A0','#B9CDB7','#F9EDE1'),
        ('#214850','#E0A17D','#E7D18C','#E8E9D5'),
        ('#3C3158','#C6AFDF','#F1A78C','#F3E6CB'),
    ]
    dark,light,rose,cream=vivid[variant]
    # Replace the generic first background with a theme-specific backdrop.
    objects[0]['fill']=dark if family in (0,1,6,8) else cream
    def motif_flower(prefix,x,y,r,petals=8):
        for j in range(petals):
            a=2*math.pi*j/petals
            ellipse(f'{prefix}_p{j}',x+math.cos(a)*r*.55,y+math.sin(a)*r*.55,
                    r*.22,r*.44,light if j%2 else rose,math.degrees(a)+90)
        circ(prefix+'_core',x,y,r*.19,gold)
        circ(prefix+'_dot',x,y,r*.075,dark)
    def motif_leaf(prefix,x,y,angle,scale=1):
        a=math.radians(angle)
        xx=x+math.cos(a)*48*scale; yy=y+math.sin(a)*48*scale
        line(prefix+'_stem',x,y,xx,yy,light,4)
        for j in range(3):
            d=(j+1)*12*scale
            cx=x+math.cos(a)*d;cy=y+math.sin(a)*d
            ellipse(f'{prefix}_leaf_l{j}',cx-12*scale,cy-8*scale,
                    10*scale,19*scale,rose,angle-35)
            ellipse(f'{prefix}_leaf_r{j}',cx+12*scale,cy+8*scale,
                    10*scale,19*scale,light,angle+35)
    def orbit(count,radius,fn):
        for j in range(count):
            a=2*math.pi*(j+.5*variant_style)/count
            fn(j,500+radius*math.cos(a),500+radius*math.sin(a),math.degrees(a))
    if family==0:  # Woodcut-inspired botanical foliage
        circ('engraved_frame',500,500,348,'transparent',light,7)
        orbit(12,285,lambda j,x,y,a:motif_leaf(f'botanical_{j}',x,y,a,1.15))
        for j in range(24):
            a=2*math.pi*j/24
            circ(f'botanical_bead_{j}',500+345*math.cos(a),500+345*math.sin(a),4,rose)
    elif family==1:  # Ornamental Art Deco fanwork
        for layer in range(3):
            orbit(16,235+layer*51,lambda j,x,y,a:ellipse(
                f'deco_fan_{layer}_{j}',x,y,10+layer*3,27+layer*5,
                light if (j+layer)%2 else rose,a+90))
        circ('deco_outer',500,500,353,'transparent',gold,5)
        circ('deco_inner',500,500,217,'transparent',light,3)
    elif family==2:  # Bold terrazzo, hand-cut aggregate
        for j in range(170):
            a=rnd.random()*2*math.pi
            radius=rnd.uniform(195,355)
            x=500+radius*math.cos(a);y=500+radius*math.sin(a)
            color=[dark,rose,light,gold][j%4]
            if j%3==0: circ(f'terrazzo_dot_{j}',x,y,rnd.uniform(5,16),color)
            else: ellipse(f'terrazzo_chip_{j}',x,y,rnd.uniform(7,20),
                          rnd.uniform(13,31),color,rnd.randrange(180))
    elif family==3:  # Coastal landscape / sunburst
        circ('coastal_sun',500,285,88,rose)
        for j in range(6):
            y=260+j*36
            for k in range(7):
                x=220+k*85
                if math.hypot(x-500,y-500)>355:continue
                circ(f'coastal_sky_{j}_{k}',x,y,6,light)
        for j in range(7):
            y=635+j*25
            for k in range(7):
                x=245+k*78
                if math.hypot(x-500,y-500)>340:continue
                ellipse(f'coastal_foam_{j}_{k}',x,y,32,8,
                        light if j%2 else rose)
    elif family==4:  # Mineral stone and gold inlay
        for j in range(130):
            a=rnd.random()*2*math.pi;r=rnd.uniform(195,355)
            x=500+r*math.cos(a);y=500+r*math.sin(a)
            ellipse(f'stone_{j}',x,y,rnd.uniform(6,28),rnd.uniform(6,19),
                    [rose,light,dark][j%3],rnd.randrange(180))
        for j in range(26):
            a=2*math.pi*j/26
            circ(f'gold_inlay_{j}',500+349*math.cos(a),500+349*math.sin(a),5,gold)
    elif family==5:  # Full botanical floral wreath
        orbit(12,290,lambda j,x,y,a:motif_flower(
            f'floral_{j}',x,y,51 if j%2 else 65,8))
        orbit(12,350,lambda j,x,y,a:motif_leaf(
            f'floral_sprig_{j}',x,y,a,.65))
    elif family==6:  # Detailed mandala, multiple radial rings
        for layer in range(5):
            count=12+layer*6
            radius=205+layer*35
            orbit(count,radius,lambda j,x,y,a:ellipse(
                f'mandala_{layer}_{j}',x,y,9+layer*2,21+layer*2,
                rose if (j+layer)%2 else light,a+90))
        circ('mandala_border',500,500,359,'transparent',gold,5)
    elif family==7:  # Modern cut-paper abstraction
        for j in range(65):
            a=rnd.random()*2*math.pi;r=rnd.uniform(210,345)
            x=500+r*math.cos(a);y=500+r*math.sin(a)
            if j%4==0: circ(f'abstract_disc_{j}',x,y,rnd.randint(15,39),
                            [dark,rose,light][j%3])
            else: ellipse(f'abstract_leaf_{j}',x,y,rnd.randint(10,30),
                          rnd.randint(25,55),[dark,rose,light][j%3],
                          rnd.randrange(180))
    elif family==8:  # Forest engraving / tree of life
        for j in range(14):
            a=2*math.pi*j/14
            x=500+275*math.cos(a);y=500+275*math.sin(a)
            line(f'forest_trunk_{j}',x,y+33,x,y-18,light,5)
            for k in range(3):
                circ(f'forest_crown_{j}_{k}',x+(k-1)*16,y-24,
                     21,rose if k==1 else light)
        circ('forest_border',500,500,356,'transparent',gold,5)
    else:  # Mosaic tiles / Portuguese azulejo
        for j in range(24):
            a=2*math.pi*j/24
            x=500+303*math.cos(a);y=500+303*math.sin(a)
            circ(f'mosaic_tile_{j}',x,y,30,rose if j%2 else light,
                 dark,3)
            circ(f'mosaic_center_{j}',x,y,10,dark)
        for j in range(16):
            a=2*math.pi*j/16
            x=500+237*math.cos(a);y=500+237*math.sin(a)
            ellipse(f'mosaic_inner_{j}',x,y,14,26,dark,math.degrees(a))
    # Dedicated central text plaque; no motif overlaps the text.
    circ('plaque_outer',500,500,201,cream,light,5)
    circ('plaque_inner',500,500,188,'transparent',gold,3)
    text('brand','YOUR BRAND',318,445,364,58,dark)
    line('brand_divider',396,519,604,519,gold,4)
    text('tagline',NAMES[family].upper(),330,551,340,19,dark,'700','Arial')
    return objects
