"""Install 100 editable coaster layouts, keeping existing template IDs."""
import copy
import io
import math
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product
from .seed_calendar_editable_templates import rect, txt, circle
from .rebuild_coaster_previews import render

PALETTES=[
 ("#F8F0E5","#24463E","#BE875C"),("#F9E5DF","#633D50","#D18C85"),
 ("#E7F0F2","#244E6C","#D99B5F"),("#F5EFCF","#57452D","#C78C48"),
 ("#E9E8F2","#40395E","#A68BC4"),("#172E2D","#F8EACD","#C7A268"),
 ("#2B2639","#F8EDF3","#CB9DB7"),("#F0F2E9","#34513D","#A6B88A"),
 ("#F9E9DB","#704B3A","#D49D6B"),("#E4EDF4","#263C60","#83A9C8")]
THEMES=[
 ("COFFEE & CO.","FRESHLY BREWED"),("THE BOTANICAL","GROW WITH LOVE"),
 ("LOVE ALWAYS","EST. 2026"),("STUDIO NORTH","CREATIVE COMPANY"),
 ("GOOD VIBES","ALL DAY LONG"),("THE SOCIAL CLUB","GOOD TIMES"),
 ("SUNDAY BRUNCH","SERVED WITH LOVE"),("WILD FLOWER","IN FULL BLOOM"),
 ("MONOGRAM","PERSONALISED FOR YOU"),("THE COAST","SUN & SEA")]
def ellipse(id,x,y,rx,ry,fill,angle=0):
 return dict(id=id,type="ellipse",left=x,top=y,rx=rx,ry=ry,angle=angle,fill=fill,selectable=True,evented=True,customerEditable=True)
def build(i):
 bg,ink,accent=PALETTES[(i//10+i%10)%10]
 title,subtitle=THEMES[i//10]
 mode=i%10
 o=[rect("background",0,0,1000,1000,bg)]
 def add(obj):o.append(obj)
 def text(id,value,y,size=65,color=None):
  add(txt(id,125,y,750,value,size,color or ink,"center","700","Georgia"))
 def ring(r,colour):
  add(dict(id="ring-"+str(len(o)),type="circle",left=500-r,top=500-r,radius=r,fill="rgba(0,0,0,0)",stroke=colour,strokeWidth=5,selectable=True,evented=True,customerEditable=True))
 def flower(x,y,scale=1):
  for k in range(7):
   a=k*math.tau/7
   add(ellipse("petal-"+str(len(o)),x+math.cos(a)*50*scale-24*scale,y+math.sin(a)*50*scale-35*scale,24*scale,35*scale,accent,math.degrees(a)))
  add(circle("flower-core-"+str(len(o)),x-19*scale,y-19*scale,19*scale,ink))
 def leaves(x,y):
  add(rect("stem-"+str(len(o)),x,y,5,250,ink))
  for k in range(5):
   add(ellipse("leaf-"+str(len(o)),x+(-65 if k%2 else 8),y+k*47,60,23,accent,35 if k%2 else -35))
 if mode==0:
  ring(415,accent);ring(390,ink);text("headline",title,405,66);text("tagline",subtitle,555,32,accent)
 elif mode==1:
  leaves(220,280);leaves(780,280);text("headline",title,425,65);text("tagline",subtitle,550,28,accent)
 elif mode==2:
  for x,y in ((200,200),(790,220),(210,780),(790,790)):flower(x,y,.9)
  text("headline",title,425,63);text("tagline",subtitle,540,30)
 elif mode==3:
  add(rect("editorial-band",0,0,260,1000,ink));add(rect("thin-band",270,0,16,1000,accent))
  text("headline",title,400,64);text("tagline",subtitle,540,28,accent)
 elif mode==4:
  for k in range(9):add(rect("deco-ray-"+str(k),150+k*86,140,5,170+(k%3)*35,accent))
  add(rect("title-panel",120,350,760,310,bg,ink,4));text("headline",title,430,62)
 elif mode==5:
  for k in range(5):add(circle("orb-"+str(k),-110+k*245,80+(k%2)*610,130,accent))
  text("headline",title,425,67);text("tagline",subtitle,555,30)
 elif mode==6:
  add(circle("sun",660,140,95,accent))
  for k in range(5):add(ellipse("wave-"+str(k),-140+k*230,690+(k%2)*50,180,100,ink if k%2 else accent))
  text("headline",title,400,65)
 elif mode==7:
  ring(420,accent)
  for k in range(16):
   a=k*math.tau/16
   add(ellipse("mandala-"+str(k),475+math.cos(a)*305,475+math.sin(a)*305,25,67,accent,math.degrees(a)))
  text("headline",title,425,62)
 elif mode==8:
  add(rect("inner-frame",110,110,780,780,bg,accent,5))
  for x,y in ((180,180),(820,180),(180,820),(820,820)):flower(x,y,.65)
  text("headline",title,420,62)
 else:
  for k in range(11):add(rect("stripe-"+str(k),k*95,0,3,1000,accent))
  add(rect("title-plaque",120,345,760,320,bg,ink,5))
  text("headline",title,420,65);text("tagline",subtitle,560,28,accent)
 return o

class Command(BaseCommand):
 help="Replace artwork in 100 existing coaster templates with editable vector designs and previews."
 def add_arguments(self,p):
  p.add_argument("--product-id",type=int,default=415)
  p.add_argument("--shape",choices=["circle","square"],default="circle")
  p.add_argument("--dry-run",action="store_true")
  p.add_argument("--apply",action="store_true")
 def handle(self,*args,**options):
  if options["dry_run"]==options["apply"]:raise CommandError("Choose exactly one of --dry-run or --apply")
  product=Product.objects.filter(pk=options["product_id"]).first()
  if product is None:raise CommandError("Product not found")
  templates=list(DesignTemplate.objects.filter(product=product,is_active=True).order_by("id"))
  if len(templates)!=100:raise CommandError("Expected exactly 100 active templates; found %d"%len(templates))
  prepared=[]
  for i,t in enumerate(templates):
   if not isinstance(t.json_data,dict) or not t.json_data.get("pages"):raise CommandError("Invalid template JSON: %s"%t.pk)
   objects=build(i)
   image=render(objects,options["shape"])
   out=io.BytesIO();image.save(out,format="PNG")
   prepared.append((t,objects,out.getvalue()))
  if options["dry_run"]:
   self.stdout.write(self.style.SUCCESS("Validated 100 coaster designs. No changes made."))
   return
  with transaction.atomic():
   for i,(t,objects,png) in enumerate(prepared):
    data=copy.deepcopy(t.json_data)
    for page in data.get("pages",[]):page["objects"]=copy.deepcopy(objects)
    for page in data.get("adminPages",[]):page["objects"]=copy.deepcopy(objects)
    data.update(generator="zenvibe-coaster-canva-inspired-v1",editable=True,editorNative=True,constrainToPrintArea=True)
    t.json_data=data
    t.preview.save("coaster-canva-%s-%03d.png"%(t.pk,i+1),ContentFile(png),save=False)
    t.save(update_fields=["json_data","preview"])
  self.stdout.write(self.style.SUCCESS("Updated 100 editable coaster templates and previews."))
