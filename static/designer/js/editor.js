/* ZenVibe customer editor V52 - reliable printed-content replace/delete + direct editable overlay model */
(function(){
const P=window.PRODUCT,W=Number(window.INITIAL_TEMPLATE?.document?.width)||P.width||1050,H=Number(window.INITIAL_TEMPLATE?.document?.height)||P.height||600;let designId=window.EXISTING_DESIGN?.id||null;
const canvas=new fabric.Canvas('designCanvas',{preserveObjectStacking:true,selection:true,subTargetCheck:true});window.designCanvas=canvas;if(window.ZenImageTools)ZenImageTools.attach(canvas,{lockBackgroundAfterEdit:false,onChange:()=>{snapshot();renderAll();}});
let pages=[],activePage=0,history=[],historyIndex=-1,loading=false,gridVisible=false,guidesVisible=false,saveTimer=null;
let printedTextReplaceMode=false, printedTextStart=null, printedTextPreview=null;
const $=id=>document.getElementById(id),uid=()=>"o"+Math.random().toString(36).slice(2,10),clone=o=>JSON.parse(JSON.stringify(o));
function csrf(){return document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1]||''}
function newPage(){return{background:'#ffffff',objects:[]}}
function normalize(t){if(t?.pages?.length)return t.pages;if(t?.objects)return[{background:t.background||'#fff',objects:t.objects}];return[newPage()]}
function prepareInitialDocument(source){
  const raw=clone(source||{});
  const sourceW=Number(raw?.document?.width||P.baseWidth||W)||W;
  const sourceH=Number(raw?.document?.height||P.baseHeight||H)||H;
  const result=clone(normalize(raw));
  if(!sourceW||!sourceH||(Math.abs(sourceW-W)<.5&&Math.abs(sourceH-H)<.5))return result;
  const sx=W/sourceW,sy=H/sourceH;
  result.forEach(page=>{
    (page.objects||[]).forEach(o=>{
      if(!o)return;
      o.left=Number(o.left??o.x??0)*sx;
      o.top=Number(o.top??o.y??0)*sy;
      o.scaleX=Number(o.scaleX??1)*sx;
      o.scaleY=Number(o.scaleY??1)*sy;
      if(o.backgroundAsset||o.exactVisualMaster)o.fitToDesignSurface=true;
    });
  });
  return result;
}
pages=prepareInitialDocument(window.INITIAL_TEMPLATE||{});

/* V58 PAGE-SPECIFIC PRINT SURFACES
 * Django Admin Print Pages / Surfaces are mapped by sort order to editor pages.
 * W/H remain the internal Fabric coordinate system; physical inches are separate.
 */
const configuredSurfaces=Array.isArray(P.printSurfaces)
  ? [...P.printSurfaces].sort((a,b)=>Number(a.sortOrder||0)-Number(b.sortOrder||0))
  : [];
function ensureConfiguredSurfacePages(){while(pages.length<configuredSurfaces.length)pages.push(newPage())}
ensureConfiguredSurfacePages();
function getPageSurface(pageIndex){
  const surface=configuredSurfaces[pageIndex];
  if(surface){return{id:surface.id??null,label:surface.label||('Page '+(pageIndex+1)),printWidth:Number(surface.printWidth),printHeight:Number(surface.printHeight),sortOrder:Number(surface.sortOrder??pageIndex)}}
  return{id:null,label:'Page '+(pageIndex+1),printWidth:Number(P.printWidth),printHeight:Number(P.printHeight),sortOrder:pageIndex};
}
window.getZenVibeActiveSurface=()=>getPageSurface(activePage);
window.getZenVibePageSurface=pageIndex=>getPageSurface(pageIndex);
function notifyPageSurfaceChanged(){
  window.dispatchEvent(new CustomEvent('zenvibe:pagechange',{detail:{pageIndex:activePage,surface:getPageSurface(activePage)}}));
}
function setCanvasScale(percent){const wrap=$('canvasWrap'),scroll=document.querySelector('.studio-canvas-scroll');const maxW=Math.max(320,(scroll?.clientWidth||wrap?.parentElement?.clientWidth||950)-150),maxH=Math.max(280,(scroll?.clientHeight||window.innerHeight-190)-150);const fit=Math.min(maxW/W,maxH/H,1);const z=Math.max(.08,fit*(percent/100));canvas.setDimensions({width:Math.round(W*z),height:Math.round(H*z)});canvas.setZoom(z);if(wrap){wrap.style.width=Math.round(W*z)+'px';wrap.style.height=Math.round(H*z)+'px';}canvas.calcOffset();canvas.requestRenderAll();window.dispatchEvent(new CustomEvent('zenvibe:zoom',{detail:{percent:Number(percent),zoom:z,fit}}));}
function isText(o){return o&&['i-text','textbox','text'].includes(o.type)}
function common(o){const asset=!!o.backgroundAsset;const exact=!!o.exactVisualMaster;/* V30: exact published master is visual source only; editable hotspots/layers sit above it. */const editable=(exact||asset)?false:o.customerEditable!==false;const locked=(exact||asset)?true:(!!o.locked||!editable);return{left:o.left??o.x??60,top:o.top??o.y??60,angle:o.angle||0,opacity:(o.opacity??1),fill:o.fill||'#111827',objectId:o.id||uid(),name:o.name||'',fieldType:o.fieldType||'',backgroundAsset:asset,exactVisualMaster:!!o.exactVisualMaster,fitToDesignSurface:!!o.fitToDesignSurface,customerEditable:editable,flipX:!!o.flipX,flipY:!!o.flipY,visible:o.visible!==false,selectable:editable,evented:editable,lockMovementX:locked,lockMovementY:locked,lockScalingX:locked,lockScalingY:locked,lockRotation:locked,hasControls:editable,originX:o.originX||'left',originY:o.originY||'top',ocrOverlayPending:!!o.ocrOverlayPending,sourceText:o.sourceText||'',autoOcrText:!!o.autoOcrText,ocrCoverFor:o.ocrCoverFor||'',sourceNormalizedBox:o.sourceNormalizedBox||null,_zvPendingArtwork:!!o._zvPendingArtwork,visualFallback:!!o.visualFallback,replacementGroupId:o.replacementGroupId||'',manualReplacement:!!o.manualReplacement,manualTextPatch:!!o.manualTextPatch}}
function fromData(o){
  let x; const c=common(o);
  if(['text','i-text','textbox'].includes(o.type)){const TextClass=o.type==='textbox'?fabric.Textbox:fabric.IText;x=new TextClass(o.text||'Text',{...c,width:o.width||undefined,fontSize:o.fontSize||32,fontFamily:o.font||o.fontFamily||'Arial',fontWeight:o.fontWeight||(o.bold?'bold':'normal'),fontStyle:o.fontStyle||'normal',underline:!!o.underline,textAlign:o.textAlign||'left',charSpacing:o.charSpacing||0,lineHeight:o.lineHeight||1});x.sourceNormalizedBox=o.sourceNormalizedBox||null;x.sourceConfidence=o.sourceConfidence??null;x.ocrOverlayPending=!!o.ocrOverlayPending;x.sourceText=o.sourceText||o.text||'';x.visualFallback=!!o.visualFallback;}
  else if(o.type==='rect') x=new fabric.Rect({...c,width:o.width||o.w||200,height:o.height||o.h||120,rx:o.rx||0,ry:o.ry||0,stroke:o.stroke||null,strokeWidth:o.strokeWidth||0});
  else if(o.type==='circle') x=new fabric.Circle({...c,radius:o.radius||o.r||60,stroke:o.stroke||null,strokeWidth:o.strokeWidth||0});
  else if(o.type==='ellipse') x=new fabric.Ellipse({...c,rx:o.rx||90,ry:o.ry||55,stroke:o.stroke||null,strokeWidth:o.strokeWidth||0});
  else if(o.type==='triangle') x=new fabric.Triangle({...c,width:o.width||150,height:o.height||130,stroke:o.stroke||null,strokeWidth:o.strokeWidth||0});
  else if(o.type==='polygon'&&o.points) x=new fabric.Polygon(o.points,{...c,stroke:o.stroke||null,strokeWidth:o.strokeWidth||0});
  else if(o.type==='line') x=new fabric.Line(o.points||[0,0,220,0],{...c,stroke:o.stroke||o.fill||'#111827',strokeWidth:o.strokeWidth||5,fill:null,strokeDashArray:o.strokeDashArray||null});
  else if(o.type==='path'&&o.path) x=new fabric.Path(o.path,{...c,stroke:o.stroke||null,strokeWidth:o.strokeWidth||0});
  return x;
}
function toData(o){
  const base={id:o.objectId||uid(),type:o.type==='i-text'?'text':o.type,left:o.left,top:o.top,angle:o.angle||0,opacity:o.opacity??1,fill:o.fill,flipX:!!o.flipX,flipY:!!o.flipY,visible:o.visible!==false,locked:!!o.lockMovementX,name:o.name||'',fieldType:o.fieldType||'',backgroundAsset:!!o.backgroundAsset,exactVisualMaster:!!o.exactVisualMaster,fitToDesignSurface:!!o.fitToDesignSurface,customerEditable:((o.backgroundAsset||o.exactVisualMaster)?false:o.customerEditable!==false),scaleX:o.scaleX,scaleY:o.scaleY,stroke:o.stroke,strokeWidth:o.strokeWidth,strokeDashArray:o.strokeDashArray,originX:o.originX||'left',originY:o.originY||'top',autoInvitationField:!!o.autoInvitationField,autoInvitationCover:!!o.autoInvitationCover,sourceNormalizedBox:o.sourceNormalizedBox||null,sourceConfidence:o.sourceConfidence??null,ocrOverlayPending:!!o.ocrOverlayPending,sourceText:o.sourceText||'',autoOcrText:!!o.autoOcrText,ocrCoverFor:o.ocrCoverFor||'',_zvPendingArtwork:!!o._zvPendingArtwork,visualFallback:!!o.visualFallback,manualReplacement:!!o.manualReplacement,manualTextPatch:!!o.manualTextPatch,replacementGroupId:o.replacementGroupId||'',adminTextEdited:!!o.adminTextEdited};
  if(isText(o)) return {...base,text:o.text,width:o.width,fontSize:o.fontSize,font:o.fontFamily,fontWeight:o.fontWeight,fontStyle:o.fontStyle,underline:o.underline,textAlign:o.textAlign,charSpacing:o.charSpacing,lineHeight:o.lineHeight};
  if(o.type==='image') return {...base,src:o.getSrc(),baseSrc:o.baseSrc||o.getSrc(),width:o.width,height:o.height,originalWidth:o.width,originalHeight:o.height,cropX:o.cropX||0,cropY:o.cropY||0,filters:(o.filters||[]).map(f=>f.toObject?f.toObject():f)};
  if(o.type==='polygon') return {...base,points:o.points,width:o.width,height:o.height};
  if(o.type==='line') return {...base,points:[o.x1,o.y1,o.x2,o.y2]};
  if(o.type==='path') return {...base,path:o.path,width:o.width,height:o.height};
  return {...base,width:o.width,height:o.height,radius:o.radius,rx:o.rx,ry:o.ry};
}
function sync(){if(loading)return;pages[activePage]={background:canvas.backgroundColor||'#fff',objects:canvas.getObjects().filter(o=>!o.excludeFromExport).map(toData)}}
function loadPage(i){loading=true;activePage=i;canvas.clear();const p=pages[i]||newPage();canvas.backgroundColor=p.background||'#fff';
  // V48 defensive migration: older V39-V47 masters can contain duplicate OCR
  // detections from several recognition passes. Keep the strongest/first region only.
  const seenOcr=[];
  const overlap=(a,b)=>{if(!a||!b)return 0;const iw=Math.max(0,Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x)),ih=Math.max(0,Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y));return iw*ih/Math.max(1,Math.min(a.w*a.h,b.w*b.h));};
  const rawObjects=(p.objects||[]);
  const coverIds=new Set(rawObjects.filter(o=>o.fieldType==='ocr-inpaint'&&o.ocrCoverFor).map(o=>String(o.ocrCoverFor)));
  const sourceObjects=rawObjects.filter(o=>{const isOcr=['text','i-text','textbox'].includes(o.type)&&(o.autoOcrText||o.fieldType==='ocr-auto'||o.fieldType==='manual-ocr');if(!isOcr||!o.sourceNormalizedBox)return true;if(seenOcr.some(b=>overlap(b,o.sourceNormalizedBox)>.72))return false;seenOcr.push(o.sourceNormalizedBox);return true;}).map(o=>{
    // V54: OCR is only a hotspot until the original pixels underneath it have
    // actually been removed. This prevents the duplicate/overprinted text seen
    // in V53 and older saved masters.
    const isOcr=['text','i-text','textbox'].includes(o.type)&&(o.autoOcrText||o.fieldType==='ocr-auto'||o.fieldType==='manual-ocr');
    const id=String(o.id||o.objectId||'');
    if(isOcr&&o.sourceNormalizedBox&&!coverIds.has(id)){return {...o,opacity:0.001,ocrOverlayPending:true,customerEditable:true,selectable:true,evented:true};}
    return o;
  });
  let pending=0;sourceObjects.forEach(o=>{if(o.type==='image'&&o.src){pending++;fabric.Image.fromURL(o.src,img=>{
    // V55: never leave the page in a permanent loading/blank state if an old
    // MEDIA_URL changed. The Django view now embeds local master images, but this
    // defensive path also handles stale drafts or third-party image failures.
    if(!img || !img.width || !img.height){
      console.error('ZenVibe: template image failed to load',o.src);pending--;finish();return;
    }
    img.set({...common(o),scaleX:o.scaleX||((o.width||250)/img.width),scaleY:o.scaleY||((o.height||180)/img.height),cropX:o.cropX||0,cropY:o.cropY||0});if(o.fitToDesignSurface&&(img.width||0)>0&&(img.height||0)>0){const cover=Math.max(W/img.width,H/img.height);img.set({left:(W-img.width*cover)/2,top:(H-img.height*cover)/2,scaleX:cover,scaleY:cover,originX:'left',originY:'top'});}img.baseSrc=o.baseSrc||o.src;img.exactVisualMaster=!!o.exactVisualMaster;img.fitToDesignSurface=!!o.fitToDesignSurface;const addImage=()=>{canvas.add(img);if(img.backgroundAsset||img.exactVisualMaster)canvas.sendToBack(img);pending--;finish()};if(o.filters&&o.filters.length&&fabric.util.enlivenObjects){fabric.util.enlivenObjects(o.filters,filters=>{img.filters=filters;img.applyFilters();addImage()})}else addImage()},{crossOrigin:'anonymous'})}else{const obj=fromData(o);if(obj){obj.set({scaleX:o.scaleX||1,scaleY:o.scaleY||1});canvas.add(obj)}}});function finish(){if(pending===0){loading=false;renderAll();checkEditableObjects();notifyPageSurfaceChanged()}}if(!pending){loading=false;renderAll();checkEditableObjects();notifyPageSurfaceChanged()}}
function checkEditableObjects(){
  const hasEditable=canvas.getObjects().some(o=>o.customerEditable!==false);
  const hint=document.getElementById('noEditableHint');
  if(!hint)return;
  hint.style.display=hasEditable?'none':'flex';
}
function addQuickEditableText(){
  const t=new fabric.IText('Your Text Here',{left:W/2,top:H/2,originX:'center',originY:'center',
    fontSize:Math.round(H*0.06),fontFamily:'Arial',fill:'#111111',name:'My editable text',
    customerEditable:true,selectable:true,evented:true,hasControls:true});
  canvas.add(t);canvas.setActiveObject(t);canvas.requestRenderAll();snapshot();checkEditableObjects();
}
window.addQuickEditableText=addQuickEditableText;
function renderAll(){drawHelpers();canvas.requestRenderAll();renderPages();renderLayers();syncPanel()}
function snapshot(){sync();const state=clone(pages);history=history.slice(0,historyIndex+1);history.push(state);if(history.length>60)history.shift();historyIndex=history.length-1;scheduleLocalSave()}
function restore(n){if(n<0||n>=history.length)return;historyIndex=n;pages=clone(history[n]);loadPage(Math.min(activePage,pages.length-1))}
function renderPages() {
    const leftContainer = $('pageButtons');
    const bottomContainer = $('bottomPageButtons');

    // Admin surfaces define physical page specifications. Existing template
    // pages are preserved; missing pages are only added when Admin has more.
    ensureConfiguredSurfacePages();

    function getPageLabel(i) {
        return getPageSurface(i).label || ('Page ' + (i + 1));
    }

    function changePage(i) {
        if (i === activePage) return;
        sync();
        loadPage(i);
    }

    if (leftContainer) {
        leftContainer.innerHTML = '';
        pages.forEach((page, i) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'page-btn' + (i === activePage ? ' active' : '');
            button.textContent = getPageLabel(i);
            button.onclick = () => changePage(i);
            leftContainer.appendChild(button);
        });
    }

    if (bottomContainer) {
        bottomContainer.innerHTML = '';
        pages.forEach((page, i) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'bottom-page-btn' + (i === activePage ? ' active' : '');
            button.textContent = getPageLabel(i);
            button.onclick = () => changePage(i);
            bottomContainer.appendChild(button);
        });
    }

    const activeLabel = $('activePageLabel');
    if (activeLabel) activeLabel.textContent = getPageLabel(activePage);
}

function labelFor(o,i){return o.name||((isText(o)?(o.text||'Text').slice(0,22):o.type)+' '+(i+1))}
function renderLayers(){const h=$('layersPanel');h.innerHTML='';[...canvas.getObjects()].reverse().forEach((o,ri)=>{if(o.excludeFromExport)return;const i=canvas.getObjects().indexOf(o),row=document.createElement('div');row.className='layer-row'+(canvas.getActiveObject()===o?' active':'');row.innerHTML=`<button data-a="select">${labelFor(o,i)}</button><button data-a="visible">${o.visible===false?'◌':'◉'}</button><button data-a="lock">${o.lockMovementX?'🔒':'🔓'}</button><button data-a="up">↑</button><button data-a="down">↓</button>`;row.querySelectorAll('button').forEach(b=>b.onclick=()=>{const a=b.dataset.a;if(a==='select'){canvas.setActiveObject(o)}if(a==='visible'){o.visible=!o.visible}if(a==='lock')toggleLock(o);if(a==='up')canvas.bringForward(o);if(a==='down')canvas.sendBackwards(o);canvas.requestRenderAll();snapshot();renderLayers()});h.appendChild(row)})}
function drawHelpers(){canvas.getObjects().filter(o=>o.excludeFromExport).forEach(o=>canvas.remove(o));if(gridVisible){for(let x=50;x<W;x+=50)canvas.add(new fabric.Line([x,0,x,H],{stroke:'#cbd5e1',strokeWidth:1,selectable:false,evented:false,excludeFromExport:true,opacity:.45}));for(let y=50;y<H;y+=50)canvas.add(new fabric.Line([0,y,W,y],{stroke:'#cbd5e1',strokeWidth:1,selectable:false,evented:false,excludeFromExport:true,opacity:.45}))}if(guidesVisible){const safe=Math.max(18,W*(Number(P.safeMarginMm||5)/210)),bleed=Math.max(10,W*(Number(P.bleedMm||3)/210));canvas.add(new fabric.Rect({left:bleed,top:bleed,width:W-bleed*2,height:H-bleed*2,fill:'transparent',stroke:'#ef4444',strokeDashArray:[12,8],selectable:false,evented:false,excludeFromExport:true}));canvas.add(new fabric.Rect({left:safe,top:safe,width:W-safe*2,height:H-safe*2,fill:'transparent',stroke:'#22c55e',strokeDashArray:[12,8],selectable:false,evented:false,excludeFromExport:true}))}}
function add(o){o.objectId=uid();canvas.add(o);canvas.setActiveObject(o);snapshot();renderAll()}
function active(){return canvas.getActiveObject()}
function toggleLock(o=active()){if(!o)return;const v=!o.lockMovementX;o.set({lockMovementX:v,lockMovementY:v,lockScalingX:v,lockScalingY:v,lockRotation:v,hasControls:!v});canvas.requestRenderAll()}
function selectedObjects(){const a=active();return a?.type==='activeSelection'?a.getObjects():a?[a]:[]}
function modify(fn){selectedObjects().forEach(fn);canvas.requestRenderAll();snapshot();renderLayers()}
function duplicate(){const a=active();if(!a)return;a.clone(c=>{c.set({left:a.left+25,top:a.top+25,objectId:uid()});canvas.add(c);canvas.setActiveObject(c);snapshot();renderAll()})}
function group(){const a=active();if(!a)return;if(a.type==='activeSelection'){a.toGroup();snapshot()}else if(a.type==='group'){a.toActiveSelection();snapshot()}renderAll()}
function syncPanel(){const o=active();const imageBtn=$('editImageBtn');if(imageBtn)imageBtn.style.display=(o&&o.type==='image')?'inline-flex':'none';if(!o){if($('textValue'))$('textValue').value='';return;}if(isText(o)){$('textValue').value=o.text||'';$('fontSize').value=o.fontSize||32;$('fontFamily').value=o.fontFamily||'Arial'}if(typeof o.fill==='string'&&/^#[0-9a-f]{6}$/i.test(o.fill)){ $('fillColor').value=o.fill; if($('textPanelColor'))$('textPanelColor').value=o.fill; if($('textPanelHex'))$('textPanelHex').textContent=o.fill.toUpperCase(); }$('opacity').value=o.ocrOverlayPending?1:(o.opacity??1);$('rotation').value=o.angle||0}
function selectedEditableObject() {
    const o = canvas.getActiveObject();

    if (!o || o.excludeFromExport) {
        return null;
    }

    return o;
}

function selectedEditableImage() {
    const o = selectedEditableObject();

    return o && o.type === 'image'
        ? o
        : null;
}

function updateToolsPanelState() {
    const object = selectedEditableObject();
    const image = selectedEditableImage();

    [
        'toolDuplicate',
        'toolDelete',
        'toolFlipH',
        'toolFlipV',
        'toolBringFront',
        'toolSendBack'
    ].forEach(id => {
        const button = document.getElementById(id);

        if (button) {
            button.disabled = !object;
        }
    });

    [
        'toolEditImage',
        'toolRemoveBg'
    ].forEach(id => {
        const button = document.getElementById(id);

        if (button) {
            button.disabled = !image;
        }
    });
}

bind('toolEditImage', () => {
    const o = selectedEditableImage();

    if (!o) return;

    if (window.ZenImageTools) {
        ZenImageTools.open(canvas, o);
    }
});

bind('toolRemoveBg', () => {
    const o = selectedEditableImage();

    if (!o) return;

    if (window.ZenImageTools) {
        ZenImageTools.open(canvas, o);

        setTimeout(() => {
            document
                .querySelector(
                    '#zvImageToolsBar [data-act="removeBg"]'
                )
                ?.click();
        }, 50);
    }
});

bind('toolDuplicate', () => {
    if (selectedEditableObject()) {
        duplicate();
    }
});

bind('toolDelete', () => {
    document.getElementById('deleteBtn')?.click();
});

bind('toolFlipH', () => {
    const o = selectedEditableObject();

    if (!o) return;

    o.set('flipX', !o.flipX);
    o.setCoords();

    snapshot();
    renderAll();
});

bind('toolFlipV', () => {
    const o = selectedEditableObject();

    if (!o) return;

    o.set('flipY', !o.flipY);
    o.setCoords();

    snapshot();
    renderAll();
});

bind('toolBringFront', () => {
    const o = selectedEditableObject();

    if (!o) return;

    canvas.bringToFront(o);

    snapshot();
    renderAll();
});

bind('toolSendBack', () => {
    const o = selectedEditableObject();

    if (!o) return;

    canvas.sendToBack(o);

    snapshot();
    renderAll();
});

canvas.on('selection:created', updateToolsPanelState);
canvas.on('selection:updated', updateToolsPanelState);
canvas.on('selection:cleared', updateToolsPanelState);

updateToolsPanelState();

window.ZENVIBE_SAVE_CURRENT_DESIGN=()=>loading?Promise.reject(new Error('Wait for the current page to finish loading.')):save(false,false);
function localKey(){return 'zenvibe-autosave-'+P.id+'-'+(designId||('template-'+(window.SOURCE_TEMPLATE_ID||'blank')))}
function scheduleLocalSave(){clearTimeout(saveTimer);saveTimer=setTimeout(()=>{sync();localStorage.setItem(localKey(),JSON.stringify({document:{width:W,height:H,profile:P.scaleProfile||'product'},pages,name:($('designName')?.value||'My Zenvibe Design'),quantity:$('quantity').value,at:Date.now()}))},500)}
async function save(autosave=false,toCart=false){sync();const status=autosave?$('autosaveStatus'):$('saveStatus');status.textContent=autosave?'Autosaving…':'Saving…';let preview='';try{preview=canvas.toDataURL({format:'png',multiplier:1})}catch(e){}const r=await fetch('/zenvibe/api/save-design/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify({design_id:designId,source_template_id:window.SOURCE_TEMPLATE_ID,product_id:P.id,cart_key:window.ZENVIBE_EDIT_CART_KEY||'',name:($('designName')?.value||'My Zenvibe Design'),quantity:$('quantity').value,size_key:window.PRODUCT_OPTIONS?.selected_size||'',color_key:window.PRODUCT_OPTIONS?.selected_color||'',design_json:{version:3,document:{width:W,height:H,profile:P.scaleProfile||'product',label:P.scaleProfileLabel||'',physical:P.physicalFormat||''},pages},preview_png:preview,autosave,status:toCart?'cart':'draft'})});const d=await r.json();if(!d.ok)throw new Error(d.error);designId=d.design_id;window.EXISTING_DESIGN={...(window.EXISTING_DESIGN||{}),id:designId};if(d.cart_key)window.ZENVIBE_EDIT_CART_KEY=d.cart_key;status.textContent=autosave?'Autosaved '+new Date().toLocaleTimeString():'Saved successfully';localStorage.removeItem(localKey());if(toCart)location.href=d.cart_url}

function collectPrintIssues(){
  sync();
  const issues=[];
  const seen=new Set();

  const pushIssue=(page,key,title,message)=>{
    const unique=`${page}:${key}`;
    if(seen.has(unique))return;
    seen.add(unique);
    issues.push({page,type:'warning',title,message});
  };

  pages.forEach((p,pi)=>(p.objects||[]).forEach(o=>{
    if(!o || o.excludeFromExport || o.visible===false)return;

    const page=pi+1;
    const type=String(o.type||'').toLowerCase();
    const isTextObject=['text','i-text','textbox'].includes(type);
    const isImageObject=type==='image';

    // Small text matters for print.
    if(isTextObject && (o.fontSize||32)*Math.abs(o.scaleY||1)<14){
      pushIssue(
        page,
        `small-text-${o.id||o.objectId||o.text||''}`,
        'Small text',
        'Some text is very small and may be difficult to read when printed.'
      );
    }

    // Do not flag intentional transparent decorative rectangles/circles.
    // Only warn for actual customer-facing text or images.
    if((isTextObject || isImageObject) && (o.opacity??1)<.35){
      pushIssue(
        page,
        `low-opacity-${o.id||o.objectId||o.name||type}`,
        'Low opacity',
        'A text or image element is very transparent. Check that it is intentionally faint.'
      );
    }

    if(isImageObject){
      const displayed=(o.width||1)*Math.abs(o.scaleX||1);
      const original=(o.originalWidth||o.width||0);
      const dpi=(original/Math.max(displayed,1))*96;
      if(P.minDpi && original>0 && dpi<P.minDpi){
        pushIssue(
          page,
          `dpi-${o.id||o.objectId||o.name||''}`,
          'Image resolution',
          `An image may print softly at approximately ${Math.round(dpi)} DPI. Recommended minimum is ${P.minDpi} DPI.`
        );
      }
    }

    if((o.left||0)<0 || (o.top||0)<0){
      pushIssue(
        page,
        `outside-${o.id||o.objectId||o.name||type}`,
        'Outside page',
        'An element extends outside the design area.'
      );
    }
  }));

  return issues;
}

function printCheck(){
  const issues=collectPrintIssues();
  const box=$('printCheckResults');

  if(box){
    if(!issues.length){
      box.innerHTML=`
        <div class="print-check-pass">
          <strong>Ready for print</strong>
          <span>No obvious text-size, visibility, boundary or image-resolution problems were found.</span>
        </div>
      `;
    }else{
      box.innerHTML=issues.map(x=>`
        <div class="print-check-item warning">
          <div class="print-check-item-head">
            <strong>${x.title}</strong>
            <small>Page ${x.page}</small>
          </div>
          <span>${x.message}</span>
        </div>
      `).join('');
    }
  }

  openEditorModal('printCheckModal');
}

async function ai(action){sync();const out=$('aiResults');out.textContent='Working…';const r=await fetch('/zenvibe/api/ai-assist/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify({action,text:$('aiPrompt').value,design:{pages}})});const d=await r.json();out.innerHTML=(d.result||[d.error||'Unable to process']).map(x=>`<button class="ai-result-item">${x}</button>`).join('');if(action==='tagline')out.querySelectorAll('button').forEach(b=>b.onclick=()=>add(new fabric.IText(b.textContent,{left:80,top:80,fontSize:34,fill:'#111827'})))}
function hexToRgb(hex){hex=String(hex||'#ffffff').replace('#','');if(hex.length===3)hex=hex.split('').map(x=>x+x).join('');const n=parseInt(hex,16);return{r:(n>>16)&255,g:(n>>8)&255,b:n&255}}
function recolourPaperPixels(img,colour){
  return new Promise((resolve,reject)=>{
    const source=img.baseSrc||img.getSrc();
    const sourceImg=new Image(); sourceImg.crossOrigin='anonymous';
    sourceImg.onload=()=>{
      try{
        const off=document.createElement('canvas');off.width=sourceImg.naturalWidth||sourceImg.width;off.height=sourceImg.naturalHeight||sourceImg.height;
        const ctx=off.getContext('2d',{willReadFrequently:true});ctx.drawImage(sourceImg,0,0,off.width,off.height);
        const frame=ctx.getImageData(0,0,off.width,off.height),d=frame.data,target=hexToRgb(colour);
        for(let i=0;i<d.length;i+=4){
          if(d[i+3]<15)continue;
          const r=d[i],g=d[i+1],b=d[i+2],mx=Math.max(r,g,b),mn=Math.min(r,g,b),chroma=mx-mn,brightness=(r+g+b)/3;
          // Target only light, low-saturation paper/cream pixels. Dark text and colourful artwork are preserved.
          if(brightness>175 && chroma<55){
            const lightFactor=Math.max(0,Math.min(1,(brightness-175)/80));
            const neutralFactor=Math.max(0,Math.min(1,1-chroma/55));
            const strength=Math.max(.28,lightFactor*neutralFactor);
            d[i]=Math.round(r*(1-strength)+target.r*strength);
            d[i+1]=Math.round(g*(1-strength)+target.g*strength);
            d[i+2]=Math.round(b*(1-strength)+target.b*strength);
          }
        }
        ctx.putImageData(frame,0,0);resolve(off.toDataURL('image/png'));
      }catch(err){reject(err)}
    };
    sourceImg.onerror=()=>reject(new Error('Background image could not be recoloured.'));
    sourceImg.src=source;
  });
}

function hexRgbArt(hex){hex=(hex||'#000000').replace('#','');return{r:parseInt(hex.slice(0,2),16)||0,g:parseInt(hex.slice(2,4),16)||0,b:parseInt(hex.slice(4,6),16)||0}}
function rgbHsvArt(r,g,b){r/=255;g/=255;b/=255;const mx=Math.max(r,g,b),mn=Math.min(r,g,b),d=mx-mn;let h=0;if(d){if(mx===r)h=((g-b)/d)%6;else if(mx===g)h=(b-r)/d+2;else h=(r-g)/d+4;h*=60;if(h<0)h+=360}return{h,s:mx?d/mx:0,v:mx}}
function hsvRgbArt(h,s,v){h=((h%360)+360)%360;const c=v*s,x=c*(1-Math.abs((h/60)%2-1)),m=v-c;let r=0,g=0,b=0;if(h<60){r=c;g=x}else if(h<120){r=x;g=c}else if(h<180){g=c;b=x}else if(h<240){g=x;b=c}else if(h<300){r=x;b=c}else{r=c;b=x}return{r:Math.round((r+m)*255),g:Math.round((g+m)*255),b:Math.round((b+m)*255)}}
function adjustColourfulArtwork(img,opts){return new Promise((resolve,reject)=>{const source=img.getSrc()||img.baseSrc;if(!source)return reject(new Error('No image selected'));const im=new Image();im.crossOrigin='anonymous';im.onload=()=>{try{const off=document.createElement('canvas');off.width=im.naturalWidth||im.width;off.height=im.naturalHeight||im.height;const ctx=off.getContext('2d',{willReadFrequently:true});ctx.drawImage(im,0,0,off.width,off.height);const frame=ctx.getImageData(0,0,off.width,off.height),d=frame.data,t=hexRgbArt(opts.tint),ts=Math.max(0,Math.min(1,Number(opts.tintStrength||0)/100)),sm=Number(opts.saturation||100)/100,bm=Number(opts.brightness||100)/100,ct=Number(opts.contrast||100)/100,hs=Number(opts.hue||0);for(let i=0;i<d.length;i+=4){if(d[i+3]<10)continue;let r=d[i],g=d[i+1],b=d[i+2],hsv=rgbHsvArt(r,g,b),ch=Math.max(r,g,b)-Math.min(r,g,b);if(hsv.s<.14||ch<24||hsv.v<.16)continue;hsv.h+=hs;hsv.s=Math.max(0,Math.min(1,hsv.s*sm));hsv.v=Math.max(0,Math.min(1,hsv.v*bm));let o=hsvRgbArt(hsv.h,hsv.s,hsv.v);o.r=(o.r-128)*ct+128;o.g=(o.g-128)*ct+128;o.b=(o.b-128)*ct+128;if(ts){o.r=o.r*(1-ts)+t.r*ts;o.g=o.g*(1-ts)+t.g*ts;o.b=o.b*(1-ts)+t.b*ts}d[i]=Math.max(0,Math.min(255,Math.round(o.r)));d[i+1]=Math.max(0,Math.min(255,Math.round(o.g)));d[i+2]=Math.max(0,Math.min(255,Math.round(o.b)))}ctx.putImageData(frame,0,0);resolve(off.toDataURL('image/png'))}catch(e){reject(e)}};im.onerror=()=>reject(new Error('Artwork image could not be adjusted'));im.src=source})}

function removeDecorativeArtworkPixels(img,strength=72){return new Promise((resolve,reject)=>{const source=img.getSrc()||img.baseSrc;if(!source)return reject(new Error('No artwork found'));const im=new Image();im.crossOrigin='anonymous';im.onload=()=>{try{const off=document.createElement('canvas');off.width=im.naturalWidth||im.width;off.height=im.naturalHeight||im.height;const ctx=off.getContext('2d',{willReadFrequently:true});ctx.drawImage(im,0,0,off.width,off.height);const frame=ctx.getImageData(0,0,off.width,off.height),d=frame.data;const amount=Math.max(.35,Math.min(.95,Number(strength||72)/100));for(let y=0;y<off.height;y++){for(let x=0;x<off.width;x++){const i=(y*off.width+x)*4;if(d[i+3]<10)continue;const r=d[i],g=d[i+1],b=d[i+2],mx=Math.max(r,g,b),mn=Math.min(r,g,b),ch=mx-mn,bright=(r+g+b)/3;const hsv=rgbHsvArt(r,g,b);const edge=Math.min(x,y,off.width-1-x,off.height-1-y)/Math.max(1,Math.min(off.width,off.height));const colourful=(hsv.s>(.18-(amount-.35)*.08)&&ch>(24-(amount-.35)*10)&&bright>45);const likelyDecor=colourful&&(edge<.24||hsv.s>.36||ch>58);if(likelyDecor){const fade=Math.min(1,.52+amount*.58);d[i+3]=Math.max(0,Math.round(d[i+3]*(1-fade)))}}}ctx.putImageData(frame,0,0);resolve(off.toDataURL('image/png'))}catch(e){reject(e)}};im.onerror=()=>reject(new Error('Artwork could not be processed'));im.src=source})}
function getMasterArtwork(){return canvas.getObjects().find(o=>o.type==='image'&&o.backgroundAsset)||null}
async function applyDocumentBackgroundColour(colour){
  canvas.backgroundColor=colour;
  const artwork=canvas.getObjects().filter(o=>o.type==='image'&&o.backgroundAsset);
  if(!artwork.length){snapshot();canvas.requestRenderAll();return}
  const status=$('saveStatus');
  try{
    for(const img of artwork){
      if(!img.baseSrc)img.baseSrc=img.getSrc();
      const dataUrl=await recolourPaperPixels(img,colour);
      await new Promise(resolve=>img.setSrc(dataUrl,()=>{img.setCoords();resolve()}));
    }
    snapshot();canvas.requestRenderAll();if(status)status.textContent='Background colour applied';
  }catch(err){snapshot();canvas.requestRenderAll();if(status)status.textContent='Page colour changed; artwork recolour was unavailable';}
}
function sampleBackgroundForOcr(o){
  try{
    const bg=canvas.getObjects().find(x=>x.type==='image'&&x.backgroundAsset);
    const box=o?.sourceNormalizedBox;if(!bg||!box)return '#ffffff';
    const el=bg.getElement(),nw=el.naturalWidth||bg.width||1,nh=el.naturalHeight||bg.height||1;
    const off=document.createElement('canvas');off.width=nw;off.height=nh;
    const ctx=off.getContext('2d',{willReadFrequently:true});ctx.drawImage(el,0,0,nw,nh);
    const x0=Math.max(0,Math.floor(box.x*nw)),y0=Math.max(0,Math.floor(box.y*nh));
    const x1=Math.min(nw-1,Math.ceil((box.x+box.w)*nw)),y1=Math.min(nh-1,Math.ceil((box.y+box.h)*nh));
    const pad=Math.max(3,Math.min(18,Math.round((y1-y0)*.6))),vals=[];
    const get=(x,y)=>{const d=ctx.getImageData(x,y,1,1).data;if(d[3]>150)vals.push([d[0],d[1],d[2]])};
    for(let x=Math.max(0,x0-pad);x<=Math.min(nw-1,x1+pad);x+=2){for(let y=Math.max(0,y0-pad);y<y0;y+=2)get(x,y);for(let y=y1+1;y<=Math.min(nh-1,y1+pad);y+=2)get(x,y)}
    for(let y=y0;y<=y1;y+=2){for(let x=Math.max(0,x0-pad);x<x0;x+=2)get(x,y);for(let x=x1+1;x<=Math.min(nw-1,x1+pad);x+=2)get(x,y)}
    if(!vals.length)return '#ffffff';
    const med=k=>{const a=vals.map(v=>v[k]).sort((a,b)=>a-b);return a[Math.floor(a.length/2)]};
    return '#'+[med(0),med(1),med(2)].map(v=>v.toString(16).padStart(2,'0')).join('');
  }catch(e){return '#ffffff'}
}
function sourceBoxCanvasRect(o){
  const bg=getMasterArtwork(),box=o?.sourceNormalizedBox;if(!bg||!box)return null;
  const el=bg.getElement(),nw=el.naturalWidth||bg.width||1,nh=el.naturalHeight||bg.height||1,sx=bg.scaleX||1,sy=bg.scaleY||1;
  return {left:(bg.left||0)+box.x*nw*sx,top:(bg.top||0)+box.y*nh*sy,width:Math.max(4,box.w*nw*sx),height:Math.max(4,box.h*nh*sy)};
}
function fitOcrTextToSourceBox(o){
  if(!o||!isText(o)||!o.sourceNormalizedBox)return;
  const r=sourceBoxCanvasRect(o);if(!r)return;
  o.set({scaleX:1,scaleY:1});o.initDimensions?.();
  let fs=Math.min(Number(o.fontSize||32),Math.max(7,r.height*.82));o.set('fontSize',fs);o.initDimensions?.();
  for(let i=0;i<40&&((o.width||1)>r.width*.94||(o.height||1)>r.height*1.05);i++){fs=Math.max(6,fs*.95);o.set('fontSize',fs);o.initDimensions?.()}
  o.set({left:r.left+(r.width-(o.width||0))/2,top:r.top+(r.height-(o.height||0))/2});o.setCoords();
}
async function activatePendingArtwork(o){
  if(!o||!o._zvPendingArtwork||o._zvActivatingArtwork)return o;
  const bg=getMasterArtwork();if(!bg||!o.sourceNormalizedBox){o.set({_zvPendingArtwork:false,opacity:1});return o;}
  o._zvActivatingArtwork=true;
  try{
    const patch=await ZenRasterEdit.addArtworkInpaintPatch(canvas,bg,o,{objectId:uid(),artPatchFor:o.objectId||o.id});
    const idx=canvas.getObjects().indexOf(o);canvas.moveTo(patch,Math.max(1,idx));canvas.bringToFront(o);o.set({_zvPendingArtwork:false,opacity:1});o.setCoords();snapshot();renderAll();
  }catch(err){console.warn('Artwork separation activation failed',err);o.set({_zvPendingArtwork:false,opacity:1});renderAll();}
  finally{o._zvActivatingArtwork=false;}
  return o;
}
async function activatePendingOcrText(o){
  if(!o||!o.ocrOverlayPending||o._zvActivatingOcr)return;
  const bg=getMasterArtwork(),box=o.sourceNormalizedBox;if(!bg||!box){o.set({ocrOverlayPending:false,opacity:1});return;}
  o._zvActivatingOcr=true;
  try{
    let patch=null;
    try{patch=await ZenRasterEdit.addPatchToCanvas(canvas,bg,box,{objectId:uid(),ocrCoverFor:o.objectId||o.id,fieldType:'ocr-inpaint'});}catch(e){console.warn('smart cleanup failed; using safe cover',e)}
    const r=ZenRasterEdit.canvasRectForNormalized(bg,box);
    if(!patch){
      // Guaranteed fallback: sample the local paper colour and cover the complete
      // printed-text box. This is intentionally conservative: no old glyph can
      // remain underneath the replacement text.
      let fill='#ffffff';
      try{
        const el=bg.getElement(),nw=el.naturalWidth||bg.width,nh=el.naturalHeight||bg.height,off=document.createElement('canvas');off.width=1;off.height=1;
        const ctx=off.getContext('2d');const sx=Math.max(0,Math.min(nw-1,Math.round((box.x+box.w/2)*nw))),sy=Math.max(0,Math.min(nh-1,Math.round((box.y-Math.min(.006,box.h*.2))*nh)));
        ctx.drawImage(el,sx,sy,1,1,0,0,1,1);const d=ctx.getImageData(0,0,1,1).data;fill=`rgb(${d[0]},${d[1]},${d[2]})`;
      }catch(e){}
      patch=new fabric.Rect({left:r.left-2,top:r.top-2,width:r.width+4,height:r.height+4,fill,stroke:null,selectable:false,evented:false,customerEditable:false,fieldType:'ocr-inpaint',name:'Printed text cleanup'});
      canvas.add(patch);
    }
    // Protected artwork must be at the bottom, cleanup immediately above it,
    // editable replacement above the cleanup. Never place the patch under bitmap.
    const bgIndex=canvas.getObjects().indexOf(bg);canvas.moveTo(patch,Math.max(1,bgIndex+1));
    o.set({ocrOverlayPending:false,opacity:1,scaleX:1,scaleY:1,left:r.left,top:r.top,manualReplacement:true,fieldType:'manual-replace',autoOcrText:false,customerEditable:true,selectable:true,evented:true,hasControls:true,lockMovementX:false,lockMovementY:false,lockScalingX:false,lockScalingY:false,lockRotation:false});
    fitOcrTextToSourceBox(o);canvas.bringToFront(o);o.setCoords();snapshot();renderAll();
  }catch(err){console.warn('Text cleanup failed',err);o.set({ocrOverlayPending:false,opacity:1});renderAll();}
  finally{o._zvActivatingOcr=false;}
}
function bind(id,fn){const e=$(id);if(e)e.onclick=fn}

const TEXT_COLOURS=['#111827','#000000','#ffffff','#4b5563','#7c3aed','#8b5cf6','#2563eb','#0ea5e9','#059669','#16a34a','#eab308','#f97316','#dc2626','#ec4899','#a855f7','#d4af37'];
const textSwatches=$('textColourSwatches');if(textSwatches)TEXT_COLOURS.forEach(c=>{const b=document.createElement('button');b.style.background=c;b.title=c;b.onclick=()=>{const o=active();if(!o||!isText(o))return;const pending=!!o.ocrOverlayPending;if(pending)activatePendingOcrText(o);o.set({fill:c,opacity:1});$('fillColor').value=c;if($('textPanelColor'))$('textPanelColor').value=c;if($('textPanelHex'))$('textPanelHex').textContent=c.toUpperCase();snapshot();renderAll()};textSwatches.appendChild(b)});
$('textPanelColor')?.addEventListener('input',e=>{const c=e.target.value,o=active();if($('textPanelHex'))$('textPanelHex').textContent=c.toUpperCase();$('fillColor').value=c;if(o&&isText(o)){if(o.ocrOverlayPending)activatePendingOcrText(o);o.set({fill:c,opacity:1});snapshot();renderAll()}});
$('fillColor')?.addEventListener('input',e=>{if($('textPanelColor'))$('textPanelColor').value=e.target.value;if($('textPanelHex'))$('textPanelHex').textContent=e.target.value.toUpperCase()});
$('textPanelHexInput')?.addEventListener('change',e=>{let c=e.target.value.trim();if(!c.startsWith('#'))c='#'+c;if(!/^#[0-9a-f]{6}$/i.test(c))return;e.target.value=c.toUpperCase();$('textPanelColor').value=c;$('fillColor').value=c;if($('textPanelHex'))$('textPanelHex').textContent=c.toUpperCase();const o=active();if(o&&isText(o)){if(o.ocrOverlayPending)activatePendingOcrText(o);o.set({fill:c,opacity:1});snapshot();renderAll();}});
['artHue','artSaturation','artBrightness','artContrast','artTintStrength'].forEach(id=>{const el=$(id),val=$(id+'Val');if(el&&val)el.addEventListener('input',()=>{val.textContent=id==='artHue'?el.value+'°':el.value+'%'})});
bind('applyArtworkColourBtn',async()=>{const o=(active()?.type==='image'?active():getMasterArtwork());if(!o){alert('No template artwork found.');return}if(o._zvPendingArtwork)await activatePendingArtwork(o);const btn=$('applyArtworkColourBtn');btn.disabled=true;btn.textContent='Applying…';try{const data=await adjustColourfulArtwork(o,{hue:$('artHue').value,saturation:$('artSaturation').value,brightness:$('artBrightness').value,contrast:$('artContrast').value,tint:$('artTint').value,tintStrength:$('artTintStrength').value});await new Promise(res=>o.setSrc(data,()=>{o.setCoords();res()}));snapshot();renderAll();$('saveStatus').textContent='Artwork colour updated';}catch(e){$('saveStatus').textContent=e.message||'Artwork colour adjustment failed'}finally{btn.disabled=false;btn.textContent='Apply artwork colour'}});
bind('resetArtworkColourBtn',()=>{const o=(active()?.type==='image'?active():getMasterArtwork());if(!o||!o.baseSrc)return;['artHue','artTintStrength'].forEach(id=>$(id).value=0);['artSaturation','artBrightness','artContrast'].forEach(id=>$(id).value=100);$('artHueVal').textContent='0°';$('artTintStrengthVal').textContent='0%';$('artSaturationVal').textContent=$('artBrightnessVal').textContent=$('artContrastVal').textContent='100%';o.setSrc(o.baseSrc,()=>{o.setCoords();snapshot();renderAll()})});
$('decorRemovalStrength')?.addEventListener('input',e=>{if($('decorRemovalVal'))$('decorRemovalVal').textContent=e.target.value+'%'});
bind('removeDecorBtn',async()=>{const o=getMasterArtwork();if(!o){alert('No template artwork found.');return}if(!o.baseSrc)o.baseSrc=o.getSrc();const btn=$('removeDecorBtn');btn.disabled=true;btn.textContent='Removing…';try{const data=await removeDecorativeArtworkPixels(o,$('decorRemovalStrength')?.value||72);await new Promise(res=>o.setSrc(data,()=>{o.setCoords();res()}));snapshot();renderAll();const st=$('saveStatus');if(st)st.textContent='Floral/decorative artwork removed. Use Restore artwork to undo.';}catch(e){alert(e.message||'Could not remove decorative artwork.')}finally{btn.disabled=false;btn.textContent='Remove floral / design'}});
bind('restoreDecorBtn',()=>{const o=getMasterArtwork();if(!o||!o.baseSrc){alert('No original artwork available to restore.');return}o.setSrc(o.baseSrc,()=>{o.setCoords();snapshot();renderAll();const st=$('saveStatus');if(st)st.textContent='Original artwork restored';})});
bind('addTextBtn',()=>add(new fabric.IText('Your text',{left:80,top:80,fontSize:36,fill:'#111827'})));bind('addRectBtn',()=>add(new fabric.Rect({left:100,top:100,width:220,height:120,fill:'#7c3aed'})));bind('addCircleBtn',()=>add(new fabric.Circle({left:100,top:100,radius:70,fill:'#ec4899'})));bind('addTriangleBtn',()=>add(new fabric.Triangle({left:100,top:100,width:160,height:140,fill:'#d4af37'})));
$('imageUpload').onchange=e=>[...e.target.files].forEach(file=>{if(file.size>15*1024*1024)return alert(file.name+' exceeds 15 MB');const rd=new FileReader();rd.onload=ev=>fabric.Image.fromURL(ev.target.result,img=>{img.scaleToWidth(Math.min(400,W*.5));img.set({left:80,top:80,name:file.name});add(img)});rd.readAsDataURL(file)});
$('bgPhotoUpload')?.addEventListener('change',e=>{
  const file=e.target.files[0];if(!file)return;
  if(file.size>15*1024*1024){alert(file.name+' exceeds 15 MB');return}
  const rd=new FileReader();
  rd.onload=ev=>fabric.Image.fromURL(ev.target.result,img=>{
    const scale=Math.min(W/img.width,H/img.height);
    img.set({left:W/2,top:H/2,originX:'center',originY:'center',scaleX:scale,scaleY:scale,
      selectable:true,evented:true,lockMovementX:false,lockMovementY:false,lockScalingX:false,
      lockScalingY:false,lockRotation:false,hasControls:true,name:'My background photo',baseSrc:ev.target.result,
      backgroundAsset:true,customerEditable:true});
    canvas.add(img);canvas.sendToBack(img);canvas.requestRenderAll();snapshot();
  });
  rd.readAsDataURL(file);
  e.target.value='';
});
$('addEditableTextBtn')?.addEventListener('click',()=>{
  const textObj=new fabric.IText('Your Text Here',{left:W/2,top:H/2,originX:'center',originY:'center',
    fontSize:Math.round(H*0.08),fontFamily:'Arial',fill:'#111111',name:'My editable text',
    customerEditable:true,selectable:true,evented:true,hasControls:true});
  canvas.add(textObj);canvas.setActiveObject(textObj);canvas.requestRenderAll();snapshot();
});

function setReplacePrintedTextMode(on){
  printedTextReplaceMode=!!on; printedTextStart=null;
  if(printedTextPreview){canvas.remove(printedTextPreview);printedTextPreview=null;}
  canvas.discardActiveObject();
  canvas.selection=!on; canvas.defaultCursor=on?'crosshair':'default';
  canvas.getObjects().forEach(o=>{
    if(on){o._zvReplaceSelectable=o.selectable;o._zvReplaceEvented=o.evented;o.selectable=false;o.evented=false;}
    else{if('_zvReplaceSelectable' in o){o.selectable=o._zvReplaceSelectable;delete o._zvReplaceSelectable;}if('_zvReplaceEvented' in o){o.evented=o._zvReplaceEvented;delete o._zvReplaceEvented;}}
  });
  const cancel=$('cancelReplacePrintedTextBtn'),status=$('replacePrintedTextStatus');
  if(cancel)cancel.style.display=on?'block':'none';
  if(status)status.textContent=on?'Drag a tight rectangle over only the printed wording you want to replace.':'';
  canvas.requestRenderAll();
}

function normalizedBoxFromCanvasRect(bg,left,top,width,height){
  const el=bg.getElement(),nw=el.naturalWidth||bg.width||W,nh=el.naturalHeight||bg.height||H,sx=bg.scaleX||1,sy=bg.scaleY||1;
  return {x:Math.max(0,(left-(bg.left||0))/(nw*sx)),y:Math.max(0,(top-(bg.top||0))/(nh*sy)),w:Math.min(1,width/(nw*sx)),h:Math.min(1,height/(nh*sy))};
}
function boxesOverlap(a,b){return a&&b&&a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+a.h > b.y;}

async function finishReplacePrintedText(rect){
  const left=rect.left,top=rect.top,width=Math.max(2,rect.width*rect.scaleX),height=Math.max(2,rect.height*rect.scaleY);
  canvas.remove(rect); printedTextPreview=null;
  const bg=getMasterArtwork();
  if(!bg){alert('No template/background image found.');setReplacePrintedTextMode(false);return;}
  const box=normalizedBoxFromCanvasRect(bg,left,top,width,height);
  if(box.x>=1||box.y>=1||box.w<=0||box.h<=0){alert('Please draw inside the template image.');setReplacePrintedTextMode(false);return;}
  const value=window.prompt('Enter the replacement text (leave blank to only remove the printed text):','');
  if(value===null){setReplacePrintedTextMode(false);return;}
  const status=$('replacePrintedTextStatus'); if(status)status.textContent='Removing printed text…';
  const replacementGroupId='replace-'+uid();
  try{
    // Explicit user selection wins over any OCR guesses in the same area.
    canvas.getObjects().slice().forEach(o=>{
      if(isText(o)&&(o.autoOcrText||o.fieldType==='ocr-auto'||o.fieldType==='manual-ocr'||o.visualFallback)&&boxesOverlap(o.sourceNormalizedBox,box)) canvas.remove(o);
    });
    const patch=await ZenRasterEdit.addPatchToCanvas(canvas,bg,box,{objectId:uid(),name:'Removed printed text background',fieldType:'manual-inpaint',manualTextPatch:true});
    const bgIndex=canvas.getObjects().indexOf(bg); canvas.moveTo(patch,Math.max(1,bgIndex+1));
    const r=ZenRasterEdit.canvasRectForNormalized(bg,box);
    if(String(value).trim()){
      const textObj=new fabric.IText(value,{left:r.left,top:r.top,originX:'left',originY:'top',fontSize:Math.max(10,r.height*.78),fontFamily:'Georgia',fill:'#111827',
        name:'Editable replacement text',fieldType:'manual-replace',customerEditable:true,selectable:true,evented:true,editable:true,hasControls:true,sourceNormalizedBox:box,sourceText:value,ocrOverlayPending:false,replacementGroupId,manualReplacement:true,opacity:1});
      textObj.initDimensions?.();
      // Keep text proportions natural: reduce font size instead of squashing glyphs horizontally.
      for(let i=0;i<30&&textObj.width>r.width*.98;i++){textObj.set('fontSize',Math.max(7,textObj.fontSize*.94));textObj.initDimensions?.();}
      canvas.add(textObj);canvas.bringToFront(textObj);canvas.setActiveObject(textObj);textObj.setCoords();
    }
    snapshot();renderAll(); if(status)status.textContent='Done. The replacement is now normal editable text.';
  }catch(err){console.error(err);alert('Could not clean this area. Try a tighter rectangle around only the text.');}
  finally{setReplacePrintedTextMode(false);}
}

bind('replacePrintedTextBtn',()=>setReplacePrintedTextMode(true));
bind('cancelReplacePrintedTextBtn',()=>setReplacePrintedTextMode(false));
canvas.on('mouse:down',ev=>{
  if(!printedTextReplaceMode)return;
  const p=canvas.getPointer(ev.e);printedTextStart={x:p.x,y:p.y};
  printedTextPreview=new fabric.Rect({left:p.x,top:p.y,width:1,height:1,fill:'rgba(124,58,237,.12)',stroke:'#7c3aed',strokeWidth:2,strokeDashArray:[7,5],selectable:false,evented:false,excludeFromExport:true});
  canvas.add(printedTextPreview);canvas.bringToFront(printedTextPreview);
});
canvas.on('mouse:move',ev=>{
  if(!printedTextReplaceMode||!printedTextStart||!printedTextPreview)return;
  const p=canvas.getPointer(ev.e),x=Math.min(printedTextStart.x,p.x),y=Math.min(printedTextStart.y,p.y);
  printedTextPreview.set({left:x,top:y,width:Math.abs(p.x-printedTextStart.x),height:Math.abs(p.y-printedTextStart.y)});printedTextPreview.setCoords();canvas.requestRenderAll();
});
canvas.on('mouse:up',ev=>{
  if(!printedTextReplaceMode||!printedTextStart||!printedTextPreview)return;
  const rect=printedTextPreview;printedTextStart=null;
  if(rect.width<5||rect.height<5){canvas.remove(rect);printedTextPreview=null;return;}
  finishReplacePrintedText(rect);
});
bind('editImageBtn',()=>{const o=active();if(o&&o.type==='image'&&window.ZenImageTools)ZenImageTools.open(canvas,o)});
bind('deleteBtn',async()=>{
  const list=selectedObjects();
 
  for(const o of list){
    if(isText(o)&&o.ocrOverlayPending) await activatePendingOcrText(o);
    if(o._zvPendingArtwork) await activatePendingArtwork(o);
  }
  list.forEach(o=>canvas.remove(o));canvas.discardActiveObject();snapshot();renderAll();
});bind('duplicateBtn',duplicate);bind('bringFrontBtn',()=>modify(o=>canvas.bringToFront(o)));bind('sendBackBtn',()=>modify(o=>canvas.sendToBack(o)));bind('flipXBtn',()=>modify(o=>o.set('flipX',!o.flipX)));bind('flipYBtn',()=>modify(o=>o.set('flipY',!o.flipY)));bind('lockBtn',()=>{toggleLock();snapshot();renderAll()});bind('groupBtn',group);
bind('leftBtn',()=>modify(o=>o.set({left:20})));bind('centerBtn',()=>modify(o=>o.set({left:(W-o.getScaledWidth())/2})));bind('rightBtn',()=>modify(o=>o.set({left:W-o.getScaledWidth()-20})));bind('topBtn',()=>modify(o=>o.set({top:20})));bind('middleBtn',()=>modify(o=>o.set({top:(H-o.getScaledHeight())/2})));bind('bottomBtn',()=>modify(o=>o.set({top:H-o.getScaledHeight()-20})));
bind('applyTextBtn',async()=>{const o=active();if(!o)return;const wasPending=!!(isText(o)&&o.ocrOverlayPending);if(wasPending)await activatePendingOcrText(o);o.set({fill:$('fillColor').value,opacity:Number($('opacity').value),angle:Number($('rotation').value)});if(isText(o)){o.set({text:$('textValue').value,fontSize:Number($('fontSize').value),fontFamily:$('fontFamily').value,scaleX:1,scaleY:1});o.initDimensions?.();if(o.sourceNormalizedBox)fitOcrTextToSourceBox(o)}snapshot();renderAll();});bind('boldBtn',()=>modify(o=>{if(isText(o)&&o.ocrOverlayPending)activatePendingOcrText(o);if(isText(o))o.set('fontWeight',o.fontWeight==='bold'?'normal':'bold')}));bind('italicBtn',()=>modify(o=>{if(isText(o)&&o.ocrOverlayPending)activatePendingOcrText(o);if(isText(o))o.set('fontStyle',o.fontStyle==='italic'?'normal':'italic')}));bind('underlineBtn',()=>modify(o=>{if(isText(o)&&o.ocrOverlayPending)activatePendingOcrText(o);if(isText(o))o.set('underline',!o.underline)}));bind('applyBackgroundBtn',()=>applyDocumentBackgroundColour($('backgroundColor').value));
bind('addPageBtn',()=>{sync();pages.push(newPage());loadPage(pages.length-1);snapshot()});
bind('duplicatePageBtn',()=>{
  if(activePage<configuredPrintSurfaces.length){
    return alert('This page is linked to the "'+getPageSurface(activePage).label+'" print surface and cannot be duplicated.');
  }
  sync();pages.splice(activePage+1,0,clone(pages[activePage]));loadPage(activePage+1);snapshot();
});
bind('deletePageBtn',()=>{
  if(activePage<configuredPrintSurfaces.length){
    return alert('The "'+getPageSurface(activePage).label+'" page is required by this product and cannot be deleted.');
  }
  if(pages.length===1)return alert('At least one page is required.');
  pages.splice(activePage,1);loadPage(Math.max(0,activePage-1));snapshot();
});
bind('undoBtn',()=>restore(historyIndex-1));bind('redoBtn',()=>restore(historyIndex+1));
bind('fitBtn',()=>setBottomZoom(100));
if($('zoomRange'))$('zoomRange').oninput=e=>setBottomZoom(Number(e.target.value));
bind('gridBtn',()=>{gridVisible=!gridVisible;renderAll()});bind('guidesBtn',()=>{guidesVisible=!guidesVisible;renderAll()});
bind('fullscreenBtn',()=>document.querySelector('.editor-shell').requestFullscreen?.());bind('printCheckBtn',printCheck);
bind('showAllBtn',()=>modify(o=>o.visible=true));bind('unlockAllBtn',()=>canvas.getObjects().forEach(o=>{if(o.excludeFromExport||o.customerEditable===false)return;o.set({selectable:true,evented:true,lockMovementX:false,lockMovementY:false,lockScalingX:false,lockScalingY:false,lockRotation:false,hasControls:true})}));
bind('aiTaglineBtn',()=>ai('tagline'));bind('aiCritiqueBtn',()=>ai('critique'));
bind('saveDraftBtn',()=>save(false,false).catch(e=>{if($('saveStatus'))$('saveStatus').textContent=e.message}));
bind('saveBtn',()=>save(false,true).catch(e=>{if($('saveStatus'))$('saveStatus').textContent=e.message}));
bind('downloadBtn',()=>{buildDownloadPageChoices();openEditorModal('downloadModal')});
bind('downloadJsonBtn',()=>{sync();const a=document.createElement('a');a.download='zenvibe-design.json';a.href=URL.createObjectURL(new Blob([JSON.stringify({version:3,document:{width:W,height:H,profile:P.scaleProfile||'product',label:P.scaleProfileLabel||'',physical:P.physicalFormat||''},pages},null,2)],{type:'application/json'}));a.click()});

function openEditorModal(id){const m=$(id);if(m){m.hidden=false;document.body.classList.add('editor-modal-open')}}
function closeEditorModal(id){const m=$(id);if(m){m.hidden=true;if(!document.querySelector('.editor-modal:not([hidden])'))document.body.classList.remove('editor-modal-open')}}
document.querySelectorAll('[data-close-editor-modal]').forEach(b=>b.addEventListener('click',()=>closeEditorModal(b.dataset.closeEditorModal)));
document.querySelectorAll('.editor-modal').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)closeEditorModal(m.id)}));

function buildDownloadPageChoices(){
  const host=$('downloadPages');if(!host)return;sync();
  host.innerHTML=pages.map((_,i)=>`<label><input type="checkbox" value="${i}" checked> ${getPageSurface(i).label||('Page '+(i+1))}</label>`).join('');
  const all=$('downloadAllPages');if(all)all.checked=true;
}
bind('downloadAllPages',e=>document.querySelectorAll('#downloadPages input').forEach(c=>c.checked=e.target.checked));
function selectedDownloadPages(){const checked=[...document.querySelectorAll('#downloadPages input:checked')].map(x=>Number(x.value));return checked.length?checked:[activePage]}
async function waitForPageLoad(){for(let i=0;i<100&&loading;i++)await new Promise(r=>setTimeout(r,30));await new Promise(r=>setTimeout(r,40))}
async function exportPage(index,format='png'){
  loadPage(index);await waitForPageLoad();canvas.discardActiveObject();canvas.requestRenderAll();
  return canvas.toDataURL({format:format==='jpg'?'jpeg':'png',quality:.95,multiplier:2});
}
function triggerDataDownload(data,name){const a=document.createElement('a');a.href=data;a.download=name;document.body.appendChild(a);a.click();a.remove()}

async function ensureJsPDF(){
  if(window.jspdf?.jsPDF)return window.jspdf.jsPDF;
  if(window.jsPDF)return window.jsPDF;

  const existing=document.querySelector('script[data-zenvibe-jspdf-fallback]');
  if(existing){
    await new Promise((resolve,reject)=>{
      if(window.jspdf?.jsPDF || window.jsPDF)return resolve();
      existing.addEventListener('load',resolve,{once:true});
      existing.addEventListener('error',reject,{once:true});
    });
    return window.jspdf?.jsPDF || window.jsPDF || null;
  }

  const script=document.createElement('script');
  script.src='https://unpkg.com/jspdf@2.5.2/dist/jspdf.umd.min.js';
  script.async=true;
  script.dataset.zenvibeJspdfFallback='1';

  await new Promise((resolve,reject)=>{
    script.onload=resolve;
    script.onerror=()=>reject(new Error('PDF library could not be loaded. Please check your internet connection and try again.'));
    document.head.appendChild(script);
  });

  return window.jspdf?.jsPDF || window.jsPDF || null;
}

async function performDownload(){
  const btn=$('confirmDownloadBtn'),format=$('downloadFormat')?.value||'png',indexes=selectedDownloadPages(),original=activePage;
  if(btn){btn.disabled=true;btn.textContent='Preparing…'}
  try{
    const base=(($('designName')?.value||'zenvibe-design').trim()||'zenvibe-design').replace(/[^a-z0-9_-]+/gi,'-');
    if(format==='pdf'){
      const jsPDF=await ensureJsPDF();
      if(!jsPDF)throw new Error('PDF export could not start because the PDF library did not load.');
      let pdf=null;
      for(let n=0;n<indexes.length;n++){
        const data=await exportPage(indexes[n],'png');
        if(!pdf)pdf=new jsPDF({orientation:W>=H?'landscape':'portrait',unit:'px',format:[W,H]});else pdf.addPage([W,H],W>=H?'landscape':'portrait');
        pdf.addImage(data,'PNG',0,0,W,H);
      }
      pdf.save(base+'.pdf');
    }else{
      for(const idx of indexes){const data=await exportPage(idx,format);triggerDataDownload(data,`${base}-page-${idx+1}.${format}`);await new Promise(r=>setTimeout(r,120));}
    }
    closeEditorModal('downloadModal');
  }catch(e){console.error(e);alert(e.message||'Download could not be created.');}
  finally{loadPage(original);await waitForPageLoad();if(btn){btn.disabled=false;btn.textContent='Download'}}
}
bind('confirmDownloadBtn',performDownload);

// View menu: only controls that are useful to the customer.
const viewBtn=$('viewMenuBtn'),viewMenu=$('viewMenu');
if(viewBtn&&viewMenu){viewBtn.addEventListener('click',e=>{e.stopPropagation();viewMenu.hidden=!viewMenu.hidden;viewBtn.setAttribute('aria-expanded',String(!viewMenu.hidden))});document.addEventListener('click',()=>{viewMenu.hidden=true;viewBtn.setAttribute('aria-expanded','false')});viewMenu.addEventListener('click',e=>e.stopPropagation())}
bind('viewFitBtn',()=>{setBottomZoom(100);if(viewMenu)viewMenu.hidden=true});
bind('viewGridBtn',()=>{gridVisible=!gridVisible;renderAll()});bind('viewSafeBtn',()=>{guidesVisible=!guidesVisible;renderAll()});
bind('viewFullscreenBtn',()=>document.querySelector('.editor-shell').requestFullscreen?.());

// Position & size controls in Tools.
function syncPositionFields(){const o=selectedEditableObject();[['positionX','left'],['positionY','top']].forEach(([id,k])=>{if($(id))$(id).value=o?Math.round(o[k]||0):''});if($('positionW'))$('positionW').value=o?Math.round(o.getScaledWidth()):'';if($('positionH'))$('positionH').value=o?Math.round(o.getScaledHeight()):'';}
canvas.on('selection:created',syncPositionFields);canvas.on('selection:updated',syncPositionFields);canvas.on('object:modified',syncPositionFields);canvas.on('selection:cleared',syncPositionFields);
bind('applyPositionBtn',()=>{const o=selectedEditableObject();if(!o)return;const x=Number($('positionX').value),y=Number($('positionY').value),w=Number($('positionW').value),h=Number($('positionH').value);if(Number.isFinite(x))o.set('left',x);if(Number.isFinite(y))o.set('top',y);if(w>0)o.set('scaleX',w/Math.max(1,o.width));if(h>0)o.set('scaleY',h/Math.max(1,o.height));o.setCoords();snapshot();renderAll()});
const pdfBtn=document.getElementById("downloadPdfBtn");

if(pdfBtn){

    pdfBtn.onclick=downloadPDF;

}
async function downloadPDF(){

    const jsPDF=await ensureJsPDF();
    if(!jsPDF){alert("PDF export could not start.");return;}

    const pdf=new jsPDF({

        orientation:"landscape",

        unit:"px",

        format:[

            canvas.getWidth(),

            canvas.getHeight()

        ]

    });

    const img=canvas.toDataURL({

        format:"png",

        multiplier:2

    });

    pdf.addImage(

        img,

        "PNG",

        0,

        0,

        canvas.getWidth(),

        canvas.getHeight()

    );

    pdf.save("design.pdf");

}
canvas.on({'selection:created':()=>{syncPanel();renderLayers()},'selection:updated':()=>{syncPanel();renderLayers()},'selection:cleared':renderLayers,'object:modified':()=>{snapshot();renderLayers()},'text:changed':scheduleLocalSave});
canvas.on('text:editing:exited',ev=>{const o=ev.target;if(o&&o.sourceNormalizedBox){fitOcrTextToSourceBox(o);snapshot();renderAll();renderLayers();}});

function ocrHotspotAtPointer(pointer){
  const bg=canvas.getObjects().find(x=>x.type==='image'&&x.backgroundAsset&&x.exactVisualMaster)||canvas.getObjects().find(x=>x.type==='image'&&x.backgroundAsset);if(!bg)return null;
  const el=bg.getElement(),nw=el.naturalWidth||bg.width||1,nh=el.naturalHeight||bg.height||1,sx=bg.scaleX||1,sy=bg.scaleY||1;
  const hits=canvas.getObjects().filter(o=>isText(o)&&o.customerEditable!==false&&o.sourceNormalizedBox&&(o.autoOcrText||o.fieldType==='ocr-auto'||o.fieldType==='manual-ocr'||o.fieldType==='manual-replace')).filter(o=>{const b=o.sourceNormalizedBox,l=(bg.left||0)+b.x*nw*sx,t=(bg.top||0)+b.y*nh*sy,w=b.w*nw*sx,h=b.h*nh*sy,pad=Math.max(5,Math.min(14,h*.45));return pointer.x>=l-pad&&pointer.x<=l+w+pad&&pointer.y>=t-pad&&pointer.y<=t+h+pad});

  hits.sort((a,b)=>{

    const am=a.fieldType==='manual-replace'?1:0,bm=b.fieldType==='manual-replace'?1:0;
    if(am!==bm)return bm-am;
    const af=a.visualFallback?1:0,bf=b.visualFallback?1:0;
    if(af!==bf)return bf-af;
    const ac=Number(a.sourceConfidence||0),bc=Number(b.sourceConfidence||0);
    if((ac>=45)!==(bc>=45))return bc-ac;
    return (a.sourceNormalizedBox.w*a.sourceNormalizedBox.h)-(b.sourceNormalizedBox.w*b.sourceNormalizedBox.h);
  });
  if(hits[0])return hits[0];


  const near=canvas.getObjects().filter(o=>isText(o)&&o.customerEditable!==false&&o.sourceNormalizedBox&&(o.autoOcrText||o.fieldType==='ocr-auto'||o.fieldType==='manual-ocr'||o.fieldType==='manual-replace')).map(o=>{
    const b=o.sourceNormalizedBox,l=(bg.left||0)+b.x*nw*sx,t=(bg.top||0)+b.y*nh*sy,w=b.w*nw*sx,h=b.h*nh*sy,cx=l+w/2,cy=t+h/2;
    const dy=Math.abs(pointer.y-cy),dx=Math.max(0,Math.abs(pointer.x-cx)-w/2);
    return {o,score:dy+dx*.3,ok:dy<=Math.max(18,h*1.7)&&dx<=Math.max(34,w*.55)};
  }).filter(x=>x.ok).sort((a,b)=>a.score-b.score);
  return near[0]?.o||null;
}

function detectPrintedBandAtPointer(pointer){
  const bg=getMasterArtwork();if(!bg)return null;
  try{
    const el=bg.getElement(),nw=el.naturalWidth||bg.width||1,nh=el.naturalHeight||bg.height||1,sx=bg.scaleX||1,sy=bg.scaleY||1;
    const ix=Math.round((pointer.x-(bg.left||0))/sx),iy=Math.round((pointer.y-(bg.top||0))/sy);
    if(ix<0||iy<0||ix>=nw||iy>=nh)return null;

    const cropW=Math.min(nw,Math.max(140,Math.round(nw*.48)));
    const cropH=Math.min(nh,Math.max(70,Math.round(nh*.14)));
    const x0=Math.max(0,Math.min(nw-cropW,Math.round(ix-cropW/2)));
    const y0=Math.max(0,Math.min(nh-cropH,Math.round(iy-cropH/2)));
    const c=document.createElement('canvas');c.width=cropW;c.height=cropH;
    const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(el,x0,y0,cropW,cropH,0,0,cropW,cropH);
    const frame=ctx.getImageData(0,0,cropW,cropH),d=frame.data;
    const vals=[];
    for(let y=0;y<cropH;y+=2)for(let x=0;x<cropW;x+=2){
      if(x>6&&x<cropW-7&&y>6&&y<cropH-7)continue;
      const i=(y*cropW+x)*4;if(d[i+3]<100)continue;
      vals.push(.299*d[i]+.587*d[i+1]+.114*d[i+2]);
    }
    vals.sort((a,b)=>a-b);const paper=vals.length?vals[Math.floor(vals.length*.72)]:242;
    const ink=(x,y)=>{if(x<0||y<0||x>=cropW||y>=cropH)return false;const i=(y*cropW+x)*4;if(d[i+3]<70)return false;const r=d[i],g=d[i+1],b=d[i+2],L=.299*r+.587*g+.114*b,mx=Math.max(r,g,b),mn=Math.min(r,g,b);return L<Math.min(220,paper-22)||((mx-mn)>34&&L<paper-10);};
    const px=ix-x0,py=iy-y0;

    // Find nearest horizontal row run containing enough ink.
    const rowScore=new Array(cropH).fill(0);
    for(let y=0;y<cropH;y++)for(let x=0;x<cropW;x++)if(ink(x,y))rowScore[y]++;
    const active=y=>rowScore[y]>=Math.max(2,Math.round(cropW*.004));
    let seed=-1,best=1e9;
    for(let y=0;y<cropH;y++)if(active(y)){const dist=Math.abs(y-py);if(dist<best){best=dist;seed=y;}}
    if(seed<0||best>Math.max(28,cropH*.32))return null;
    let top=seed,bottom=seed,gap=0;
    for(let y=seed-1;y>=0;y--){if(active(y)){top=y;gap=0}else if(++gap>2)break;}
    gap=0;for(let y=seed+1;y<cropH;y++){if(active(y)){bottom=y;gap=0}else if(++gap>2)break;}
    // Never allow a text replacement to become a giant vertical block.
    const maxLineH=Math.max(18,Math.round(nh*.075));
    if(bottom-top+1>maxLineH){top=Math.max(0,seed-Math.floor(maxLineH/2));bottom=Math.min(cropH-1,top+maxLineH-1);}

    // Column projection only across this row band. Split at large blank gaps and
    // choose the segment nearest the click; this isolates one name/phrase.
    const colScore=new Array(cropW).fill(0);
    for(let x=0;x<cropW;x++)for(let y=top;y<=bottom;y++)if(ink(x,y))colScore[x]++;
    const colActive=x=>colScore[x]>=1;
    const runs=[];let s=-1,last=-1;
    for(let x=0;x<cropW;x++){
      if(colActive(x)){if(s<0)s=x;last=x;}
      else if(s>=0&&x-last>Math.max(7,Math.round((bottom-top+1)*.85))){runs.push([s,last]);s=-1;last=-1;}
    }
    if(s>=0)runs.push([s,last]);if(!runs.length)return null;
    let run=runs[0],runDist=1e9;
    for(const r of runs){const cx=(r[0]+r[1])/2,dist=px>=r[0]&&px<=r[1]?0:Math.abs(cx-px);if(dist<runDist){runDist=dist;run=r;}}
    let left=run[0],right=run[1];
    const lineH=Math.max(6,bottom-top+1),padX=Math.max(5,Math.round(lineH*.55)),padY=Math.max(3,Math.round(lineH*.35));
    left=Math.max(0,left-padX);right=Math.min(cropW-1,right+padX);top=Math.max(0,top-padY);bottom=Math.min(cropH-1,bottom+padY);

    // Hard safety clamps: a click-to-edit region can never wipe most of the card.
    const maxW=Math.round(nw*.55),maxH=Math.round(nh*.09);
    let absL=x0+left,absT=y0+top,absR=x0+right,absB=y0+bottom;
    if(absR-absL>maxW){absL=Math.max(0,ix-Math.floor(maxW/2));absR=Math.min(nw-1,absL+maxW);}
    if(absB-absT>maxH){absT=Math.max(0,iy-Math.floor(maxH/2));absB=Math.min(nh-1,absT+maxH);}
    if(absR-absL<8||absB-absT<4)return null;
    return {x:absL/nw,y:absT/nh,w:(absR-absL+1)/nw,h:(absB-absT+1)/nh};
  }catch(e){console.warn('V57 printed-text detection failed',e);return null;}
}
async function activateOrCreateTextAtPointer(pointer){
  let hit=ocrHotspotAtPointer(pointer);
  if(!hit){
    const box=detectPrintedBandAtPointer(pointer);
    if(box){
      const value=window.prompt('This printed text was not recognised automatically. Enter the replacement text:','');
      if(value===null)return null;
      const r=sourceBoxCanvasRect({sourceNormalizedBox:box});
      hit=new fabric.IText(String(value),{left:r.left,top:r.top,originX:'left',originY:'top',fontSize:Math.max(10,r.height*.78),fontFamily:'Georgia',fill:'#111827',name:'Editable missed text',fieldType:'ocr-auto',autoOcrText:true,visualFallback:true,customerEditable:true,selectable:true,evented:true,editable:true,hasControls:true,opacity:0.001,sourceNormalizedBox:box,sourceText:'',ocrOverlayPending:true});
      hit.objectId=uid();canvas.add(hit);canvas.bringToFront(hit);
    }
  }
  if(!hit)return null;
  canvas.discardActiveObject();canvas.setActiveObject(hit);
  if(hit.ocrOverlayPending){
    if(hit.visualFallback&&!String(hit.text||'').trim()){const value=window.prompt('Enter replacement text',String(hit.sourceText||''));if(value===null)return null;hit.set({text:value,opacity:0});hit.initDimensions?.();}
    await activatePendingOcrText(hit);
  }
  syncPanel();renderLayers();canvas.requestRenderAll();
  if(isText(hit)&&hit.customerEditable!==false){setTimeout(()=>{try{canvas.setActiveObject(hit);hit.enterEditing?.();hit.selectAll?.();canvas.requestRenderAll();}catch(_e){}},0);}
  return hit;
}
canvas.on('mouse:down',async ev=>{
  if(printedTextReplaceMode)return;
  const pointer=canvas.getPointer(ev.e);
  // Never allow the protected uploaded raster (or a giant helper artwork mask)
  // to become the customer's active selection. Printed content must win.
  const t=ev.target,helper=t&&(t.backgroundAsset||t.exactVisualMaster||t.fieldType==='auto-art-layer');
  const known=ocrHotspotAtPointer(pointer);
  let hit=null;
  // V57: one click is enough. If OCR knows the field, activate it. If the user
  // clicked the protected uploaded bitmap and OCR missed the wording (common for
  // script names), detect the local printed line and convert that region now.
  if(known||helper) hit=await activateOrCreateTextAtPointer(pointer);
  if(hit||helper){if(ev.e){ev.e.preventDefault?.();ev.e.stopPropagation?.();}if(!hit)canvas.discardActiveObject();canvas.requestRenderAll();}
});
// V41: every published editable text object, including manual replacements, can
// be edited directly on the canvas. This does not depend on OCR recognition.
canvas.on('mouse:dblclick',ev=>{const direct=ev.target;if(printedTextReplaceMode||!isText(direct)||direct.customerEditable===false)return;canvas.setActiveObject(direct);direct.enterEditing?.();direct.selectAll?.();syncPanel();renderLayers();canvas.requestRenderAll();});
canvas.on('mouse:dblclick',async ev=>{if(printedTextReplaceMode)return;const pointer=canvas.getPointer(ev.e);let hit=ocrHotspotAtPointer(pointer);if(!hit)hit=await activateOrCreateTextAtPointer(pointer);else{if(hit.visualFallback&&!String(hit.text||'').trim()){const value=window.prompt('Enter replacement text','');if(value===null)return;hit.set({text:value,opacity:0.001});hit.initDimensions?.();}await activatePendingOcrText(hit);}if(hit){canvas.setActiveObject(hit);hit.enterEditing?.();hit.selectAll?.();syncPanel();renderLayers();canvas.requestRenderAll();snapshot()}});
canvas.on('selection:created',e=>{const o=e.selected?.[0]||e.target;if(o&&o._zvPendingArtwork)activatePendingArtwork(o);});canvas.on('selection:updated',e=>{const o=e.selected?.[0]||e.target;if(o&&o._zvPendingArtwork)activatePendingArtwork(o);});

window.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName))return;if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();e.shiftKey?restore(historyIndex+1):restore(historyIndex-1)}else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='y'){e.preventDefault();restore(historyIndex+1)}else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='d'){e.preventDefault();duplicate()}else if(e.key==='Delete'||e.key==='Backspace'){$('deleteBtn').click()}else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){const d=e.shiftKey?10:1;modify(o=>o.set({left:o.left+(e.key==='ArrowRight'?d:e.key==='ArrowLeft'?-d:0),top:o.top+(e.key==='ArrowDown'?d:e.key==='ArrowUp'?-d:0)}))}});

// Canva-style presentation controls and expanded asset libraries.
const FONT_LIST=['Arial','Georgia','Verdana','Trebuchet MS','Times New Roman','Courier New','Inter','Poppins','Montserrat','Roboto','Open Sans','Lato','Nunito','Raleway','Oswald','Playfair Display','Merriweather','DM Sans','Manrope','Bebas Neue','Anton','Pacifico','Lobster','Abril Fatface','Cinzel','Cormorant Garamond','Cormorant SC','Quicksand','Rubik','Work Sans','Source Sans 3','Josefin Sans','Archivo','Fira Sans','Ubuntu','Cabin','Karla','Libre Baskerville','Dancing Script','Great Vibes','Caveat','Permanent Marker','Sacramento','Parisienne','Allura','Alex Brush','Marck Script','Satisfy','Kaushan Script','Courgette','Yellowtail','Cookie','Rochester','Tangerine','Italianno','Petit Formal Script','Bodoni Moda','Prata','Lora','Crimson Text','EB Garamond','Spectral','Libre Caslon Text','Cardo','Domine','Arvo','Roboto Slab','Zilla Slab','Alegreya','Alegreya Sans','Barlow','Barlow Condensed','Exo 2','Orbitron','Rajdhani','Titillium Web','Mukta','PT Sans','PT Serif','Noto Sans','Noto Serif','Noto Sans Display','Noto Serif Display'];
const EMOJIS=[['smile','😀'],['smile','😁'],['laugh','😂'],['happy','😊'],['love','😍'],['cool','😎'],['thinking','🤔'],['party','🥳'],['heart','❤️'],['heart','💙'],['star','⭐'],['sparkle','✨'],['fire','🔥'],['rocket','🚀'],['celebrate','🎉'],['check','✅'],['phone','☎️'],['email','✉️'],['location','📍'],['website','🌐'],['gift','🎁'],['coffee','☕'],['food','🍕'],['flower','🌸'],['leaf','🌿'],['sun','☀️'],['moon','🌙'],['camera','📷'],['music','🎵'],['business','💼'],['building','🏢'],['cart','🛒'],['truck','🚚'],['crown','👑'],['diamond','💎'],['light','💡'],['target','🎯'],['thumb','👍'],['clap','👏'],['hand','👋']];
function loadGoogleFont(name){if(['Arial','Georgia','Verdana','Trebuchet MS','Times New Roman','Courier New'].includes(name))return;const id='gf-'+name.replace(/\W/g,'-');if(document.getElementById(id))return;const l=document.createElement('link');l.id=id;l.rel='stylesheet';l.href='https://fonts.googleapis.com/css2?family='+encodeURIComponent(name).replace(/%20/g,'+')+':wght@300;400;500;600;700;800&display=swap';document.head.appendChild(l)}
function buildFontLibrary(filter=''){
 const select=$('fontFamily'),lib=$('fontLibrary'); if(!select||!lib)return;
 if(!select.options.length) FONT_LIST.forEach(f=>select.add(new Option(f,f)));
 lib.innerHTML=''; FONT_LIST.filter(f=>f.toLowerCase().includes(filter.toLowerCase())).forEach(f=>{const b=document.createElement('button');b.textContent=f;b.style.fontFamily=f;b.onclick=()=>{loadGoogleFont(f);modify(o=>isText(o)&&o.set('fontFamily',f));select.value=f};lib.appendChild(b)});
}
function buildEmojiLibrary(filter=''){
 const lib=$('emojiLibrary');if(!lib)return;lib.innerHTML='';EMOJIS.filter(([n,e])=>(n+' '+e).toLowerCase().includes(filter.toLowerCase())).forEach(([n,e])=>{const b=document.createElement('button');b.textContent=e;b.title=n;b.onclick=()=>add(new fabric.IText(e,{left:W/2-35,top:H/2-35,fontSize:70,fontFamily:'Arial',fill:'#111827',name:n}));lib.appendChild(b)});
}
function polygonPoints(sides,radius){const pts=[];for(let i=0;i<sides;i++){const a=-Math.PI/2+i*2*Math.PI/sides;pts.push({x:radius+Math.cos(a)*radius,y:radius+Math.sin(a)*radius})}return pts}
function starPoints(outer=85,inner=38,points=5){const p=[];for(let i=0;i<points*2;i++){const r=i%2?inner:outer,a=-Math.PI/2+i*Math.PI/points;p.push({x:outer+Math.cos(a)*r,y:outer+Math.sin(a)*r})}return p}
function addLibraryShape(type){const base={left:W/2-90,top:H/2-70,fill:'#6c4cf1',strokeWidth:0,name:type};let o;
 if(type==='rect')o=new fabric.Rect({...base,width:180,height:140});
 else if(type==='roundRect')o=new fabric.Rect({...base,width:200,height:130,rx:24,ry:24});
 else if(type==='circle')o=new fabric.Circle({...base,radius:72});
 else if(type==='ellipse')o=new fabric.Ellipse({...base,rx:100,ry:62});
 else if(type==='triangle')o=new fabric.Triangle({...base,width:170,height:150});
 else if(type==='diamond')o=new fabric.Polygon(polygonPoints(4,80),{...base,angle:45});
 else if(type==='pentagon')o=new fabric.Polygon(polygonPoints(5,82),base);
 else if(type==='hexagon')o=new fabric.Polygon(polygonPoints(6,82),base);
 else if(type==='star')o=new fabric.Polygon(starPoints(),base);
 else if(type==='heart')o=new fabric.Path('M 90 160 C 20 110 0 65 28 28 C 55 -7 88 15 90 42 C 92 15 125 -7 152 28 C 180 65 160 110 90 160 z',{...base,left:W/2-90,top:H/2-80});
 else if(type==='arrowRight')o=new fabric.Path('M 0 35 L 110 35 L 110 0 L 180 70 L 110 140 L 110 105 L 0 105 z',base);
 else if(type==='speech')o=new fabric.Path('M 10 10 Q 10 0 20 0 L 180 0 Q 190 0 190 10 L 190 100 Q 190 110 180 110 L 75 110 L 35 145 L 45 110 L 20 110 Q 10 110 10 100 z',base);
 else if(type==='line')o=new fabric.Line([0,0,220,0],{left:W/2-110,top:H/2,stroke:'#17233c',strokeWidth:6,name:type});
 else if(type==='dashLine')o=new fabric.Line([0,0,220,0],{left:W/2-110,top:H/2,stroke:'#17233c',strokeWidth:5,strokeDashArray:[16,10],name:type});
 else if(type==='wave')o=new fabric.Path('M 0 35 C 35 0 70 70 105 35 C 140 0 175 70 210 35',{left:W/2-105,top:H/2-35,fill:'transparent',stroke:'#17233c',strokeWidth:6,name:type});
 else if(type==='cross')o=new fabric.Path('M 60 0 L 100 0 L 100 60 L 160 60 L 160 100 L 100 100 L 100 160 L 60 160 L 60 100 L 0 100 L 0 60 L 60 60 z',base);
 if(o)add(o)
}
document.querySelectorAll('.rail-tab').forEach(tab=>tab.onclick=()=>{document.querySelectorAll('.rail-tab').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.studio-panel-section').forEach(x=>x.classList.remove('active'));tab.classList.add('active');const panel=$(tab.dataset.panel);panel?.classList.add('active');$('panelTitle').textContent=tab.querySelector('b').textContent;document.querySelector('.studio-panel').classList.remove('panel-closed')});
$('closePanelBtn')?.addEventListener('click',()=>document.querySelector('.studio-panel').classList.toggle('panel-closed'));
document.querySelectorAll('#shapeLibrary [data-shape]').forEach(b=>b.onclick=()=>addLibraryShape(b.dataset.shape));
document.querySelectorAll('.text-preset').forEach(b=>b.onclick=()=>{const t=b.dataset.textPreset,settings=t==='heading'?{text:'Add a heading',fontSize:64,fontWeight:'bold'}:t==='subheading'?{text:'Add a subheading',fontSize:38,fontWeight:'600'}:{text:'Add a little bit of body text',fontSize:25,fontWeight:'normal'};add(new fabric.IText(settings.text,{left:80,top:80,fontSize:settings.fontSize,fontWeight:settings.fontWeight,fill:'#17233c',fontFamily:'Poppins'}));});
$('fontSearch')?.addEventListener('input',e=>buildFontLibrary(e.target.value));$('emojiSearch')?.addEventListener('input',e=>buildEmojiLibrary(e.target.value));
const swatches=['#ffffff','#f7f5ff','#eef5ff','#fff3ec','#f1fff6','#17233c','#06142b','#6c4cf1','#e83e8c','#f4b400','#1e9e68','#e7d8c9'];const sw=$('backgroundSwatches');if(sw)swatches.forEach(c=>{const b=document.createElement('button');b.style.background=c;b.title=c;b.onclick=()=>{$('backgroundColor').value=c;applyDocumentBackgroundColour(c)};sw.appendChild(b)});
function setBottomZoom(v){v=Math.max(20,Math.min(180,Number(v)));$('bottomZoomRange').value=v;$('zoomRange').value=v;$('zoomLabel').textContent=v+'%';setCanvasScale(v)}
$('bottomZoomRange')?.addEventListener('input',e=>setBottomZoom(e.target.value));$('bottomZoomOut')?.addEventListener('click',()=>setBottomZoom(Number($('bottomZoomRange').value)-10));$('bottomZoomIn')?.addEventListener('click',()=>setBottomZoom(Number($('bottomZoomRange').value)+10));
buildFontLibrary();buildEmojiLibrary();FONT_LIST.slice(0,15).forEach(loadGoogleFont);

const recovered=localStorage.getItem(localKey());
// V27: a published template must always open from the exact latest admin master.
// Never let an old browser draft replace template JSON. Draft recovery is only for blank canvases.
if(window.SOURCE_TEMPLATE_ID && !window.EXISTING_DESIGN?.id){
  if(recovered) localStorage.removeItem(localKey());
}else if(recovered&&!window.EXISTING_DESIGN?.id){try{const d=JSON.parse(recovered);if(Date.now()-d.at<86400000&&confirm('Recover your personal unsaved draft?')){pages=prepareInitialDocument(d);if($('designName'))$('designName').value=d.name||$('designName').value;$('quantity').value=new URLSearchParams(location.search).has('quantity')?window.ZENVIBE_INITIAL_QUANTITY:(d.quantity||window.ZENVIBE_INITIAL_QUANTITY||1)}}catch(e){}}
setBottomZoom(100);loadPage(0);snapshot();setInterval(()=>save(true,false).catch(()=>{$('autosaveStatus').textContent='Autosave unavailable'}),30000);
$('clearLocalDraftBtn')?.addEventListener('click',()=>{localStorage.removeItem(localKey());location.reload()});
})();
const discardBtn=document.getElementById("discardBtn");

if(discardBtn){

    discardBtn.onclick=function(){

        if(confirm("Discard all unsaved changes?")){

            location.reload();

        }

    };

}


(function(){
  function textFirst(){
    if(!window.canvas || !canvas.getObjects) return;
    canvas.getObjects().forEach(function(o){
      if(o && o.fieldType==='auto-art-layer' && o._zvPendingArtwork){
        o.evented=false; o.selectable=false;
      }
      if(o && (o.autoOcrText || o.fieldType==='ocr-auto' || o.fieldType==='manual-ocr')){
        o.evented=true; o.selectable=true; o.editable=true;
      }
    });
    canvas.requestRenderAll && canvas.requestRenderAll();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',()=>setTimeout(textFirst,700));
  else setTimeout(textFirst,700);
  setTimeout(textFirst,1800);
})();
