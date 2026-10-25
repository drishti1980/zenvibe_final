from __future__ import annotations
import base64, hashlib, json, re
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

GENERATOR_ID='zenvibe-marketing-materials-v1-json-svg'
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

def uri(svg): return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()
def textbox(i,x,y,w,text,size,color,font='Arial',weight=400,align='left'):
 return {'id':i,'name':i.replace('_',' ').title(),'type':'textbox','left':round(x,2),'top':round(y,2),'width':round(w,2),'text':text,'fontSize':size,'font':font,'fontFamily':font,'fontWeight':weight,'fill':color,'textAlign':align,'lineHeight':1.12,'customerEditable':True,'locked':False,'fieldType':'marketing-text','manualReplacement':True}
def image(i,x,y,w,h,src,editable=True,bg=False):
 return {'id':i,'name':i.replace('_',' ').title(),'type':'image','left':round(x,2),'top':round(y,2),'width':round(w,2),'height':round(h,2),'src':src,'baseSrc':src,'scaleX':1,'scaleY':1,'customerEditable':editable,'backgroundAsset':bg,'locked':bg,'fieldType':'marketing-background' if bg else 'marketing-photo','manualReplacement':not bg}
def photo_svg(w,h,label,color,seed):
 return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#e8eceb"/><stop offset="1" stop-color="#cfd8d5"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#g)"/><circle cx="{w*(.22+(seed%5)*.08):.1f}" cy="{h*.30:.1f}" r="{min(w,h)*.14:.1f}" fill="{color}" opacity=".22"/><path d="M0 {h*.88:.1f} L{w*.28:.1f} {h*.52:.1f} L{w*.48:.1f} {h*.70:.1f} L{w*.72:.1f} {h*.42:.1f} L{w} {h*.72:.1f} V{h} H0Z" fill="{color}" opacity=".25"/><text x="{w/2}" y="{h*.92}" text-anchor="middle" font-family="Arial" font-size="{max(11,min(w,h)*.055):.1f}" fill="{color}">{escape(label)}</text></svg>'''
def bg_svg(W,H,pal,fam,side,kind):
 primary,paper,accent,white,dark=pal; m=fam%20; s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',f'<rect width="{W}" height="{H}" fill="{paper}"/>']
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
 if kind in ('bifold','trifold'):
  folds=2 if kind=='bifold' else 3
  for k in range(1,folds): s.append(f'<line x1="{W*k/folds}" y1="0" x2="{W*k/folds}" y2="{H}" stroke="{dark}" stroke-opacity=".08"/>')
 s.append('</svg>'); return ''.join(s)
def add_photo(objs,i,x,y,w,h,pal,label,seed): objs.append(image(i,x,y,w,h,uri(photo_svg(max(100,int(w)),max(100,int(h)),label,pal[0],seed))))
def common_content(idx):
 theme=THEMES[idx%20]; return theme+(f'CALL 1300 {100+idx:03d} {200+idx:03d}',f'zenvibe.example/{theme[0].lower().replace(" ","")}',f'Offer {idx+1:03d}')
def brochure_page(kind,idx,side,W,H):
 pal=PALETTES[(idx*3+side)%20]; head,body=FONTS[idx%len(FONTS)]; cat,title,sub,desc,contact,web,offer=common_content(idx); bg=bg_svg(W,H,pal,idx,side,kind); objs=[image(f'bg_{side}',0,0,W,H,uri(bg),False,True)]; panels=2 if kind=='bifold' else 3; pw=W/panels; margin=pw*.07
 # deterministic 20 macro arrangements x 5 variants; every panel has reserved, non-overlapping zones.
 for p in range(panels):
  x=p*pw+margin; usable=pw-2*margin; variant=(idx//20)%5; local=(p+side+idx)%4
  if local==0:
   add_photo(objs,f'photo_{side}_{p}',x,H*.10,usable,H*.28,pal,'Replace photo',idx+p+side)
   objs += [textbox(f'title_{side}_{p}',x,H*.43,usable,title if p==panels-1 else sub,26 if panels==2 else 20,pal[4],head,700),textbox(f'body_{side}_{p}',x,H*.56,usable,desc,13,pal[4],body),textbox(f'contact_{side}_{p}',x,H*.79,usable,contact,11,pal[0],body,700)]
  elif local==1:
   objs += [textbox(f'eyebrow_{side}_{p}',x,H*.10,usable,cat.upper(),11,pal[2],body,700),textbox(f'title_{side}_{p}',x,H*.17,usable,title,24 if panels==2 else 19,pal[4],head,700)]
   add_photo(objs,f'photo_{side}_{p}',x,H*.37,usable,H*.28,pal,'Replace photo',idx+p+side)
   objs += [textbox(f'body_{side}_{p}',x,H*.70,usable,desc,12,pal[4],body),textbox(f'web_{side}_{p}',x,H*.88,usable,web,10,pal[0],body,700)]
  elif local==2:
   add_photo(objs,f'photo_{side}_{p}',x,H*.08,usable,H*.42,pal,'Replace photo',idx+p+side)
   objs += [textbox(f'title_{side}_{p}',x,H*.55,usable,sub,22 if panels==2 else 18,pal[4],head,700),textbox(f'body_{side}_{p}',x,H*.67,usable,desc,12,pal[4],body),textbox(f'cta_{side}_{p}',x,H*.86,usable,offer.upper(),10,pal[0],body,700)]
  else:
   objs += [textbox(f'title_{side}_{p}',x,H*.10,usable,title if p==0 else sub,24 if panels==2 else 19,pal[4],head,700),textbox(f'body_{side}_{p}',x,H*.27,usable,desc,12,pal[4],body)]
   add_photo(objs,f'photo_{side}_{p}',x,H*.48,usable,H*.30,pal,'Replace photo',idx+p+side)
   objs += [textbox(f'contact_{side}_{p}',x,H*.84,usable,contact,10,pal[0],body,700)]
 return bg,objs
def door_page(idx,side,W,H):
 pal=PALETTES[(idx*5+side)%20]; head,body=FONTS[idx%5]; cat,title,sub,desc,contact,web,offer=common_content(idx); bg=bg_svg(W,H,pal,idx,side,'doorhanger'); objs=[image(f'bg_{side}',0,0,W,H,uri(bg),False,True)]; m=W*.08
 # reserve top 30% as knob/die-cut safety zone: no important text there; photo/decor may sit below.
 if side==0:
  add_photo(objs,'photo_front',m,H*.31,W-2*m,H*.24,pal,'Replace photo',idx)
  objs += [textbox('headline',m,H*.59,W-2*m,title,30,pal[4],head,700,'center'),textbox('subhead',m,H*.69,W-2*m,sub,15,pal[0],body,700,'center'),textbox('offer',m,H*.78,W-2*m,offer.upper(),18,pal[2],head,700,'center'),textbox('contact',m,H*.89,W-2*m,contact,11,pal[4],body,700,'center')]
 else:
  objs += [textbox('back_title',m,H*.32,W-2*m,'WHY CHOOSE US',24,pal[4],head,700,'center'),textbox('back_body',m,H*.42,W-2*m,desc+'\n\n✓ Professional service\n✓ Clear communication\n✓ Local support',13,pal[4],body),textbox('back_cta',m,H*.69,W-2*m,'GET IN TOUCH TODAY',18,pal[0],head,700,'center')]
  add_photo(objs,'photo_back',m,H*.76,W*.34,H*.14,pal,'QR / Logo',idx+100); objs += [textbox('back_web',m+W*.40,H*.79,W*.43,web+'\n'+contact,11,pal[4],body,700)]
 return bg,objs
def ticket_page(idx,side,W,H):
 pal=PALETTES[(idx*7+side)%20]; head,body=FONTS[idx%5]; cat,title,sub,desc,contact,web,offer=common_content(idx); bg=bg_svg(W,H,pal,idx,side,'ticket'); objs=[image(f'bg_{side}',0,0,W,H,uri(bg),False,True)]; m=W*.045; stub=W*.22
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
  seen=set(); built=[]
  for idx in range(opt['count']):
   pages=build(kind,idx,W,H); validate(kind,pages,W,H); fp=fingerprint(pages)
   if fp in seen: raise CommandError(f'duplicate composition at {idx+1}')
   seen.add(fp); built.append((idx,pages,fp))
  self.stdout.write(f'Validated {len(built)} unique {KINDS[kind]["label"]} templates for Product {product.id}: {product.name}')
  self.stdout.write(f'Canvas: {W} x {H}; JSON + SVG; editable text/photos; locked SVG background.')
  self.stdout.write('Pages: '+('mixed 1/2 sides' if kind=='ticket' else '2 sides each'))
  if opt['dry_run']:
   self.stdout.write(self.style.SUCCESS('Dry run complete; database unchanged.')); return
  out=Path('media')/MEDIA_DIR/kind/str(product.id); out.mkdir(parents=True,exist_ok=True)
  prefix=f'ZV {KINDS[kind]["label"]} '
  with transaction.atomic():
   if opt['replace_generated']: DesignTemplate.objects.filter(product=product,name__startswith=prefix).delete()
   for idx,pages,fp in built:
    theme=THEMES[idx%20][0]; variation=idx//20+1; name=f'{prefix}{idx+1:03d} · {theme} · Layout {variation}'
    doc={'generator':GENERATOR_ID,'kind':kind,'version':1,'width':W,'height':H,'pages':[{k:v for k,v in p.items() if k!='backgroundSvg'} for p in pages],'meta':{'compositionFingerprint':fp,'theme':theme,'layoutFamily':idx%20+1,'variation':variation}}
    for side,p in enumerate(pages): (out/f'{idx+1:03d}_{side+1}_{p["name"].lower().replace(" ","_")}.svg').write_text(p['backgroundSvg'],encoding='utf-8')
    preview_svg=pages[0]['backgroundSvg']; preview_name=f'{kind}_{idx+1:03d}.svg'; preview_bytes=preview_svg.encode();
    if cairosvg:
     try: preview_bytes=cairosvg.svg2png(bytestring=preview_bytes,output_width=min(W,1000)); preview_name=f'{kind}_{idx+1:03d}.png'
     except Exception: pass
    t=DesignTemplate(product=product,name=name,json_data=json.dumps(doc,ensure_ascii=False),is_active=True); t.preview.save(preview_name,ContentFile(preview_bytes),save=False); t.save()
  self.stdout.write(self.style.SUCCESS(f'Created {len(built)} templates.'))
