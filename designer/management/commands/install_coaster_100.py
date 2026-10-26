"""Install 100 native editable JSON coaster templates. No JPEG or SVG assets required.

Uses the same Fabric JSON object conventions as seed_calendar_editable_templates.
Does not claim to recreate photo textures from a textual artwork description.
"""
from __future__ import annotations
import copy
import json
import math
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product
from .seed_calendar_editable_templates import rect, txt, circle
from .rebuild_coaster_previews import render

PAPERS=["#F6F0E7","#F1E7DF","#F2F4ED","#E8EFF2","#F7E5E8","#1D2936","#1D3733","#30283D","#EEE2D0","#FBF7EF"]
INKS=["#342F2C","#5B4338","#294A3B","#24445D","#79465C","#F9F1E5","#F4E7CE","#F4E9E0","#664B36","#3D4B3D"]
GOLDS=["#BA914C","#B18A55","#B19B69","#B6A18C","#C48F83","#D9B879","#C5A66A","#C4A8B6","#A47B50","#C3A76E"]
TITLES=["THE BOTANICAL HOUSE","GOOD VIBES","TROPICAL PARADISE","BLOOM WHERE YOU ARE PLANTED","ZEN LIVING","OCEAN BREEZE","GOOD FOOD GOOD MOOD","SIMPLE MOMENTS","COFFEE ALWAYS","HOME SWEET HOME","HERITAGE","STAY POSITIVE","LUXURY LIVING","BE KIND TO YOURSELF","NATURAL LIFE","ADVENTURE AWAITS","GRATEFUL TODAY","CREATE BEAUTIFUL THINGS","LOVE LAUGH LIVE","GOLDEN HOUR","BALANCE","FLOWERS & JOY","BEAUTY IN SIMPLICITY","ATELIER"]
SUBTITLES=["EST. 2026","THE SIGNATURE COLLECTION","HANDCRAFTED FOR YOU","LITTLE THINGS MATTER","MADE WITH LOVE","A BEAUTIFUL DAY","CURATED MOMENTS","SLOW LIVING","SPECIAL EDITION","THE ART OF EVERYDAY"]
def editable(o):
    o.update(selectable=True,evented=True,customerEditable=True)
    return o
def ellipse(name,x,y,rx,ry,color,angle=0):
    return editable(dict(id=name,type="ellipse",left=round(x,2),top=round(y,2),rx=rx,ry=ry,angle=angle,fill=color))
def line(name,x,y,w,h,color,weight=3):
    return editable(dict(id=name,type="rect",left=round(x,2),top=round(y,2),width=round(max(1,w),2),height=round(max(1,h),2),fill=color))
def objects_for(index):
    """25 composition types, 4 carefully coordinated palettes each; all JSON primitives."""
    theme=index%25; colorway=index//25
    p=(theme*3+colorway*7)%len(PAPERS)
    paper,ink,gold=PAPERS[p],INKS[p],GOLDS[p]
    soft=PAPERS[(p+3)%len(PAPERS)]
    o=[rect("paper",0,0,1000,1000,paper)]
    def add(x):o.append(x)
    def label(text,y,size=75,font="Georgia",weight="500",color=None):
        add(txt("title-"+str(len(o)),125,y,750,text,size,color or ink,"center",weight,font))
    def flower(cx,cy,scale=1):
        for j in range(6):
            a=j*math.pi/3
            add(ellipse("petal-"+str(len(o)),cx+math.cos(a)*48*scale-24*scale,cy+math.sin(a)*48*scale-36*scale,24*scale,36*scale,soft,math.degrees(a)))
        add(circle("flower-center-"+str(len(o)),cx-14*scale,cy-14*scale,14*scale,gold))
    def branch(cx,cy,flip=1):
        add(line("stem-"+str(len(o)),cx,cy,3,255,ink))
        for j in range(6):
            yy=cy+j*39
            add(ellipse("leaf-"+str(len(o)),cx+(15 if j%2 else -65)*flip,yy,42,19,gold if j%2 else ink,-28 if j%2 else 28))
    def ring(radius,stroke):
        add(editable(dict(id="ring-"+str(len(o)),type="circle",left=500-radius,top=500-radius,radius=radius,fill="rgba(0,0,0,0)",stroke=stroke,strokeWidth=3)))
    family=theme%12
    if family==0: # monogram with offset editorial rings
        ring(412,gold);ring(380,gold)
        label("ZV",345,215,"Georgia", "700",ink)
        label(TITLES[theme],635,42,color=gold)
    elif family==1: # botanical wreath
        ring(425,gold);branch(185,310);branch(805,310,-1)
        label(TITLES[theme],420,60)
        label(SUBTITLES[(theme+colorway)%10],565,30,color=gold)
    elif family==2: # porcelain flowers
        for x,y,s in [(195,200,1.2),(795,235,1),(225,790,1),(790,760,1.3)]:
            flower(x,y,s)
        ring(335,gold);label(TITLES[theme],430,63)
    elif family==3: # architectural / deco
        for j in range(12):
            add(line("ray-"+str(j),105+j*72,130,3,190+(j%3)*30,gold))
        add(rect("central-panel",145,365,710,280,soft,gold,4))
        label(TITLES[theme],455,59)
    elif family==4: # coastal waves
        for j in range(7):
            add(ellipse("wave-"+str(j),-120+j*160,680+(j%2)*45,185,110,gold if j%2 else soft))
        add(circle("sun",700,170,90,gold))
        label(TITLES[theme],390,70)
    elif family==5: # modern editorial
        add(rect("vertical-band",0,0,260,1000,ink))
        add(rect("accent-band",265,0,16,1000,gold))
        label(TITLES[theme],355,72)
        label(SUBTITLES[(theme+colorway)%10],525,28,color=gold)
    elif family==6: # ornamental mandala
        ring(435,gold)
        for j in range(18):
            a=j*math.pi/9
            add(ellipse("mandala-"+str(j),470+math.cos(a)*300,470+math.sin(a)*300,28,75,gold,math.degrees(a)))
        label(TITLES[theme],430,63)
    elif family==7: # terracotta / organic circles
        for j in range(5):
            add(circle("organic-"+str(j),-125+j*240,90+(j%2)*560,125,soft if j%2 else gold))
        label(TITLES[theme],425,69)
    elif family==8: # frame and corners
        add(rect("panel",110,110,780,780,soft,gold,5))
        for x,y in [(145,145),(855,145),(145,855),(855,855)]:
            flower(x,y,.7)
        label(TITLES[theme],420,70)
    elif family==9: # Japanese minimal
        add(circle("sun",320,160,180,gold))
        for j in range(4):add(line("horizon-"+str(j),90,730+j*42,820,3,ink))
        label(TITLES[theme],480,67)
    elif family==10: # elegant stripes
        for j in range(14):
            add(line("pinstripe-"+str(j),j*76,0,2,1000,gold))
        add(rect("label-panel",125,335,750,330,paper,gold,4))
        label(TITLES[theme],445,66)
    else: # geometric tile, botanical crest
        for j in range(8):
            x=95+(j%4)*230;y=90+(j//4)*750
            flower(x,y,.65)
        ring(325,gold);label(TITLES[theme],430,68)
    label(SUBTITLES[(theme+colorway)%10],875,24,color=gold)
    return o

class Command(BaseCommand):
    help="Install 100 JSON-native, editable coaster templates; no images required."
    def add_arguments(self,parser):
        parser.add_argument("--dry-run",action="store_true")
        parser.add_argument("--apply",action="store_true")
        parser.add_argument("--shape",choices=("circle","square"),default="circle")
    def handle(self,*args,**options):
        if options["dry_run"]==options["apply"]:
            raise CommandError("Specify exactly one of --dry-run or --apply.")
        product=Product.objects.filter(pk=415).first()
        if not product:
            raise CommandError("Coaster product 415 not found.")
        templates=list(DesignTemplate.objects.filter(product_id=415,is_active=True).order_by("id"))
        if len(templates)!=100:
            raise CommandError(f"Expected exactly 100 active templates; found {len(templates)}.")
        prepared=[]
        for i,t in enumerate(templates):
            if not isinstance(t.json_data,dict) or not t.json_data.get("pages"):
                raise CommandError(f"Template {t.pk} has no editable pages.")
            obj=objects_for(i)
            prepared.append((t,obj))
        self.stdout.write("Validated 100 native editable JSON designs; no JPG or SVG files required.")
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run successful; no database or preview changes."))
            return
        backup_dir=Path(settings.BASE_DIR)/"coaster_template_backups"
        backup_dir.mkdir(parents=True,exist_ok=True)
        backup=backup_dir/f"coasters_json_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        backup.write_text(json.dumps([{"id":t.pk,"name":t.name,"json_data":t.json_data,"preview":t.preview.name if t.preview else ""} for t,_ in prepared],default=str,indent=2),encoding="utf-8")
        with transaction.atomic():
            for i,(t,obj) in enumerate(prepared):
                data=copy.deepcopy(t.json_data)
                for page in data.get("pages",[]):
                    page["objects"]=copy.deepcopy(obj)
                for page in data.get("adminPages",[]):
                    page["objects"]=copy.deepcopy(obj)
                data.update(availableShapes=["Circle","Square"],shapeIndependentArtwork=True,constrainToPrintArea=True,coasterArtworkIndex=i,coasterArtworkSource="native-json")
                t.json_data=data
                t.save(update_fields=["json_data"])
        self.stdout.write(self.style.SUCCESS(f"Updated 100 editable JSON templates. Backup: {backup}. Existing previews unchanged; rebuild gallery previews separately."))
