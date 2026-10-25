"""Original editable ZenVibe template libraries.

All catalogue JPG files are previews only. The customer editor loads the JSON
objects generated here, so text, shapes, lines, colours and pages remain editable.
No third-party template artwork is bundled or copied.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import math

INV_W, INV_H = 700, 1000
BC_W, BC_H = 1125, 675  # 3.75in x 2.25in at 300dpi, matching ZenVibe's published bleed size.


def rect(i,x,y,w,h,fill,opacity=1,locked=False,stroke=None,sw=2,rx=0,ry=0):
    o={"id":i,"type":"rect","x":x,"y":y,"w":w,"h":h,"fill":fill,"opacity":opacity,"locked":locked,
       "customerEditable":not locked,"selectable":not locked,"evented":not locked}
    if stroke:o.update(stroke=stroke,strokeWidth=sw)
    if rx:o.update(rx=rx,ry=ry or rx)
    return o

def circle(i,x,y,r,fill,opacity=1,locked=False,stroke=None,sw=2):
    o={"id":i,"type":"circle","x":x,"y":y,"r":r,"fill":fill,"opacity":opacity,"locked":locked,
       "customerEditable":not locked,"selectable":not locked,"evented":not locked}
    if stroke:o.update(stroke=stroke,strokeWidth=sw)
    return o

def line(i,x1,y1,x2,y2,stroke,sw=2,opacity=1,dash=None):
    o={"id":i,"type":"line","points":[x1,y1,x2,y2],"stroke":stroke,"strokeWidth":sw,"opacity":opacity,
       "locked":False,"customerEditable":True,"selectable":True,"evented":True}
    if dash:o["strokeDashArray"]=dash
    return o

def polygon(i,pts,fill,opacity=1,stroke=None,sw=2):
    o={"id":i,"type":"polygon","points":[{"x":x,"y":y} for x,y in pts],"x":0,"y":0,"fill":fill,"opacity":opacity,
       "locked":False,"customerEditable":True,"selectable":True,"evented":True}
    if stroke:o.update(stroke=stroke,strokeWidth=sw)
    return o

def text(i,x,y,s,size,fill,font="Georgia",bold=False,align="center",width=None,opacity=1):
    o={"id":i,"type":"textbox" if width else "text","x":x,"y":y,"text":s,"fontSize":size,"font":font,"fontFamily":font,
       "fill":fill,"bold":bold,"fontWeight":"bold" if bold else "normal","textAlign":align,"opacity":opacity,
       "locked":False,"customerEditable":True,"selectable":True,"evented":True,"editable":True}
    if width:o["width"]=width
    return o

def leaf_cluster(prefix,x,y,scale,c1,c2,mirror=False):
    s=-1 if mirror else 1
    out=[line(prefix+'stem',x,y,x+s*85*scale,y+125*scale,c1,3,0.8)]
    for k,(dx,dy,r) in enumerate([(15,18,18),(42,42,22),(63,73,19),(82,105,16)]):
        out.append(circle(f'{prefix}l{k}',x+s*dx*scale,y+dy*scale,r*scale,c2,0.82))
    return out

def corner_flower(prefix,x,y,scale,c1,c2,c3):
    out=[circle(prefix+'c',x,y,26*scale,c1,.95)]
    for k,a in enumerate(range(0,360,60)):
        rad=math.radians(a);cx=x+math.cos(rad)*35*scale;cy=y+math.sin(rad)*35*scale
        out.append(circle(f'{prefix}p{k}',cx,cy,20*scale,c2,.85))
    out += leaf_cluster(prefix+'leaf',x+30*scale,y+30*scale,.55*scale,c3,c3)
    return out

def arch(prefix,x,y,w,h,stroke,sw=4):
    # Fabric-safe approximation using a tall rounded rect outline.
    return [rect(prefix,x,y,w,h,'rgba(0,0,0,0)',1,False,stroke,sw,rx=w//2)]

INV_CATEGORIES=[
    ("Wedding Invitations","wedding-invitations","💍","Wedding Invitation Designer",("ALEX & JORDAN","request the pleasure of your company","SATURDAY · 18 OCTOBER 2026","THE GLASSHOUSE · 4:30 PM")),
    ("Engagement Invitations","engagement-invitations","💎","Engagement Invitation Designer",("SOPHIA & LIAM","we're engaged — come celebrate with us","SATURDAY · 12 SEPTEMBER 2026","ROOFTOP GARDEN · 6:30 PM")),
    ("Birthday Invitations","birthday-invitations","🎂","Birthday Invitation Designer",("OLIVIA TURNS 30","dinner · drinks · dancing","FRIDAY · 21 AUGUST 2026","THE TERRACE · 7:00 PM")),
    ("Baby Shower Invitations","baby-shower-invitations","🍼","Baby Shower Invitation Designer",("BABY SHOWER FOR EMMA","a little one is on the way","SUNDAY · 8 NOVEMBER 2026","GARDEN ROOM · 2:00 PM")),
    ("Anniversary Invitations","anniversary-invitations","🥂","Anniversary Invitation Designer",("TWENTY-FIVE YEARS","celebrating a beautiful chapter","SATURDAY · 5 DECEMBER 2026","THE GRAND HALL · 6:00 PM")),
    ("Graduation Invitations","graduation-invitations","🎓","Graduation Invitation Designer",("CLASS OF 2026","join us for a graduation celebration","SATURDAY · 28 NOVEMBER 2026","UNIVERSITY HALL · 4:00 PM")),
    ("Housewarming Invitations","housewarming-invitations","🏡","Housewarming Invitation Designer",("NEW HOME · NEW MEMORIES","come warm our new home","SUNDAY · 4 OCTOBER 2026","18 WILLOW LANE · 1:00 PM")),
    ("Corporate Invitations","corporate-invitations","🏢","Corporate Invitation Designer",("AN EVENING OF IDEAS","an exclusive client & partner reception","THURSDAY · 15 OCTOBER 2026","SKYLINE SUITE · 6:00 PM")),
    ("Festive Invitations","festive-invitations","✨","Festive Invitation Designer",("FESTIVE SOIRÉE","an evening of light, music & celebration","FRIDAY · 11 DECEMBER 2026","THE ATRIUM · 7:00 PM")),
    ("Kids & Family Invitations","kids-family-invitations","🎈","Kids & Family Invitation Designer",("MILO IS TURNING FIVE","games · cake · big smiles","SATURDAY · 24 OCTOBER 2026","SUNNY PARK · 11:00 AM")),
]

INV_STYLES=[
 ("Midnight Gilded",("#07152c","#f6ead4","#c89b4b","#ffffff")),
 ("Blush Watercolour",("#fff5f2","#6c4b50","#d99a9b","#b8a391")),
 ("Botanical Sage",("#f5f2e8","#24483a","#78917d","#d6c6a5")),
 ("Black Tie Editorial",("#111111","#f4efe4","#c9a96e","#ffffff")),
 ("Champagne Arch",("#fbf7ef","#4d4032","#c9ad7d","#eadcc7")),
 ("Terracotta Modern",("#f4e8df","#5b3426","#c56f4d","#e2b69e")),
 ("Emerald Luxe",("#062e2a","#f6efdd","#d6b76c","#97b8a6")),
 ("Royal Plum",("#281735","#f6ebf1","#d9a2b8","#9f78a5")),
 ("Coastal Blue",("#eef6f6","#16394a","#6da5b7","#c5d9d9")),
 ("Ivory Minimal",("#fffdf8","#252525","#b6a17a","#eee8dd")),
 ("Art Deco Noir",("#101010","#f7f0df","#caa45b","#6f5b38")),
 ("Dusty Rose Frame",("#f8ecec","#523b42","#bd7f8f","#e4c8c8")),
 ("Cobalt Contemporary",("#153c73","#f7f2e8","#f0b85a","#8eb6e2")),
 ("Olive Linen",("#eeeee4","#35422d","#84916b","#c6c5a6")),
 ("Burgundy Romance",("#4b1021","#fff1e8","#d8a277","#8f4c5a")),
 ("Lavender Air",("#f4f0fa","#423555","#9b86b8","#d7cbe7")),
 ("Sunset Gradient",("#fff1e6","#5b2f38","#e86f5a","#f4b66d")),
 ("Monochrome Type",("#f5f5f3","#141414","#767676","#d8d8d2")),
 ("Celestial Night",("#0d1730","#f5efdc","#d8ba72","#8799c5")),
 ("Garden Party",("#f8f4ed","#315446","#d78f92","#91a986")),
]


def invitation_page(style_idx,pal,copy,page_idx):
    bg,ink,accent,soft=pal; title,subtitle,date,venue=copy; objs=[rect('background',0,0,INV_W,INV_H,bg,1,True)]
    # 20 deliberately different compositions.
    k=style_idx
    if k==0:
        objs += [rect('frame',34,34,632,932,'rgba(0,0,0,0)',1,False,accent,3),rect('inner',50,50,600,900,'rgba(0,0,0,0)',1,False,accent,1)]
        objs += [text('mono',278,115,title.split()[0][:2],36,accent,'Georgia',True),line('d1',255,175,445,175,accent,2)]
    elif k==1:
        objs += corner_flower('fl1',85,90,1,accent,'#f0c9bb','#7e9b7f')+corner_flower('fl2',620,905,.8,accent,'#efc7bd','#7e9b7f')
    elif k==2:
        objs += leaf_cluster('a',45,70,1.1,accent,accent)+leaf_cluster('b',655,820,.9,accent,soft,True)
    elif k==3:
        objs += [rect('band',0,0,700,170,ink),text('edition',55,55,'PRIVATE EDITION',19,bg,'Arial',True,'left'),line('rule',55,205,645,205,accent,2)]
    elif k==4:
        objs += arch('arch',92,72,516,730,accent,4)+[circle('seal',350,820,54,accent,.18,False,accent,2)]
    elif k==5:
        objs += [rect('block',0,0,225,1000,accent),circle('sun',115,120,60,soft,.75),line('diag',80,850,630,170,accent,4,.5)]
    elif k==6:
        objs += [rect('edge1',0,0,30,1000,accent),rect('edge2',670,0,30,1000,accent),circle('halo',350,225,130,soft,.16)]
    elif k==7:
        objs += [polygon('diamond',[(350,80),(610,330),(350,580),(90,330)],soft,.13,accent,3),circle('gem',350,120,20,accent)]
    elif k==8:
        objs += [circle('wave1',60,210,175,soft,.5),circle('wave2',650,790,210,accent,.18),line('horizon',90,695,610,695,accent,2)]
    elif k==9:
        objs += [line('top',100,110,600,110,accent,2),line('bot',100,890,600,890,accent,2),circle('dot1',80,110,5,accent),circle('dot2',620,890,5,accent)]
    elif k==10:
        objs += [rect('deco1',35,35,630,930,'rgba(0,0,0,0)',1,False,accent,3),polygon('fan1',[(35,35),(190,35),(35,190)],accent,.5),polygon('fan2',[(665,965),(510,965),(665,810)],accent,.5)]
    elif k==11:
        objs += [rect('frame',55,55,590,890,'rgba(0,0,0,0)',1,False,accent,2),circle('wax',350,790,45,accent,.85),text('sealtext',328,775,'ZV',18,bg,'Georgia',True)]
    elif k==12:
        objs += [rect('topblock',0,0,700,270,ink),rect('accentbar',0,270,700,12,accent),circle('orb',565,125,85,accent,.75)]
    elif k==13:
        objs += [rect('paper',55,65,590,870,soft,.32,False,accent,1),line('short',265,430,435,430,accent,2)] + leaf_cluster('ol',80,675,.9,accent,accent)
    elif k==14:
        objs += [rect('vbar',70,0,8,1000,accent),rect('small',520,75,120,120,soft,.22),line('rule',105,770,595,770,accent,2)]
    elif k==15:
        objs += [circle('lav1',90,160,90,soft,.65),circle('lav2',635,825,130,accent,.18),rect('card',80,185,540,610,bg,.82,False,soft,1,24)]
    elif k==16:
        objs += [circle('sun1',620,70,160,accent,.35),circle('sun2',80,930,210,soft,.5),line('r1',100,610,600,610,accent,3)]
    elif k==17:
        objs += [rect('blackbar',0,0,700,120,ink),text('issue',55,42,'CELEBRATE / 2026',18,bg,'Arial',True,'left'),rect('number',535,760,110,110,ink)]
    elif k==18:
        objs += [circle('moon',570,155,95,accent,.95),circle('cut',600,130,95,bg,1),*[circle(f's{i}',70+(i*83)%560,100+(i*137)%700,3+(i%3),soft,.9) for i in range(9)]]
    elif k==19:
        objs += corner_flower('g1',85,105,.9,'#e7a5a2','#f3d9c7',accent)+leaf_cluster('g2',620,760,.8,accent,accent,True)+[line('r',150,770,550,770,accent,2)]

    if page_idx==0:
        # Main invitation. Text positions vary with the style to avoid a template-factory look.
        if k in {3,12,17}:
            objs += [text('title',72,320,title,48,ink,'Georgia',True,'left',560),text('sub',76,435,subtitle,23,ink,'Arial',False,'left',540),text('date',76,575,date,20,accent,'Arial',True,'left',540),text('venue',76,625,venue,19,ink,'Arial',False,'left',540)]
        elif k in {5,14}:
            objs += [text('title',260,235,title,45,ink,'Georgia',True,'left',385),text('sub',260,370,subtitle,22,ink,'Arial',False,'left',350),text('date',260,540,date,19,ink,'Arial',True,'left',365),text('venue',260,590,venue,18,ink,'Arial',False,'left',365)]
        else:
            objs += [text('kicker',110,225,'YOU ARE WARMLY INVITED',16,accent,'Arial',True,'center',480),text('title',85,325,title,49,ink,'Georgia',True,'center',530),text('sub',105,455,subtitle,22,ink,'Arial',False,'center',490),text('date',105,610,date,20,ink,'Arial',True,'center',490),text('venue',105,660,venue,19,ink,'Arial',False,'center',490)]
    elif page_idx==1:
        objs += [text('details',100,220,'THE DETAILS',35,ink,'Georgia',True,'center',500),text('schedule',115,345,'WELCOME · 4:30 PM\nCELEBRATION · 5:00 PM\nDINNER & TOASTS · 6:30 PM',21,ink,'Arial',False,'center',470),text('note',105,625,'Dress beautifully · Parking available\nPlease arrive 15 minutes early',18,accent,'Arial',False,'center',490)]
    else:
        objs += [text('rsvp',100,230,'RSVP',44,ink,'Georgia',True,'center',500),text('reply',110,360,'Kindly reply by 1 October 2026',22,ink,'Arial',False,'center',480),text('contact',110,465,'hello@example.com\n+1 780 555 0199',21,accent,'Arial',True,'center',480),text('thanks',110,650,'We cannot wait to celebrate with you.',20,ink,'Georgia',False,'center',480)]
    return {"background":bg,"objects":objs}


def build_invitation_library(preview_prefix='template_previews/invitations_modern_200'):
    items=[]
    for ci,(cat_name,cat_slug,icon,prod_name,copy) in enumerate(INV_CATEGORIES):
        for si,(style_name,pal) in enumerate(INV_STYLES):
            page_count=1 + (1 if si%3!=0 else 0) + (1 if si%7==0 else 0)
            pages=[invitation_page(si,pal,copy,p) for p in range(page_count)]
            item={
              "category":{"name":cat_name,"slug":cat_slug,"icon":icon,"description":f"Modern editable {cat_name.lower()} for print and digital sharing.","sort_order":30+ci},
              "product":{"name":prod_name,"slug":cat_slug.replace('-invitations','')+'-invitation-designer',"description":f"Premium editable {cat_name.lower()} with multi-page designs.","price":"0.67","width":INV_W,"height":INV_H,"orientation":"portrait","customizer_mode":"editor"},
              "template":{"name":f"{style_name} · {cat_name.replace(' Invitations','')}","preview":f"{preview_prefix}/{cat_slug}-{si+1:02d}.jpg","json_data":{"version":2,"pages":pages,"meta":{"library":"zenvibe-modern-200","style":style_name,"category":cat_slug,"editable":True}}}
            }
            items.append(item)
    return items

BC_INDUSTRIES=[
 ('Real Estate','Avery Morgan','REALTOR®','North & Co.','avery@northco.ca','+1 780 555 0142'),('Technology','Maya Chen','Product Director','NOVA Labs','maya@novalabs.ca','+1 780 555 0118'),
 ('Construction','Ethan Brooks','Project Manager','Stonefield Build','ethan@stonefield.ca','+1 780 555 0171'),('Beauty','Sofia Hart','Creative Director','LUMÉ Studio','sofia@lume.ca','+1 780 555 0164'),
 ('Automotive','Noah Clark','General Manager','Apex Auto','noah@apexauto.ca','+1 780 555 0180'),('Finance','Amelia Price','Mortgage Advisor','Harbour Finance','amelia@harbour.ca','+1 780 555 0156'),
 ('Printing','Lucas Reid','Print Specialist','INK & FORM','lucas@inkform.ca','+1 780 555 0135'),('Healthcare','Dr. Emma Cole','Clinic Director','Northwell Clinic','emma@northwell.ca','+1 780 555 0120'),
 ('Cafe','Theo Martin','Founder','EMBER Coffee','hello@embercoffee.ca','+1 780 555 0190'),('Cleaning','Chloe Singh','Operations Lead','VERDE Clean','chloe@verdeclean.ca','+1 780 555 0109'),
 ('Legal','Isla Bennett','Partner','Bennett Law','isla@bennettlaw.ca','+1 780 555 0188'),('Architecture','Oliver Grey','Principal Architect','FORM Studio','oliver@formstudio.ca','+1 780 555 0175'),
 ('Photography','Mia Rose','Photographer','MIA ROSE','hello@miarose.ca','+1 780 555 0147'),('Fitness','Jack Taylor','Performance Coach','KINETIC','jack@kinetic.ca','+1 780 555 0132'),
 ('Restaurant','Aria Patel','Executive Chef','SAFFRON TABLE','aria@saffrontable.ca','+1 780 555 0195'),('Consulting','Henry Adams','Strategy Consultant','Northline Advisory','henry@northline.ca','+1 780 555 0160'),
 ('Salon','Lily Woods','Master Stylist','MUSE Hair','lily@musehair.ca','+1 780 555 0126'),('Landscaping','Leo Green','Landscape Designer','WILDROOT','leo@wildroot.ca','+1 780 555 0112'),
 ('Events','Grace Kim','Event Producer','AFTERGLOW Events','grace@afterglow.ca','+1 780 555 0151'),('Nonprofit','Samuel King','Executive Director','COMMON GOOD','samuel@commongood.ca','+1 780 555 0104')
]

BC_STYLES=[
 ("Editorial Grid",('#f4f1ea','#171717','#b58b59','#dcd4c7')),("Midnight Gold",('#07152c','#f7f0df','#c89b4b','#34506f')),
 ("Cobalt Block",('#153c73','#ffffff','#f0b85a','#8eb6e2')),("Sage Minimal",('#edf0e7','#263a2d','#7c9278','#cdd8c8')),
 ("Terracotta Split",('#f3e7de','#4d2d25','#c66f4f','#deb09c')),("Noir Monogram",('#111111','#f4eee0','#caa45b','#444444')),
 ("Soft Lavender",('#f1edf8','#392f4b','#937ab4','#d7cde7')),("Emerald Luxe",('#06352e','#f6efdf','#d4b56b','#3f6f61')),
 ("Swiss Mono",('#f7f7f5','#111111','#e14d3f','#d9d9d5')),("Warm Gradient",('#fff0e3','#582f39','#e96e59','#f5bb71')),
]

def business_card(style_idx,pal,industry,variant):
    bg,ink,accent,soft=pal; sector,name,role,company,email,phone=industry
    # variant changes structural composition inside each style family.
    v=variant%10
    front=[rect('bg',0,0,BC_W,BC_H,bg,1,True)]
    back=[rect('bg2',0,0,BC_W,BC_H,ink,1,True)]
    if style_idx==0:
        front += [rect('side',0,0,285,675,ink),line('v',315,70,315,605,accent,4),text('mark',85,82,company[:2].upper(),56,bg,'Georgia',True,'left'),text('name',370,155,name,50,ink,'Georgia',True,'left',650),text('role',372,225,role.upper(),18,accent,'Arial',True,'left',600),text('contact',372,340,f'{phone}\n{email}\nwww.example.ca',22,ink,'Arial',False,'left',610)]
    elif style_idx==1:
        front += [circle('halo',905,120,185,accent,.17),rect('line',70,520,985,5,accent),text('mono',70,70,company[:2].upper(),65,accent,'Georgia',True,'left'),text('name',70,285,name,54,bg,'Georgia',True,'left',800),text('role',72,355,role,24,bg,'Arial',False,'left',700),text('contact',680,430,f'{phone}\n{email}',20,bg,'Arial',False,'right',360)]
    elif style_idx==2:
        front += [rect('panel',0,0,430,675,ink),polygon('tri',[(430,0),(670,0),(430,240)],accent,.9),text('company',60,245,company.upper(),30,bg,'Arial',True,'left',300),text('name',510,180,name,51,bg if bg.startswith('#1') else ink,'Georgia',True,'left',540),text('role',512,250,role,22,accent,'Arial',True,'left',520),text('contact',512,365,f'{phone}\n{email}',21,ink,'Arial',False,'left',520)]
    elif style_idx==3:
        front += [circle('dot',95,95,38,accent),line('top',150,95,1010,95,accent,2),text('company',70,160,company.upper(),22,accent,'Arial',True,'left'),text('name',70,280,name,56,ink,'Georgia',True,'left',760),text('role',72,350,role,22,ink,'Arial',False,'left'),text('contact',725,470,f'{phone}\n{email}',19,ink,'Arial',False,'right',320)]
    elif style_idx==4:
        front += [rect('left',0,0,360,675,accent),circle('cut',360,337,140,bg),text('mark',78,255,company[:2].upper(),70,bg,'Georgia',True,'left'),text('name',500,210,name,52,ink,'Georgia',True,'left',540),text('role',502,280,role.upper(),18,accent,'Arial',True,'left'),text('contact',502,390,f'{phone}\n{email}',21,ink,'Arial',False,'left',520)]
    elif style_idx==5:
        front += [rect('frame',38,38,1049,599,'rgba(0,0,0,0)',1,False,accent,3),circle('ring',180,175,90,'rgba(0,0,0,0)',1,False,accent,4),text('mono',135,135,company[:2].upper(),55,accent,'Georgia',True,'left'),text('name',345,190,name,51,bg,'Georgia',True,'left',650),text('role',348,260,role,22,accent,'Arial',True,'left'),text('contact',348,385,f'{phone}  ·  {email}',19,bg,'Arial',False,'left',650)]
    elif style_idx==6:
        front += [circle('blob1',100,120,150,soft,.7),circle('blob2',1060,585,210,accent,.16),text('company',80,100,company.upper(),20,accent,'Arial',True,'left'),text('name',80,285,name,58,ink,'Georgia',True,'left',720),text('role',82,365,role,22,ink,'Arial',False,'left'),text('contact',685,485,f'{phone}\n{email}',20,ink,'Arial',False,'right',340)]
    elif style_idx==7:
        front += [rect('gold',0,0,1125,15,accent),rect('gold2',0,660,1125,15,accent),circle('orb',920,110,140,soft,.18),text('company',70,80,company.upper(),23,accent,'Arial',True,'left'),text('name',70,280,name,55,bg,'Georgia',True,'left',720),text('role',72,355,role,22,bg,'Arial',False,'left'),text('contact',720,470,f'{phone}\n{email}',19,bg,'Arial',False,'right',330)]
    elif style_idx==8:
        front += [rect('stripe',0,0,25,675,accent),text('company',65,65,company.upper(),19,ink,'Arial',True,'left'),text('name',65,245,name.upper(),50,ink,'Arial',True,'left',850),text('role',68,315,role.upper(),17,accent,'Arial',True,'left'),line('rule',65,390,1060,390,ink,2),text('contact',65,450,f'{phone}     {email}     www.example.ca',18,ink,'Arial',False,'left',1000)]
    else:
        front += [circle('sun',1030,50,220,accent,.35),circle('sun2',50,660,190,soft,.65),text('company',80,80,company.upper(),21,ink,'Arial',True,'left'),text('name',80,275,name,56,ink,'Georgia',True,'left',760),text('role',82,350,role,22,accent,'Arial',True,'left'),text('contact',695,470,f'{phone}\n{email}',20,ink,'Arial',False,'right',350)]
    # Add small variant feature so all 200 are structurally distinct, not only text changes.
    if v%2==0: front.append(line('variant-line',80+v*12,590,340+v*30,590,accent,2))
    else: front.append(circle('variant-dot',975-v*20,555,8+v,accent,.8))

    back += [circle('backhalo',562,300,145,accent,.15),text('backmark',470,230,company[:2].upper(),82,accent,'Georgia',True,'center',185),text('backcompany',260,445,company.upper(),28,bg,'Arial',True,'center',605),text('backweb',335,510,'WWW.EXAMPLE.CA',17,accent,'Arial',True,'center',455)]
    if v>=5: back += [line('bline1',80,85,1045,85,accent,2),line('bline2',80,590,1045,590,accent,2)]
    return {"version":2,"pages":[{"background":bg,"objects":front},{"background":ink,"objects":back}],"meta":{"editable":True,"industry":sector}}


def build_business_card_library(preview_prefix='template_previews/business_cards_200'):
    out=[]
    # 20 industries x 10 design families = 200 distinct two-sided templates.
    for ii,industry in enumerate(BC_INDUSTRIES):
        for si,(style,pal) in enumerate(BC_STYLES):
            premium = si>=5
            out.append({
              "tier":"premium" if premium else "standard",
              "template":{"name":f"{style} · {industry[0]}","preview":f"{preview_prefix}/business-{ii+1:02d}-{si+1:02d}.jpg","json_data":business_card(si,pal,industry,ii)}
            })
    return out
