"""Umbrella full-canopy editable artwork. Fabric path objects remain individually editable."""
from __future__ import annotations
import math
import colorsys

CENTER=(525,500)
RIM=[(525,105),(755,170),(865,425),(815,680),(660,830),(390,830),(235,680),(185,425),(295,170)]
THEMES=[
("Corporate", "NORTH / CO", "BRAND IDENTITY"),
("Wedding", "LOVE & ALWAYS", "OUR SPECIAL DAY"),
("Birthday", "LET'S CELEBRATE", "MAKE A WISH"),
("Festival", "GOOD VIBES", "LIVE • LOVE • MUSIC"),
("Sports", "THE CHAMPIONS", "ONE TEAM"),
("Travel", "WANDER MORE", "EXPLORE EVERYWHERE"),
("Nature", "WILD BLOOM", "GROW BEAUTIFULLY"),
("Luxury", "ATELIER", "SIGNATURE COLLECTION"),
("Photo", "YOUR MOMENTS", "ADD YOUR PHOTOS"),
("Community", "BETTER TOGETHER", "MAKE AN IMPACT"),
]
COLORS=[
("#0D467C","#EAF6FF","#F2A900"),("#7A264D","#FFF1E8","#D5A56D"),
("#6D28D9","#FDF2F8","#F9A826"),("#A9380D","#FFF2CB","#1D7C80"),
("#123E32","#F1FFF0","#F8BB3B"),("#125D86","#E7F8FF","#FF7B55"),
("#205A3B","#F4F6DE","#E7A5B3"),("#1E2237","#F7EAD3","#C49A49"),
("#77456C","#FFF2F5","#3D9FA8"),("#155E60","#FFF6DA","#DCA14A"),
]

def build_umbrella_v2(product,idx,rect,circle,text,line):
    if not 0 <= idx < 100:
        raise ValueError("Umbrella designs are numbered 0 through 99")
    theme,layout=divmod(idx,10)
    title,brand,subtitle=THEMES[theme]
    dark,light,accent=COLORS[theme]
    out=[]
    def path(name,d,fill,stroke=None,sw=0):
        out.append({"id":name,"name":name.replace("_"," ").title(),"type":"path",
                    "path":d,"fill":fill,"stroke":stroke,"strokeWidth":sw,
                    "left":0,"top":0,"scaleX":1,"scaleY":1,"angle":0,"opacity":1,
                    "customerEditable":True,"selectable":True,"evented":True})
    def poly(name,points,fill):
        d="M "+" L ".join(f"{x:.1f} {y:.1f}" for x,y in points)+" Z"
        path(name,d,fill)
    def circ(name,x,y,r,fill):
        out.append(circle(name,x,y,r,fill))
    def label(name,x,y,width,value,size,color,weight="800"):
        out.append(text(name,x,y,width,value,size,color,weight,"center"))
    def box(name,x,y,width,height,fill):
        out.append(rect(name,x,y,width,height,fill))
    # A true octagonal canopy base and eight independently editable fabric panels.
    # The central hub stays clear. Background is never the old black placeholder.
    poly("fabric_base",RIM,dark)
    for panel in range(8):
        a=RIM[panel];b=RIM[panel+1]
        colors=(
            [dark,light]*4 if layout==0 else
            [dark,dark,light,light]*2 if layout==1 else
            [light,dark,accent,dark]*2 if layout==2 else
            [dark,light,light,dark,accent,dark,light,dark] if layout==3 else
            [light,light,dark,dark,light,light,dark,dark] if layout==4 else
            [dark,accent,dark,light,dark,accent,dark,light] if layout==5 else
            [light,dark,dark,dark,light,dark,dark,dark] if layout==6 else
            [dark,dark,accent,accent,dark,dark,accent,accent] if layout==7 else
            [light,dark,light,dark,dark,light,dark,light] if layout==8 else
            [dark,light,dark,accent,light,dark,accent,dark]
        )
        poly(f"fabric_panel_{panel}",[(525,500),a,b],colors[panel])
    # Distinct visual storytelling: large illustrations and graphic systems.
    if theme==0:  # Corporate: bold identity / professional striping
        for j in range(3):
            poly(f"corporate_chevron_{j}",[(285+j*48,320),(325+j*48,320),
                (535+j*25,475),(510+j*25,475)],accent if j%2==0 else light)
    elif theme==1: # Wedding: floral sprays and rings
        for j,(x,y) in enumerate([(330,325),(715,330),(325,665),(720,670)]):
            for k in range(5):
                a=k*math.tau/5
                circ(f"petal_{j}_{k}",x+math.cos(a)*31,y+math.sin(a)*31,20,light)
            circ(f"flower_centre_{j}",x,y,16,accent)
    elif theme==2: # Birthday: streamers and confetti
        for j in range(14):
            x=260+(j*73)%535;y=250+(j*97)%490
            if 405<x<645 and 395<y<620: continue
            circ(f"party_confetti_{j}",x,y,10+(j%3)*5,accent if j%2 else light)
        poly("party_bunting",[(300,290),(370,345),(440,290),(510,345),(580,290),(650,345),(720,290)],accent)
    elif theme==3: # Festival: graphic sunburst
        for j in range(8):
            a=j*math.tau/8
            x=525+math.cos(a)*275;y=500+math.sin(a)*265
            circ(f"festival_light_{j}",x,y,22,accent)
    elif theme==4: # Sport: large athletic numbers and field marks
        label("team_number",320,245,410,str(10+idx),92,accent)
        for j in range(3):
            box(f"sport_stripe_{j}",315+j*22,665,16,115,accent)
    elif theme==5: # Travel: mountains and sunrise
        poly("mountain_far",[(235,630),(360,380),(470,560),(590,350),(805,630)],light)
        poly("mountain_near",[(235,680),(425,470),(535,610),(665,445),(815,680)],dark)
        circ("travel_sun",700,305,60,accent)
    elif theme==6: # Nature: distinct branching leaves
        for j in range(6):
            x=285+j*85;y=300+(j%2)*350
            poly(f"nature_leaf_{j}",[(x,y),(x+35,y-55),(x+65,y),(x+35,y+35)],accent if j%2 else light)
    elif theme==7: # Luxury: fine framed crest and medallion
        circ("luxury_medallion",525,320,94,accent)
        circ("luxury_inset",525,320,78,dark)
        label("luxury_monogram",460,270,130,"A",85,light)
    elif theme==8: # Photo: large editable image-placement areas
        for j,(x,y) in enumerate([(300,300),(660,300),(300,635),(660,635)]):
            box(f"photo_frame_{j}",x,y,100,100,light)
            label(f"photo_replace_{j}",x+8,y+38,84,"PHOTO",14,dark)
    else: # Community: connected geometric badges
        for j,(x,y) in enumerate([(330,320),(715,320),(330,680),(715,680)]):
            circ(f"community_disc_{j}",x,y,55,accent)
            circ(f"community_inner_{j}",x,y,35,light)
    # Make each layout meaningfully different in typography placement and hierarchy.
    placements=[(350,445,350),(350,575,350),(375,440,300),
                (355,555,340),(355,470,340),(350,545,350),
                (365,430,320),(350,565,350),(365,460,320),(350,520,350)]
    x,y,w=placements[layout]
    box("brand_panel",x-16,y-22,w+32,115,dark)
    label("brand_name",x,y,w,brand,34,light)
    label("brand_subtitle",x,y+52,w,subtitle,17,accent,"600")
    circ("hub",525,500,10,dark)
    # The editor expects Fabric-native objects with unique identifiers.
    for n,obj in enumerate(out):
        obj["id"]=f"umbrella_{idx+1:03d}_{n:03d}"
        obj["customerEditable"]=True
        obj["selectable"]=True
        obj["evented"]=True
    return 1050,1000,out
