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
        objects.append(dict(id=name,name=name.replace('_',' ').title(),type=kind,scaleX=1,scaleY=1,angle=0,opacity=1,selectable=True,evented=True,customerEditable=True,**kw))
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
    if family==0:
        leaf_branch('left_botanical',285,670,1)
        leaf_branch('right_botanical',715,670,-1)
        leaf_branch('top_botanical',370,380,1)
        circ('botanical_mark',500,327,17,gold)
    elif family==1:
        for j in range(5):
            r=340-j*18
            circ(f'deco_frame_{j}',500,500,r,'transparent',gold if j%2==0 else muted,2)
        for j in range(7):
            a=math.pi+j*math.pi/6
            line(f'deco_ray_{j}',500+185*math.cos(a),500+185*math.sin(a),500+295*math.cos(a),500+295*math.sin(a),gold,3)
        rect('deco_centre_panel',285,399,430,203,bg)
    elif family==2:
        for j in range(72):
            a=rnd.random()*2*math.pi;r=rnd.uniform(260,335)
            x=500+r*math.cos(a);y=500+r*math.sin(a)
            if rnd.random()<.65:
                ellipse(f'terrazzo_chip_{j}',x,y,rnd.randint(5,13),rnd.randint(7,18),rnd.choice([ink,gold,muted]),rnd.randint(0,170))
            else:
                circ(f'terrazzo_stone_{j}',x,y,rnd.randint(4,10),rnd.choice([ink,gold,muted]))
    elif family==3:
        for j in range(22):
            yy=250+j*8
            for k in range(10):
                x=235+k*55;y=yy+10*math.sin(k*.85+j*.35)
                if math.hypot(x-500,y-500)<335:
                    line(f'coast_wave_{j}_{k}',x,y,x+45,y+8*math.sin((k+1)*.85+j*.35),muted if j%2 else gold,2)
        rect('coast_text_panel',287,421,426,177,bg)
    elif family==4:
        for j in range(9):
            for k in range(11):
                x=230+k*51;y=270+j*52+15*math.sin(k*.65+j)
                if math.hypot(x-500,y-500)>335 or 405<y<600:continue
                line(f'marble_vein_{j}_{k}',x,y,x+44,y+12*math.sin((k+1)*.65+j),gold if j%3==0 else muted,2)
    elif family==5:
        for j in range(10):
            a=j*math.pi/5+variant*.05
            petal_cluster(f'flower_{j}',500+295*math.cos(a),500+295*math.sin(a),.65 if j%2 else .85,5)
    elif family==6:
        for layer in range(4):
            n=10+layer*4;radius=240+layer*29
            for j in range(n):
                a=j*2*math.pi/n
                ellipse(f'mandala_{layer}_{j}',500+radius*math.cos(a),500+radius*math.sin(a),7+layer,13+layer,gold if (j+layer)%2 else muted,math.degrees(a)+90)
        circ('mandala_center_clear',500,500,185,bg)
    elif family==7:
        for j in range(12):
            a=j*math.pi/6
            ellipse(f'abstract_shape_{j}',500+280*math.cos(a),500+280*math.sin(a),23+rnd.randint(0,15),39+rnd.randint(0,25),gold if j%2 else muted,j*30)
    elif family==8:
        for j in range(8):
            a=2*math.pi*j/8;x=500+300*math.cos(a);y=500+300*math.sin(a)
            circ(f'woodland_canopy_{j}',x,y,20,muted)
            line(f'woodland_trunk_{j}',x,y+13,x,y+37,ink,3)
        circ('woodland_inner_ring',500,500,252,'transparent',gold,3)
    else:
        for j in range(24):
            a=j*math.pi/12;x=500+305*math.cos(a);y=500+305*math.sin(a)
            rect(f'mosaic_tile_{j}',x-12,y-12,24,24,gold if j%3==0 else muted)
        circ('mosaic_inner_ring',500,500,260,'transparent',ink,2)
    rect('brand_panel',299,419,402,164,bg)
    text('brand','YOUR BRAND',310,449,380,49,ink)
    line('brand_divider',403,516,597,516,gold,3)
    text('tagline',NAMES[family].upper(),330,539,340,17,gold,'700','Arial')
    return objects
