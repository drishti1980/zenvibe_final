(()=>{
'use strict';
const app=document.querySelector('.zv-editor'); if(!app||!window.fabric)return;
const $=id=>document.getElementById(id);
const productId=Number(app.dataset.productId), price=Number(app.dataset.productPrice||0);
let designId=app.dataset.designId||'', activeSide='front', zoom=1, history=[], historyIndex=-1, restoring=false, clipboard=null;
const W=600,H=560,PPI=10;
const sides={front:null,back:null};
let currentBase={type:'template',data:null};
function rebuildCurrentBase(){
  if(currentBase.type==='photo'&&currentBase.data)buildPhotoGarment(currentBase.data);
  else buildJersey(currentBase.data||templateDefs[0],true);
}
// Garment geometry is defined in local coordinates, then positioned once.
// This avoids Fabric.Path pathOffset/absolute clip mismatches.
const GARMENT={left:112,top:42,width:376,height:470};
const shirtPath='M 108 0 Q 148 42 188 42 Q 228 42 268 0 L 376 62 L 338 164 L 294 143 L 294 470 L 82 470 L 82 143 L 38 164 L 0 62 Z';
const shirtPathSvg=`M ${GARMENT.left+108} ${GARMENT.top} Q ${GARMENT.left+148} ${GARMENT.top+42} ${GARMENT.left+188} ${GARMENT.top+42} Q ${GARMENT.left+228} ${GARMENT.top+42} ${GARMENT.left+268} ${GARMENT.top} L ${GARMENT.left+376} ${GARMENT.top+62} L ${GARMENT.left+338} ${GARMENT.top+164} L ${GARMENT.left+294} ${GARMENT.top+143} L ${GARMENT.left+294} ${GARMENT.top+470} L ${GARMENT.left+82} ${GARMENT.top+470} L ${GARMENT.left+82} ${GARMENT.top+143} L ${GARMENT.left+38} ${GARMENT.top+164} L ${GARMENT.left} ${GARMENT.top+62} Z`;
const canvas=new fabric.Canvas('tshirtCanvas',{width:W,height:H,preserveObjectStacking:true,selection:true,backgroundColor:'#f7f8fa'});window.designCanvas=canvas;if(window.ZenImageTools)ZenImageTools.attach(canvas);
fabric.Object.prototype.set({transparentCorners:false,cornerColor:'#fff',cornerStrokeColor:'#1599dc',borderColor:'#1599dc',cornerStyle:'circle',padding:2});
const csrf=()=>document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';
const cloneClip=()=>new fabric.Path(shirtPath,{left:GARMENT.left,top:GARMENT.top,absolutePositioned:true,fill:'#000',selectable:false,evented:false,objectCaching:false,originX:'left',originY:'top'});
const templateDefs=[
 {name:'Midnight Strike',body:'#07255f',accent:'#0d55c7',accent2:'#e2a62c',dark:'#031532',style:0},
 {name:'Aqua Velocity',body:'#087985',accent:'#12b6bd',accent2:'#063249',dark:'#061b25',style:1},
 {name:'Silver Edge',body:'#ececeb',accent:'#292929',accent2:'#aeb4b7',dark:'#111',style:2},
 {name:'Mint Frost',body:'#edf0e8',accent:'#96c6b5',accent2:'#d5df58',dark:'#202a29',style:3},
 {name:'Magenta Rush',body:'#b84f8a',accent:'#ed83b7',accent2:'#1c3168',dark:'#151b3d',style:4},
 {name:'Neon Circuit',body:'#101010',accent:'#9bd700',accent2:'#363636',dark:'#000',style:5},
 {name:'Crimson Wave',body:'#8f1e2c',accent:'#ed4b35',accent2:'#efaf35',dark:'#35090f',style:0},
 {name:'Royal Matrix',body:'#271d62',accent:'#6a4ed5',accent2:'#17d3d7',dark:'#120b37',style:1},
 {name:'Sunset Pro',body:'#ef5f31',accent:'#f4ba32',accent2:'#8b1e3f',dark:'#351019',style:3},
 {name:'Forest Elite',body:'#123c2d',accent:'#2e7b59',accent2:'#d0bd5e',dark:'#071b13',style:5}
];
function svgThumb(t){
 const p=patternsSVG(t);
 return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 560"><defs><clipPath id="s"><path d="${shirtPathSvg}"/></clipPath><linearGradient id="shade" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff" stop-opacity=".18"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".22"/></linearGradient></defs><g clip-path="url(#s)"><rect width="600" height="560" fill="${t.body}"/>${p}<rect width="600" height="560" fill="url(#shade)"/></g><path d="${shirtPathSvg}" fill="none" stroke="${t.dark}" stroke-width="5"/><path d="M260 44 Q268 92 300 92 Q332 92 340 44" fill="${t.dark}" stroke="${t.dark}" stroke-width="14"/><path d="M194 185L150 206M406 185L450 206" stroke="#fff" stroke-opacity=".15" stroke-width="3"/><circle cx="300" cy="112" r="4" fill="#fff"/><circle cx="300" cy="132" r="4" fill="#fff"/></svg>`);
}
function patternsSVG(t){
 const a=t.accent,b=t.accent2;
 switch(t.style){
  case 0:return `<path d="M50 465Q190 290 355 382T620 250V560H0Z" fill="${a}"/><path d="M0 180Q150 70 310 205T620 90" fill="none" stroke="${b}" stroke-width="34" opacity=".85"/>`;
  case 1:return `<path d="M-100 0L500 560M20 0L620 560M140 0L740 560" stroke="${a}" stroke-width="62"/><path d="M0 420Q190 300 360 410T650 330" fill="none" stroke="${b}" stroke-width="20"/>`;
  case 2:return `<path d="M0 70L600 400M0 170L600 500" stroke="${a}" stroke-width="90"/><path d="M0 230L600 75" stroke="${b}" stroke-width="18"/>`;
  case 3:return `<path d="M0 0L265 560H0zM600 0L355 560H600z" fill="${a}"/><path d="M0 480Q300 375 600 480V560H0z" fill="${b}"/>`;
  case 4:return `<defs><pattern id="p" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M0 38L38 0" stroke="${a}" stroke-width="12"/></pattern></defs><rect width="600" height="560" fill="url(#p)" opacity=".72"/><path d="M0 405Q300 280 600 405V560H0z" fill="${b}"/>`;
  default:return `<path d="M0 0H185L350 560H145z" fill="${a}"/><path d="M600 0H430L250 560H455z" fill="${b}"/>`;
 }
}
function decorativeObjects(t){
 const objs=[];
 const add=(o)=>{o.set({selectable:false,evented:false,isBase:true,name:'Jersey artwork'});o.clipPath=cloneClip();objs.push(o)};
 switch(t.style){
  case 0:add(new fabric.Path('M 35 470 Q 190 280 355 380 T 635 245 L 650 600 L 0 600 Z',{fill:t.accent})); add(new fabric.Path('M -20 180 Q 150 70 310 205 T 630 85',{fill:'',stroke:t.accent2,strokeWidth:34,opacity:.85}));break;
  case 1:[-100,20,140].forEach(x=>add(new fabric.Line([x,0,x+600,560],{stroke:t.accent,strokeWidth:62}))); add(new fabric.Path('M -10 420 Q 190 300 360 410 T 650 330',{fill:'',stroke:t.accent2,strokeWidth:20}));break;
  case 2:add(new fabric.Line([0,70,600,400],{stroke:t.accent,strokeWidth:90}));add(new fabric.Line([0,170,600,500],{stroke:t.accent,strokeWidth:90}));add(new fabric.Line([0,230,600,75],{stroke:t.accent2,strokeWidth:18}));break;
  case 3:add(new fabric.Polygon([{x:0,y:0},{x:265,y:560},{x:0,y:560}],{fill:t.accent}));add(new fabric.Polygon([{x:600,y:0},{x:355,y:560},{x:600,y:560}],{fill:t.accent}));add(new fabric.Path('M 0 480 Q 300 375 600 480 L 600 560 L 0 560 Z',{fill:t.accent2}));break;
  case 4:for(let x=-450;x<700;x+=48)add(new fabric.Line([x,560,x+560,0],{stroke:t.accent,strokeWidth:14,opacity:.75}));add(new fabric.Path('M 0 405 Q 300 280 600 405 L 600 560 L 0 560 Z',{fill:t.accent2}));break;
  default:add(new fabric.Polygon([{x:0,y:0},{x:185,y:0},{x:350,y:560},{x:145,y:560}],{fill:t.accent}));add(new fabric.Polygon([{x:600,y:0},{x:430,y:0},{x:250,y:560},{x:455,y:560}],{fill:t.accent2}));
 }
 return objs;
}
function buildJersey(t,withLogo=true){
 canvas.clear(); canvas.backgroundColor='#f7f8fa';
 const baseOpts={left:GARMENT.left,top:GARMENT.top,originX:'left',originY:'top',selectable:false,evented:false,isBase:true,objectCaching:false};
 const shadow=new fabric.Path(shirtPath,{...baseOpts,left:GARMENT.left+5,top:GARMENT.top+8,fill:'rgba(0,0,0,.16)',stroke:'transparent',name:'Garment shadow',shadow:new fabric.Shadow({color:'rgba(14,24,45,.28)',blur:20,offsetX:0,offsetY:12})});
 const body=new fabric.Path(shirtPath,{...baseOpts,fill:t.body,stroke:t.dark,strokeWidth:4,name:'Jersey base'});
 canvas.add(shadow,body,...decorativeObjects(t));
 const shade=new fabric.Rect({left:0,top:0,width:600,height:560,fill:new fabric.Gradient({type:'linear',gradientUnits:'pixels',coords:{x1:0,y1:0,x2:600,y2:560},colorStops:[{offset:0,color:'rgba(255,255,255,.18)'},{offset:.45,color:'rgba(255,255,255,0)'},{offset:1,color:'rgba(0,0,0,.23)'}]}),selectable:false,evented:false,isBase:true,name:'Fabric shading'}); shade.clipPath=cloneClip(); canvas.add(shade);
 const seam1=new fabric.Line([194,185,150,206],{stroke:'rgba(255,255,255,.18)',strokeWidth:3,selectable:false,evented:false,isBase:true,name:'Sleeve seam'});
 const seam2=new fabric.Line([406,185,450,206],{stroke:'rgba(255,255,255,.18)',strokeWidth:3,selectable:false,evented:false,isBase:true,name:'Sleeve seam'});
 const collar=new fabric.Path('M 260 44 Q 268 92 300 92 Q 332 92 340 44',{fill:t.dark,stroke:t.dark,strokeWidth:15,selectable:false,evented:false,isBase:true,name:'Collar'});
 const btn1=new fabric.Circle({left:296,top:108,radius:4,fill:'#fff',selectable:false,evented:false,isBase:true,name:'Button'}),btn2=new fabric.Circle({left:296,top:128,radius:4,fill:'#fff',selectable:false,evented:false,isBase:true,name:'Button'});
 canvas.add(seam1,seam2,collar,btn1,btn2);
 if(withLogo)addLogoPlaceholder();
 canvas.requestRenderAll(); commit();
}
function addLogoPlaceholder(){const tx=new fabric.Textbox('YOUR\nLOGO',{left:365,top:108,width:105,fontFamily:'Arial',fontSize:25,lineHeight:.75,fontWeight:'bold',fill:'#fff',textAlign:'center',name:'YOURLOGO'});applyUserDefaults(tx);canvas.add(tx);canvas.setActiveObject(tx)}
function applyUserDefaults(o){o.set({isBase:false});o.clipPath=cloneClip();return o}
function applyTemplate(t){currentBase={type:'template',data:t};buildJersey(t,true)}
function renderTemplates(filter=''){const g=$('templateGrid');g.innerHTML='';templateDefs.filter(t=>t.name.toLowerCase().includes(filter.toLowerCase())).forEach(t=>{const b=document.createElement('button');b.className='template-card';b.innerHTML=`<img src="${svgThumb(t)}" alt="${t.name}"><span>PRO</span>`;b.title=t.name;b.onclick=()=>applyTemplate(t);g.appendChild(b)})}

// ---- Real garment photos (additive alternative to the vector jersey templates above) ----
const realGarments=window.REAL_GARMENTS||[];
const garmentImageCandidates=g=>[...(g?.image_urls||[]),g?.image_url].filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i);
function firstWorkingGarmentImage(g,ok,fail){const urls=garmentImageCandidates(g);let i=0;const next=()=>{if(i>=urls.length)return fail?.();const url=urls[i++],img=new Image();img.onload=()=>ok(url,img);img.onerror=next;img.src=url;};next();}
function bindGarmentFallback(imgEl,g){const urls=garmentImageCandidates(g);let i=Math.max(0,urls.indexOf(imgEl.src))+1;imgEl.onerror=()=>{if(i<urls.length)imgEl.src=urls[i++];else imgEl.onerror=null;};}
function buildPhotoGarment(g){
  currentBase={type:'photo',data:g};
  if(!garmentImageCandidates(g).length)return;
  firstWorkingGarmentImage(g,(url,probe)=>{
    canvas.clear();canvas.backgroundColor='#f7f8fa';
    const img=new fabric.Image(probe);
    const maxW=GARMENT.width,maxH=GARMENT.height;
    const scale=Math.min(maxW/img.width,maxH/img.height);
    img.set({originX:'center',originY:'center',left:GARMENT.left+GARMENT.width/2,top:GARMENT.top+GARMENT.height/2,
      scaleX:scale,scaleY:scale,selectable:false,evented:false,isBase:true,objectCaching:false,name:'Real garment photo',sourceUrl:url});
    canvas.add(img);
    addLogoPlaceholder();
    canvas.requestRenderAll();commit();
  },()=>{});
}
function renderGarmentPhotos(filter=''){
  const box=$('garmentPhotoGrid');if(!box)return;box.innerHTML='';
  realGarments.filter(g=>g.name.toLowerCase().includes(filter.toLowerCase())).forEach(g=>{
    const isActive=currentBase.type==='photo'&&currentBase.data?.key===g.key;
    const b=document.createElement('button');b.type='button';b.className='zv-garment-card'+(isActive?' active':'');
    b.innerHTML=`<img src="${g.image_url||''}" alt="${g.name}" loading="lazy"><b>${g.name}</b>`;
    const thumb=b.querySelector('img');if(thumb)bindGarmentFallback(thumb,g);
    b.onclick=()=>{buildPhotoGarment(g);renderGarmentPhotos($('garmentSearch')?.value||'');};
    box.appendChild(b);
  });
}
$('garmentSearch')?.addEventListener('input',e=>renderGarmentPhotos(e.target.value));
renderGarmentPhotos();
function buildRulers(){
 const rx=$('rulerX'),ry=$('rulerY');rx.innerHTML='';ry.innerHTML='';
 for(let i=0;i<=60;i++){
  const t=document.createElement('i');
  t.className='tick-x '+(i%10===0?'major':i%5===0?'mid':'');
  t.style.left=(i*PPI)+'px';
  if(i>0&&i%10===0)t.innerHTML=`<span>${i}</span>`;
  rx.appendChild(t);
 }
 for(let i=0;i<=56;i++){
  const t=document.createElement('i');
  t.className='tick-y '+(i%10===0?'major':i%5===0?'mid':'');
  t.style.top=(i*PPI)+'px';
  if(i>0&&i%10===0&&i<56)t.innerHTML=`<span>${i}</span>`;
  ry.appendChild(t);
 }
 const zx=document.createElement('span');zx.className='ruler-zero-x';zx.textContent='0 in';rx.appendChild(zx);
 const zy=document.createElement('span');zy.className='ruler-zero-y';zy.textContent='0 in';ry.appendChild(zy);
 const bx=document.createElement('span');bx.className='ruler-badge ruler-badge-x';bx.textContent='60 in';rx.appendChild(bx);
 const by=document.createElement('span');by.className='ruler-badge ruler-badge-y';by.textContent='56 in';ry.appendChild(by);
 const mx=document.createElement('span');mx.className='ruler-marker ruler-marker-x';rx.appendChild(mx);
 const my=document.createElement('span');my.className='ruler-marker ruler-marker-y';ry.appendChild(my);
}
const cliparts=['➟','➤','➲','⚡','★','✦','🏆','⚽','🏀','🏏','♛','♞','☄','🔥','✓','◆','⬟','〽'];
function renderAssets(id,arr,kind){const g=$(id);g.innerHTML='';arr.forEach(x=>{const b=document.createElement('button');b.className='asset-card';b.textContent=x;b.onclick=()=>addText(x,85,kind);g.appendChild(b)})}
function addText(text,size=48,name='Text'){const o=applyUserDefaults(new fabric.Textbox(text,{left:190,top:205,width:220,fontFamily:$('fontFamily').value,fontSize:size,fill:$('fillColor').value,textAlign:'center',name}));canvas.add(o);canvas.setActiveObject(o);commit()}
function currentJSON(){return canvas.toJSON(['name','isBase'])}
function saveSide(){sides[activeSide]=currentJSON()}
function loadSide(side){saveSide();activeSide=side;$('sideTopBtn').textContent=side==='front'?'Side 1':'Side 2';$('pageCount').textContent=side==='front'?'1/2':'2/2';canvas.clear();if(sides[side])canvas.loadFromJSON(sides[side],()=>{canvas.renderAll();refreshLayers();quality()});else rebuildCurrentBase()}
function commit(){if(restoring)return;saveSide();const state=JSON.stringify({sides,activeSide});history=history.slice(0,historyIndex+1);history.push(state);if(history.length>60)history.shift();historyIndex=history.length-1;$('undoBtn').disabled=historyIndex<=0;$('redoBtn').disabled=true;localStorage.setItem('zv-apparel-'+productId,state);refreshLayers();quality()}
function restore(i){if(i<0||i>=history.length)return;restoring=true;const state=JSON.parse(history[i]);Object.assign(sides,state.sides);activeSide=state.activeSide;canvas.clear();canvas.loadFromJSON(sides[activeSide],()=>{canvas.renderAll();refreshLayers();restoring=false;historyIndex=i;$('undoBtn').disabled=i<=0;$('redoBtn').disabled=i>=history.length-1;quality()})}
function refreshLayers(){const l=$('layersList');l.innerHTML='';[...canvas.getObjects()].reverse().forEach(o=>{const r=document.createElement('div');r.className='layer-row'+(canvas.getActiveObject()===o?' active':'');r.innerHTML=`<span class="thumb">${o.type==='textbox'?'Tt':'▧'}</span><input value="${String(o.name||o.type).replace(/"/g,'&quot;')}"><button class="vis">${o.visible===false?'○':'◉'}</button><button class="lock">${o.selectable?'♙':'🔒'}</button><button class="del">⊗</button>`;r.onclick=e=>{if(!e.target.matches('button,input')&&o.selectable){canvas.setActiveObject(o);canvas.requestRenderAll();refreshLayers()}};r.querySelector('input').onchange=e=>{o.name=e.target.value;commit()};r.querySelector('.vis').onclick=()=>{o.visible=!o.visible;canvas.renderAll();commit()};r.querySelector('.lock').onclick=()=>{if(o.isBase)return;o.selectable=!o.selectable;o.evented=o.selectable;canvas.discardActiveObject();canvas.renderAll();commit()};r.querySelector('.del').onclick=()=>{if(!o.isBase){canvas.remove(o);commit()}};l.appendChild(r)})}
function quality(){let score=100;canvas.getObjects().forEach(o=>{if(o.isBase)return;if(o.type==='image'&&o.width*o.scaleX<150)score-=10;if(o.left<80||o.top<25||o.left+o.getScaledWidth()>520||o.top+o.getScaledHeight()>530)score-=5});$('qualityScore').textContent=Math.max(50,score)+'%'}
const selected=()=>canvas.getActiveObject();
function mutate(fn){const o=selected();if(o&&!o.isBase){fn(o);o.setCoords();canvas.renderAll();commit()}}
function setZoom(z){zoom=Math.max(.35,Math.min(1.5,z));const stage=$('designStage');if(stage)stage.style.transform=`scale(${zoom})`;$('zoomLabel').textContent=Math.round(zoom*100)+'%'}
function userObjects(){return canvas.getObjects().filter(o=>!o.isBase)}
function deleteSelected(){const a=canvas.getActiveObjects().filter(o=>!o.isBase);a.forEach(o=>canvas.remove(o));canvas.discardActiveObject();commit()}
document.querySelectorAll('.rail-btn').forEach(b=>b.onclick=()=>{document.querySelectorAll('.rail-btn').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.pane').forEach(x=>x.classList.remove('active'));b.classList.add('active');$('pane-'+b.dataset.panel).classList.add('active');requestAnimationFrame(fitEditor)});
document.querySelectorAll('[data-text]').forEach(b=>b.onclick=()=>addText(b.dataset.text,b.classList.contains('heading')?48:b.classList.contains('subheading')?34:22));
$('curvedText').onclick=()=>addText('CURVED TEXT',34,'Curved text');
$('templateSearch').oninput=e=>renderTemplates(e.target.value);$('clipSearch').oninput=e=>document.querySelectorAll('#clipGrid .asset-card').forEach(x=>x.style.display=x.textContent.includes(e.target.value)?'grid':'none');
$('imageUpload').onchange=e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();r.onload=ev=>fabric.Image.fromURL(ev.target.result,img=>{img.scaleToWidth(Math.min(220,img.width));img.set({left:190,top:175,name:f.name});applyUserDefaults(img);canvas.add(img);canvas.setActiveObject(img);commit()});r.readAsDataURL(f)};
$('fontFamily').onchange=e=>mutate(o=>o.set('fontFamily',e.target.value));$('fontSize').onchange=e=>mutate(o=>o.set('fontSize',Number(e.target.value)));$('fillColor').oninput=e=>mutate(o=>o.set('fill',e.target.value));$('boldBtn').onclick=()=>mutate(o=>o.set('fontWeight',o.fontWeight==='bold'?'normal':'bold'));$('italicBtn').onclick=()=>mutate(o=>o.set('fontStyle',o.fontStyle==='italic'?'normal':'italic'));$('caseBtn').onclick=()=>mutate(o=>{if(o.text)o.set('text',o.text===o.text.toUpperCase()?o.text.toLowerCase():o.text.toUpperCase())});$('alignBtn').onclick=()=>mutate(o=>o.set('textAlign',o.textAlign==='center'?'left':o.textAlign==='left'?'right':'center'));$('rotateBtn').onclick=()=>mutate(o=>o.rotate((o.angle||0)+15));$('opacityBtn').onclick=()=>mutate(o=>o.set('opacity',o.opacity===1?.65:1));$('shadowBtn').onclick=()=>mutate(o=>o.set('shadow',o.shadow?null:new fabric.Shadow({color:'rgba(0,0,0,.45)',blur:8,offsetX:4,offsetY:4})));$('strokeBtn').onclick=()=>mutate(o=>o.set({stroke:o.stroke?null:'#fff',strokeWidth:o.stroke?0:2}));
$('undoBtn').onclick=()=>restore(historyIndex-1);$('redoBtn').onclick=()=>restore(historyIndex+1);$('deleteBtn').onclick=deleteSelected;$('sideTopBtn').onclick=()=>loadSide(activeSide==='front'?'back':'front');$('upLayer').onclick=()=>mutate(o=>canvas.bringForward(o));$('downLayer').onclick=()=>mutate(o=>canvas.sendBackwards(o));$('resetView').onclick=fitEditor;$('zoomIn').onclick=()=>setZoom(zoom+.1);$('zoomOut').onclick=()=>setZoom(zoom-.1);$('fitBtn').onclick=fitEditor;
$('cutGuide').onclick=()=>document.querySelector('.cut-line').classList.toggle('hidden');$('safeGuide').onclick=()=>document.querySelector('.safe-line').classList.toggle('hidden');
$('drawBtn').onclick=()=>{canvas.isDrawingMode=!canvas.isDrawingMode;canvas.freeDrawingBrush.width=5;canvas.freeDrawingBrush.color=$('fillColor').value};$('qrBtn').onclick=()=>{const v=prompt('Enter text or URL for QR code');if(v)addText('▦\n'+v,26,'QR code')};$('vcardBtn').onclick=()=>addText('YOUR NAME\nRole / Company\nPhone · Email',24,'vCard');$('gridFrameBtn').onclick=()=>{const o=applyUserDefaults(new fabric.Rect({left:170,top:150,width:260,height:240,fill:'transparent',stroke:'#fff',strokeWidth:4,name:'Grid frame'}));canvas.add(o);canvas.setActiveObject(o);commit()};$('photoFrameBtn').onclick=$('gridFrameBtn').onclick;
canvas.on('object:modified',commit);canvas.on('object:added',e=>{if(canvas.isDrawingMode&&e.target&&!e.target.isBase){applyUserDefaults(e.target);commit()}});canvas.on('selection:created',refreshLayers);canvas.on('selection:updated',refreshLayers);canvas.on('selection:cleared',refreshLayers);
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();restore(historyIndex+(e.shiftKey?1:-1))}if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='c'){const o=selected();if(o&&!o.isBase)o.clone(c=>clipboard=c)}if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='v'&&clipboard){clipboard.clone(c=>{c.set({left:(c.left||0)+18,top:(c.top||0)+18});applyUserDefaults(c);canvas.add(c);canvas.setActiveObject(c);commit()})}if(e.key==='Delete')deleteSelected()});
function menu(type){const p=$('menuPopup');const data={file:[['Download high-resolution PNG',download],['Save for later',()=>save('draft')],['Clear editable artwork',()=>{userObjects().forEach(o=>canvas.remove(o));commit()}]],edit:[['Copy',()=>document.dispatchEvent(new KeyboardEvent('keydown',{key:'c',ctrlKey:true}))],['Paste',()=>document.dispatchEvent(new KeyboardEvent('keydown',{key:'v',ctrlKey:true}))],['Delete',deleteSelected],['Select all',()=>{const a=new fabric.ActiveSelection(userObjects(),{canvas});canvas.setActiveObject(a);canvas.requestRenderAll()}]],view:[['Toggle cut line',()=>$('cutGuide').click()],['Toggle safe zone',()=>$('safeGuide').click()],['Fit garment',()=>$('fitBtn').click()]]}[type];p.innerHTML='';data.forEach(([n,f])=>{const b=document.createElement('button');b.textContent=n;b.onclick=()=>{f();p.classList.remove('show')};p.appendChild(b)});p.classList.add('show')}
document.querySelectorAll('[data-menu]').forEach(b=>b.onclick=()=>menu(b.dataset.menu));document.addEventListener('click',e=>{if(!e.target.closest('[data-menu],#menuPopup'))$('menuPopup').classList.remove('show')});
const tip=$('tip'),tipClose=tip?.querySelector('button');if(tipClose)tipClose.onclick=()=>tip.remove();const helpBtn=$('helpBtn');if(helpBtn)helpBtn.onclick=()=>alert('Choose a jersey template, add text or artwork, switch Front/Back, then click Process to review both garment previews.');
async function renderSide(side){saveSide();return new Promise(resolve=>{const temp=document.createElement('canvas');temp.width=W;temp.height=H;const fc=new fabric.StaticCanvas(temp,{width:W,height:H,backgroundColor:'#f7f8fa'});const data=sides[side]||sides.front;fc.loadFromJSON(data,()=>{fc.renderAll();resolve(fc.toDataURL({format:'png',multiplier:2}))})})}
$('processBtn').onclick=async()=>{$('proofFront').src=await renderSide('front');$('proofBack').src=await renderSide('back');$('processModal').classList.add('show');$('totalPrice').textContent='$'+(price*(Number($('quantity').value)||1)).toFixed(2)};
document.querySelectorAll('.modal-x').forEach(b=>b.onclick=()=>b.closest('.modal').classList.remove('show'));$('quantity').oninput=()=>{$('totalPrice').textContent='$'+(price*(Number($('quantity').value)||1)).toFixed(2)};
async function save(status){saveSide();const payload={product_id:productId,design_id:designId||null,name:app.dataset.productName+' Apparel Design',quantity:Number($('quantity').value)||1,status,design_json:{type:'apparel-pro',version:7,physical_size:{width_in:60,height_in:56,ppi:PPI},size:$('shirtSize').value,sides},preview_png:await renderSide('front')};const r=await fetch('/api/save-design/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify(payload)}),d=await r.json();if(!d.ok)throw Error(d.error||'Unable to save');designId=d.design_id;if(status==='cart')location.href=d.cart_url;else alert('Design saved successfully.')}
function download(){const a=document.createElement('a');a.download=app.dataset.productName.replace(/\W+/g,'-')+'-'+activeSide+'.png';a.href=canvas.toDataURL({format:'png',multiplier:4});a.click()}
$('saveDraft').onclick=()=>save('draft').catch(e=>alert(e.message));$('addCart').onclick=()=>save('cart').catch(e=>alert(e.message));$('shareBtn').onclick=()=>navigator.clipboard?.writeText(location.href).then(()=>alert('Design link copied'));

function installTshirtArrange(){
 const root=$('tshirtArrange'),trigger=$('tshirtArrangeBtn');if(!root||!trigger)return;
 const active=()=>canvas.getActiveObject();
 const selectedMany=()=>canvas.getActiveObjects().filter(o=>!o.isBase);
 const align=(kind)=>{const o=active();if(!o||o.isBase)return;const b=o.getBoundingRect(true,true);const margin=18;
  if(kind==='left')o.left+=(margin-b.left);if(kind==='center')o.left+=(W/2-(b.left+b.width/2));if(kind==='right')o.left+=(W-margin-(b.left+b.width));
  if(kind==='top')o.top+=(margin-b.top);if(kind==='middle')o.top+=(H/2-(b.top+b.height/2));if(kind==='bottom')o.top+=(H-margin-(b.top+b.height));o.setCoords();canvas.requestRenderAll();commit();};
 trigger.onclick=e=>{e.stopPropagation();root.classList.toggle('open')};
 root.querySelectorAll('[data-zv-arrange]').forEach(b=>b.onclick=e=>{e.stopPropagation();const a=b.dataset.zvArrange,o=active();
  if(['left','center','right','top','middle','bottom'].includes(a))align(a);
  else if(o&&!o.isBase&&a==='forward')mutate(x=>canvas.bringForward(x));else if(o&&!o.isBase&&a==='backward')mutate(x=>canvas.sendBackwards(x));
  else if(o&&!o.isBase&&a==='flipH')mutate(x=>x.set('flipX',!x.flipX));else if(o&&!o.isBase&&a==='flipV')mutate(x=>x.set('flipY',!x.flipY));
  else if(a==='group'){if(o?.type==='activeSelection'){o.toGroup();canvas.requestRenderAll();commit()}else if(o?.type==='group'){o.toActiveSelection();canvas.requestRenderAll();commit()}else if(selectedMany().length>1){new fabric.ActiveSelection(selectedMany(),{canvas}).toGroup();canvas.requestRenderAll();commit()}}
  root.classList.remove('open');});
 document.addEventListener('click',e=>{if(!root.contains(e.target))root.classList.remove('open')});
}
installTshirtArrange();
renderTemplates();renderAssets('clipGrid',cliparts,'Clipart');renderAssets('elementSubgrid',['●','■','▲','★','♥','⬟','◆','✦','➤','☀','☁','⚡'],'Element');buildRulers();
['THE NEW YOU','Medieval','ALEX ♥ SARA','Smith & Sons','MEXICO','Blackbird'].forEach((x,i)=>{const b=document.createElement('button');b.className='style-thumb';b.textContent=x;b.style.fontFamily=i%2?'Georgia':'Times New Roman';b.onclick=()=>addText(x,28,'Styled text');$('textStyles').appendChild(b)});
let initial={};try{initial=JSON.parse($('initialDesign').textContent||'{}')}catch(e){}const local=localStorage.getItem('zv-apparel-'+productId);let state=initial.type==='apparel-pro'&&Number(initial.version)>=7?initial:(local?JSON.parse(local):null);if(state&&Number(state.version||0)<7)state=null;if(state?.sides){Object.assign(sides,state.sides);activeSide=state.activeSide||'front';canvas.loadFromJSON(sides[activeSide],()=>{canvas.renderAll();commit()})}else if(realGarments.length){buildPhotoGarment(realGarments[0])}else{buildJersey(templateDefs[0],true)}
renderGarmentPhotos();
function fitEditor(){const sc=$('canvasScroll'),stage=$('designStage');if(!sc||!stage)return;const reserveX=20,reserveY=18;const stageW=630,stageH=590;const availableW=Math.max(240,sc.clientWidth-reserveX);const availableH=Math.max(240,sc.clientHeight-reserveY);setZoom(Math.min(.9,availableW/stageW,availableH/stageH));}
requestAnimationFrame(fitEditor);window.addEventListener('resize',fitEditor);
})();
