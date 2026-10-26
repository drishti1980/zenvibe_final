/* ZenVibe Admin-driven print-area guard.
   Opt-in only: legacy products/templates are never constrained by this file. */
(function(){
'use strict';
const OPT=window.PRODUCT_OPTIONS||{};
const CFG=OPT.editor_config||OPT.editorConfig||{};
if(!CFG.enabled)return;
const SHOULD_CONSTRAIN=CFG.mode==='print_area' && CFG.constrainToPrintArea===true;

const states=new WeakMap();
let canvas=null, guideTimer=null, applying=false;

function editable(o){
  return !!o && !o.excludeFromExport && !o.zvProductMockup &&
    !o.backgroundAsset && !o.exactVisualMaster && o.customerEditable!==false;
}
function pageSurfaceId(){
  const surfaces=OPT.print_surfaces||OPT.printSurfaces||[];
  const page=(window.INITIAL_TEMPLATE?.pages||[])[window.ZV_ACTIVE_PAGE||0]||{};
  return Number(page.surfaceId||page.surface_id||surfaces[window.ZV_ACTIVE_PAGE||0]?.id||0)||null;
}
function referenceObject(){
  if(!canvas)return null;
  return canvas.getObjects().find(o=>o && o.zvProductMockup &&
    (o.name==='Locked product reference'||o.name==='Locked product mockup'))||null;
}
function currentImageId(){
  const ref=referenceObject();
  const url=String(ref?.baseSrc||ref?._element?.src||'').split('?')[0];
  const images=Array.isArray(CFG.referenceImages)?CFG.referenceImages:[];
  const match=images.find(im=>im && im.url && String(im.url).split('?')[0]===url);
  return match ? (match.productImageId ?? null) : null;
}
function areas(){
  const all=Array.isArray(CFG.printAreas)?CFG.printAreas:[];
  const imageId=currentImageId();
  const byImage=all.filter(a=>imageId===null
    ? a.productImageId==null : Number(a.productImageId)===Number(imageId));
  const candidates=byImage.length?byImage:all.filter(a=>a.productImageId==null);
  const sid=pageSurfaceId();
  const scoped=sid?candidates.filter(a=>!a.surfaceId||Number(a.surfaceId)===sid):candidates.filter(a=>!a.surfaceId);
  return scoped.length?scoped:candidates;
}
function imageBounds(){
  const ref=referenceObject();
  if(ref){
    ref.setCoords();
    const b=ref.getBoundingRect(true,true);
    if(b.width>0&&b.height>0)return b;
  }
  const z=Math.max(0.0001,Number(canvas.getZoom?.()||1));
  return {left:0,top:0,width:canvas.getWidth()/z,height:canvas.getHeight()/z};
}
function rect(a){
  // Admin coordinates are percentages of the product IMAGE, not the artboard.
  const b=imageBounds();
  return {
    left:b.left+b.width*Number(a.leftPct??0)/100,
    top:b.top+b.height*Number(a.topPct??0)/100,
    width:b.width*Number(a.widthPct??100)/100,
    height:b.height*Number(a.heightPct??100)/100
  };
}
function objectBox(o){
  o.setCoords();
  return o.getBoundingRect(true,true);
}
function contains(r,b){
  const e=.5;
  return b.left>=r.left-e && b.top>=r.top-e &&
    b.left+b.width<=r.left+r.width+e &&
    b.top+b.height<=r.top+r.height+e;
}
function matchingArea(o){
  const b=objectBox(o);
  return areas().map(rect).find(r=>contains(r,b))||null;
}
function remember(o){
  states.set(o,{left:o.left,top:o.top,scaleX:o.scaleX,scaleY:o.scaleY,angle:o.angle});
}
function restore(o){
  const s=states.get(o);
  if(!s)return;
  applying=true;o.set(s);o.setCoords();applying=false;
}
function clipTo(r,o){
  if(!r||!o)return;
  o.clipPath=new fabric.Rect({
    left:r.left,top:r.top,width:r.width,height:r.height,
    absolutePositioned:true,fill:'#000',selectable:false,evented:false
  });
}
function enforce(o){
  if(!SHOULD_CONSTRAIN||applying||!editable(o))return;
  const r=matchingArea(o);
  if(r){remember(o);if(!o.zvAdminTextSource)clipTo(r,o);return;}
  restore(o);
  const fallback=matchingArea(o);
  if(fallback)clipTo(fallback,o);
  canvas.requestRenderAll();
}
function removeGuides(){
  canvas.getObjects().filter(o=>o.zvPrintAreaGuide).forEach(o=>canvas.remove(o));
}
function isCircularCoaster(){
  const ref=referenceObject();
  const image=String(ref?.baseSrc||ref?._element?.src||'').toLowerCase();
  const product=String(OPT.product_name||OPT.productName||CFG.productName||'').toLowerCase();
  const shape=String(CFG.shape||CFG.productShape||OPT.selectedShape||'').toLowerCase();
  // Image-specific detection takes precedence when switching product shapes.
  if(/(?:square|rectangle|rectangular)[-_ ]?coaster|coaster[-_ ]?(?:square|rectangle)/.test(image))return false;
  if(/(?:round|circle|circular)[-_ ]?coaster|coaster[-_ ]?(?:round|circle)/.test(image))return true;
  return /coaster/.test(product) && /round|circle/.test(shape+' '+product);
}
function drawGuides(){
  if(!canvas)return;
  removeGuides();
  areas().forEach((a,i)=>{
    const r=rect(a);
    const circular=isCircularCoaster();
    // A circle's safe zone must be inset from the actual circular cut edge.
    const inset=circular ? Math.min(r.width,r.height)*0.055 : 0;
    const guideProps=circular ? {
      left:r.left+r.width/2,top:r.top+r.height/2,
      radius:Math.max(1,Math.min(r.width,r.height)/2-inset),
      originX:'center',originY:'center'
    } : {left:r.left,top:r.top,width:r.width,height:r.height};
    const g=new (circular?fabric.Circle:fabric.Rect)({
      ...guideProps,
      fill:'rgba(0,0,0,0)',stroke:'#16a34a',strokeWidth:2,
      strokeDashArray:[10,7],selectable:false,evented:false,
      excludeFromExport:true,zvPrintAreaGuide:true,
      name:(a.name||('Print Area '+(i+1)))+' — guide only'
    });
    canvas.add(g);
    canvas.bringToFront(g);
  });
  canvas.requestRenderAll();
}
// Convert Admin engraving text (percentages of its saved print rectangle)
// into editable Fabric text objects on the product photograph.
let adminTextLoadedFor=null;
function syncAdminTexts(){
  if(!canvas || !referenceObject())return;
  const key=String(currentImageId()??'main');
  const stored=CFG.adminPrintTexts||{};
  const entries=Array.isArray(stored[key])?stored[key]:[];
  const area=areas()[0];
  if(!area)return;
  const r=rect(area);
  // Legacy designs may already contain copies of the same placeholder text.
  // Remove only duplicate placeholder objects that sit outside the saved
  // print region; never remove arbitrary customer text or artwork.
  const adminLabels=new Set(entries.map(e=>String(e?.text||'').trim()).filter(Boolean));
  if(adminLabels.size){
    canvas.getObjects().slice().forEach(o=>{
      if(o.zvAdminTextSource || o.zvProductMockup || o.zvPrintAreaGuide ||
         !['textbox','i-text','text'].includes(String(o.type||'').toLowerCase()))return;
      if(!adminLabels.has(String(o.text||'').trim()))return;
      const b=objectBox(o);
      if(!contains(r,b) && !o.zvAdminDuplicateCleaned){
        o.zvAdminDuplicateCleaned=true;
        canvas.remove(o);
      }
    });
  }
  const signature=key+'|'+r.left.toFixed(1)+'|'+r.top.toFixed(1)+'|'+r.width.toFixed(1)+'|'+r.height.toFixed(1);
  if(adminTextLoadedFor===signature)return;
  // Only initialize a given image once per editor session. Never overwrite
  // text that the customer has already edited.
  if(canvas.getObjects().some(o=>o.zvAdminTextSource===key)){
    adminTextLoadedFor=signature;return;
  }
  if(adminTextLoadedFor && adminTextLoadedFor.split('|')[0]===key)return;
  adminTextLoadedFor=signature;
  entries.forEach((item,index)=>{
    if(!item || !String(item.text||'').trim())return;
    const x=Math.max(0,Math.min(100,Number(item.x??50)));
    const y=Math.max(0,Math.min(100,Number(item.y??50)));
    const fontSize=Math.max(8,Math.min(80,Number(item.size)||20));
    const t=new fabric.Textbox(String(item.text),{
      left:r.left+r.width*x/100,
      top:r.top+r.height*y/100,
      originX:'center',originY:'center',
      width:Math.max(18,r.width*.9),
      fontSize:Math.max(7,fontSize*imageBounds().width/1000),
      fontFamily:'Arial',fontWeight:item.bold?'bold':'normal',
      fill:/^#[0-9a-f]{6}$/i.test(String(item.color))?item.color:'#ffffff',
      textAlign:'center',editable:true,
      zvAdminTextSource:key,zvAdminTextIndex:index,
      name:'Admin engraving text',customerEditable:true
    });
    // Fabric absolute clipPaths can render stray glyph fragments when
    // combined with narrow textboxes. Keep text wholly within its print
    // rectangle instead of clipping a textbox through a separate mask.
    t.setCoords();
    const bounds=t.getBoundingRect(true,true);
    if(bounds.width>r.width*.98 && bounds.width>0){
      const factor=(r.width*.98)/bounds.width;
      t.set({scaleX:factor,scaleY:factor});
      t.setCoords();
    }
    canvas.add(t);
    remember(t);
  });
  canvas.requestRenderAll();
}
function scheduleGuides(){
  clearTimeout(guideTimer);
  guideTimer=setTimeout(drawGuides,60);
}
function attach(){
  canvas=window.designCanvas;
  if(!canvas){setTimeout(attach,50);return;}
  canvas.on('object:added',e=>{
    const o=e.target;
    if(SHOULD_CONSTRAIN && editable(o)){setTimeout(()=>{if(matchingArea(o)){remember(o);if(!o.zvAdminTextSource)clipTo(matchingArea(o),o);}else enforce(o);},0);}
    scheduleGuides();
  });
  canvas.on('object:moving',e=>enforce(e.target));
  canvas.on('object:scaling',e=>enforce(e.target));
  canvas.on('object:rotating',e=>enforce(e.target));
  canvas.on('object:modified',e=>enforce(e.target));
  canvas.on('text:changed',e=>enforce(e.target));
  if(SHOULD_CONSTRAIN){
    canvas.getObjects().forEach(o=>{if(editable(o)){const r=matchingArea(o);if(r){remember(o);clipTo(r,o);}}});
  }
  drawGuides();
  // Reference photos load asynchronously; wait until the image is present.
  const adminTextPoll=setInterval(()=>{
    if(!canvas || !document.body.contains(canvas.upperCanvasEl)){clearInterval(adminTextPoll);return;}
    syncAdminTexts();
  },700);
  window.addEventListener('resize',scheduleGuides);
}
window.ZVPrintAreaGuard={drawGuides:()=>drawGuides()};
attach();
})();