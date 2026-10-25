(()=>{
'use strict';
const app=document.querySelector('.pen-editor');
if(!app||!window.fabric)return;
const $=id=>document.getElementById(id);
const productId=Number(app.dataset.productId||0);
const productSlug=(app.dataset.productSlug||'business-signature-metal-gel-pen').toLowerCase();
const unitPrice=Number(app.dataset.productPrice||0);
let designId=app.dataset.designId||'';
let penColor=app.dataset.selectedColor||'navy';
let inkColor=app.dataset.selectedInk||'black';
let activeSide=1;
let zoom=1;
let restoring=false;
let historyStack=[];
let historyIndex=-1;

const W=900,H=300;
const VIEW_Y=-60;
let PRINT={left:238,top:187,width:325,height:58};
const canvas=new fabric.Canvas('penCanvas',{
 width:W,height:H,backgroundColor:'#fff',preserveObjectStacking:true,
 selection:true,stopContextMenu:true
});
window.designCanvas=canvas;if(window.ZenImageTools)ZenImageTools.attach(canvas);
canvas.setDimensions({width:W,height:H});
canvas.setViewportTransform([1,0,0,1,0,VIEW_Y]);
fabric.Object.prototype.set({
 transparentCorners:false,cornerStyle:'circle',cornerColor:'#fff',cornerStrokeColor:'#485476',
 borderColor:'#2f9ad8',padding:4,cornerSize:10
});

const palette={
 black:{top:'#555b63',mid:'#111318',bottom:'#242a31',edge:'#020306',accent:'#0b0d11'},
 navy:{top:'#5577a6',mid:'#17345d',bottom:'#294f7e',edge:'#07162c',accent:'#102b50'},
 silver:{top:'#ffffff',mid:'#c5cbd1',bottom:'#eef2f5',edge:'#858d95',accent:'#aab1b8'}
};
const inkMap={black:'#111',blue:'#133dcc'};
const csrf=()=>document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';
const baseObjects=()=>canvas.getObjects().filter(o=>o.isBase);
const userObjects=()=>canvas.getObjects().filter(o=>!o.isBase&&!o.printZone);

function gradient(stops,x2=0,y2=1){
 return new fabric.Gradient({type:'linear',gradientUnits:'percentage',coords:{x1:0,y1:0,x2,y2},colorStops:stops});
}
function chrome(horizontal=false){
 return gradient([
  {offset:0,color:'#6e7378'},{offset:.12,color:'#fdfefe'},{offset:.27,color:'#a5aaae'},
  {offset:.45,color:'#ffffff'},{offset:.66,color:'#777d82'},{offset:.82,color:'#f6f7f8'},{offset:1,color:'#74797d'}
 ],horizontal?1:0,horizontal?0:1);
}
function addBase(obj){obj.set({selectable:false,evented:false,isBase:true,hoverCursor:'default'});canvas.add(obj);return obj}

function addHighlight(left,top,width,height,opacity=.22){
 addBase(new fabric.Rect({left,top,width,height,rx:height/2,ry:height/2,fill:`rgba(255,255,255,${opacity})`}));
}
function addShadow(left=105,top=282,rx=345,ry=15){
 addBase(new fabric.Ellipse({left,top,rx,ry,fill:'rgba(11,18,30,.15)',shadow:new fabric.Shadow({color:'rgba(0,0,0,.10)',blur:13,offsetY:6})}));
}
function bodyGradient(c){return gradient([{offset:0,color:c.top},{offset:.18,color:c.mid},{offset:.48,color:c.edge},{offset:.74,color:c.bottom},{offset:.92,color:c.mid},{offset:1,color:c.edge}]);}
function setPrint(left,top,width,height){PRINT={left,top,width,height};}

function buildSignaturePen(c){
 setPrint(238,187,325,58); addShadow();
 addBase(new fabric.Rect({left:111,top:179,width:52,height:72,rx:28,ry:28,fill:chrome(),stroke:'#777',strokeWidth:1}));
 addBase(new fabric.Rect({left:137,top:184,width:470,height:62,rx:30,ry:30,fill:bodyGradient(c),stroke:'#4d5259',strokeWidth:1}));
 addHighlight(155,189,425,8,.24);
 addBase(new fabric.Rect({left:596,top:176,width:31,height:79,fill:chrome(true),stroke:'#74797d',strokeWidth:1}));
 addBase(new fabric.Rect({left:626,top:177,width:209,height:76,rx:34,ry:34,fill:bodyGradient(c),stroke:'#4b5057',strokeWidth:1}));
 addHighlight(644,184,170,8,.20);
 addBase(new fabric.Rect({left:828,top:185,width:38,height:60,rx:18,ry:18,fill:chrome(),stroke:'#777',strokeWidth:1}));
 addBase(new fabric.Path('M 678 196 C 715 181 760 180 809 194 L 800 205 C 754 198 719 201 685 215 L 670 208 Z',{fill:chrome(true),stroke:'#60656a',strokeWidth:1}));
 addBase(new fabric.Circle({left:666,top:201,radius:6,fill:'#d8dbde',stroke:'#686d72',strokeWidth:1}));
}
function buildRollerPen(c){
 setPrint(263,190,300,50); addShadow(120,278,330,14);
 addBase(new fabric.Path('M 85 214 L 142 186 L 142 244 Z',{fill:chrome(true),stroke:'#74797d',strokeWidth:1}));
 addBase(new fabric.Rect({left:130,top:185,width:470,height:60,rx:28,ry:28,fill:bodyGradient(c),stroke:'#4d5259',strokeWidth:1}));
 addBase(new fabric.Rect({left:590,top:181,width:35,height:68,fill:chrome(true),stroke:'#777'}));
 addBase(new fabric.Rect({left:620,top:180,width:210,height:70,rx:28,ry:28,fill:bodyGradient(c),stroke:'#4d5259'}));
 addBase(new fabric.Rect({left:820,top:188,width:45,height:54,rx:20,ry:20,fill:chrome(),stroke:'#777'}));
 addHighlight(158,191,405,7,.28); addHighlight(642,187,156,7,.20);
 addBase(new fabric.Path('M 676 195 C 720 180 765 181 814 196 L 803 207 C 757 198 718 202 684 216 Z',{fill:chrome(true),stroke:'#656a70',strokeWidth:1}));
}
function buildTwistPen(c){
 setPrint(265,193,285,44); addShadow(125,270,320,12);
 addBase(new fabric.Path('M 80 216 L 154 190 L 154 242 Z',{fill:chrome(true),stroke:'#777'}));
 addBase(new fabric.Rect({left:145,top:190,width:500,height:52,rx:25,ry:25,fill:bodyGradient(c),stroke:'#4b5057'}));
 addBase(new fabric.Rect({left:635,top:187,width:30,height:58,fill:chrome(true),stroke:'#777'}));
 addBase(new fabric.Rect({left:660,top:189,width:125,height:54,rx:22,ry:22,fill:bodyGradient(c),stroke:'#4b5057'}));
 addBase(new fabric.Rect({left:775,top:195,width:72,height:42,rx:18,ry:18,fill:chrome(),stroke:'#777'}));
 addHighlight(170,195,440,6,.24);
 addBase(new fabric.Path('M 700 194 C 730 185 760 184 795 195 L 786 203 C 754 198 730 201 707 211 Z',{fill:chrome(true),stroke:'#62676d'}));
}
function buildStylusPen(c){
 setPrint(245,193,300,44); addShadow(115,275,330,13);
 addBase(new fabric.Circle({left:92,top:192,radius:25,fill:'#16181d',stroke:'#555'}));
 addBase(new fabric.Circle({left:99,top:199,radius:18,fill:'#2e3339'}));
 addBase(new fabric.Rect({left:135,top:190,width:485,height:52,rx:24,ry:24,fill:bodyGradient(c),stroke:'#4c5157'}));
 addBase(new fabric.Rect({left:610,top:187,width:35,height:58,fill:chrome(true),stroke:'#777'}));
 addBase(new fabric.Rect({left:640,top:190,width:155,height:52,rx:22,ry:22,fill:bodyGradient(c),stroke:'#4c5157'}));
 addBase(new fabric.Path('M 794 191 L 855 216 L 794 241 Z',{fill:chrome(true),stroke:'#777'}));
 addHighlight(157,195,430,6,.23);
 addBase(new fabric.Path('M 690 194 C 720 186 751 187 783 198 L 774 207 C 746 200 721 202 698 213 Z',{fill:chrome(true),stroke:'#63686d'}));
}
function buildBambooPen(c){
 setPrint(235,190,320,50); addShadow(110,278,335,13);
 const bamboo=gradient([{offset:0,color:'#d2a55f'},{offset:.2,color:'#f1d49b'},{offset:.45,color:'#b77b32'},{offset:.72,color:'#e6c17f'},{offset:1,color:'#a66b2c'}]);
 addBase(new fabric.Path('M 82 216 L 145 190 L 145 242 Z',{fill:chrome(true),stroke:'#777'}));
 addBase(new fabric.Rect({left:138,top:187,width:490,height:58,rx:25,ry:25,fill:bamboo,stroke:'#986427'}));
 addBase(new fabric.Rect({left:618,top:184,width:34,height:64,fill:chrome(true),stroke:'#777'}));
 addBase(new fabric.Rect({left:646,top:187,width:145,height:58,rx:24,ry:24,fill:bodyGradient(c),stroke:'#4c5157'}));
 addBase(new fabric.Rect({left:780,top:193,width:66,height:46,rx:20,ry:20,fill:bodyGradient(c),stroke:'#4c5157'}));
 addHighlight(162,193,430,7,.20);
 addBase(new fabric.Path('M 689 194 C 722 185 752 186 784 198 L 775 207 C 747 201 721 204 697 214 Z',{fill:chrome(true),stroke:'#62676d'}));
}
function buildGiftPen(c){
 setPrint(250,190,300,50); addShadow(118,280,330,14);
 addBase(new fabric.Path('M 85 216 L 145 188 L 145 244 Z',{fill:chrome(true),stroke:'#777'}));
 addBase(new fabric.Rect({left:138,top:184,width:470,height:64,rx:30,ry:30,fill:bodyGradient(c),stroke:'#34383e',strokeWidth:2}));
 addBase(new fabric.Rect({left:596,top:178,width:40,height:76,fill:chrome(true),stroke:'#777'}));
 addBase(new fabric.Rect({left:630,top:180,width:190,height:72,rx:30,ry:30,fill:bodyGradient(c),stroke:'#34383e',strokeWidth:2}));
 addBase(new fabric.Rect({left:810,top:187,width:54,height:58,rx:24,ry:24,fill:chrome(),stroke:'#777'}));
 addHighlight(160,191,415,9,.28); addHighlight(650,187,140,8,.22);
 addBase(new fabric.Path('M 672 194 C 715 177 762 178 811 194 L 800 206 C 755 197 718 201 682 217 Z',{fill:chrome(true),stroke:'#5a6066',strokeWidth:1.5}));
 addBase(new fabric.Circle({left:664,top:202,radius:7,fill:'#f5f6f7',stroke:'#666'}));
}

function buildPen(){
 baseObjects().forEach(o=>canvas.remove(o));
 const c=palette[penColor]||palette.navy;
 if(productSlug.includes('roller')) buildRollerPen(c);
 else if(productSlug.includes('twist')) buildTwistPen(c);
 else if(productSlug.includes('stylus')) buildStylusPen(c);
 else if(productSlug.includes('bamboo')) buildBambooPen(c);
 else if(productSlug.includes('gift-box')) buildGiftPen(c);
 else buildSignaturePen(c);
 drawPrintZone();
 userObjects().forEach(o=>canvas.bringToFront(o));
 canvas.requestRenderAll();
}

function drawPrintZone(){
 canvas.getObjects().filter(o=>o.printZone).forEach(o=>canvas.remove(o));
 const zone=new fabric.Rect({
  ...PRINT,fill:'rgba(20,160,90,.025)',stroke:'#20a05a',strokeWidth:1.25,
  strokeDashArray:[5,3],selectable:false,evented:false,excludeFromExport:true,
  isBase:true,printZone:true
 });
 canvas.add(zone);canvas.bringToFront(zone);
}

function constrainObject(o){
 if(!o||o.isBase)return;
 const br=o.getBoundingRect(true,true);
 let dx=0,dy=0;
 if(br.left<PRINT.left)dx=PRINT.left-br.left;
 if(br.top<PRINT.top)dy=PRINT.top-br.top;
 if(br.left+br.width>PRINT.left+PRINT.width)dx=(PRINT.left+PRINT.width)-(br.left+br.width);
 if(br.top+br.height>PRINT.top+PRINT.height)dy=(PRINT.top+PRINT.height)-(br.top+br.height);
 o.left+=dx;o.top+=dy;o.setCoords();
}

function addText(text='Company Name / Phone',size=26){
 const t=new fabric.IText(text,{
  left:PRINT.left+PRINT.width/2,top:PRINT.top+PRINT.height/2,
  originX:'center',originY:'center',fontFamily:'Roboto',fontSize:size,
  fill:penColor==='silver'?'#172033':'#ffffff',fontWeight:'600',
  textAlign:'center',name:text,lockScalingFlip:true
 });
 const maxW=PRINT.width-18;
 if(t.width>maxW)t.scaleToWidth(maxW);
 canvas.add(t);canvas.setActiveObject(t);canvas.bringToFront(t);drawPrintZone();commit();
}

function serialise(){return canvas.toDatalessJSON(['name','isBase','printZone']);}
function state(){return{type:'pen-pro',version:2,pen_color:penColor,ink_color:inkColor,active_side:activeSide,document:{width_in:36,height_in:18,ppi:25},print_area:PRINT,canvas:serialise()};}
function commit(){
 if(restoring)return;
 const json=JSON.stringify(serialise());
 if(historyStack[historyIndex]===json)return;
 historyStack=historyStack.slice(0,historyIndex+1);historyStack.push(json);historyIndex=historyStack.length-1;
 updateHistory();renderLayers();localStorage.setItem('zv-pen-'+productId,JSON.stringify(state()));
}
function restore(index){
 if(index<0||index>=historyStack.length)return;
 restoring=true;
 canvas.loadFromJSON(historyStack[index],()=>{
  historyIndex=index;restoring=false;canvas.renderAll();updateHistory();renderLayers();
 });
}
function updateHistory(){$('undoBtn').disabled=historyIndex<=0;$('redoBtn').disabled=historyIndex>=historyStack.length-1;}
function renderLayers(){
 const box=$('layersList');if(!box)return;box.innerHTML='';
 [...userObjects()].reverse().forEach(o=>{
  const row=document.createElement('div');row.className='layer-row';
  row.innerHTML=`<span>${o.name||o.type}</span><button class="eye">◉</button><button class="del">×</button>`;
  row.querySelector('.eye').onclick=()=>{o.visible=!o.visible;canvas.requestRenderAll();commit()};
  row.querySelector('.del').onclick=()=>{canvas.remove(o);commit()};box.appendChild(row);
 });
}
function syncUrl(){const u=new URL(location.href);u.searchParams.set('color',penColor);u.searchParams.set('ink',inkColor);history.replaceState({},'',u)}
function applyPenColor(color){
 const normalised=String(color||'navy').toLowerCase();
 if(!palette[normalised])return;
 penColor=normalised;
 document.querySelectorAll('[data-color]').forEach(b=>{
  const active=b.dataset.color===penColor;
  b.classList.toggle('active',active);
  b.setAttribute('aria-pressed',active?'true':'false');
 });
 // Rebuild only the non-editable product artwork. All customer text/logo objects remain.
 buildPen();
 const designFill=penColor==='silver'?'#172033':'#ffffff';
 userObjects().forEach(o=>{
  if(o.type==='i-text'||o.type==='text'||o.type==='textbox')o.set('fill',designFill);
 });
 canvas.discardActiveObject();
 canvas.requestRenderAll();
 commit();
 syncUrl();
 localStorage.setItem('zv-pen-'+productId,JSON.stringify(state()));
}
function applyInkColor(color){
 inkColor=color;document.querySelectorAll('[data-ink]').forEach(b=>b.classList.toggle('active',b.dataset.ink===color));
 syncUrl();localStorage.setItem('zv-pen-'+productId,JSON.stringify(state()));
}

// panels and variants
document.querySelectorAll('.pe-rail button[data-panel]').forEach(btn=>btn.onclick=()=>{
 document.querySelectorAll('.pe-rail button').forEach(x=>x.classList.remove('active'));
 document.querySelectorAll('.pe-pane').forEach(x=>x.classList.remove('active'));
 btn.classList.add('active');$('pane-'+btn.dataset.panel).classList.add('active');requestAnimationFrame(fit);
});
document.querySelectorAll('[data-color]').forEach(b=>b.onclick=()=>applyPenColor(b.dataset.color));
document.querySelectorAll('[data-ink]').forEach(b=>b.onclick=()=>applyInkColor(b.dataset.ink));
document.querySelectorAll('.add-text').forEach(b=>b.onclick=()=>addText(b.dataset.text,b.classList.contains('big')?29:25));
document.querySelectorAll('[data-layout]').forEach(b=>b.onclick=()=>{
 userObjects().forEach(o=>canvas.remove(o));
 const copy={company:'Company Name / Phone',logo:'YOUR LOGO',name:'Your Name'};
 addText(copy[b.dataset.layout],b.dataset.layout==='logo'?29:25);
});

$('imageUpload').onchange=e=>{
 const f=e.target.files[0];if(!f)return;
 const reader=new FileReader();reader.onload=ev=>fabric.Image.fromURL(ev.target.result,img=>{
  img.scaleToWidth(Math.min(180,img.width));
  if(img.getScaledHeight()>PRINT.height-10)img.scaleToHeight(PRINT.height-10);
  img.set({left:PRINT.left+PRINT.width/2,top:PRINT.top+PRINT.height/2,originX:'center',originY:'center',name:f.name,lockScalingFlip:true});
  canvas.add(img);canvas.setActiveObject(img);constrainObject(img);canvas.bringToFront(img);drawPrintZone();commit();
 },{crossOrigin:'anonymous'});reader.readAsDataURL(f);
};
document.querySelectorAll('[data-shape]').forEach(b=>b.onclick=()=>{
 let o;
 if(b.dataset.shape==='line')o=new fabric.Line([0,0,110,0],{stroke:'#fff',strokeWidth:3});
 else if(b.dataset.shape==='circle')o=new fabric.Circle({radius:17,fill:'#fff'});
 else o=new fabric.Text(b.dataset.shape==='star'?'★':'◆',{fontSize:34,fill:'#fff'});
 o.set({left:PRINT.left+PRINT.width/2,top:PRINT.top+PRINT.height/2,originX:'center',originY:'center',name:b.dataset.shape});
 canvas.add(o);canvas.setActiveObject(o);drawPrintZone();commit();
});

const selected=()=>canvas.getActiveObject();
function mutate(fn){const o=selected();if(!o||o.isBase)return;fn(o);constrainObject(o);o.setCoords();canvas.requestRenderAll();commit();}
$('fontFamily').onchange=e=>mutate(o=>o.set('fontFamily',e.target.value));
$('fontSize').onchange=e=>mutate(o=>o.set({fontSize:Number(e.target.value)||26,scaleX:1,scaleY:1}));
$('fillColor').oninput=e=>mutate(o=>o.set('fill',e.target.value));
$('boldBtn').onclick=()=>mutate(o=>o.set('fontWeight',o.fontWeight==='bold'?'normal':'bold'));
$('italicBtn').onclick=()=>mutate(o=>o.set('fontStyle',o.fontStyle==='italic'?'normal':'italic'));
$('caseBtn').onclick=()=>mutate(o=>o.text&&o.set('text',o.text===o.text.toUpperCase()?o.text.toLowerCase():o.text.toUpperCase()));
$('alignBtn').onclick=()=>mutate(o=>o.set('textAlign','center'));
$('centerBtn').onclick=()=>mutate(o=>o.set({left:PRINT.left+PRINT.width/2,top:PRINT.top+PRINT.height/2,originX:'center',originY:'center'}));
$('rotateBtn').onclick=()=>mutate(o=>o.rotate((o.angle||0)+15));
$('deleteBtn').onclick=()=>{canvas.getActiveObjects().filter(o=>!o.isBase).forEach(o=>canvas.remove(o));canvas.discardActiveObject();commit()};
$('undoBtn').onclick=()=>restore(historyIndex-1);$('redoBtn').onclick=()=>restore(historyIndex+1);
$('upLayer').onclick=()=>mutate(o=>canvas.bringForward(o));$('downLayer').onclick=()=>mutate(o=>canvas.sendBackwards(o));
canvas.on('object:moving',e=>constrainObject(e.target));
canvas.on('object:scaling',e=>constrainObject(e.target));
canvas.on('object:modified',commit);
canvas.on('text:changed',e=>{const o=e.target;if(o.width*o.scaleX>PRINT.width-12)o.scaleToWidth(PRINT.width-12);constrainObject(o);canvas.requestRenderAll()});
canvas.on('selection:created',renderLayers);canvas.on('selection:updated',renderLayers);

function buildRulers(){
 // Pen products use a compact product artboard rather than document rulers.
 // Keeping this function as a no-op preserves compatibility with older templates.
 const rx=$('rulerX'),ry=$('rulerY');
 if(rx)rx.innerHTML='';
 if(ry)ry.innerHTML='';
}
function applyZoom(){
 const stage=$('designStage'),scroll=$('stageScroll');
 stage.style.transform=`scale(${zoom})`;stage.style.transformOrigin='top left';
 const naturalW=960,naturalH=330;
 stage.parentElement.style.setProperty('--stage-w',`${naturalW*zoom}px`);
 stage.parentElement.style.setProperty('--stage-h',`${naturalH*zoom}px`);
 $('zoomLabel').textContent=Math.round(zoom*100)+'%';
 requestAnimationFrame(()=>{scroll.scrollLeft=Math.max(0,(scroll.scrollWidth-scroll.clientWidth)/2);scroll.scrollTop=Math.max(0,(scroll.scrollHeight-scroll.clientHeight)/2)});
}
function fit(){
 const sc=$('stageScroll');if(!sc)return;
 const w=Math.max(320,sc.clientWidth-54),h=Math.max(220,sc.clientHeight-44);
 zoom=Math.max(.62,Math.min(1.35,w/960,h/330));applyZoom();
}
function setZoom(v){zoom=Math.max(.4,Math.min(1.7,v));applyZoom();}
$('fitBtn').onclick=fit;$('resetView').onclick=fit;$('zoomIn').onclick=()=>setZoom(zoom+.1);$('zoomOut').onclick=()=>setZoom(zoom-.1);
if($('cutGuide'))$('cutGuide').onclick=()=>document.querySelector('.cut-line')?.classList.toggle('hidden');
if($('safeGuide'))$('safeGuide').onclick=()=>document.querySelector('.safe-line')?.classList.toggle('hidden');
$('sideBtn').onclick=()=>{activeSide=activeSide===1?2:1;$('sideBtn').textContent='Side '+activeSide;$('pageCount').textContent=activeSide+'/2'};

function preview(){
 const guides=canvas.getObjects().filter(o=>o.printZone);guides.forEach(o=>o.visible=false);canvas.discardActiveObject();canvas.renderAll();
 const url=canvas.toDataURL({format:'png',multiplier:2});guides.forEach(o=>o.visible=true);canvas.renderAll();return url;
}
async function save(status){
 const payload={product_id:productId,design_id:designId||null,name:app.dataset.productName+' Pen Design',quantity:Number($('quantity').value)||1,status,design_json:state(),preview_png:preview()};
 const response=await fetch('/zenvibe/api/save-design/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify(payload)});
 const data=await response.json();if(!data.ok)throw new Error(data.error||'Unable to save design');designId=data.design_id;
 if(status==='cart')location.href=data.cart_url;else alert('Design saved successfully.');
}
$('processBtn').onclick=()=>{$('proofImage').src=preview();$('reviewPenColor').textContent=penColor;$('reviewInkColor').textContent=inkColor;$('totalPrice').textContent='$'+(unitPrice*(Number($('quantity').value)||1)).toFixed(2);$('processModal').classList.add('show')};
document.querySelector('.modal-x').onclick=()=>$('processModal').classList.remove('show');
$('saveDraft').onclick=()=>save('draft').catch(e=>alert(e.message));$('addCart').onclick=()=>save('cart').catch(e=>alert(e.message));
$('shareBtn').onclick=()=>navigator.clipboard?.writeText(location.href).then(()=>alert('Design link copied'));
function menu(type){
 const popup=$('menuPopup');const items={
  file:[['Download PNG',()=>{const a=document.createElement('a');a.download='pen-design.png';a.href=preview();a.click()}],['Save for later',()=>save('draft')]],
  edit:[['Delete selected',()=>$('deleteBtn').click()],['Select all',()=>canvas.setActiveObject(new fabric.ActiveSelection(userObjects(),{canvas}))]],
  view:[['Fit to screen',fit],['Toggle cut line',()=>$('cutGuide').click()],['Toggle safe zone',()=>$('safeGuide').click()]]
 }[type]||[];
 popup.innerHTML='';items.forEach(([name,fn])=>{const b=document.createElement('button');b.textContent=name;b.onclick=()=>{fn();popup.classList.remove('show')};popup.appendChild(b)});popup.classList.add('show');
}
document.querySelectorAll('[data-menu]').forEach(b=>b.onclick=()=>menu(b.dataset.menu));
document.addEventListener('click',e=>{if(!e.target.closest('[data-menu],#menuPopup'))$('menuPopup').classList.remove('show')});
$('helpBtn').onclick=()=>alert('Add text or a logo, keep the artwork inside the green imprint area, then click Process. The workspace can be scrolled and zoomed.');


function installPenArrange(){
 const root=$('penArrange'),trigger=$('penArrangeBtn');if(!root||!trigger)return;
 const align=(kind)=>{const o=selected();if(!o||o.isBase)return;const a=PRINT,b=o.getBoundingRect(true,true),pad=4;
  if(kind==='left')o.left+=a.left+pad-b.left;if(kind==='center')o.left+=a.left+a.width/2-(b.left+b.width/2);if(kind==='right')o.left+=a.left+a.width-pad-(b.left+b.width);
  if(kind==='top')o.top+=a.top+pad-b.top;if(kind==='middle')o.top+=a.top+a.height/2-(b.top+b.height/2);if(kind==='bottom')o.top+=a.top+a.height-pad-(b.top+b.height);o.setCoords();canvas.requestRenderAll();commit();};
 trigger.onclick=e=>{e.stopPropagation();root.classList.toggle('open')};
 root.querySelectorAll('[data-pe-arrange]').forEach(b=>b.onclick=e=>{e.stopPropagation();const a=b.dataset.peArrange,o=selected();
  if(['left','center','right','top','middle','bottom'].includes(a))align(a);
  else if(o&&!o.isBase&&a==='forward')mutate(x=>canvas.bringForward(x));else if(o&&!o.isBase&&a==='backward')mutate(x=>canvas.sendBackwards(x));
  else if(o&&!o.isBase&&a==='flipH')mutate(x=>x.set('flipX',!x.flipX));else if(o&&!o.isBase&&a==='flipV')mutate(x=>x.set('flipY',!x.flipY));
  else if(a==='group'){if(o?.type==='activeSelection'){o.toGroup();canvas.requestRenderAll();commit()}else if(o?.type==='group'){o.toActiveSelection();canvas.requestRenderAll();commit()}}
  root.classList.remove('open');});
 document.addEventListener('click',e=>{if(!root.contains(e.target))root.classList.remove('open')});
}
installPenArrange();
let initial={};try{initial=JSON.parse($('initialDesign').textContent||'{}')}catch(_e){}
let saved=null;try{const local=localStorage.getItem('zv-pen-'+productId);saved=initial.type==='pen-pro'?initial:(local?JSON.parse(local):null)}catch(_e){}
if(saved&&saved.canvas){
 penColor=saved.pen_color||penColor;inkColor=saved.ink_color||inkColor;
 canvas.loadFromJSON(saved.canvas,()=>{buildPen();userObjects().forEach(o=>canvas.bringToFront(o));drawPrintZone();canvas.renderAll();commit()});
}else{buildPen();addText();}
document.querySelectorAll('[data-color]').forEach(b=>b.classList.toggle('active',b.dataset.color===penColor));
document.querySelectorAll('[data-ink]').forEach(b=>b.classList.toggle('active',b.dataset.ink===inkColor));
buildRulers();requestAnimationFrame(fit);
let timer;window.addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(fit,120)});
})();
