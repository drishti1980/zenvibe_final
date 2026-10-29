"""Install missing 100-template libraries for audited display products.

Dry-run by default. No existing template is changed or deleted.
Uses Admin print surfaces and physical dimensions; skips unconfigured products.
"""
from __future__ import annotations
import copy
import hashlib
import html
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from designer.models import Product, ProductPrintSurface, DesignTemplate

TARGET_IDS = (289,411,349,219,269,433,440,238,227,284,89,412,422,250,235,313,432,430,297,298,465,466,187,467,233,186,413,319,438,277,447)
GENERATOR = "zenvibe-display-library-100-v1"
PALETTES = [
 ("#112B3C","#F5EFE3","#C49A58"),("#143C35","#F6F0DE","#B9A073"),
 ("#253B68","#F3F7FA","#D69A45"),("#622E43","#FAF0EB","#D7A36A"),
 ("#1C3337","#EAF3EE","#B1C6A6"),("#252329","#F8F5EE","#C3A56D"),
 ("#0B6471","#F3F7F6","#E6A25E"),("#714437","#FBF1E6","#D6AA76"),
 ("#423E6D","#F4F1F9","#BBA7D4"),("#2F4935","#F4F2E7","#D7B36B"),
]
SECTORS = [
 ("CORPORATE","BUILD YOUR BRAND","Stand out with confident design"),
 ("REAL ESTATE","FIND YOUR PLACE","Spaces worth discovering"),
 ("HOSPITALITY","WELCOME IN","Make every visit memorable"),
 ("WELLNESS","FEEL YOUR BEST","A better way to recharge"),
 ("TECHNOLOGY","WHAT'S NEXT","Modern ideas. Clear results."),
 ("EDUCATION","GROW FURTHER","Learn. Create. Succeed."),
 ("RETAIL","NEW COLLECTION","Discover something different"),
 ("FITNESS","MOVE FORWARD","Strength starts here"),
 ("EVENTS","MAKE IT COUNT","Experiences worth sharing"),
 ("CONSTRUCTION","BUILT TO LAST","Quality you can trust"),
 ("TRAVEL","EXPLORE MORE","Find your next adventure"),
 ("BEAUTY","THE ART OF CARE","Thoughtfully made for you"),
 ("AUTOMOTIVE","DRIVE BETTER","Confidence in every detail"),
 ("FINANCE","PLAN AHEAD","Clarity for your next step"),
 ("FOOD & DRINK","FRESH IDEAS","Made with passion"),
 ("CREATIVE","MAKE YOUR MARK","Design with purpose"),
 ("COMMUNITY","TOGETHER WE GROW","People. Purpose. Progress."),
 ("LIFESTYLE","LIVE BEAUTIFULLY","Everyday essentials elevated"),
 ("HEALTHCARE","CARE THAT MATTERS","Here for your wellbeing"),
 ("SUSTAINABILITY","A BETTER TOMORROW","Small changes. Big impact"),
]

def box(id,x,y,w,h,fill):
 return dict(id=id,type="rect",left=round(x,2),top=round(y,2),width=round(w,2),height=round(h,2),fill=fill,selectable=True,evented=True,customerEditable=True)
def text(id,x,y,w,value,size,color,align="left",weight=600):
 return dict(id=id,type="textbox",left=round(x,2),top=round(y,2),width=round(w,2),text=value,fontSize=round(size,2),fontFamily="Arial",fontWeight=weight,fill=color,textAlign=align,lineHeight=1.15,selectable=True,evented=True,customerEditable=True)
def circle(id,x,y,r,fill):
 return dict(id=id,type="circle",left=round(x-r,2),top=round(y-r,2),radius=round(r,2),fill=fill,selectable=True,evented=True,customerEditable=True)
def art(index,w,h):
 sector=SECTORS[index%20]; palette=PALETTES[(index//10)%10]
 dark,paper,accent=palette; mode=index%20; variant=index//20
 m=min(w,h); pad=min(w*.09,h*.12); fs=min(h*.15,w*.09)
 objs=[box("background",0,0,w,h,paper)]
 # Twenty distinct compositions, with five structural variations each.
 if mode in (0,5,10,15):
  side=w*(.18+.055*variant)
  objs += [box("left-band",0,0,side,h,dark),box("accent-bar",side,0,max(4,w*.012),h,accent)]
  tx=side+pad; tw=w-tx-pad
 elif mode in (1,6,11,16):
  band=h*(.18+.035*variant)
  objs += [box("top-band",0,0,w,band,dark),box("gold-line",0,band,w,max(3,h*.012),accent)]
  tx=pad;tw=w-2*pad
 elif mode in (2,7,12,17):
  side=w*(.19+.04*variant)
  objs += [box("right-band",w-side,0,side,h,dark),box("accent-bar",w-side-max(4,w*.012),0,max(4,w*.012),h,accent)]
  tx=pad;tw=w-side-2*pad
 elif mode in (3,8,13,18):
  band=h*(.18+.035*variant)
  objs += [box("bottom-band",0,h-band,w,band,dark),box("gold-line",0,h-band-max(3,h*.012),w,max(3,h*.012),accent)]
  tx=pad;tw=w-2*pad
 else:
  inset=pad*(.6+.08*variant)
  objs += [box("frame-top",inset,inset,w-2*inset,max(3,m*.008),accent),
           box("frame-bottom",inset,h-inset,w-2*inset,max(3,m*.008),accent),
           box("frame-left",inset,inset,max(3,m*.008),h-2*inset,accent),
           box("frame-right",w-inset,inset,max(3,m*.008),h-2*inset,accent)]
  tx=pad*1.3;tw=w-2*tx
 # Deliberately avoid decorative elements in the central text-safe zone.
 if mode%4==0:
  objs.append(circle("corner-disc",w*.91,h*.83,m*(.055+.009*variant),accent))
 elif mode%4==1:
  objs.append(circle("corner-disc",w*.88,h*.78,m*(.045+.008*variant),accent))
 elif mode%4==2:
  objs.append(box("corner-tile",w*.84,h*.76,w*.07,h*.10,accent))
 else:
  objs.append(box("corner-tile",w*.86,h*.77,w*.06,h*.09,accent))
 align="center" if mode%5==4 else "left"
 # Keep type within the safe central region even on narrow/tall products.
 title_size=min(fs,tw/max(7,len(sector[1])*.59))
 title_size=max(8,title_size)
 subtitle_size=min(title_size*.43,tw/max(10,len(sector[2])*.54))
 subtitle_size=max(6,subtitle_size)
 y=h*.35
 objs += [text("industry",tx,y-h*.16,tw,sector[0],max(7,title_size*.36),accent,align,700),
          text("headline",tx,y,tw,sector[1],title_size,dark,align,800),
          text("tagline",tx,y+title_size*1.55,tw,sector[2],subtitle_size,dark,align,400)]
 return objs

def svg_preview(objects,w,h):
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
 for o in objects:
  typ=o["type"];fill=html.escape(str(o.get("fill","#000")),quote=True)
  if typ=="rect":
   s.append(f'<rect x="{o["left"]}" y="{o["top"]}" width="{o["width"]}" height="{o["height"]}" fill="{fill}"/>')
  elif typ=="circle":
   r=o["radius"];s.append(f'<circle cx="{o["left"]+r}" cy="{o["top"]+r}" r="{r}" fill="{fill}"/>')
  elif typ=="textbox":
   anchor="middle" if o.get("textAlign")=="center" else "start"
   x=o["left"]+o["width"]/2 if anchor=="middle" else o["left"]
   s.append(f'<text x="{x}" y="{o["top"]+o["fontSize"]}" text-anchor="{anchor}" font-family="Arial" font-size="{o["fontSize"]}" font-weight="{o["fontWeight"]}" fill="{fill}">{html.escape(o["text"])}</text>')
 s.append("</svg>")
 return "".join(s).encode("utf-8")

def surfaces_for(product):
 surfaces=list(ProductPrintSurface.objects.filter(product=product,is_active=True).order_by("sort_order","id"))
 if surfaces:
  return [(s.label,float(s.print_width_in),float(s.print_height_in)) for s in surfaces]
 if product.print_width_in and product.print_height_in:
  return [("Main",float(product.print_width_in),float(product.print_height_in))]
 return []

class Command(BaseCommand):
 help="Safely install up to 100 editable templates per audited display product. Default dry-run; --apply writes."
 def add_arguments(self,parser):
  parser.add_argument("--apply",action="store_true")
  parser.add_argument("--product-id",type=int)
 def handle(self,*args,**opts):
  ids=[opts["product_id"]] if opts["product_id"] else TARGET_IDS
  total=0; skipped=[]
  for pid in ids:
   product=Product.objects.filter(pk=pid,is_active=True).first()
   if not product:
    skipped.append((pid,"not an active product"));continue
   surfaces=surfaces_for(product)
   if not surfaces or any(w<=0 or h<=0 for _,w,h in surfaces):
    skipped.append((pid,"missing Admin print dimensions"));continue
   # A frame or hardware-only product is not an artwork surface.
   if "FRAME" in product.name.upper() and not ProductPrintSurface.objects.filter(product=product,is_active=True).exists():
    skipped.append((pid,"frame/hardware: requires an explicitly configured print surface"));continue
   existing=DesignTemplate.objects.filter(product=product,is_active=True).count()
   if existing>=100:
    self.stdout.write(f"SKIP {pid} {product.name}: already {existing} active");continue
   count=100-existing
   self.stdout.write(f"{pid} {product.name}: {existing} active; adding {count}; {len(surfaces)} print surface(s)")
   total+=count
   if not opts["apply"]:continue
   with transaction.atomic():
    for i in range(100):
     name=f"Display Collection {i+1:03d} — {SECTORS[i%20][0]}"
     if DesignTemplate.objects.filter(product=product,name=name).exists():continue
     pages=[]
     for label,wi,hi in surfaces:
      ratio=wi/hi
      w=round(min(1800,max(400,800*ratio)))
      h=round(w/ratio)
      objects=art(i,w,h)
      pages.append(dict(name=label,background=PALETTES[(i//10)%10][1],
                        physical=dict(widthIn=wi,heightIn=hi),objects=objects))
     data=dict(version=2,templateType="editable-master",generator=GENERATOR,
               document=dict(width=round(min(1800,max(400,800*surfaces[0][1]/surfaces[0][2]))),
                             height=round(min(1800,max(400,800*surfaces[0][1]/surfaces[0][2]))/(surfaces[0][1]/surfaces[0][2])),
                             physical=dict(widthIn=surfaces[0][1],heightIn=surfaces[0][2]),unit="in"),
               pageCount=len(pages),pages=pages,adminPages=copy.deepcopy(pages),
               editable=True,editorNative=True,editorSchema="fabric-primitives-v1")
     t=DesignTemplate(product=product,name=name,json_data=data,is_active=True)
     w=data["document"]["width"];h=data["document"]["height"]
     t.preview.save(f"display_{pid}_{i+1:03d}.svg",ContentFile(svg_preview(pages[0]["objects"],w,h)),save=False)
     t.save()
  self.stdout.write(f"{'APPLIED' if opts['apply'] else 'DRY RUN'}: up to {total} new templates. Skipped: {skipped}")
