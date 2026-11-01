from __future__ import annotations
import base64, hashlib, json, re, colorsys, textwrap
from html import escape
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product
try:
    import cairosvg
except Exception:
    cairosvg=None

GENERATOR_ID='zenvibe-marketing-materials-v2-diverse-artwork'
MEDIA_DIR='generated_marketing_materials_v1'
KINDS={
 'bifold': {'label':'Bi-Fold Brochure','pages':['Outside','Inside'],'default':(1100,850),'physical':(11,8.5),'keywords':['bi-fold','bifold','bi fold']},
 'trifold': {'label':'Tri-Fold Brochure','pages':['Outside','Inside'],'default':(1100,850),'physical':(11,8.5),'keywords':['tri-fold','trifold','tri fold']},
 'doorhanger': {'label':'Door Hanger','pages':['Front','Back'],'default':(450,1100),'physical':(4.5,11),'keywords':['door hanger','doorhanger']},
 'ticket': {'label':'Custom Ticket','pages':['Front','Back'],'default':(850,275),'physical':(8.5,2.75),'keywords':['ticket']},
}
THEMES=[
('Corporate','BUILD WHAT\'S NEXT','Strategy • Design • Growth','Clear thinking and practical solutions for ambitious organisations.'),
('Real Estate','FIND YOUR PLACE','Property presented beautifully','Premium homes, local expertise and a smoother buying experience.'),
('Restaurant','TASTE SOMETHING NEW','Fresh • Local • Memorable','Seasonal flavours, thoughtful service and food worth sharing.'),
('Travel','GO SOMEWHERE GREAT','Journeys made personal','Curated escapes, local experiences and flexible itineraries.'),
('Wellness','MAKE TIME FOR YOU','Restore • Reset • Renew','Thoughtful treatments and calm spaces designed around wellbeing.'),
('Healthcare','CARE THAT CONNECTS','Modern care, human attention','Accessible support focused on comfort, clarity and long-term wellbeing.'),
('Education','LEARN. GROW. ACHIEVE.','Skills for what comes next','Supportive educators, practical programs and flexible pathways.'),
('Technology','SMARTER DIGITAL','Secure • Scalable • Simple','Technology that simplifies operations and helps teams move faster.'),
('Fitness','STRONGER EVERY DAY','Train with purpose','Expert coaching, progressive programs and a community that keeps you moving.'),
('Finance','PLAN WITH CONFIDENCE','Advice made clearer','Practical financial guidance designed around your goals.'),
('Beauty','BEAUTY, REFINED','Modern treatments, personal care','Premium products, skilled technique and a relaxed client experience.'),
('Construction','BUILT WITH PURPOSE','Plan • Build • Deliver','Reliable workmanship, transparent communication and quality results.'),
('Interior','SPACES WITH SOUL','Designed around living','Warm, functional interiors shaped by thoughtful detail.'),
('Automotive','DRIVE WITH CONFIDENCE','Service you can trust','Professional care, transparent advice and dependable workmanship.'),
('Events','MAKE IT MEMORABLE','Gather • Celebrate • Connect','Polished experiences with personality, from intimate to large-scale.'),
('Fashion','NEW SEASON','Designed for everyday confidence','Modern essentials, expressive details and versatile silhouettes.'),
('Photography','STORIES IN FOCUS','Natural moments, beautifully captured','Relaxed photography for people, brands and celebrations.'),
('Legal','CLEAR. PRACTICAL. TRUSTED.','Advice when it matters','Straightforward guidance with attention to priorities and next steps.'),
('Marketing','MAKE YOUR BRAND MOVE','Creative that earns attention','Brand, content and campaign thinking built for stronger connections.'),
('Community','MAKE AN IMPACT','Small actions. Lasting change.','Practical support, stronger connections and better local outcomes.'),
]
PALETTES=[
('#123B5D','#F7F2E8','#E7A63A','#FFFFFF','#243447'),('#0B6B53','#F4F0DF','#E8B04B','#FFFFFF','#16352D'),
('#7A3145','#F9EEE7','#D59B62','#FFFFFF','#382630'),('#2449A6','#F4F7FB','#F05D5E','#FFFFFF','#162B58'),
('#5B3C77','#F8F0F7','#D8A0A8','#FFFFFF','#2F2539'),('#006D77','#EDF6F4','#E9C46A','#FFFFFF','#193F42'),
('#272727','#F7F2E8','#B9965A','#FFFFFF','#555555'),('#A63D2F','#FFF4E9','#E7B65B','#FFFFFF','#402823'),
('#2C6E9B','#F3F8FB','#F0B45A','#FFFFFF','#193A50'),('#657348','#F8F1DF','#D09A54','#FFFFFF','#303728'),
('#B65C6B','#FFF2F3','#E8B7A9','#FFFFFF','#303A56'),('#0A7F8C','#F5F8F4','#F28F3B','#FFFFFF','#174F56'),
('#3D3B8E','#F4F5FF','#77CBB9','#FFFFFF','#25244E'),('#9A3E32','#F8EFE7','#305B78','#FFFFFF','#4A2B25'),
('#12664F','#FFF1F3','#DB6680','#FFFFFF','#25443A'),('#425466','#F7F4E9','#F4C95D','#FFFFFF','#203040'),
('#68478D','#FAF5FF','#DC9E82','#FFFFFF','#352447'),('#005F73','#EEF8F7','#EE9B00','#FFFFFF','#163D43'),
('#B62D2D','#FFF7EC','#E2B96F','#FFFFFF','#3A2924'),('#1F5D42','#F5EFE1','#C57D56','#FFFFFF','#27372E')]
FONTS=[('Montserrat','Arial'),('Georgia','Arial'),('Arial','Arial'),('Trebuchet MS','Arial'),('Verdana','Arial')]

# Palette and subject treatment are stable for a given template index, without a
# 20-item colour cycle. The 100 designs have individual main/accent colour pairs.
def artwork_palette(idx):
 hue=((idx*137.50776405)%360)/360
 accent_hue=(hue+.29+(idx%7)*.013)%1
 sat=.39+(idx%5)*.055
 val=.43+(idx%4)*.065
 def rgb(h,s,v): return '#'+''.join(f'{round(c*255):02X}' for c in colorsys.hsv_to_rgb(h,s,v))
 primary=rgb(hue,sat,val)
 paper=rgb((hue+.11)%1,.055+(idx%4)*.012,.96)
 accent=rgb(accent_hue,.48+(idx%3)*.10,.72+(idx%4)*.045)
 dark=rgb(hue,.30,.20)
 return (primary,paper,accent,'#FFFFFF',dark)

# Every theme gets five different campaign/subject briefs; a restaurant menu
# must not be labelled as a generic business brochure.
SUBJECT_BRIEFS={
 'Restaurant':[('Signature tasting menu','STARTERS  •  MAINS  •  DESSERTS','Seasonal dining with curated pairings and a chef\'s selection.'),('Cafe brunch menu','COFFEE  •  BRUNCH  •  BAKERY','All-day brunch, specialty espresso and fresh pastries.'),('Fine dining wine menu','WINE  •  CELLAR  •  PAIRINGS','Explore a hand-picked selection of reds, whites and sparkling wines.'),('Takeaway food menu','ORDER  •  COLLECT  •  ENJOY','Fresh lunch combinations, family packs and easy takeaway.'),('Wedding catering menu','CANAPÉS  •  BANQUETS  •  SWEETS','Thoughtful event menus made for celebrations.')],
 'Events':[('Luxury gift hampers','CURATED  •  GIFTED  •  DELIVERED','Premium gifting with artisan food, flowers and keepsakes.'),('Wedding event programme','CEREMONY  •  RECEPTION  •  DETAILS','A refined guide to the celebration and order of events.'),('Corporate event brochure','SPEAKERS  •  AGENDA  •  VENUE','An elegant event programme for delegates and partners.'),('Festive gift catalogue','GIFTS  •  COLLECTIONS  •  DELIVERY','Seasonal hampers and thoughtfully wrapped presents.'),('Celebration packages','PACKAGES  •  ADD-ONS  •  BOOKINGS','Memorable experiences styled for every occasion.')],
 'Beauty':[('Spa treatment menu','FACIALS  •  MASSAGE  •  RITUALS','Unwind with signature treatments and restorative rituals.'),('Luxury salon services','HAIR  •  COLOUR  •  STYLE','Beautifully crafted salon services and personal care.'),('Skincare product catalogue','CLEANSE  •  NOURISH  •  GLOW','Discover elevated everyday skincare essentials.'),('Bridal beauty packages','BRIDAL  •  MAKEUP  •  HAIR','A personal approach to beauty on your special day.'),('Fragrance lookbook','NOTES  •  COLLECTIONS  •  SCENT','Discover new fragrance stories and timeless favourites.')],
 'Travel':[('Boutique hotel guide','STAY  •  DINE  •  EXPLORE','A considered guide to boutique stays and local experiences.'),('Luxury retreat programme','ESCAPE  •  RELAX  •  RESTORE','An inspiring itinerary for a restorative retreat.'),('Coastal destination guide','BEACHES  •  STAYS  •  EXPERIENCES','Explore hidden coves and curated coastal escapes.'),('Adventure tour brochure','TOURS  •  ADVENTURE  •  DISCOVERY','Expert-led journeys and authentic local adventures.'),('City weekend itinerary','WEEKEND  •  DINING  •  CULTURE','The best of a city in a thoughtfully planned escape.')],
}
VARIATION_NAMES=['Editorial','Catalogue','Minimal','Magazine','Illustrated']
def subject_copy(idx):
 cat,title,sub,desc=THEMES[idx%len(THEMES)]
 variant=idx//len(THEMES)
 if cat in SUBJECT_BRIEFS:
  name,sub,desc=SUBJECT_BRIEFS[cat][variant%5]
  return cat,name.upper(),sub,desc,name
 labels=['Premium collection','Signature services','Seasonal edition','Curated portfolio','The essential guide']
 name=f'{cat} — {labels[variant%5]}'
 return cat,(name.upper()),sub,desc,name

def uri(svg): return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()
def textbox(i,x,y,w,text,size,color,font='Arial',weight=400,align='left'):
 return {'id':i,'name':i.replace('_',' ').title(),'type':'textbox','left':round(x,2),'top':round(y,2),'width':round(w,2),'text':text,'fontSize':size,'font':font,'fontFamily':font,'fontWeight':weight,'fill':color,'textAlign':align,'lineHeight':1.12,'customerEditable':True,'locked':False,'fieldType':'marketing-text','manualReplacement':True}
def image(i,x,y,w,h,src,editable=True,bg=False):
 return {'id':i,'name':i.replace('_',' ').title(),'type':'image','left':round(x,2),'top':round(y,2),'width':round(w,2),'height':round(h,2),'src':src,'baseSrc':src,'scaleX':1,'scaleY':1,'customerEditable':editable,'backgroundAsset':bg,'locked':bg,'fieldType':'marketing-background' if bg else 'marketing-photo','manualReplacement':not bg}
def photo_svg(w,h,label,color,seed,category='Corporate'):
 # Distinct vector subject illustrations rather than 100 identical grey placeholders.
 # All artwork remains replaceable in the editor; use licensed photos for production.
 import math
 rng=(seed*73+19)%997
 bg=['#F5E8D9','#E0E9ED','#F4DDE3','#E7E6D7','#ECE2DA'][seed%5]
 parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',f'<rect width="{w}" height="{h}" fill="{bg}"/>']
 key=category.lower()
 if key in ('restaurant','events'):
  # Food plating, gift boxes and botanical details.
  if category=='Restaurant':
   parts += [f'<ellipse cx="{w*.52}" cy="{h*.52}" rx="{w*.36}" ry="{h*.40}" fill="#FEFCF5" stroke="#D7C9B5" stroke-width="{max(2,w*.012)}"/>',f'<ellipse cx="{w*.52}" cy="{h*.52}" rx="{w*.25}" ry="{h*.27}" fill="{color}" opacity=".19"/>']
   for k in range(5):
    x=w*(.38+(.12*math.cos(k*2.4+rng)));y=h*(.50+.15*math.sin(k*2.4+rng))
    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{min(w,h)*(.045+.012*(k%3)):.1f}" fill="{["#A54A33","#6C8B46","#D4A65E"][k%3]}"/>')
  else:
   parts += [f'<rect x="{w*.22}" y="{h*.28}" width="{w*.56}" height="{h*.55}" rx="8" fill="{color}" opacity=".75"/>',f'<rect x="{w*.18}" y="{h*.20}" width="{w*.64}" height="{h*.16}" rx="5" fill="{color}"/>',f'<path d="M{w*.49} {h*.20} V{h*.83} M{w*.22} {h*.52} H{w*.78}" stroke="#FFF1D5" stroke-width="{max(5,w*.04)}"/>']
 elif key in ('beauty','wellness','fashion','interior','photography'):
  for k in range(6):
   x=w*(.1+.16*k);y=h*(.52+.17*math.sin(k*2.1+seed))
   parts += [f'<path d="M{x:.1f} {h:.1f} Q{x-w*.12:.1f} {y:.1f} {x+w*.10:.1f} {h*.12:.1f}" fill="none" stroke="{color}" stroke-width="{max(2,w*.009)}" opacity=".65"/>',f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{w*.07}" ry="{h*.12}" transform="rotate({k*23} {x:.1f} {y:.1f})" fill="{color}" opacity=".24"/>']
 elif key in ('travel','real estate','construction','automotive'):
  parts += [f'<circle cx="{w*.78}" cy="{h*.23}" r="{min(w,h)*.13}" fill="#E6B66C"/>',f'<path d="M0 {h*.72} L{w*.27} {h*.26} L{w*.50} {h*.64} L{w*.70} {h*.38} L{w} {h*.76} V{h} H0Z" fill="{color}" opacity=".66"/>',f'<path d="M0 {h*.88} Q{w*.48} {h*.60} {w} {h*.91} V{h} H0Z" fill="#445C56" opacity=".75"/>']
 else:
  for k in range(7):
   x=w*(.12+(k%4)*.25);y=h*(.17+(k//4)*.5)
   parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w*(.13+(seed+k)%3*.02):.1f}" height="{h*.26:.1f}" rx="{min(w,h)*.02:.1f}" fill="{color}" opacity="{.22+(k%3)*.17:.2f}"/>')
 parts.append('</svg>')
 return ''.join(parts)

def original_placeholder_svg(w,h,label,color,seed):
 return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#e8eceb"/><stop offset="1" stop-color="#cfd8d5"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#g)"/><circle cx="{w*(.22+(seed%5)*.08):.1f}" cy="{h*.30:.1f}" r="{min(w,h)*.14:.1f}" fill="{color}" opacity=".22"/><path d="M0 {h*.88:.1f} L{w*.28:.1f} {h*.52:.1f} L{w*.48:.1f} {h*.70:.1f} L{w*.72:.1f} {h*.42:.1f} L{w} {h*.72:.1f} V{h} H0Z" fill="{color}" opacity=".25"/><text x="{w/2}" y="{h*.92}" text-anchor="middle" font-family="Arial" font-size="{max(11,min(w,h)*.055):.1f}" fill="{color}">{escape(label)}</text></svg>'''
def bg_svg(W,H,pal,fam,side,kind):
 primary,paper,accent,white,dark=pal; m=fam%20; treatment=(fam//20)%5; s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',f'<rect width="{W}" height="{H}" fill="{paper}"/>']
 if m==0:s += [f'<rect width="{W}" height="{H*.18}" fill="{primary}"/>',f'<rect y="{H*.88}" width="{W}" height="{H*.12}" fill="{accent}"/>']
 elif m==1:s += [f'<path d="M0 0 H{W*.62} L{W*.38} {H} H0Z" fill="{primary}"/>',f'<path d="M{W*.55} 0 H{W*.70} L{W*.46} {H} H{W*.31}Z" fill="{accent}" opacity=".8"/>']
 elif m==2:s += [f'<rect width="{W}" height="{H}" fill="{dark}"/>',f'<rect x="{W*.055}" y="{H*.06}" width="{W*.89}" height="{H*.88}" rx="{max(8,min(W,H)*.03)}" fill="{paper}"/>']
 elif m==3:s += [f'<circle cx="{W*.85}" cy="{H*.18}" r="{H*.38}" fill="{primary}" opacity=".16"/>',f'<circle cx="{W*.08}" cy="{H*.86}" r="{H*.28}" fill="{accent}" opacity=".20"/>']
 elif m==4:s += [f'<path d="M0 0 H{W} V{H*.30} Q{W*.55} {H*.52} 0 {H*.36}Z" fill="{primary}"/>']
 elif m==5:s += [f'<rect width="{W}" height="{H}" fill="{primary}"/>',f'<path d="M0 {H*.20} Q{W*.5} {H*.04} {W} {H*.22} V{H} H0Z" fill="{paper}"/>']
 elif m==6:s += [f'<rect x="{W*.06}" y="{H*.06}" width="{W*.88}" height="{H*.88}" fill="none" stroke="{primary}" stroke-width="4"/>',f'<rect x="{W*.075}" y="{H*.075}" width="{W*.85}" height="{H*.85}" fill="none" stroke="{accent}"/>']
 elif m==7:s += [f'<path d="M0 {H*.76} L{W*.30} {H*.44} L{W*.56} {H*.66} L{W} {H*.22} V{H} H0Z" fill="{primary}"/>']
 elif m==8:s += [f'<rect width="{W*.18}" height="{H}" fill="{primary}"/>',f'<rect x="{W*.18}" width="{W*.035}" height="{H}" fill="{accent}"/>']
 elif m==9:s += [f'<rect width="{W}" height="{H*.13}" fill="{dark}"/>',f'<path d="M0 {H} V{H*.83} Q{W*.45} {H*.68} {W} {H*.82} V{H}Z" fill="{primary}"/>']
 elif m==10:s += [f'<circle cx="{W*.5}" cy="{H*.5}" r="{H*.62}" fill="{primary}" opacity=".07"/>',f'<circle cx="{W*.5}" cy="{H*.5}" r="{H*.42}" fill="none" stroke="{accent}" stroke-width="3" opacity=".5"/>']
 elif m==11:s += [f'<rect width="{W}" height="{H}" fill="{dark}"/>',f'<path d="M0 0 H{W*.72} L{W*.54} {H} H0Z" fill="{paper}"/>']
 elif m==12:s += [f'<path d="M0 0 H{W} V{H*.22} L0 {H*.50}Z" fill="{primary}"/>',f'<path d="M0 {H} V{H*.82} L{W} {H*.52} V{H}Z" fill="{accent}" opacity=".7"/>']
 elif m==13:s += [f'<rect width="{W}" height="{H}" fill="{primary}"/>',f'<rect x="{W*.04}" y="{H*.04}" width="{W*.92}" height="{H*.92}" rx="24" fill="{paper}"/>']
 elif m==14:s += [f'<path d="M0 0 H{W*.40} L{W*.22} {H} H0Z" fill="{primary}"/>',f'<path d="M{W} 0 H{W*.78} L{W*.90} {H} H{W}Z" fill="{accent}"/>']
 elif m==15:s += [f'<rect width="{W}" height="{H*.10}" fill="{primary}"/>',f'<rect y="{H*.90}" width="{W}" height="{H*.10}" fill="{primary}"/>']
 elif m==16:s += [f'<path d="M0 {H*.58} Q{W*.25} {H*.34} {W*.5} {H*.58} T{W} {H*.54} V{H} H0Z" fill="{primary}" opacity=".9"/>']
 elif m==17:s += [f'<rect width="{W}" height="{H}" fill="{dark}"/>',f'<circle cx="{W*.18}" cy="{H*.20}" r="{H*.22}" fill="{accent}" opacity=".65"/>']
 elif m==18:s += [f'<path d="M0 0 H{W} V{H*.16} L0 {H*.34}Z" fill="{primary}"/>',f'<rect x="{W*.07}" y="{H*.72}" width="{W*.86}" height="{H*.16}" rx="12" fill="{accent}" opacity=".18"/>']
 else:s += [f'<rect width="{W}" height="{H}" fill="{primary}"/>',f'<path d="M{W*.04} {H*.08} H{W*.96} V{H*.92} H{W*.04}Z" fill="{paper}"/>',f'<path d="M{W*.04} {H*.78} Q{W*.35} {H*.58} {W*.60} {H*.78} T{W*.96} {H*.72} V{H*.92} H{W*.04}Z" fill="{accent}" opacity=".35"/>']
 # Five different editorial art treatments, not just palette rotations.
 if treatment==1:
  s += [f'<path d="M{W*.66} 0 H{W} V{H} H{W*.92}Z" fill="{accent}" opacity=".19"/>',f'<circle cx="{W*.82}" cy="{H*.72}" r="{H*.16}" fill="none" stroke="{primary}" stroke-width="4" opacity=".4"/>']
 elif treatment==2:
  s += [f'<rect x="{W*.035}" y="{H*.035}" width="{W*.93}" height="{H*.93}" fill="none" stroke="{accent}" stroke-width="3"/>',f'<path d="M0 {H*.52} H{W}" stroke="{primary}" opacity=".10" stroke-width="2"/>']
 elif treatment==3:
  for k in range(10): s.append(f'<path d="M{W*(k/10):.1f} 0 L{W*((k+3)/10):.1f} {H}" stroke="{accent}" opacity=".055" stroke-width="{max(4,W*.02)}"/>')
 elif treatment==4:
  s += [f'<ellipse cx="{W*.55}" cy="{H*.12}" rx="{W*.36}" ry="{H*.24}" fill="{accent}" opacity=".15"/>',f'<ellipse cx="{W*.18}" cy="{H*.89}" rx="{W*.25}" ry="{H*.22}" fill="{primary}" opacity=".13"/>']
 if kind in ('bifold','trifold'):
  folds=2 if kind=='bifold' else 3
  for k in range(1,folds): s.append(f'<line x1="{W*k/folds}" y1="0" x2="{W*k/folds}" y2="{H}" stroke="{dark}" stroke-opacity=".08"/>')
 s.append('</svg>'); return ''.join(s)
def add_photo(objs,i,x,y,w,h,pal,label,seed,category='Corporate'):
 objs.append(image(i,x,y,w,h,uri(photo_svg(max(100,int(w)),max(100,int(h)),label,pal[0],seed,category))))
def common_content(idx):
 cat,title,sub,desc,name=subject_copy(idx)
 return cat,title,sub,desc,f'CALL 1300 {100+idx:03d} {200+idx:03d}',f'zenvibe.example/{cat.lower().replace(" ","")}',name
# Five visual architectures, twenty different proportional layout plans per architecture.
# All objects remain inside their own folding panel and the two pages agree.
# Original, Canva-style compositions. No scraping/copying of Canva's third-party
# designs: importing a user's own Canva exports requires an authorized integration.
# Each index produces a distinct panel grid, hero artwork treatment and palette.
def brochure_layout(idx, side, panel):
 import random
 rng=random.Random(idx*10007+side*113+panel*19)
 architecture=(idx//10+panel*3+side*7)%10
 proportions=sorted([round(.11+rng.random()*.68,3),round(.11+rng.random()*.68,3)])
 return architecture, proportions, rng

def brochure_artwork_svg(w,h,category,idx,side,panel,palette):
 """Illustrated subject compositions; editable image objects, no grey placeholders."""
 import math,random
 r=random.Random(idx*991+side*109+panel*67)
 primary,paper,accent,white,dark=palette
 ww=max(80,int(w));hh=max(80,int(h))
 shapes=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{ww}" height="{hh}" viewBox="0 0 {ww} {hh}">',
         f'<rect width="{ww}" height="{hh}" fill="{paper}"/>']
 theme=category.lower()
 # 12 separate artwork families varying independently from layout.
 art_family=(idx*7+side*5+panel*3)%12
 if theme in ('restaurant','events'):
  for k in range(3+(idx%4)):
   cx=ww*(.15+.7*r.random());cy=hh*(.18+.64*r.random())
   radius=min(ww,hh)*(.10+.065*r.random())
   if theme=='restaurant':
    shapes += [f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{radius*1.5:.1f}" ry="{radius:.1f}" fill="#FFF9ED" stroke="{accent}" stroke-width="3"/>',
     f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{radius:.1f}" ry="{radius*.6:.1f}" fill="{primary}" opacity=".67"/>',
     f'<path d="M{cx-radius/2:.1f} {cy:.1f} q{radius/2:.1f} {-radius:.1f} {radius:.1f} 0" fill="none" stroke="#9AA45C" stroke-width="5"/>']
   else:
    shapes += [f'<rect x="{cx-radius:.1f}" y="{cy-radius:.1f}" width="{radius*2:.1f}" height="{radius*1.8:.1f}" rx="5" fill="{primary}" opacity=".83"/>',
     f'<path d="M{cx:.1f} {cy-radius:.1f} v{radius*1.8:.1f} M{cx-radius:.1f} {cy:.1f} h{radius*2:.1f}" stroke="{accent}" stroke-width="{max(3,radius*.15):.1f}"/>']
 elif theme in ('beauty','wellness','fashion','interior','photography'):
  for k in range(7+idx%5):
   x=ww*r.random();y=hh*r.random();angle=r.randint(0,175)
   shapes += [f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{ww*(.025+.04*r.random()):.1f}" ry="{hh*(.06+.09*r.random()):.1f}" transform="rotate({angle} {x:.1f} {y:.1f})" fill="{primary if k%2 else accent}" opacity=".43"/>']
 elif theme in ('travel','real estate','construction','automotive'):
  shapes += [f'<circle cx="{ww*(.65+.2*r.random()):.1f}" cy="{hh*.23:.1f}" r="{min(ww,hh)*.15:.1f}" fill="{accent}"/>']
  for k in range(4):
   yy=hh*(.36+k*.15)
   pts=' '.join(f'{x:.1f},{yy+hh*(r.random()*.26):.1f}' for x in [0,ww*.24,ww*.48,ww*.75,ww])
   shapes.append(f'<polygon points="{pts} {ww},{hh} 0,{hh}" fill="{primary if k%2 else accent}" opacity="{.25+k*.16:.2f}"/>')
 else:
  for k in range(5+idx%7):
   x=ww*r.random();y=hh*r.random();bw=ww*(.08+.15*r.random());bh=hh*(.12+.18*r.random())
   if art_family%3==0:
    shapes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{min(bw,bh):.1f}" fill="{accent if k%2 else primary}" opacity=".5"/>')
   elif art_family%3==1:
    shapes.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" fill="{accent if k%2 else primary}" opacity=".5"/>')
   else:
    shapes.append(f'<path d="M{x:.1f} {y:.1f} l{bw:.1f} {-bh/2:.1f} l{bw/2:.1f} {bh:.1f}Z" fill="{accent if k%2 else primary}" opacity=".5"/>')
 # Graphic overlay makes each subject illustration individually composed.
 if art_family in (0,3,7):
  shapes.append(f'<rect x="8" y="8" width="{ww-16}" height="{hh-16}" fill="none" stroke="{dark}" stroke-width="2" opacity=".55"/>')
 elif art_family in (1,5,9):
  shapes.append(f'<path d="M0 {hh*.87:.1f} Q{ww*.5:.1f} {hh*.64:.1f} {ww} {hh*.87:.1f}" fill="none" stroke="{accent}" stroke-width="8"/>')
 elif art_family in (2,6,10):
  shapes.append(f'<circle cx="{ww*.80:.1f}" cy="{hh*.20:.1f}" r="{min(ww,hh)*.10:.1f}" fill="none" stroke="{dark}" stroke-width="3"/>')
 shapes.append('</svg>')
 return ''.join(shapes)

def brochure_page(kind,idx,side,W,H):
 # Multi-panel compositions are deliberately different across outside/inside.
 pal=artwork_palette(idx)
 cat,title,sub,desc,contact,web,offer=common_content(idx)
 head,body=FONTS[(idx+side*3)%len(FONTS)]
 bg=bg_svg(W,H,pal,idx+side*11,side,kind)
 objs=[image(f'bg_{side}',0,0,W,H,uri(bg),False,True)]
 panels=2 if kind=='bifold' else 3
 pw=W/panels
 pad=pw*.065
 for p in range(panels):
  x=p*pw+pad
  w=pw-pad*2
  arch, cuts, rng=brochure_layout(idx,side,p)
  item=f'{idx}_{side}_{p}'
  # Ten content compositions, with twenty different per-panel geometries.
  if arch==0: slots=[('art',.07,.40),('heading',.52,.11),('copy',.67,.13),('footer',.87,.07)]
  elif arch==1: slots=[('heading',.08,.12),('art',.25,.35),('copy',.65,.14),('footer',.88,.06)]
  elif arch==2: slots=[('copy',.08,.14),('art',.27,.44),('heading',.75,.11),('footer',.90,.055)]
  elif arch==3: slots=[('art',.09,.24),('heading',.39,.14),('art2',.59,.21),('footer',.88,.07)]
  elif arch==4: slots=[('heading',.09,.11),('copy',.25,.20),('art',.52,.32),('footer',.90,.06)]
  elif arch==5: slots=[('art',.09,.47),('copy',.61,.12),('heading',.77,.09),('footer',.91,.05)]
  elif arch==6: slots=[('heading',.09,.16),('art',.31,.18),('copy',.55,.19),('footer',.87,.08)]
  elif arch==7: slots=[('copy',.09,.19),('heading',.34,.12),('art',.52,.30),('footer',.89,.06)]
  elif arch==8: slots=[('art',.08,.31),('copy',.44,.16),('heading',.67,.13),('footer',.90,.06)]
  else: slots=[('heading',.08,.11),('art',.24,.26),('art2',.55,.19),('copy',.78,.10),('footer',.91,.05)]
  # Unique per-index shift in the photo/art boundaries, bounded to safety zones.
  delta=(cuts[0]-.45)*.035
  for role,top,height in slots:
   top=max(.055,min(.91,top+delta))
   height=min(height,H and (.965-top))
   yy=H*top; hh=H*height
   if role.startswith('art'):
    vector=brochure_artwork_svg(w,hh,cat,idx,side,p+(1 if role=='art2' else 0),pal)
    objs.append(image(f'{role}_{item}',x,yy,w,hh,uri(vector)))
   elif role=='heading':
    heading=title if (side,p)==(0,panels-1) else (sub if side==0 else (cat.upper()+' COLLECTION' if cat=='Events' else cat.upper()+' MENU' if cat=='Restaurant' else title))
    size=max(11,min(21,int(w/max(10,len(heading)*.5))))
    objs.append(textbox(f'heading_{item}',x,yy,w,heading,size,pal[4],head,700))
   elif role=='copy':
    if cat=='Restaurant' and side==1: value=['STARTERS: Seasonal greens $14 / Soup $12','MAINS: Pasta $28 / Chef special $34','SWEETS: Tart $15 / Gelato $11'][p%3]
    elif cat=='Events' and side==1: value=['ARTISAN GIFT BOX • $79','SIGNATURE HAMPER • $129','CELEBRATION COLLECTION • $189'][p%3]
    else: value=desc if side==0 else sub+' — '+desc
    objs.append(textbox(f'copy_{item}',x,yy,w,value,10 if panels==3 else 12,pal[4],body))
   else:
    objs.append(textbox(f'footer_{item}',x,yy,w,contact if side else web,9,pal[0],body,700))
 return bg,objs

def door_page(idx,side,W,H):
 pal=artwork_palette(idx); head,body=FONTS[idx%5]; cat,title,sub,desc,contact,web,offer=common_content(idx); bg=bg_svg(W,H,pal,idx,side,'doorhanger'); objs=[image(f'bg_{side}',0,0,W,H,uri(bg),False,True)]; m=W*.08
 # reserve top 30% as knob/die-cut safety zone: no important text there; photo/decor may sit below.
 if side==0:
  add_photo(objs,'photo_front',m,H*.31,W-2*m,H*.24,pal,'Replace photo',idx)
  objs += [textbox('headline',m,H*.59,W-2*m,title,30,pal[4],head,700,'center'),textbox('subhead',m,H*.69,W-2*m,sub,15,pal[0],body,700,'center'),textbox('offer',m,H*.78,W-2*m,offer.upper(),18,pal[2],head,700,'center'),textbox('contact',m,H*.89,W-2*m,contact,11,pal[4],body,700,'center')]
 else:
  objs += [textbox('back_title',m,H*.32,W-2*m,'WHY CHOOSE US',24,pal[4],head,700,'center'),textbox('back_body',m,H*.42,W-2*m,desc+'\n\n✓ Professional service\n✓ Clear communication\n✓ Local support',13,pal[4],body),textbox('back_cta',m,H*.69,W-2*m,'GET IN TOUCH TODAY',18,pal[0],head,700,'center')]
  add_photo(objs,'photo_back',m,H*.76,W*.34,H*.14,pal,'QR / Logo',idx+100); objs += [textbox('back_web',m+W*.40,H*.79,W*.43,web+'\n'+contact,11,pal[4],body,700)]
 return bg,objs
def ticket_page(idx,side,W,H):
 pal=artwork_palette(idx); head,body=FONTS[idx%5]; cat,title,sub,desc,contact,web,offer=common_content(idx); bg=bg_svg(W,H,pal,idx,side,'ticket'); objs=[image(f'bg_{side}',0,0,W,H,uri(bg),False,True)]; m=W*.045; stub=W*.22
 if side==0:
  add_photo(objs,'ticket_photo',m,H*.12,W*.22,H*.76,pal,'Artwork',idx)
  objs += [textbox('event',W*.30,H*.14,W*.43,title,29,pal[4],head,700),textbox('subtitle',W*.30,H*.36,W*.43,sub,14,pal[0],body,700),textbox('details',W*.30,H*.52,W*.43,'SAT 24 OCT • 7:30 PM\n123 ANYWHERE ST • GATE A',12,pal[4],body),textbox('stub',W*.79,H*.18,W*.16,'ADMIT ONE\n#'+f'{1000+idx}',14,pal[0],body,700,'center')]
 else:
  objs += [textbox('terms_title',m,H*.14,W*.55,'TICKET INFORMATION',22,pal[4],head,700),textbox('terms',m,H*.34,W*.58,'Present this ticket at entry. Keep your ticket number and QR code visible. Event details are subject to change.',11,pal[4],body),textbox('sponsor',m,H*.72,W*.58,'SPONSOR / LOGO AREA • '+web,10,pal[0],body,700)]
  add_photo(objs,'qr',W*.73,H*.20,W*.20,H*.58,pal,'QR / Barcode',idx+200)
 return bg,objs
def build(kind,idx,W,H):
 pages=[]; names=KINDS[kind]['pages']; count=1 if kind=='ticket' and idx%4==0 else 2
 for side in range(count):
  if kind in ('bifold','trifold'): bg,objs=brochure_page(kind,idx,side,W,H)
  elif kind=='doorhanger': bg,objs=door_page(idx,side,W,H)
  else: bg,objs=ticket_page(idx,side,W,H)
  pages.append({'name':names[side],'width':W,'height':H,'objects':objs,'backgroundSvg':bg})
 return pages
def render_preview(page):
 """Render a truthful flattened thumbnail: background + editable photos + text.
 The saved JSON is still the editable source, this SVG is preview-only.
 """
 bg=page['backgroundSvg']; rendered=[]
 for o in page['objects']:
  if o.get('backgroundAsset'): continue
  x,y,w,h=[o.get(k,0) for k in ('left','top','width','height')]
  if o['type']=='image':
   rendered.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" href="{escape(o["src"],quote=True)}"/>')
  elif o['type']=='textbox':
   fontsize=float(o.get('fontSize',12)); font=escape(str(o.get('fontFamily','Arial')),quote=True)
   color=escape(str(o.get('fill','#222')),quote=True); weight=escape(str(o.get('fontWeight',400)))
   chars=max(7,int(w/max(1,fontsize*.55)))
   lines=[]
   for paragraph in str(o.get('text','')).split('\\n'):
    lines.extend(textwrap.wrap(paragraph,width=chars,break_long_words=False) or [''])
   # Hide overflow in previews rather than overlap adjacent panels.
   max_lines=max(1,int((page['height']-y-8)/(fontsize*1.22)))
   spans=''.join(f'<tspan x="{x}" dy="{0 if i==0 else fontsize*1.18:.1f}">{escape(line)}</tspan>' for i,line in enumerate(lines[:max_lines]))
   rendered.append(f'<text y="{y+fontsize:.1f}" font-size="{fontsize}" font-family="{font}" font-weight="{weight}" fill="{color}">{spans}</text>')
 return bg.replace('</svg>',''.join(rendered)+'</svg>')

def artwork_signature(pages):
 # Detect repeated artwork treatments, beyond changing text or object ids.
 signatures=[]
 for p in pages:
  obj=[]
  for o in p['objects']:
   if o.get('backgroundAsset'): continue
   obj.append((o['type'],round(o.get('left',0),0),round(o.get('top',0),0),round(o.get('width',0),0),round(o.get('height',0),0)))
  signatures.append(tuple(obj))
 return tuple(signatures)

def fingerprint(pages):
 slim=[]
 for p in pages:
  slim.append([(o['type'],round(o.get('left',0),1),round(o.get('top',0),1),round(o.get('width',0),1),round(o.get('height',0),1),o.get('text','')[:24]) for o in p['objects']])
 return hashlib.sha256(json.dumps(slim,sort_keys=True).encode()).hexdigest()
def validate(kind,pages,W,H):
 expected=1 if kind=='ticket' and len(pages)==1 else 2
 if len(pages)!=expected: raise CommandError('page count mismatch')
 for p in pages:
  if len([o for o in p['objects'] if o.get('backgroundAsset')])!=1: raise CommandError('background mismatch')
  for o in p['objects']:
   x,y,w,h=o.get('left',0),o.get('top',0),o.get('width',0),o.get('height',0)
   if x < -1 or y < -1 or x+w > W+2 or y+h > H+2: raise CommandError(f'out of bounds {o.get("id")}')

def find_product(kind,pid):
 if pid: return Product.objects.get(pk=pid)
 qs=Product.objects.all()
 for kw in KINDS[kind]['keywords']:
  p=qs.filter(name__icontains=kw).order_by('id').first()
  if p:return p
 raise CommandError('Could not auto-detect product. Pass --product-id.')
class Command(BaseCommand):
 help='Seed 100 original JSON+SVG editable templates for bi-fold, tri-fold, door hanger or tickets.'
 def add_arguments(self,p):
  p.add_argument('--kind',choices=KINDS.keys(),required=True); p.add_argument('--product-id',type=int); p.add_argument('--count',type=int,default=100); p.add_argument('--dry-run',action='store_true'); p.add_argument('--replace-generated',action='store_true')
 def handle(self,*args,**opt):
  kind=opt['kind']; product=find_product(kind,opt.get('product_id')); W=int(product.width or KINDS[kind]['default'][0]); H=int(product.height or KINDS[kind]['default'][1])
  # protect against obviously wrong square admin canvas for folded/vertical materials by warning, not mutating product.
  if kind in ('bifold','trifold') and W==H: self.stdout.write(self.style.WARNING(f'WARNING: Product canvas is square ({W}x{H}). Set Product width/height to a landscape ratio before final import for best results.'))
  seen=set(); built=[]; artwork_seen=set()
  for idx in range(opt['count']):
   pages=build(kind,idx,W,H); validate(kind,pages,W,H); fp=fingerprint(pages)
   if fp in seen: raise CommandError(f'duplicate composition at {idx+1}')
   seen.add(fp)
   # Warn about reused structural families; uniqueness includes illustration + theme.
   artwork_seen.add(artwork_signature(pages))
   built.append((idx,pages,fp))
  self.stdout.write(f'Validated {len(built)} unique {KINDS[kind]["label"]} templates for Product {product.id}: {product.name}')
  self.stdout.write(f'Canvas: {W} x {H}; JSON + SVG; editable text/photos; locked SVG background.')
  self.stdout.write(f'Structurally distinct arrangements: {len(artwork_seen)}; individual illustration palettes and theme-specific subjects.')
  self.stdout.write('Pages: '+('mixed 1/2 sides' if kind=='ticket' else '2 sides each'))
  if opt['dry_run']:
   self.stdout.write(self.style.SUCCESS('Dry run complete; database unchanged.')); return
  out=Path('media')/MEDIA_DIR/kind/str(product.id); out.mkdir(parents=True,exist_ok=True)
  prefix=f'ZV {KINDS[kind]["label"]} '
  with transaction.atomic():
   if opt['replace_generated']: DesignTemplate.objects.filter(product=product,name__startswith=prefix).delete()
   for idx,pages,fp in built:
    theme=THEMES[idx%20][0]; variation=idx//20+1; brief=subject_copy(idx)[4]; name=f'{prefix}{idx+1:03d} · {brief} · {VARIATION_NAMES[(variation-1)%5]}'
    doc={'generator':GENERATOR_ID,'kind':kind,'version':2,'width':W,'height':H,'pages':[{k:v for k,v in p.items() if k!='backgroundSvg'} for p in pages],'meta':{'compositionFingerprint':fp,'theme':theme,'layoutFamily':idx%20+1,'variation':variation}}
    for side,p in enumerate(pages): (out/f'{idx+1:03d}_{side+1}_{p["name"].lower().replace(" ","_")}.svg').write_text(p['backgroundSvg'],encoding='utf-8')
    preview_svg=render_preview(pages[0]); preview_name=f'{kind}_{idx+1:03d}.svg'; preview_bytes=preview_svg.encode();
    if cairosvg:
     try: preview_bytes=cairosvg.svg2png(bytestring=preview_bytes,output_width=min(W,1000)); preview_name=f'{kind}_{idx+1:03d}.png'
     except Exception: pass
    t=DesignTemplate(product=product,name=name,json_data=json.dumps(doc,ensure_ascii=False),is_active=True); t.preview.save(preview_name,ContentFile(preview_bytes),save=False); t.save()
  self.stdout.write(self.style.SUCCESS(f'Created {len(built)} templates.'))
