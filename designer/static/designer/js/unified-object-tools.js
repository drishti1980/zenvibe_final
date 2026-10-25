/* ZenVibe shared object editing + 3D/360 preview.
 * Loaded by every customer customizer. The selected object decides which
 * controls are enabled; the product category does not.
 */
(function(){
'use strict';

const $ = id => document.getElementById(id);
const TEXT_TYPES = new Set(['i-text','textbox','text']);
let canvas = null;
let mounted = false;
let productId = null;

function getProductId(){
  const root = document.querySelector('[data-product-id]');
  return Number(window.PRODUCT?.id || root?.dataset?.productId || 0) || null;
}
function previewKind(){
  const root=document.querySelector('[data-preview-kind]');
  if(root?.dataset?.previewKind)return root.dataset.previewKind;
  const path=(location.pathname||'').toLowerCase();
  if(path.includes('/editor/'))return 'flat';
  if(path.includes('-customizer/'))return 'physical';
  return 'physical';
}

function isText(o){ return !!o && TEXT_TYPES.has(o.type); }
function isImage(o){ return !!o && o.type === 'image'; }
function active(){ return canvas?.getActiveObject?.() || null; }
function activeList(){
  const o=active();
  if(!o)return [];
  if(o.type==='activeSelection' && o.getObjects)return o.getObjects();
  return [o];
}
function editable(o){ return !!o && !o.excludeFromExport && !o.isBase && o.customerEditable !== false; }
function fireChanged(){
  canvas?.requestRenderAll?.();
  const o=active();
  if(o)canvas?.fire?.('object:modified',{target:o});
}
function toast(message){
  let el=$('zvUnifiedToast');
  if(!el){el=document.createElement('div');el.id='zvUnifiedToast';el.className='zv-unified-toast';document.body.appendChild(el);}
  el.textContent=message;el.classList.add('show');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),2200);
}

function findPanelHost(){
  const generic=$('toolsPanel');
  if(generic)return {panel:generic,existing:true};
  const side=document.querySelector('.studio-panel,.panel,.pe-panel');
  if(!side)return null;
  let panel=$('zvUnifiedObjectPanel');
  if(!panel){
    panel=document.createElement('section');
    panel.id='zvUnifiedObjectPanel';
    panel.className='studio-panel-section pane pe-pane zv-unified-panel';
    side.appendChild(panel);
  }
  return {panel,existing:false};
}

function ensureRailButton(hostInfo){
  if(hostInfo.existing)return;
  const rail=document.querySelector('.studio-rail,.rail,.pe-rail');
  if(!rail || $('zvUnifiedToolsTab'))return;
  const b=document.createElement('button');
  b.id='zvUnifiedToolsTab';b.type='button';b.className='rail-tab rail-btn';
  b.innerHTML='<span class="zv-rail-glyph">✦</span><b>Tools</b>';
  b.addEventListener('click',()=>{
    document.querySelectorAll('.studio-panel-section,.pane,.pe-pane').forEach(x=>x.classList.remove('active'));
    document.querySelectorAll('.studio-rail button,.rail button,.pe-rail button').forEach(x=>x.classList.remove('active'));
    hostInfo.panel.classList.add('active');b.classList.add('active');
    const title=$('panelTitle');if(title)title.textContent='Tools';
    document.querySelector('.studio-panel,.panel,.pe-panel')?.classList.remove('panel-closed');
  });
  const layers=[...rail.querySelectorAll('button')].find(x=>(x.textContent||'').toLowerCase().includes('layers'));
  rail.insertBefore(b,layers||null);
}

function panelMarkup(){
return `
<div id="zvSharedObjectEditor" class="zv-shared-editor">
  <div class="zv-shared-heading">
    <div><small>OBJECT EDITING</small><h3 id="zvObjectTitle">Select an object</h3></div>
    <span id="zvObjectKind" class="zv-kind-badge">None</span>
  </div>
  <p id="zvObjectHint" class="zv-object-hint">Select text, an image, shape, icon, QR code or barcode to edit it.</p>

  <div id="zvTextTools" class="zv-context-section" hidden>
    <h4>Text</h4>
    <div class="zv-field-grid two">
      <label>Font<select id="zvFontFamily"><option>Arial</option><option>Georgia</option><option>Montserrat</option><option>Roboto</option><option>Poppins</option><option>Times New Roman</option></select></label>
      <label>Size<input id="zvFontSize" type="number" min="6" max="300" value="32"></label>
    </div>
    <label class="zv-color-field">Text colour<input id="zvTextColor" type="color" value="#111827"></label>
    <div class="zv-tool-grid four compact">
      <button data-zv="bold" title="Bold"><b>B</b></button>
      <button data-zv="italic" title="Italic"><i>I</i></button>
      <button data-zv="underline" title="Underline"><u>U</u></button>
      <button data-zv="textAlign" title="Text alignment">≡</button>
    </div>
  </div>

  <div id="zvImageTools" class="zv-context-section" hidden>
    <h4>Image</h4>
    <div class="zv-tool-grid two">
      <button data-zv="crop"><span>✂</span><b>Crop</b></button>
      <button data-zv="erase"><span>⌫</span><b>Erase object</b></button>
      <button data-zv="removeBg"><span>◐</span><b>Remove background</b></button>
      <button data-zv="adjust"><span>☼</span><b>Adjust</b></button>
      <button data-zv="rotateLeft"><span>↶</span><b>Rotate left</b></button>
      <button data-zv="rotateRight"><span>↷</span><b>Rotate right</b></button>
      <button data-zv="resetImage"><span>↺</span><b>Reset image</b></button>
    </div>
  </div>

  <div id="zvShapeTools" class="zv-context-section" hidden>
    <h4>Colour</h4>
    <label class="zv-color-field">Fill colour<input id="zvObjectColor" type="color" value="#6c4cf1"></label>
  </div>

  <div id="zvCommonTools" class="zv-context-section" hidden>
    <h4>Transform</h4>
    <div class="zv-tool-grid two">
      <button data-zv="flipH"><span>↔</span><b>Flip horizontal</b></button>
      <button data-zv="flipV"><span>↕</span><b>Flip vertical</b></button>
      <button data-zv="duplicate"><span>▣</span><b>Duplicate</b></button>
      <button data-zv="delete" class="danger"><span>⌫</span><b>Delete</b></button>
      <button data-zv="forward"><span>↑</span><b>Forward</b></button>
      <button data-zv="backward"><span>↓</span><b>Backward</b></button>
    </div>
    <div class="zv-slider-row"><label>Opacity <output id="zvOpacityValue">100%</output></label><input id="zvOpacity" type="range" min="5" max="100" value="100"></div>
    <div class="zv-slider-row"><label>Rotation <output id="zvRotationValue">0°</output></label><input id="zvRotation" type="range" min="-180" max="180" value="0"></div>
    <h4>Position & size</h4>
    <div class="zv-field-grid four">
      <label>X<input id="zvX" type="number"></label><label>Y<input id="zvY" type="number"></label>
      <label>W<input id="zvW" type="number" min="1"></label><label>H<input id="zvH" type="number" min="1"></label>
    </div>
    <button id="zvApplyGeometry" class="zv-wide-primary" type="button">Apply position & size</button>
  </div>

  <div id="zvMultiTools" class="zv-context-section" hidden>
    <h4>Multiple objects</h4>
    <div class="zv-tool-grid three compact">
      <button data-zv="alignLeft">Left</button><button data-zv="alignCenter">Centre</button><button data-zv="alignRight">Right</button>
      <button data-zv="alignTop">Top</button><button data-zv="alignMiddle">Middle</button><button data-zv="alignBottom">Bottom</button>
    </div>
    <div class="zv-tool-grid two compact"><button data-zv="distributeH">Distribute H</button><button data-zv="distributeV">Distribute V</button></div>
    <button data-zv="group" class="zv-wide-primary">Group / ungroup</button>
  </div>
</div>`;
}

function mountPanel(){
  const info=findPanelHost();if(!info)return false;
  ensureRailButton(info);
  if(!$('zvSharedObjectEditor'))info.panel.insertAdjacentHTML('afterbegin',panelMarkup());
  bindPanel();return true;
}

function switchToToolsPanel(){
  const existing=$('toolsPanel');
  if(existing){
    const tab=[...document.querySelectorAll('.rail-tab')].find(x=>x.dataset.panel==='toolsPanel');
    if(tab)tab.click(); else {document.querySelectorAll('.studio-panel-section').forEach(x=>x.classList.remove('active'));existing.classList.add('active');}
  }else $('zvUnifiedToolsTab')?.click();
}

function imageAction(action){
  const o=active();if(!isImage(o)||!editable(o)){toast('Select an editable image first.');return;}
  if(!window.ZenImageTools){toast('Image tools are unavailable.');return;}
  if(typeof ZenImageTools.run==='function')ZenImageTools.run(canvas,action,o);
  else {ZenImageTools.open(canvas,o);setTimeout(()=>document.querySelector(`#zvImageToolsBar [data-act="${action}"]`)?.click(),0);}
}

function cloneActive(){
  const o=active();if(!o)return;
  o.clone(c=>{c.set({left:(o.left||0)+22,top:(o.top||0)+22,objectId:'o'+Math.random().toString(36).slice(2,10),isBase:false,customerEditable:true,selectable:true,evented:true});canvas.add(c);canvas.setActiveObject(c);fireChanged();});
}
function removeActive(){ activeList().filter(editable).forEach(o=>canvas.remove(o));canvas.discardActiveObject();fireChanged();sync(); }
function modify(fn){activeList().filter(editable).forEach(fn);fireChanged();sync();}
function groupToggle(){
  const o=active();if(!o)return;
  if(o.type==='activeSelection'&&o.toGroup)o.toGroup();else if(o.type==='group'&&o.toActiveSelection)o.toActiveSelection();
  fireChanged();sync();
}
function align(which){
  const list=activeList().filter(editable);if(list.length<2)return;
  const left=Math.min(...list.map(o=>o.getBoundingRect(true,true).left));
  const right=Math.max(...list.map(o=>{const r=o.getBoundingRect(true,true);return r.left+r.width}));
  const top=Math.min(...list.map(o=>o.getBoundingRect(true,true).top));
  const bottom=Math.max(...list.map(o=>{const r=o.getBoundingRect(true,true);return r.top+r.height}));
  list.forEach(o=>{const r=o.getBoundingRect(true,true);if(which==='left')o.left+=(left-r.left);if(which==='center')o.left+=((left+right)/2-(r.left+r.width/2));if(which==='right')o.left+=(right-(r.left+r.width));if(which==='top')o.top+=(top-r.top);if(which==='middle')o.top+=((top+bottom)/2-(r.top+r.height/2));if(which==='bottom')o.top+=(bottom-(r.top+r.height));o.setCoords();});fireChanged();sync();
}
function distribute(axis){
  const list=activeList().filter(editable);if(list.length<3)return;
  const sorted=[...list].sort((a,b)=>axis==='h'?a.getBoundingRect().left-b.getBoundingRect().left:a.getBoundingRect().top-b.getBoundingRect().top);
  const first=sorted[0].getBoundingRect(true,true),last=sorted[sorted.length-1].getBoundingRect(true,true);
  const start=axis==='h'?first.left:first.top,end=axis==='h'?last.left:last.top,step=(end-start)/(sorted.length-1);
  sorted.slice(1,-1).forEach((o,i)=>{const r=o.getBoundingRect(true,true),target=start+step*(i+1);if(axis==='h')o.left+=target-r.left;else o.top+=target-r.top;o.setCoords();});fireChanged();sync();
}

function bindPanel(){
  const root=$('zvSharedObjectEditor');if(!root||root.dataset.bound)return;root.dataset.bound='1';
  root.addEventListener('click',e=>{
    const b=e.target.closest('[data-zv]');if(!b)return;const a=b.dataset.zv,o=active();
    if(['crop','erase','removeBg','adjust','rotateLeft','rotateRight','resetImage'].includes(a)){imageAction(a==='resetImage'?'reset':a);return;}
    if(a==='duplicate')return cloneActive();if(a==='delete')return removeActive();if(a==='flipH')return modify(x=>x.set('flipX',!x.flipX));if(a==='flipV')return modify(x=>x.set('flipY',!x.flipY));
    if(a==='forward')return modify(x=>canvas.bringForward(x));if(a==='backward')return modify(x=>canvas.sendBackwards(x));if(a==='group')return groupToggle();
    if(a==='bold'&&isText(o))return modify(x=>x.set('fontWeight',x.fontWeight==='bold'?'normal':'bold'));
    if(a==='italic'&&isText(o))return modify(x=>x.set('fontStyle',x.fontStyle==='italic'?'normal':'italic'));
    if(a==='underline'&&isText(o))return modify(x=>x.set('underline',!x.underline));
    if(a==='textAlign'&&isText(o)){const seq=['left','center','right'];return modify(x=>x.set('textAlign',seq[(seq.indexOf(x.textAlign||'left')+1)%seq.length]));}
    if(a.startsWith('align'))return align(a.replace('align','').toLowerCase());
    if(a==='distributeH')return distribute('h');if(a==='distributeV')return distribute('v');
  });
  $('zvFontFamily')?.addEventListener('change',e=>modify(o=>isText(o)&&o.set('fontFamily',e.target.value)));
  $('zvFontSize')?.addEventListener('change',e=>modify(o=>isText(o)&&o.set('fontSize',Math.max(6,Number(e.target.value)||32))));
  $('zvTextColor')?.addEventListener('input',e=>modify(o=>isText(o)&&o.set('fill',e.target.value)));
  $('zvObjectColor')?.addEventListener('input',e=>modify(o=>{if(!isText(o)&&!isImage(o)&&typeof o.fill==='string')o.set('fill',e.target.value);}));
  $('zvOpacity')?.addEventListener('input',e=>{const v=Number(e.target.value)/100;$('zvOpacityValue').value=Math.round(v*100)+'%';modify(o=>o.set('opacity',v));});
  $('zvRotation')?.addEventListener('input',e=>{const v=Number(e.target.value)||0;$('zvRotationValue').value=v+'°';modify(o=>{o.rotate(v);o.setCoords();});});
  $('zvApplyGeometry')?.addEventListener('click',()=>{
    const o=active();if(!editable(o))return;const x=Number($('zvX').value),y=Number($('zvY').value),w=Number($('zvW').value),h=Number($('zvH').value);
    if(Number.isFinite(x))o.set('left',x);if(Number.isFinite(y))o.set('top',y);
    if(w>0)o.scaleToWidth(w);if(h>0)o.scaleToHeight(h);o.setCoords();fireChanged();sync();
  });
}

function sync(){
  if(!canvas)return;const o=active(),list=activeList();
  const title=$('zvObjectTitle'),kind=$('zvObjectKind'),hint=$('zvObjectHint');
  const textSec=$('zvTextTools'),imgSec=$('zvImageTools'),shapeSec=$('zvShapeTools'),common=$('zvCommonTools'),multi=$('zvMultiTools');
  [textSec,imgSec,shapeSec,common,multi].forEach(x=>{if(x)x.hidden=true;});
  if(!o){if(title)title.textContent='Select an object';if(kind)kind.textContent='None';if(hint)hint.hidden=false;return;}
  if(hint)hint.hidden=true;
  const multiSel=o.type==='activeSelection';
  if(title)title.textContent=o.name||o.text?.slice(0,28)|| (multiSel?`${list.length} objects`:'Selected object');
  if(kind)kind.textContent=multiSel?'Multiple':isText(o)?'Text':isImage(o)?'Image':(o.type||'Object');
  if(multiSel){if(multi)multi.hidden=false;if(common)common.hidden=false;return;}
  if(!editable(o)){if(title)title.textContent=(o.name||'Protected object');if(kind)kind.textContent='Protected';if(hint){hint.hidden=false;hint.textContent='This product/background layer is protected. Select a customer text, image, shape or icon to edit it.';}return;}
  if(common)common.hidden=false;
  if(isText(o)){if(textSec)textSec.hidden=false;$('zvFontFamily').value=o.fontFamily||'Arial';$('zvFontSize').value=Math.round(o.fontSize||32);if(typeof o.fill==='string'&&/^#[0-9a-f]{6}$/i.test(o.fill))$('zvTextColor').value=o.fill;}
  else if(isImage(o)){if(imgSec)imgSec.hidden=false;}
  else {if(shapeSec)shapeSec.hidden=false;if(typeof o.fill==='string'&&/^#[0-9a-f]{6}$/i.test(o.fill))$('zvObjectColor').value=o.fill;}
  $('zvOpacity').value=Math.round((o.opacity??1)*100);$('zvOpacityValue').value=Math.round((o.opacity??1)*100)+'%';$('zvRotation').value=Math.round(o.angle||0);$('zvRotationValue').value=Math.round(o.angle||0)+'°';
  const r=o.getBoundingRect(true,true);$('zvX').value=Math.round(o.left||0);$('zvY').value=Math.round(o.top||0);$('zvW').value=Math.round(r.width||0);$('zvH').value=Math.round(r.height||0);
}

function mount3D(){
  const existing=$('threeDViewBtn');
  if(existing){existing.addEventListener('click',open3D);return;}
  const top=document.querySelector('.studio-primary-actions');if(!top||$('zv3dBtn'))return;
  const b=document.createElement('button');b.id='zv3dBtn';b.type='button';b.className='studio-secondary zv-3d-button';b.textContent='3D view';
  const first=top.firstElementChild;top.insertBefore(b,first);
  b.addEventListener('click',open3D);
}
function build3DModal(){
  if($('zvUnified3dModal'))return;
  document.body.insertAdjacentHTML('beforeend',`<div id="zvUnified3dModal" class="zv-3d-modal" hidden><div class="zv-3d-backdrop"></div><section class="zv-3d-card"><header><div><small>LIVE PRODUCT PREVIEW</small><h2>3D / 360 view</h2></div><button id="zvUnified3dClose" aria-label="Close">×</button></header><div class="zv-3d-stage" id="zvUnified3dStage"><div class="zv-3d-object" id="zvUnified3dObject"><img id="zvUnified3dImage" alt="Live customised product preview"></div><div class="zv-3d-loading" id="zvUnified3dLoading">Rendering your current design…</div></div><div class="zv-3d-controls"><button id="zvUnified3dPrev" aria-label="Previous view">←</button><span id="zvUnified3dStatus">Preparing live preview</span><button id="zvUnified3dNext" aria-label="Next view">→</button></div><p class="zv-3d-note" id="zvUnified3dNote"></p></section></div>`);
  $('zvUnified3dClose').onclick=close3D;document.querySelector('#zvUnified3dModal .zv-3d-backdrop').onclick=close3D;
}
let frames=[],frameIndex=0,dragging=false,startX=0,startFrame=0;
function set3DFrame(i){
  if(!frames.length)return;
  frameIndex=((i%frames.length)+frames.length)%frames.length;
  const frame=frames[frameIndex];
  $('zvUnified3dImage').src=typeof frame==='string'?frame:frame.url;
  const label=typeof frame==='string'?'Live edited view':(frame.label||`View ${frameIndex+1}`);
  $('zvUnified3dStatus').textContent=frames.length>1?`${label} · ${frameIndex+1} of ${frames.length} · drag to rotate`:label;
}
function loadImg(url){
  return new Promise((resolve,reject)=>{const im=new Image();im.crossOrigin='anonymous';im.onload=()=>resolve(im);im.onerror=()=>reject(new Error('Could not load product view'));im.src=url;});
}
function logicalCanvasSize(){
  return {w:Number(window.PRODUCT?.width)||canvas.getWidth?.()||1050,h:Number(window.PRODUCT?.height)||canvas.getHeight?.()||600};
}
function productBackgroundRect(){
  const bg=canvas?.backgroundImage;if(!bg)return null;
  try{
    const w=(bg.width||0)*Math.abs(bg.scaleX||1),h=(bg.height||0)*Math.abs(bg.scaleY||1);
    return {left:(bg.left||0)-(bg.originX==='center'?w/2:0),top:(bg.top||0)-(bg.originY==='center'?h/2:0),width:w,height:h};
  }catch(_e){return null;}
}
function activeClipRect(){
  const objs=canvas?.getObjects?.()||[];
  for(const o of objs){
    if(o.excludeFromExport||o.bagGuide||o.customerEditable===false)continue;
    const c=o.clipPath;
    if(c && c.absolutePositioned){
      return {left:Number(c.left)||0,top:Number(c.top)||0,width:(Number(c.width)||0)*Math.abs(Number(c.scaleX)||1),height:(Number(c.height)||0)*Math.abs(Number(c.scaleY)||1)};
    }
  }
  return null;
}
async function captureEditableArtwork(){
  if(!canvas || !window.fabric)return null;
  const {w,h}=logicalCanvasSize();
  const customProps=['excludeFromExport','bagGuide','isBase','customerEditable','backgroundAsset','exactVisualMaster','awardLockedAsset','objectId','fieldType'];
  const json=canvas.toJSON(customProps);
  json.objects=(json.objects||[]).filter(o=>!o.excludeFromExport&&!o.bagGuide&&!o.isBase&&!o.backgroundAsset&&!o.exactVisualMaster&&!o.awardLockedAsset&&o.customerEditable!==false);
  delete json.backgroundImage;delete json.background;json.backgroundColor='rgba(0,0,0,0)';
  const el=document.createElement('canvas');const off=new fabric.StaticCanvas(el,{width:w,height:h,backgroundColor:'rgba(0,0,0,0)'});
  await new Promise(resolve=>off.loadFromJSON(json,()=>{off.setDimensions({width:w,height:h});off.setZoom(1);off.renderAll();resolve();}));
  let area=activeClipRect()||productBackgroundRect()||{left:0,top:0,width:w,height:h};
  area.left=Math.max(0,area.left);area.top=Math.max(0,area.top);area.width=Math.max(1,Math.min(w-area.left,area.width));area.height=Math.max(1,Math.min(h-area.top,area.height));
  const dataUrl=off.toDataURL({format:'png',left:area.left,top:area.top,width:area.width,height:area.height,multiplier:2});
  off.dispose();
  return {dataUrl,area};
}
function captureLiveCanvas(){
  try{return canvas.toDataURL({format:'png',multiplier:2});}catch(_e){return null;}
}
async function composeProductFrame(meta,artwork){
  const base=await loadImg(meta.url);const art=await loadImg(artwork.dataUrl);
  const out=document.createElement('canvas');out.width=base.naturalWidth||base.width;out.height=base.naturalHeight||base.height;
  const ctx=out.getContext('2d');ctx.drawImage(base,0,0,out.width,out.height);
  const area=(meta.print_areas||[])[0]||{left:30,top:55,width:40,height:20};
  const x=out.width*Number(area.left||0)/100,y=out.height*Number(area.top||0)/100,w=out.width*Number(area.width||40)/100,h=out.height*Number(area.height||20)/100;
  // Draw a subtle neutral underlay only inside the configured print area. It helps
  // current artwork visually replace any sample logo printed in old catalogue photos.
  ctx.save();ctx.globalAlpha=.10;ctx.fillStyle='#ffffff';ctx.fillRect(x,y,w,h);ctx.restore();
  ctx.drawImage(art,x,y,w,h);
  return out.toDataURL('image/jpeg',.92);
}
async async function open3D(){
  build3DModal();
  const m=$('zvUnified3dModal');
  m.hidden=false;
  document.body.classList.add('zv-modal-open');
  $('zvUnified3dLoading').hidden=false;
  frames=[];
  frameIndex=0;

  const kind=previewKind();
  const isPhysical=kind==='physical';
  const live=captureLiveCanvas();
  const obj=$('zvUnified3dObject');
  const stage=$('zvUnified3dStage');
  m.dataset.previewKind=kind;

  if(isPhysical){
    try{
      productId=productId||getProductId();
      const artwork=await captureEditableArtwork();
      if(productId){
        const r=await fetch(`/api/product/${productId}/viewer/`,{credentials:'same-origin'});
        if(r.ok){
          const d=await r.json();
          const metas=d.frames||[];
          if(artwork && metas.length){
            for(const meta of metas){
              try{
                frames.push({
                  url:await composeProductFrame(meta,artwork),
                  label:meta.label||'Customised product view'
                });
              }catch(e){
                console.warn('Could not render customised product angle',e);
              }
            }
          }
          // If there is no customer artwork yet, product photos are still a useful
          // product preview. Never replace them with a blank editor canvas.
          if(!frames.length){
            metas.forEach(meta=>frames.push({url:meta.url,label:meta.label||'Product view'}));
          }
        }
      }
    }catch(e){
      console.warn('ZenVibe live product preview unavailable',e);
    }

    // Final fallback only: category studios normally contain the product mockup
    // directly on the canvas, so this can still show a useful current product view.
    if(!frames.length && live)frames=[{url:live,label:'Current customised product'}];
  }else{
    // Business cards and invitations are paper products. Their current editable
    // page is rendered as a perspective card mock-up instead of pretending it is
    // a product photograph.
    if(live)frames=[{url:live,label:'Current edited card'}];
  }

  $('zvUnified3dLoading').hidden=true;
  const note=$('zvUnified3dNote');
  if(isPhysical && frames.length>1){
    note.textContent='Your current artwork is mapped into the configured print area on each available product view. Drag or use the arrows to rotate through the customised views.';
  }else if(isPhysical){
    note.textContent='This preview uses the current product and your latest artwork. Add more product-angle images in Admin to create a fuller 360° sequence.';
  }else{
    note.textContent='Live perspective preview of the exact invitation/business-card page you are editing. Front/back or extra pages remain editable from the Pages panel.';
  }

  set3DFrame(0);
  obj.style.transform=isPhysical?'rotateY(0deg) rotateX(0deg)':'rotateY(-12deg) rotateX(3deg)';

  stage.onpointerdown=e=>{
    dragging=true;startX=e.clientX;startFrame=frameIndex;stage.setPointerCapture?.(e.pointerId);
  };
  stage.onpointermove=e=>{
    if(!dragging)return;
    const dx=e.clientX-startX;
    if(frames.length>1){
      set3DFrame(startFrame-Math.round(dx/55));
    }else{
      const max=isPhysical?28:38;
      obj.style.transform=`rotateY(${Math.max(-max,Math.min(max,dx/4.5))}deg) rotateX(${isPhysical?-3:3}deg)`;
    }
  };
  stage.onpointerup=()=>{
    dragging=false;
    if(frames.length===1)obj.style.transform=isPhysical?'rotateY(0deg) rotateX(0deg)':'rotateY(-12deg) rotateX(3deg)';
  };
  $('zvUnified3dPrev').onclick=()=>set3DFrame(frameIndex-1);
  $('zvUnified3dNext').onclick=()=>set3DFrame(frameIndex+1);
}

function close3D(){$('zvUnified3dModal')?.setAttribute('hidden','');document.body.classList.remove('zv-modal-open');}

function normalizeExistingUI(){
  // Existing category-specific image button should open the same shared editing panel.
  const edit=$('editImageBtn');if(edit)edit.onclick=()=>{switchToToolsPanel();sync();};
  // Keep object editing in one place: hide the old floating image tools bar unless a
  // crop operation itself needs a temporary confirmation bar.
  const old=$('zvImageToolsBar');if(old)old.classList.add('zv-headless-image-tools');
}

function start(){
  if(mounted)return;canvas=window.designCanvas||window.__zenvibeCanvas||window.canvas;
  if(!canvas || !canvas.on){setTimeout(start,120);return;}
  mounted=true;productId=getProductId();mountPanel();mount3D();normalizeExistingUI();
  canvas.on('selection:created',sync);canvas.on('selection:updated',sync);canvas.on('selection:cleared',sync);canvas.on('object:modified',sync);canvas.on('object:added',()=>setTimeout(sync,0));
  sync();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(start,0));else setTimeout(start,0);
window.ZenVibeUnifiedTools={open:switchToToolsPanel,sync:()=>sync(),open3D};
})();
