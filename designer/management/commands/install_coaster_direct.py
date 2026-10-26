"""Coaster-only installer: 100 editable brand-first layouts with matching previews.

No ZIP, network requests or source database required.
"""
from __future__ import annotations
import copy
import io
import math
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product
from .seed_calendar_editable_templates import rect, txt, circle
from .rebuild_coaster_previews import render

PALETTES = [
    ("#F8F3E9", "#213D35", "#C58D56"), ("#102E30", "#FAEED9", "#D9A65E"),
    ("#F6DCE1", "#66334A", "#C87689"), ("#E8F1EF", "#174B55", "#E4A064"),
    ("#242337", "#FFF5E6", "#D3AD75"), ("#F4E7D5", "#65432F", "#B88450"),
    ("#E8E7F3", "#393455", "#9A81BA"), ("#FFF5DC", "#3B4D38", "#D5A93F"),
    ("#DDE9F3", "#253C62", "#83A5C5"), ("#F4E6E1", "#743F43", "#C28E78"),
]
BRANDS = [
    ("NORTH & CO.", "CREATIVE STUDIO"), ("THE DAILY GRIND", "COFFEE ROASTERS"),
    ("MAISON BLOOM", "FLORAL ATELIER"), ("GOLDEN HOUR", "EVENTS & WEDDINGS"),
    ("KINFIELD", "NATURAL GOODS"), ("THE SOCIAL", "BAR & KITCHEN"),
    ("TERRA STUDIO", "DESIGN COMPANY"), ("SALT & SEA", "COASTAL LIVING"),
    ("LITTLE OAK", "HANDMADE WITH CARE"), ("ATELIER NO. 8", "EST. 2026"),
]
def editable(o):
    o.update(selectable=True, evented=True, customerEditable=True)
    return o
def ellipse(i,x,y,rx,ry,color,angle=0):
    return editable(dict(id=i,type="ellipse",left=x,top=y,rx=rx,ry=ry,angle=angle,fill=color))
def build(index):
    family=index//10
    variant=index%10
    bg,ink,accent=PALETTES[(family+variant)%10]
    brand,tagline=BRANDS[family]
    o=[rect("coaster-background",0,0,1000,1000,bg)]
    def add(x):o.append(x)
    def t(key,value,y,size=60,color=None,x=140,w=720,weight="700"):
        add(txt(key,x,y,w,value,size,color or ink,"center",weight,"Georgia"))
    def ring(radius,color,width=4):
        add(editable(dict(id="ring-%s"%len(o),type="circle",left=500-radius,top=500-radius,
                          radius=radius,fill="transparent",stroke=color,strokeWidth=width)))
    def petal(x,y,s=1):
        for j in range(6):
            a=math.tau*j/6
            add(ellipse("petal-%s"%len(o),x+math.cos(a)*35*s-17*s,
                        y+math.sin(a)*35*s-32*s,17*s,32*s,accent,math.degrees(a)))
        add(circle("flower-%s"%len(o),x-14*s,y-14*s,14*s,ink))
    def line(x,y,w,h,color=None):
        add(rect("line-%s"%len(o),x,y,w,h,color or accent))
    def leaves(x,y,scale=1):
        line(x,y,4*scale,190*scale,ink)
        for j in range(5):
            add(ellipse("leaf-%s"%len(o),x+(-50 if j%2 else 9)*scale,
                        y+(j*35)*scale,47*scale,18*scale,accent,25 if j%2 else -25))
    # Ten genuinely different structures; variation controls illustrations, not just palette.
    if family==0:  # identity / editorial
        if variant%2:line(160,205,680,6)
        t("hero-monogram","N",245,245)
        t("brand",brand,555,63)
        t("descriptor",tagline,658,29,accent)
        line(300,745,400,5)
    elif family==1:  # café iconography
        add(ellipse("cup",335,280,165,110,ink))
        add(ellipse("coffee",365,295,135,76,bg))
        add(circle("handle",650,330,48,accent))
        for k in range(3):add(ellipse("bean-%d"%k,290+k*175,220+(k%2)*80,20,42,accent,k*25))
        t("brand",brand,535,61)
        t("tagline",tagline,635,31,accent)
    elif family==2:  # botanical wreath
        leaves(210,315,1.2);leaves(780,315,1.2)
        if variant%2==0:petal(500,255,1.4)
        t("brand",brand,425,66)
        t("tagline",tagline,535,28,accent)
    elif family==3:  # wedding stationery
        ring(408,accent,4)
        for x,y in ((265,265),(735,265),(265,735),(735,735)):
            if variant%2==0:petal(x,y,.65)
        t("wedding","G  &  H",305,122)
        t("brand",brand,545,55)
        t("tagline",tagline,625,27,accent)
    elif family==4:  # natural goods
        add(circle("sun",380,210,120,accent))
        for j in range(4):line(135,590+j*55,730,13,ink if j%2 else accent)
        t("brand",brand,400,73)
        t("tagline",tagline,515,29)
    elif family==5:  # bold social / hospitality
        add(rect("central-panel",105,310,790,390,ink))
        t("brand",brand,395,95,bg)
        t("tagline",tagline,560,36,accent)
        for j in range(7):
            a=j*math.tau/7
            add(circle("confetti-%d"%j,450+math.cos(a)*355,450+math.sin(a)*355,14,accent))
    elif family==6:  # modern architecture
        line(205,195,590,7)
        for j in range(5):
            add(rect("column-%d"%j,220+j*118,230,35,230+(j%2)*70,accent if j%2 else ink))
        t("brand",brand,565,75)
        t("tagline",tagline,675,30,accent)
    elif family==7:  # coastal
        add(circle("sun",620,185,112,accent))
        for j in range(5):
            for k in range(5):
                add(ellipse("wave-%d-%d"%(j,k),-50+k*230,600+j*52,130,38,
                            ink if j%2 else accent))
        t("brand",brand,375,82)
        t("tagline",tagline,495,30)
    elif family==8:  # craft and botanical seal
        ring(380,ink,5)
        petal(500,305,1.55)
        t("brand",brand,475,75)
        t("tagline",tagline,590,30,accent)
        if variant%2:petal(500,750,.75)
    else:  # art deco label
        for j in range(7):
            line(205+j*97,185,4,135+(j%2)*55,accent)
        add(rect("label-panel",125,355,750,300,ink))
        t("brand",brand,420,74,bg)
        t("tagline",tagline,555,31,accent)
        for j in range(7):line(205+j*97,710,4,105+(j%2)*55,accent)
    # Distinct accent layouts within each theme.
    if variant in (1,4,7):
        add(circle("accent-dot-left",105,475,17,accent))
        add(circle("accent-dot-right",861,475,17,accent))
    if variant in (2,5,8):
        line(350,835,300,4,accent)
    return o

class Command(BaseCommand):
    help="Install 100 editable logo coaster designs directly in the existing product."
    def add_arguments(self,parser):
        parser.add_argument("--product-id",type=int,default=415)
        parser.add_argument("--shape",choices=("circle","square"),default="circle")
        parser.add_argument("--dry-run",action="store_true")
        parser.add_argument("--apply",action="store_true")
    def handle(self,*args,**opts):
        if opts["dry_run"] == opts["apply"]:
            raise CommandError("Use exactly one of --dry-run or --apply")
        if not Product.objects.filter(pk=opts["product_id"]).exists():
            raise CommandError("Coaster product does not exist")
        templates=list(DesignTemplate.objects.filter(product_id=opts["product_id"],
                                                      is_active=True).order_by("id"))
        if len(templates)!=100:
            raise CommandError("Expected 100 active coaster templates, found %d"%len(templates))
        prepared=[]
        for i,template in enumerate(templates):
            data=copy.deepcopy(template.json_data)
            if not isinstance(data,dict) or not data.get("pages"):
                raise CommandError("Template %s has no pages"%template.pk)
            objects=build(i)
            for page in data["pages"]:
                page["objects"]=copy.deepcopy(objects)
            for page in data.get("adminPages",[]):
                page["objects"]=copy.deepcopy(objects)
            data["generator"]="zenvibe-logo-coaster-direct-v1"
            image=render(objects,opts["shape"])
            buffer=io.BytesIO();image.save(buffer,format="PNG")
            prepared.append((template,data,buffer.getvalue()))
        self.stdout.write("Validated %d editable coaster designs and previews"%len(prepared))
        if opts["dry_run"]:
            self.stdout.write("Dry run: no changes made.")
            return
        with transaction.atomic():
            for i,(template,data,png) in enumerate(prepared):
                template.json_data=data
                template.preview.save("coaster-logo-%s-%03d.png"%(template.pk,i+1),
                                      ContentFile(png),save=False)
                template.save(update_fields=["json_data","preview"])
        self.stdout.write(self.style.SUCCESS("Updated 100 coaster templates and previews."))
