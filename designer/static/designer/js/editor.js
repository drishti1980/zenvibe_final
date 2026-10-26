// ZENVIBE V57 CLICK-ANY-PRINTED-TEXT EDITING
// ZENVIBE_V55_STABLE_BUILD 2026-08-10
/* ZenVibe customer editor V52 - reliable printed-content replace/delete + direct editable overlay model */
(function(){
const P=window.PRODUCT||{},EP=P.editorProfile||{},OPT=window.PRODUCT_OPTIONS||{};
function zvSelectedSize(){const key=String(OPT.selected_size||OPT.selected_size_key||new URLSearchParams(location.search).get('size')||new URLSearchParams(location.search).get('size_key')||'');return (Array.isArray(OPT.sizes)?OPT.sizes:[]).find(x=>String(x.key||x.size_key||'')===key)||null;}
function zvAdminSurfaces(){const direct=Array.isArray(window.ZV_ADMIN_PRINT_SURFACES)?window.ZV_ADMIN_PRINT_SURFACES:[];const a=Array.isArray(OPT.print_surfaces)?OPT.print_surfaces:[];const b=Array.isArray(OPT.printSurfaces)?OPT.printSurfaces:[];const c=Array.isArray(P.printSurfaces)?P.printSurfaces:[];return direct.length?direct:(a.length?a:(b.length?b:c));}
function zvPhysicalForPage(pageIndex){
  const page=Math.max(0,Number(pageIndex)||0);

  // Product 427 follows the production Name Badge editor: a 10 x 10 inch
  // workspace containing the centred physical badge and its own print face.
  if(Number(P.id||P.productId||P.product_id)===427){
    return {width:10,height:10,unit:'in',surface:(zvAdminSurfaces()[page]||zvAdminSurfaces()[0]||null),inheritedFromPage1:page>0};
  }

  // Product 428 matches the production Office Door Name Plate workspace:
  // 10 inches wide by 2 inches high. The old 10 x 3 admin values were making
  // the plate/ruler too tall and separating the guide from the artwork.
  if(Number(P.id||P.productId||P.product_id)===428){
    return {width:10,height:2,unit:'in',surface:(zvAdminSurfaces()[page]||zvAdminSurfaces()[0]||null),inheritedFromPage1:page>0};
  }

  // Product 420 (Custom Car Keychain) uses a 9 x 10 inch editor workspace on
  // BOTH Front and Back, matching the production editor. The smaller 3.5 x 1.5
  // value is the keychain/print-area size and must never drive the outer ruler.
  // Keep this workspace rule separate from the editable print-area geometry.
  if(Number(P.id||P.productId||P.product_id)===420){
    return {
      width:9,
      height:10,
      unit:'in',
      surface:(zvAdminSurfaces()[page]||zvAdminSurfaces()[0]||null),
      inheritedFromPage1:page>0
    };
  }

  const surfaces=zvAdminSurfaces();
  const cfg=OPT.editor_config||OPT.editorConfig||{};
  const size=zvSelectedSize();
  const sp=size?.editor_profile||size?.editorProfile||{};

  const positive=v=>{
    const n=Number(v);
    return Number.isFinite(n)&&n>0?n:0;
  };
  const dims=s=>({
    // New Admin-driven products use explicit WORKSPACE dimensions for the outer ruler.
    // Legacy products keep the old printable-dimension ruler behaviour.
    width:positive(cfg.enabled ? (s?.workspaceWidth ?? s?.workspace_width_in) : (s?.printWidth ?? s?.print_width_in ?? s?.width)),
    height:positive(cfg.enabled ? (s?.workspaceHeight ?? s?.workspace_height_in) : (s?.printHeight ?? s?.print_height_in ?? s?.height))
  });

  // Admin surface for the requested page. Existing projects use array/display order.
  const surface=surfaces[page]||null;
  const page1Surface=surfaces[0]||null;
  const current=dims(surface);
  const page1=dims(page1Surface);

  // Product/selected-size physical values are the fallback for page 1.
  const productWidth=positive(
    (cfg.enabled ? cfg.workspaceWidth : null) ??
    sp.physicalWidth ?? sp.printWidth ??
    sp.physical_width_in ?? sp.print_width_in ??
    P.printWidth ?? P.physicalWidthIn ?? P.physical_width_in
  );
  const productHeight=positive(
    (cfg.enabled ? cfg.workspaceHeight : null) ??
    sp.physicalHeight ?? sp.printHeight ??
    sp.physical_height_in ?? sp.print_height_in ??
    P.printHeight ?? P.physicalHeightIn ?? P.physical_height_in
  );

  // Rule:
  // page 1 -> its Admin ruler, otherwise product/size Admin ruler.
  // page 2+ -> its own Admin ruler when BOTH values exist;
  //            otherwise inherit page 1 completely.
  const page1Width=page1.width||productWidth;
  const page1Height=page1.height||productHeight;
  const hasOwnPageRuler=page>0 && current.width>0 && current.height>0;

  const width=page===0 ? page1Width : (hasOwnPageRuler?current.width:page1Width);
  const height=page===0 ? page1Height : (hasOwnPageRuler?current.height:page1Height);

  return {
    width,
    height,
    unit:'in',
    surface:hasOwnPageRuler?surface:(page1Surface||surface),
    inheritedFromPage1:page>0&&!hasOwnPageRuler
  };
}
const ZV_DOC=window.INITIAL_TEMPLATE?.document||{};
const ZV_BASE_W=Number(ZV_DOC.width)||Number(EP.canvas_width)||Number(P.width)||1050;
const ZV_BASE_H=Number(ZV_DOC.height)||Number(EP.canvas_height)||Number(P.height)||600;

// Fabric keeps an internal pixel coordinate system. The white artboard aspect ratio,
// however, must always match the ACTIVE Admin print surface measured in inches.
function zvLogicalSizeForPage(pageIndex,pageData){
  const saved=pageData;
  if(saved?.editorCoordinates && Number(saved.editorWidth)>0 && Number(saved.editorHeight)>0){
    return {width:Number(saved.editorWidth),height:Number(saved.editorHeight)};
  }
  const d=zvPhysicalForPage(pageIndex);
  const bw=Math.max(1,Number(ZV_BASE_W)||1050);
  const bh=Math.max(1,Number(ZV_BASE_H)||600);

  if(!(d.width>0&&d.height>0)){
    return {width:bw,height:bh};
  }

  // Admin inches define the artboard ratio. Fabric remains an internal pixel system.
  const ratio=d.width/d.height;
  const area=Math.max(1,bw*bh);
  let w=Math.sqrt(area*ratio);
  let h=w/ratio;

  // Keep logical coordinates practical and deterministic; this does not represent inches.
  const maxAxis=Math.max(w,h);
  if(maxAxis>1600){
    const k=1600/maxAxis; w*=k; h*=k;
  }
  const minAxis=Math.min(w,h);
  if(minAxis<240){
    const k=240/minAxis; w*=k; h*=k;
  }
  return {width:Math.round(w),height:Math.round(h)};
}

const ZV_INITIAL_LOGICAL=zvLogicalSizeForPage(0,window.INITIAL_TEMPLATE?.pages?.[0]);
let W=ZV_INITIAL_LOGICAL.width,H=ZV_INITIAL_LOGICAL.height;

// Product 416: the photo includes the metal body and key ring, but only
// the narrow upper flat face is printable. Do not include the curved lip.
if(Number(P.id||P.productId||P.product_id)===416){
  const cfg416=OPT.editor_config||OPT.editorConfig||{};
  if(cfg416.enabled && cfg416.mode==='print_area' && !(Array.isArray(cfg416.printAreas) && cfg416.printAreas.some(a=>a && (Number(a.leftPct)!==0 || Number(a.topPct)!==0 || Number(a.widthPct)!==100 || Number(a.heightPct)!==100)))){
    const oldAreas=Array.isArray(cfg416.printAreas)?cfg416.printAreas:[];
    const src=oldAreas[0]||{};
    cfg416.printAreas=[{
      ...src,
      surfaceId:src.surfaceId||zvAdminSurfaces()[0]?.id||null,
      leftPct:31.5,
      topPct:43.8,
      widthPct:36,
      heightPct:8.5
    }];
  }
}

// Product 420: after moving the outer editor to the production 9 x 10 inch
// workspace, the legacy Admin print-area percentages point at a portrait box.
// Replace them in the runtime editor config with the actual horizontal fabric
// face. Front and Back use the same printable geometry.
if(Number(P.id||P.productId||P.product_id)===420){
  const cfg420=OPT.editor_config||OPT.editorConfig||{};
  if(cfg420.enabled && cfg420.mode==='print_area' && !(Array.isArray(cfg420.printAreas) && cfg420.printAreas.some(a=>a && (Number(a.leftPct)!==0 || Number(a.topPct)!==0 || Number(a.widthPct)!==100 || Number(a.heightPct)!==100)))){
    const oldAreas=Array.isArray(cfg420.printAreas)?cfg420.printAreas:[];
    const surfaces420=zvAdminSurfaces();
    const mk=(src,idx)=>({
      ...(src||{}),
      surfaceId:(src&&src.surfaceId)||surfaces420[idx]?.id||surfaces420[0]?.id||null,
      leftPct:13.7,
      topPct:43.85,
      widthPct:61.88,
      heightPct:12.0
    });
    const count=Math.max(2,oldAreas.length,surfaces420.length);
    cfg420.printAreas=Array.from({length:count},(_,i)=>mk(oldAreas[i]||oldAreas[0],i));
  }
}
let designId=window.EXISTING_DESIGN?.id||null;
const canvas=new fabric.Canvas('designCanvas',{preserveObjectStacking:true,selection:true,subTargetCheck:true});window.designCanvas=canvas;if(window.ZenImageTools)ZenImageTools.attach(canvas,{lockBackgroundAfterEdit:false});
let pages=[],activePage=0,history=[],historyIndex=-1,loading=false,gridVisible=false,guidesVisible=false,saveTimer=null;
let printedTextReplaceMode=false, printedTextStart=null, printedTextPreview=null;
const $=id=>document.getElementById(id),uid=()=>"o"+Math.random().toString(36).slice(2,10),clone=o=>JSON.parse(JSON.stringify(o));

// ZENVIBE PHYSICAL RULER V3 — ADMIN DRIVEN, INCHES ONLY
let zvCurrentZoom=1;

function zvFmtMeasure(v){
  const n=Math.round(Number(v)*1000)/1000;
  return Number.isInteger(n)?String(n):String(n).replace(/0+$/,'').replace(/\.$/,'');
}

function zvRulerStep(span, pxLen){
  // ZenVibe-style adaptive physical ruler. The ruler always represents the
  // Admin-configured inch span; zoom only changes pixel spacing, never units.
  span=Number(span)||0;
  pxLen=Math.max(1,Number(pxLen)||1);
  if(span<=0)return {major:1,minor:.25};

  // Product-sized workspaces (including keychain 9 x 10) use a true 1-inch
  // labelled ruler like the production editor, with quarter-inch minor ticks.
  if(span<=12)return {major:1,minor:.25};

  // Aim for a readable major label about every 55-85 screen pixels.
  const targetMajor=span/Math.max(1,Math.floor(pxLen/70));
  const pow=Math.pow(10,Math.floor(Math.log10(Math.max(targetMajor,0.000001))));
  const normalized=targetMajor/pow;
  let nice;
  if(normalized<=1) nice=1;
  else if(normalized<=2) nice=2;
  else if(normalized<=5) nice=5;
  else nice=10;
  const major=nice*pow;

  // Five subdivisions per major interval gives familiar print-layout ticks.
  let minor=major/5;
  if(span<=12) minor=Math.max(.125,minor);
  return {major,minor};
}
function zvNearlyMultiple(value,step){
  if(!step)return false;
  return Math.abs(value/step-Math.round(value/step))<0.0001;
}

function zvDrawOneRuler(el,physical,canvasPx,vertical){
  physical=Number(physical)||0;
  if(!el)return;
  el.innerHTML='';
  if(physical<=0){
    el.dataset.empty='1';
    return;
  }
  delete el.dataset.empty;

  const pxLen=canvasPx*zvCurrentZoom;
  if(vertical) el.style.height=pxLen+'px';
  else el.style.width=pxLen+'px';

  const step=zvRulerStep(physical,pxLen);
  // On narrow screens, suppress labels that would overlap the next label or
  // the physical endpoint. Tick positions still represent the true inch scale.
  const mobileRuler=window.matchMedia('(max-width:767px)').matches;
  const minLabelGap=mobileRuler?64:42;
  let lastLabelPosition=-Infinity;
  const count=Math.floor(physical/step.minor+0.0001);

  for(let i=0;i<=count;i++){
    const value=i*step.minor;
    if(value>=physical-0.0001) break;
    const pos=(value/physical)*pxLen;
    const major=zvNearlyMultiple(value,step.major);

    const tick=document.createElement('span');
    tick.style.position='absolute';
    tick.style.background='#8b98aa';
    tick.style.pointerEvents='none';

    if(vertical){
      tick.style.left='0';
      tick.style.top=pos+'px';
      tick.style.width=(major?'12':'6')+'px';
      tick.style.height='1px';
    }else{
      tick.style.top='0';
      tick.style.left=pos+'px';
      tick.style.height=(major?'12':'6')+'px';
      tick.style.width='1px';
    }
    el.appendChild(tick);

    if(major && (!mobileRuler || (pos-lastLabelPosition>=minLabelGap && pos<pxLen-(mobileRuler?42:0)))){
      lastLabelPosition=pos;
      const label=document.createElement('span');
      label.textContent=value===0?'0 in':zvFmtMeasure(value);
      label.style.position='absolute';
      label.style.font='11px Inter,Arial,sans-serif';
      label.style.color='#667085';
      label.style.whiteSpace='nowrap';
      label.style.pointerEvents='none';

      if(vertical){
        label.style.left='15px';
        label.style.top=(pos-6)+'px';
        label.style.transform='rotate(90deg)';
        label.style.transformOrigin='left top';
      }else{
        label.style.left=(pos+3)+'px';
        label.style.top='14px';
      }
      el.appendChild(label);
    }
  }

  // Always show the exact Admin-configured endpoint. This is important for
  // non-round print sizes such as 117 × 80 and 233 × 80 inches.
  if(true){
    const pos=pxLen;
    const tick=document.createElement('span');
    tick.style.position='absolute';
    tick.style.background='#667085';

    if(vertical){
      tick.style.left='0'; tick.style.top=pos+'px';
      tick.style.width='14px'; tick.style.height='1px';
    }else{
      tick.style.top='0'; tick.style.left=pos+'px';
      tick.style.height='14px'; tick.style.width='1px';
    }
    el.appendChild(tick);

    const label=document.createElement('span');
    label.textContent=zvFmtMeasure(physical);
    label.style.position='absolute';
    label.style.font='600 11px Inter,Arial,sans-serif';
    label.style.color='#475467';

    if(vertical){
      label.style.left='15px';
      label.style.top=(pos-6)+'px';
      label.style.transform='rotate(90deg)';
      label.style.transformOrigin='left top';
    }else{
      label.style.right=mobileRuler?'2px':'0';
      label.style.top='14px';
      if(mobileRuler){
        label.style.background='#fff';
        label.style.padding='0 2px';
        label.style.fontSize='10px';
      }
    }
    el.appendChild(label);
  }
}

function zvRenderPhysicalRulers(){
  const d=zvPhysicalForPage(activePage||0);
  const hr=document.getElementById('horizontalRuler');
  const vr=document.getElementById('verticalRuler');
  const stage=document.querySelector('.canvas-stage');
  const canvasEl=canvas.upperCanvasEl||canvas.lowerCanvasEl;

  if(!hr||!vr||!stage||!canvasEl)return;

  const sr=stage.getBoundingClientRect();
  const cr=canvasEl.getBoundingClientRect();
  const canvasLeft=cr.left-sr.left;
  const canvasTop=cr.top-sr.top;
  const z=Math.max(.0001,Number(zvCurrentZoom)||canvas.getZoom()||1);

  // Name Badge uses a 10 x 10 in production workspace. Its ruler belongs to
  // that workspace (as in the reference), while cut/safe guides belong only to
  // the small badge body in the centre.

  // Normal products measure the complete configured artboard. Car freshener
  // product 419 is a die-cut product: its 4 x 4 in ruler belongs to the selected
  // physical freshener body, not to the surrounding square editor workspace.
  let left=canvasLeft;
  let top=canvasTop;
  let renderedW=cr.width;
  let renderedH=cr.height;
  if(Number(P.id)===419){
    const body=canvas.getObjects().find(o=>o&&o.zvProductMockup&&o.name==='Locked freshener shape');
    if(body){
      body.setCoords();
      const box=body.getBoundingRect(true,true);
      left=canvasLeft+(box.left*z);
      top=canvasTop+(box.top*z);
      renderedW=Math.max(1,box.width*z);
      renderedH=Math.max(1,box.height*z);
    }
  }

  Object.assign(hr.style,{
    position:'absolute',
    left:left+'px',
    top:Math.max(0,top-28)+'px',
    width:renderedW+'px',
    height:'28px'
  });
  Object.assign(vr.style,{
    position:'absolute',
    left:Math.max(0,left-28)+'px',
    top:top+'px',
    width:'28px',
    height:renderedH+'px'
  });

  // The labels remain the Admin physical dimensions (inches); only their screen
  // position/length follows the die-cut body for product 419.
  zvDrawOneRuler(hr,d.width,renderedW/z,false);
  zvDrawOneRuler(vr,d.height,renderedH/z,true);

  const label=document.getElementById('zvArtboardSizeLabel');
  if(label){
    const cfg=OPT.editor_config||OPT.editorConfig||{};
    label.textContent=d.width&&d.height
      ? `${zvFmtMeasure(d.width)} × ${zvFmtMeasure(d.height)} in`
      : (cfg.enabled ? 'Set workspace width/height (in) in Admin' : 'Set print width/height (in) in Admin');
  }
}

window.getZenVibeActiveSurface=()=>zvPhysicalForPage(activePage||0).surface;
window.getZenVibePhysicalSize=()=>zvPhysicalForPage(activePage||0);
window.ZV_RENDER_PHYSICAL_RULERS=zvRenderPhysicalRulers;
window.addEventListener('zenvibe:zoom',e=>{
  zvCurrentZoom=Number(e.detail?.zoom)||1;
  requestAnimationFrame(zvRenderPhysicalRulers);
});
document.addEventListener('DOMContentLoaded',()=>requestAnimationFrame(zvRenderPhysicalRulers));

function csrf(){return document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1]||''}
function newPage(){return{background:'#ffffff',objects:[]}}
function normalize(t){
  let out;
  if(t?.pages?.length) out=clone(t.pages);
  else if(t?.objects) out=[{background:t.background||'#fff',objects:clone(t.objects)}];
  else out=[newPage()];

  // Admin Print Surfaces are the source of truth for page count, order, labels and rulers.
  // Never collapse a 2/7/etc-page product because an older PRODUCT payload only exposed one page.
  const surfaces=zvAdminSurfaces();
  if(surfaces.length){
    // Product 420 is physically two-sided (Front + Back). Older admin data can
    // contain only one surface row, so never collapse a two-page template to 1/1.
    const isCarKeychain=Number(P.id)===420;
    // Keep every existing template page even when admin has fewer print surfaces.
    // A partial/legacy surface configuration must never discard customer artwork.
    const wanted=Math.max(out.length, surfaces.length, isCarKeychain?2:1);
    while(out.length<wanted) out.push(newPage());
    out.forEach((page,i)=>{
      // Never apply the first surface's dimensions to unrelated later pages.
      const surface=surfaces[i]||{};
      page.name=isCarKeychain?(i===0?'Front':'Back'):(surface.label||page.name||('Page '+(i+1)));
      page.printWidth=Number(surface.printWidth||surface.print_width_in||0)||undefined;
      page.printHeight=Number(surface.printHeight||surface.print_height_in||0)||undefined;
    });
  } else {
    // Legacy fallback for old Full Back Wall templates.
    const isBackWall=String(P?.name||'').toLowerCase().includes('full back wall');
    if(isBackWall && Number(t?.pageCount||0)===2){
      while(out.length<2) out.push(newPage());
      out=out.slice(0,2);
      out[0].name=out[0].name||'Inside Back Wall';
      out[1].name=out[1].name||'Outside Back Wall';
    }
  }
  return out;
}
pages=clone(normalize(window.INITIAL_TEMPLATE||{}));
// The published master is the authoritative source of existing page artwork.
// Keep its complete page array intact; never replace it with generated pages.
const zvPublishedPages=Array.isArray(window.INITIAL_TEMPLATE?.pages)
  ? clone(window.INITIAL_TEMPLATE.pages) : [];
if(zvPublishedPages.length>pages.length){
  pages=zvPublishedPages;
}
window.ZV_LOADED_PAGE_COUNT=pages.length;

// ZENVIBE UNIVERSAL EDITABLE MASTER V1
// Product catalogue PNG/JPG/WEBP is NOT design artwork. It is shown only when an
// editable template explicitly opts into a locked product-reference layer.
function zvSelectedColorKey(){
  const q=new URLSearchParams(location.search);
  return String(window.ZV_SELECTED_COLOR_KEY||q.get('color')||window.PRODUCT_OPTIONS?.selected_color_key||window.PRODUCT_OPTIONS?.selected_color||'');
}
function zvProductImageCandidates(){
  const out=[]; const add=u=>{u=String(u||'').trim();if(u&&!out.includes(u))out.push(u)};
  const key=zvSelectedColorKey().toLowerCase();
  const colors=Array.isArray(window.PRODUCT_OPTIONS?.colors)?window.PRODUCT_OPTIONS.colors:[];
  const c=colors.find(x=>String(x.color_key||x.key||x.slug||x.name||'').toLowerCase()===key);
  if(c){add(c.image_url||c.imageUrl||c.image);(c.image_urls||[]).forEach(add)}
  // Admin-driven restricted editors must use the dedicated clean/front-facing
  // reference, not the tilted storefront/marketing Product.image.
  const cfg=window.PRODUCT_OPTIONS?.editor_config||window.PRODUCT_OPTIONS?.editorConfig||{};
  if(cfg.enabled && cfg.mode==='print_area'){
    // Dedicated editor reference first; storefront image is only a fallback.
    const refs=Array.isArray(cfg.referenceImages)?cfg.referenceImages:[];
    refs.forEach(r=>add(r&&r.url));
    add(window.PRODUCT_OPTIONS?.base_image_url||window.PRODUCT_OPTIONS?.baseImageUrl);
  }
  add(window.PRODUCT?.imageUrl);add(window.PRODUCT?.image_url);add(window.PRODUCT?.image);
  (Array.isArray(window.PRODUCT_IMAGE_URLS)?window.PRODUCT_IMAGE_URLS:[]).forEach(add);
  return out;
}
// Golf ball uses the real 1.68 in physical ruler, but its editable artwork
// must be fitted into the configured logo patch on the ball rather than left at
// generic full-artboard template coordinates.
function zvGolfBallPrintBounds(){
  const cfg=OPT.editor_config||OPT.editorConfig||{};
  const a=Array.isArray(cfg.printAreas)&&cfg.printAreas.length?cfg.printAreas[0]:null;
  if(a){
    return {
      left:W*Number(a.leftPct||0)/100,
      top:H*Number(a.topPct||0)/100,
      right:W*(Number(a.leftPct||0)+Number(a.widthPct||0))/100,
      bottom:H*(Number(a.topPct||0)+Number(a.heightPct||0))/100
    };
  }
  return {left:W*.30,top:H*.31,right:W*.70,bottom:H*.69};
}
function zvFitGolfBallArtwork(){
  if((typeof familyName==='undefined'||familyName!=='golf-ball') && !String(P?.name||'').toLowerCase().includes('golf ball'))return false;
  const b=zvGolfBallPrintBounds();
  const objects=canvas.getObjects().filter(o=>o&&!o.zvProductMockup&&!o.zvPrintAreaGuide&&!o.excludeFromExport);
  if(!objects.length)return false;
  objects.forEach(o=>{o.clipPath=null;o.dirty=true;});
  // New golf-ball masters are authored around the centre 40% x 34% region.
  // Fit their combined bounds into the real admin print area with padding.
  const group=new fabric.ActiveSelection(objects,{canvas});
  group.setCoords();
  const box=group.getBoundingRect(true,true);
  const tw=(b.right-b.left)*.82, th=(b.bottom-b.top)*.82;
  const scale=Math.min(tw/Math.max(1,box.width),th/Math.max(1,box.height),1.6);
  const targetCx=(b.left+b.right)/2,targetCy=(b.top+b.bottom)/2;
  const srcCx=box.left+box.width/2,srcCy=box.top+box.height/2;
  objects.forEach(o=>{
    const ox=(Number(o.left)||0)-srcCx, oy=(Number(o.top)||0)-srcCy;
    o.set({
      left:targetCx+ox*scale,
      top:targetCy+oy*scale,
      scaleX:(Number(o.scaleX)||1)*scale,
      scaleY:(Number(o.scaleY)||1)*scale
    });
    o.setCoords();o.dirty=true;
  });
  canvas.discardActiveObject();
  return true;
}
// Product 427 — Custom Name Badge. The 10 x 10 ruler is the workspace;
// the badge is a locked product body and templates remain editable on its front face.
function zvBadgeColor(){
  const key=String(window.PRODUCT_OPTIONS?.badgeColor||new URLSearchParams(location.search).get('color')||'blue').toLowerCase();
  return ({red:'#BE2D2A',blue:'#2417B8',green:'#00B93B',pink:'#F25AA8',purple:'#6D28B7'})[key]||'#2417B8';
}
function zvBadgeBounds(){
  // Match the production 10 x 10 workspace: the badge is intentionally small
  // and sits slightly right/below centre. Front and back overlap diagonally.
  // Match Zenvibe.ca's 10 x 10 view: front badge is roughly 3.5 in diameter,
  // centred slightly right/below the workspace centre.
  const s=Math.min(W,H)*.35,cx=W*.625,cy=H*.565;
  return {left:cx-s/2,top:cy-s/2,right:cx+s/2,bottom:cy+s/2,cx,cy,s};
}
function zvBadgePrintBounds(){
  // The editable/safe region is the small square shown on the FRONT badge.
  const b=zvBadgeBounds(), inset=b.s*.055;
  return {left:b.left+inset,top:b.top+inset,right:b.right-inset,bottom:b.bottom-inset};
}
function zvFitBadgeTemplateToFront(){
  if(Number(P.id)!==427)return false;
  const b=zvBadgeBounds();
  const objects=canvas.getObjects().filter(o=>o&&!o.zvProductMockup&&!o.zvBadgeGuide&&!o.zvPrintAreaGuide&&!o.excludeFromExport);
  if(!objects.length)return false;
  // Seeded badge templates use a 1000 x 1000 reference workspace and place
  // their artwork around the old front centre (585,525). Translate/scale that
  // artwork onto the ACTUAL front badge. Do not move the badge to the template.
  const src={cx:585,cy:525,s:410};
  const target=b.s*.78, scale=target/src.s;
  objects.forEach(o=>{
    if(!o._zvBadgeCanonical){
      o._zvBadgeCanonical={left:Number(o.left)||0,top:Number(o.top)||0,scaleX:Number(o.scaleX)||1,scaleY:Number(o.scaleY)||1};
    }
    const g=o._zvBadgeCanonical;
    o.set({
      left:b.cx+(g.left-src.cx)*scale,
      top:b.cy+(g.top-src.cy)*scale,
      scaleX:g.scaleX*scale,
      scaleY:g.scaleY*scale
    });
    o.setCoords();o.dirty=true;
  });
  return true;
}
function zvRefreshBadgeBody(){
  if(Number(P.id)!==427)return false;
  zvRemoveProductMockup();
  canvas.getObjects().filter(o=>o&&(o.zvBadgeGuide||o.zvPrintAreaGuide)).forEach(o=>canvas.remove(o));
  // Remove the generic full-workspace guide before drawing badge-local guides.
  canvas.getObjects().filter(o=>o&&o.excludeFromExport&&!o.zvProductMockup&&
    (o.name==='Print area'||o.name==='Safe zone'||o.name==='Bleed')).forEach(o=>canvas.remove(o));
  const b=zvBadgeBounds(), r=b.s/2;
  // Zenvibe reference: the silver pin/back plate sits behind the coloured
  // printable face. Keep only a small upper-left rim visible instead of
  // placing two separate circles side-by-side.
  // Reference has the silver backing mostly hidden behind the front badge:
  // only the upper-left crescent/rim should remain visible.
  const back=new fabric.Circle({left:b.left-r*.58,top:b.top-r*.62,radius:r*.92,fill:'#E7E7E7',stroke:'#2f5fc4',strokeWidth:Math.max(2,b.s*.018),selectable:false,evented:false,excludeFromExport:true,customerEditable:false,zvProductMockup:true,name:'Badge back'});
  const front=new fabric.Circle({left:b.left,top:b.top,radius:r,fill:zvBadgeColor(),stroke:'#A9AFB8',strokeWidth:Math.max(2,b.s*.012),selectable:false,evented:false,excludeFromExport:true,customerEditable:false,zvProductMockup:true,name:'Badge front'});
  // Keep the silver plate behind the coloured printable face.
  // sendToBack(front) used to reverse the intended visual order.
  canvas.add(back);canvas.sendToBack(back);
  canvas.add(front);canvas.bringToFront(front);
  // Match the source editor: rectangular cut/safe guides surround the round
  // badge face. They are intentionally local to the badge, never the 10 x 10 workspace.
  const pb=zvBadgePrintBounds(), pad=b.s*.035;
  const cutGuide=new fabric.Rect({left:b.left-pad,top:b.top-pad,width:b.s+pad*2,height:b.s+pad*2,fill:'rgba(0,0,0,0)',stroke:'#344054',strokeWidth:Math.max(1,b.s*.004),strokeDashArray:[5,4],selectable:false,evented:false,excludeFromExport:true,customerEditable:false,zvPrintAreaGuide:true,zvBadgeGuide:true,name:'Badge cut line'});
  const bleedGuide=new fabric.Rect({left:b.left,top:b.top,width:b.s,height:b.s,fill:'rgba(0,0,0,0)',stroke:'#ef4444',strokeWidth:Math.max(1,b.s*.004),selectable:false,evented:false,excludeFromExport:true,customerEditable:false,zvPrintAreaGuide:true,zvBadgeGuide:true,name:'Badge bleed'});
  const safeGuide=new fabric.Rect({left:pb.left,top:pb.top,width:pb.right-pb.left,height:pb.bottom-pb.top,fill:'rgba(0,0,0,0)',stroke:'#22b35b',strokeWidth:Math.max(1,b.s*.004),selectable:false,evented:false,excludeFromExport:true,customerEditable:false,zvPrintAreaGuide:true,zvBadgeGuide:true,name:'Badge safe zone'});
  canvas.add(cutGuide);canvas.add(bleedGuide);canvas.add(safeGuide);
  canvas.bringToFront(cutGuide);canvas.bringToFront(bleedGuide);canvas.bringToFront(safeGuide);
  // Template follows the coloured FRONT badge; the silver back is only a
  // locked product reference and never receives customer artwork.
  zvFitBadgeTemplateToFront();
  canvas.getObjects().forEach(o=>{
    if(!o||o.zvProductMockup||o.zvBadgeGuide||o.zvPrintAreaGuide||o.excludeFromExport)return;
    o.clipPath=new fabric.Circle({absolutePositioned:true,left:b.left,top:b.top,radius:r,selectable:false,evented:false});o.dirty=true;
  });
  canvas.requestRenderAll();return true;
}
if(Number(P.id)===427){document.addEventListener('zenvibe:badge-color-change',()=>zvRefreshBadgeBody());}

// Mouse-pad shape is a physical cut only. Rectangle and Round share the
// exact same DesignTemplate IDs, so switching shape never reloads/replaces artwork.
function zvMousePadShape(){
  const value=String(window.PRODUCT_OPTIONS?.mousepadShape||new URLSearchParams(location.search).get('shape')||'rectangle').toLowerCase();
  return value==='round'?'round':'rectangle';
}
function zvApplyMousePadShape(){
  if(Number(P.id)!==426)return false;
  const round=zvMousePadShape()==='round';
  // Rectangle and Round share one template record, but Round must adapt the
  // complete composition to the circular printable surface rather than merely
  // hiding the rectangle's corners.  Fit the original composition into the
  // largest centred square, then apply a true circular clip.
  const objects=canvas.getObjects().filter(o=>o&&!o.zvProductMockup&&!o.zvPrintAreaGuide&&!o.excludeFromExport);
  objects.forEach(o=>{
    // Restore canonical rectangle-template geometry before applying either
    // shape. This makes repeated Rectangle <-> Round switching lossless.
    if(o._zvMousePadRect){
      const g=o._zvMousePadRect;
      o.set({left:g.left,top:g.top,scaleX:g.scaleX,scaleY:g.scaleY});
    }else{
      o._zvMousePadRect={left:Number(o.left)||0,top:Number(o.top)||0,scaleX:Number(o.scaleX)||1,scaleY:Number(o.scaleY)||1};
    }
    if(round){
      const g=o._zvMousePadRect;
      const side=Math.min(W,H), ox=(W-side)/2, oy=(H-side)/2;
      const sx=side/W, sy=side/H;
      o.set({
        left:ox+g.left*sx,
        top:oy+g.top*sy,
        scaleX:g.scaleX*sx,
        scaleY:g.scaleY*sy
      });
      o.clipPath=new fabric.Circle({
        absolutePositioned:true,left:W/2,top:H/2,originX:'center',originY:'center',
        radius:side/2,selectable:false,evented:false
      });
    }else{
      o.clipPath=null;
    }
    o.setCoords();
    o.dirty=true;
  });
  // Show the actual mouse-pad cut edge. Previously only the artwork was
  // clipped, so on a white/light template the round edge disappeared into the
  // white editor canvas. This guide is editor-only and is never exported.
  canvas.getObjects().filter(o=>o&&o.zvMousePadShapeGuide).forEach(o=>canvas.remove(o));
  if(round){
    const side=Math.min(W,H), ox=(W-side)/2, oy=(H-side)/2;
    const edge=new fabric.Circle({
      left:ox,top:oy,radius:side/2,
      fill:'rgba(0,0,0,0)',stroke:'#667085',
      strokeWidth:Math.max(2,side*.004),
      selectable:false,evented:false,excludeFromExport:true,
      customerEditable:false,zvMousePadShapeGuide:true,
      name:'Round mouse pad cut line'
    });
    canvas.add(edge);
    canvas.bringToFront(edge);
  }
  const wrap=document.getElementById('canvasWrap');
  if(wrap)wrap.dataset.mousepadShape=round?'round':'rectangle';
  canvas.requestRenderAll();
  return true;
}
if(Number(P.id)===426){
  document.addEventListener('zenvibe:mousepad-shape-change',()=>zvApplyMousePadShape());
}
// Freshener-only locked die-cut reference. Never clip the source product photo:
 // each option is a clean physical silhouette below the editable customer artwork.
function zvFreshenerShape(){
  const value=String(window.PRODUCT_OPTIONS?.shape||new URLSearchParams(location.search).get('shape')||'round').toLowerCase();
  const valid=['square','round','rounded-square','diamond','hexagon','octagon','ticket','badge','clover','butterfly','scallop','flower','star','heart','burst','seal','shield','triangle'];
  return valid.includes(value)?value:'round';
}
function zvFreshenerReference(){
  const s=Math.min(W,H)*.72,cx=W/2,cy=H/2+H*.015,shape=zvFreshenerShape();
  const common={left:cx,top:cy,originX:'center',originY:'center',fill:'#F2E2C5',stroke:'#C99B61',strokeWidth:Math.max(2,s*.012),
    selectable:false,evented:false,hasControls:false,hasBorders:false,customerEditable:false,excludeFromExport:true,zvProductMockup:true,name:'Locked freshener shape'};
  const poly=(count,r=s*.40,rotation=-Math.PI/2)=>{const p=[];for(let i=0;i<count;i++){const a=rotation+i*Math.PI*2/count;p.push({x:Math.cos(a)*r,y:Math.sin(a)*r});}return new fabric.Polygon(p,{...common});};
  let body;
  if(shape==='round') body=new fabric.Circle({...common,radius:s*.40});
  else if(shape==='square') body=new fabric.Rect({...common,width:s*.70,height:s*.70});
  else if(shape==='rounded-square') body=new fabric.Rect({...common,width:s*.70,height:s*.70,rx:s*.07,ry:s*.07});
  else if(shape==='diamond') body=new fabric.Rect({...common,width:s*.58,height:s*.58,rx:s*.04,ry:s*.04,angle:45});
  else if(shape==='hexagon') body=poly(6);
  else if(shape==='octagon') body=poly(8);
  else if(shape==='triangle') body=poly(3,s*.42,-Math.PI/2);
  else if(shape==='star'||shape==='burst'){
    const pts=[],spikes=shape==='star'?5:8;for(let i=0;i<spikes*2;i++){const an=-Math.PI/2+i*Math.PI/spikes,r=i%2?s*(shape==='star'?.19:.28):s*.42;pts.push({x:Math.cos(an)*r,y:Math.sin(an)*r});}body=new fabric.Polygon(pts,{...common});
  }else if(shape==='heart') body=new fabric.Path('M 0 -30 C -55 -92 -128 -10 0 96 C 128 -10 55 -92 0 -30 Z',{...common,scaleX:s/250,scaleY:s/205});
  else if(shape==='shield') body=new fabric.Path('M -90 -80 L 90 -80 L 90 20 Q 70 80 0 110 Q -70 80 -90 20 Z',{...common,scaleX:s/220,scaleY:s/220});
  else if(shape==='ticket') body=new fabric.Path('M -95 -80 L 95 -80 L 95 -60 Q 70 -45 95 -30 L 95 80 L -95 80 L -95 30 Q -70 15 -95 0 Z',{...common,scaleX:s/220,scaleY:s/200});
  else if(shape==='badge') body=new fabric.Path('M -85 -70 Q -45 -95 0 -72 Q 45 -95 85 -70 L 85 70 Q 45 95 0 72 Q -45 95 -85 70 Z',{...common,scaleX:s/210,scaleY:s/210});
  else {
    const lobes=shape==='butterfly'?4:(shape==='clover'?4:(shape==='flower'?6:(shape==='scallop'?10:12))),pts=[];
    for(let i=0;i<lobes*12;i++){const a=i*Math.PI*2/(lobes*12),r=s*(.34+.065*Math.cos(lobes*a));pts.push({x:Math.cos(a)*r,y:Math.sin(a)*r});}
    body=new fabric.Polygon(pts,{...common});
  }
  const hole=new fabric.Circle({...common,left:cx,top:cy-s*.30,radius:s*.027,fill:'#FFFFFF',stroke:'#B88952',strokeWidth:Math.max(1,s*.007)});
  const string=new fabric.Line([cx,Math.max(8,cy-s*.52),cx,cy-s*.327],{stroke:'#B8B8B8',strokeWidth:Math.max(2,s*.008),selectable:false,evented:false,excludeFromExport:true,zvProductMockup:true,name:'Freshener string'});
  return [string,body,hole];
}
function zvRefreshFreshenerShape(){
  if(Number(P.id)!==419)return false;

  // The selected option is the PHYSICAL freshener body, not a decoration
  // behind a rectangular template. Remove the old body and rebuild it first.
  zvRemoveProductMockup();
  const reference=zvFreshenerReference();
  reference.forEach(o=>canvas.add(o));
  canvas.getObjects().filter(o=>o.zvProductMockup).forEach(o=>canvas.sendToBack(o));

  // Clip every printable/template layer to the same physical die. This includes
  // locked master/background artwork; only editor-only guides/mockups are exempt.
  canvas.getObjects().forEach(o=>{
    if(!o||o.zvProductMockup||o.zvPrintAreaGuide)return;
    const clip=zvFreshenerReference()[1];
    clip.set({
      absolutePositioned:true,
      selectable:false,evented:false,
      excludeFromExport:false,zvProductMockup:false,
      left:W/2,top:H/2+H*.015,originX:'center',originY:'center'
    });
    o.clipPath=clip;
    o.dirty=true;
  });

  // Keep the hanging string and punched hole visible above the printed artwork.
  const refs=canvas.getObjects().filter(o=>o.zvProductMockup);
  refs.forEach(o=>{
    if(o.name==='Freshener string'||o.name==='Locked freshener shape')canvas.sendToBack(o);
  });
  refs.forEach(o=>{
    if(o.name!=='Freshener string'&&o.name!=='Locked freshener shape')canvas.bringToFront(o);
  });
  canvas.requestRenderAll();
  // Shape changes also change the physical ruler's on-screen bounds.
  requestAnimationFrame(()=>requestAnimationFrame(zvRenderPhysicalRulers));
  return true;
}
if(Number(P.id)===419){
  document.addEventListener('zenvibe:freshener-option-change',e=>{
    if(e.detail?.key==='shape')zvRefreshFreshenerShape();
  });
}
function zvRemoveProductMockup(){
  canvas.getObjects().filter(o=>o.zvProductMockup).forEach(o=>canvas.remove(o))}
function zvTemplateWantsProductMockup(){
  const cfg=window.PRODUCT_OPTIONS?.editor_config||window.PRODUCT_OPTIONS?.editorConfig||{};
  // Awards always need the physical product image under editable artwork.
  // Older server DB rows may still have show_product_reference=False.
  const categoryText=[P?.category,P?.categorySlug,P?.parentCategory,OPT?.category]
    .map(v=>String(v||'').toLowerCase()).join(' ');
  const isAward=/(award|troph|medal|plaque)/.test(categoryText);
  if(isAward && (OPT.base_image_url||OPT.baseImageUrl||P?.imageUrl)) return true;
  if(cfg.enabled) return cfg.showProductReference===true;
  const root=window.INITIAL_TEMPLATE||{};
  const page=(root.pages||[])[activePage]||{};
  return root.showProductMockup===true || root.show_product_mockup===true ||
         page.showProductMockup===true || page.show_product_mockup===true;
}
function zvKeychainColor(){
  const key=String(window.PRODUCT_OPTIONS?.keychainColor||new URLSearchParams(location.search).get('color')||'red');
  return ({red:'#ed1111','light-blue':'#45a8c9',blue:'#1761c9',black:'#111111',orange:'#f45b35',green:'#237d08',purple:'#6b00a8',yellow:'#fff000'})[key]||'#ed1111';
}
function zvRefreshKeychainBody(){
  if(Number(P.id)!==420)return false;
  zvRemoveProductMockup();
  // Reference proportions follow the real fabric loop keychain: long narrow strap
  // with a short black connector and metal ring/clip at the right. It is an
  // editor-only physical reference; customer artwork remains independent/editable.
  // 9 x 10 in is the surrounding editor workspace, NOT the product size.
  // Match the real keychain reference: a long ~1.5 in high fabric strap centred
  // inside the 9 x 10 workspace, with connector/hardware outside the print face.
  const bodyW=W*.68, bodyH=H*.15, left=W*.12, top=(H-bodyH)/2;
  const strap=new fabric.Rect({left,top,width:bodyW,height:bodyH,rx:bodyH*.06,ry:bodyH*.06,fill:zvKeychainColor(),stroke:'#25232b',strokeWidth:Math.max(2,H*.006),selectable:false,evented:false,customerEditable:false,excludeFromExport:true,zvProductMockup:true,name:'Locked keychain strap'});
  const connectorW=W*.055;
  const connector=new fabric.Rect({left:left+bodyW*.965,top:top+bodyH*.08,width:connectorW,height:bodyH*.84,rx:bodyH*.07,ry:bodyH*.07,fill:'#242126',stroke:'#111',strokeWidth:Math.max(1,H*.004),selectable:false,evented:false,excludeFromExport:true,zvProductMockup:true,name:'Locked keychain connector'});
  const ringR=bodyH*.22;
  const ring=new fabric.Circle({left:left+bodyW+connectorW+W*.018,top:top+(bodyH/2)-ringR,radius:ringR,fill:'rgba(0,0,0,0)',stroke:'#333238',strokeWidth:Math.max(2,H*.006),selectable:false,evented:false,excludeFromExport:true,zvProductMockup:true,name:'Locked keychain ring'});
  [strap,connector,ring].forEach(o=>canvas.add(o));
  [ring,connector,strap].forEach(o=>canvas.sendToBack(o));

  // Product 420 owns its print-area guide because the Admin percentages belong
  // to the legacy 3.5 x 1.5 artboard. Draw the guide directly over the strap.
  canvas.getObjects().filter(o=>o&&o.zvPrintAreaGuide).forEach(o=>canvas.remove(o));
  const pb=zvKeychainPrintBounds();
  const guide=new fabric.Rect({
    left:pb.left,top:pb.top,width:pb.right-pb.left,height:pb.bottom-pb.top,
    fill:'rgba(0,0,0,0)',stroke:'#22b35b',strokeWidth:Math.max(1,H*.003),
    strokeDashArray:[Math.max(5,W*.008),Math.max(4,W*.006)],
    selectable:false,evented:false,excludeFromExport:true,zvPrintAreaGuide:true,
    name:'Keychain print area'
  });
  canvas.add(guide);
  canvas.bringToFront(guide);

  // The printable face is the fabric strap itself. Clip all editable template
  // layers to the strap, just as the source product's green print box sits on it.
  canvas.getObjects().forEach(o=>{
    if(!o||o.zvProductMockup||o.zvPrintAreaGuide)return;
    o.clipPath=new fabric.Rect({absolutePositioned:true,left:left+bodyW*.025,top:top+bodyH*.10,width:bodyW*.91,height:bodyH*.80,rx:bodyH*.025,ry:bodyH*.025,selectable:false,evented:false});
    o.dirty=true;
  });
  canvas.bringToFront(guide);
  canvas.requestRenderAll();
  return true;
}
if(Number(P.id)===420){
  document.addEventListener('zenvibe:keychain-color-change',()=>zvRefreshKeychainBody());
}
// Product 416: editable artwork sits above an unbranded, locked vector mockup.
// Unlike the catalogue photo, this mockup contains NO preprinted logo.
function zvRefreshBottleOpener416(){
  if(Number(P.id)!==416)return false;
  zvRemoveProductMockup();
  const selected=String(window.PRODUCT_OPTIONS?.bottleColor||
    new URLSearchParams(location.search).get('color')||'red').toLowerCase();
  const paint={blue:'#2563eb',red:'#ef4444',white:'#e5e7eb',
    green:'#2f9e44',black:'#333333'}[selected]||'#ef4444';
  // Flat face matches 31.5%,43.8%,36%,8.5% of the editor canvas.
  const left=W*.315,top=H*.438,bw=W*.36,bh=H*.085;
  const common={selectable:false,evented:false,customerEditable:false,
    excludeFromExport:true,zvProductMockup:true};
  const body=new fabric.Rect({...common,left:left-W*.014,top:top-bh*.06,
    width:bw+W*.028,height:bh*1.22,rx:bh*.22,ry:bh*.22,
    fill:paint,stroke:'#737373',strokeWidth:Math.max(1,W*.0015),
    name:'Locked bottle opener body'});
  const rim=new fabric.Rect({...common,left,top,width:bw,height:bh,
    rx:bh*.12,ry:bh*.12,fill:paint,stroke:'rgba(255,255,255,.48)',
    strokeWidth:Math.max(1,W*.001),name:'Locked bottle opener printable face'});
  const lip=new fabric.Rect({...common,left:left-W*.015,top:top+bh*.88,
    width:bw*.18,height:bh*.35,rx:bh*.14,ry:bh*.14,
    fill:paint,stroke:'#666',strokeWidth:1,name:'Locked bottle opener lip'});
  const connector=new fabric.Rect({...common,left:left+bw+W*.004,
    top:top+bh*.28,width:W*.025,height:bh*.4,rx:bh*.1,ry:bh*.1,
    fill:'#777',name:'Locked bottle opener connector'});
  const ring=new fabric.Circle({...common,left:left+bw+W*.015,
    top:top-bh*.08,radius:bh*.64,fill:'rgba(0,0,0,0)',
    stroke:'#a3a3a3',strokeWidth:Math.max(3,W*.005),
    name:'Locked bottle opener key ring'});
  [ring,connector,lip,body,rim].forEach(o=>canvas.add(o));
  [ring,connector,lip,body,rim].forEach(o=>canvas.sendToBack(o));
  canvas.requestRenderAll();
  return true;
}
document.addEventListener('zenvibe:bottle-color-change',event=>{
  if(Number(P.id)!==416)return;
  window.PRODUCT_OPTIONS=window.PRODUCT_OPTIONS||{};
  window.PRODUCT_OPTIONS.bottleColor=event.detail?.color||'red';
  zvRefreshBottleOpener416();
});

// Round Lapel Pin (234): front-facing blank disc, not the catalogue photo
// showing both sides and permanently printed artwork.
function zvRefreshRoundLapelPin234(){
  if(Number(P.id)!==234)return false;
  zvRemoveProductMockup();
  const side=Math.min(W,H),radius=side*.43,cx=W/2,cy=H/2;
  const common={selectable:false,evented:false,customerEditable:false,
    zvProductMockup:true,excludeFromExport:true};
  const outer=new fabric.Circle({...common,left:cx-radius,top:cy-radius,
    radius,fill:'#f5c451',stroke:'#ad812e',strokeWidth:Math.max(3,side*.012),
    name:'Locked lapel pin metal rim'});
  const innerR=radius*.955;
  const inner=new fabric.Circle({...common,left:cx-innerR,top:cy-innerR,
    radius:innerR,fill:'#fff',stroke:'#e9c46a',strokeWidth:Math.max(2,side*.004),
    name:'Locked blank lapel pin front'});
  canvas.add(outer,inner);
  canvas.sendToBack(inner);canvas.sendToBack(outer);
  canvas.requestRenderAll();
  return true;
}
function zvLoadProductMockup(done){
  if(Number(P.id)===234){zvRefreshRoundLapelPin234();done?.(true);return;}

  if(Number(P.id)===416){zvRefreshBottleOpener416();done?.(true);return;}
  if(Number(P.id)===427){zvRefreshBadgeBody();done?.(true);return;}
  // Product 428 templates already contain the complete editable plate artwork.
  // Do not place a locked catalogue photo underneath/over them.
  if(Number(P.id)===428){zvRemoveProductMockup();done?.(true);return;}
  if(Number(P.id)===426){zvApplyMousePadShape();done?.(true);return;}
  if(Number(P.id)===419){zvRefreshFreshenerShape();done?.(true);return;}
  if(Number(P.id)===420){zvRefreshKeychainBody();done?.(true);return;}
  if(!zvTemplateWantsProductMockup()){zvRemoveProductMockup();done?.(true);return;}
  const isFlatBackWall=String(P?.name||'').toLowerCase().includes('full back wall');
  if(isFlatBackWall){zvRemoveProductMockup();done?.(true);return;}

  const cfg=OPT.editor_config||OPT.editorConfig||{};
  const category=String(P?.category||'').toLowerCase();
  const promoRefs=Array.isArray(cfg.referenceImages)?cfg.referenceImages.filter(x=>x&&x.url):[];
  const promoOnePage=cfg.referenceLayout==='single-page-front-back';

  // Promotional products use ONE locked product reference workspace. Do not
  // reinterpret gallery/lifestyle ProductImage rows as front/back editor sides.
  // If the source mockup itself contains front+back (as on Zenvibe), both remain
  // visible together as a single locked, non-printing reference.
  if(promoOnePage){
    const ref=promoRefs[0] || {url:(P.editor_reference_image||P.image||'')};
    if(ref.url){
      zvRemoveProductMockup();
      const rawUrl=String(ref.url);
      const refUrl=rawUrl+(rawUrl.includes('?')?'&':'?')+'zvref=3';

      const lockReference=(obj)=>{
        if(!obj) return false;
        const bw=Math.max(1,Number(obj.width||1));
        const bh=Math.max(1,Number(obj.height||1));
        const scale=Math.min((W*.94)/bw,(H*.90)/bh);
        obj.set({
          left:W/2,top:H/2,originX:'center',originY:'center',
          scaleX:scale,scaleY:scale,selectable:false,evented:false,
          hasControls:false,hasBorders:false,lockMovementX:true,lockMovementY:true,
          lockScalingX:true,lockScalingY:true,lockRotation:true,
          customerEditable:false,excludeFromExport:true,zvProductMockup:true,
          name:'Locked product reference'
        });
        obj.baseSrc=rawUrl;
        // Keep the locked product reference in Fabric's normal object stack.
        // It is marked excludeFromExport, but drawHelpers explicitly preserves
        // zvProductMockup objects. This avoids the Fabric backgroundImage reset
        // that occurred after canvas.clear() when switching ?template=...
        canvas.add(obj);
        canvas.sendToBack(obj);
        canvas.requestRenderAll();
        done?.(true);
        return true;
      };

      // Fabric's Image.fromURL is unreliable for SVG references in some browsers.
      // Load SVG as Fabric vector objects and group them; raster references still
      // use Image.fromURL. This makes the locked product silhouette deterministic.
      if(/\.svg(?:[?#]|$)/i.test(rawUrl) && typeof fabric.loadSVGFromURL==='function'){
        fabric.loadSVGFromURL(refUrl,(objects,options)=>{
          if(objects&&objects.length){
            const grouped=fabric.util.groupSVGElements(objects,options||{});
            if(lockReference(grouped)) return;
          }
          console.warn('ZenVibe: SVG product reference failed; trying image loader',rawUrl);
          fabric.Image.fromURL(refUrl,img=>{
            if(!img||!img.width||!img.height){loadFallback();return;}
            lockReference(img);
          },{crossOrigin:'anonymous'});
        });
      }else{
        fabric.Image.fromURL(refUrl,img=>{
          if(!img||!img.width||!img.height){console.warn('ZenVibe: locked reference failed',rawUrl);loadFallback();return;}
          lockReference(img);
        },{crossOrigin:'anonymous'});
      }
      return;
    }
  }

  function loadFallback(){
    const urls=zvProductImageCandidates(); let n=0;
    function next(){
      if(n>=urls.length){console.error('ZenVibe: no product image could be loaded',urls);done?.(false);return}
      const src=urls[n++];
      fabric.Image.fromURL(src,img=>{
        if(!img||!img.width||!img.height){next();return}
        zvRemoveProductMockup();
        const fitWhole=cfg.enabled && cfg.mode==='print_area';
        const referenceInset=fitWhole ? 0.94 : 0.88;
        const mode=String(P?.customizer_mode||P?.customizerMode||OPT?.customizer_mode||OPT?.customizerMode||'').toLowerCase();
        const isDrinkware=mode==='drinkware' || category==='drinkware';
        const isPen=mode==='pen' || category==='pens' || category==='pen';
        const productFill=(fitWhole && isPen) ? 1.18 : ((fitWhole && isDrinkware) ? 1.34 : 1);
        const scale=Math.min((W*referenceInset)/img.width,(H*referenceInset)/img.height)*productFill;
        img.set({left:W/2,top:H/2,originX:'center',originY:'center',scaleX:scale,scaleY:scale,
          selectable:false,evented:false,hasControls:false,hasBorders:false,lockMovementX:true,lockMovementY:true,
          lockScalingX:true,lockScalingY:true,lockRotation:true,customerEditable:false,excludeFromExport:true,zvProductMockup:true,
          name:'Locked product mockup'});
        img.baseSrc=src;canvas.add(img);canvas.sendToBack(img);canvas.requestRenderAll();done?.(true);
      },{crossOrigin:'anonymous'});
    }
    next();
  }
  loadFallback();
  return;
}
window.ZV_SET_PRODUCT_COLOUR=function(colorKey){window.ZV_SELECTED_COLOR_KEY=colorKey||'';zvLoadProductMockup()};

function setCanvasScale(percent){
  const wrap=$('canvasWrap');
  const scroll=document.querySelector('.studio-canvas-scroll');
  const stage=document.querySelector('.canvas-stage');

  const hostW=Math.max(320,scroll?.clientWidth||stage?.clientWidth||wrap?.parentElement?.clientWidth||950);
  const hostH=Math.max(280,scroll?.clientHeight||stage?.clientHeight||window.innerHeight-190);

  // Reserve only UI space required by rulers/padding. Product dimensions are never hardcoded.
  const padX=72;
  const padY=72;
  const fit=Math.min(
    Math.max(1,hostW-padX)/Math.max(1,W),
    Math.max(1,hostH-padY)/Math.max(1,H),
    1
  );
  const z=Math.max(.08,fit*(Math.max(10,Number(percent)||100)/100));

  const displayW=Math.max(1,Math.round(W*z));
  const displayH=Math.max(1,Math.round(H*z));

  canvas.setDimensions({width:displayW,height:displayH});
  canvas.setZoom(z);
  if(wrap){
    wrap.style.width=displayW+'px';
    wrap.style.height=displayH+'px';
  }
  canvas.calcOffset();
  canvas.requestRenderAll();

  window.dispatchEvent(new CustomEvent('zenvibe:zoom',{
    detail:{percent:Number(percent)||100,zoom:z,fit}
  }));
}
function isText(o){return o&&['i-text','textbox','text'].includes(o.type)}
function common(o){const asset=!!o.backgroundAsset;const exact=!!o.exactVisualMaster;/* V30: exact published master is visual source only; editable hotspots/layers sit above it. */const editable=(exact||asset)?false:o.customerEditable!==false;const locked=(exact||asset)?true:(!!o.locked||!editable);return{left:o.left??o.x??60,top:o.top??o.y??60,angle:o.angle||0,opacity:(o.opacity??1),fill:o.fill||'#111827',objectId:o.id||uid(),name:o.name||'',fieldType:o.fieldType||'',backgroundAsset:asset,exactVisualMaster:!!o.exactVisualMaster,customerEditable:editable,flipX:!!o.flipX,flipY:!!o.flipY,visible:o.visible!==false,selectable:editable,evented:editable,lockMovementX:locked,lockMovementY:locked,lockScalingX:locked,lockScalingY:locked,lockRotation:locked,hasControls:editable,originX:o.originX||'left',originY:o.originY||'top',ocrOverlayPending:!!o.ocrOverlayPending,sourceText:o.sourceText||'',autoOcrText:!!o.autoOcrText,ocrCoverFor:o.ocrCoverFor||'',sourceNormalizedBox:o.sourceNormalizedBox||null,_zvPendingArtwork:!!o._zvPendingArtwork,visualFallback:!!o.visualFallback,replacementGroupId:o.replacementGroupId||'',manualReplacement:!!o.manualReplacement,manualTextPatch:!!o.manualTextPatch}}
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
  const base={id:o.objectId||uid(),type:o.type==='i-text'?'text':o.type,left:o.left,top:o.top,angle:o.angle||0,opacity:o.opacity??1,fill:o.fill,flipX:!!o.flipX,flipY:!!o.flipY,visible:o.visible!==false,locked:!!o.lockMovementX,name:o.name||'',fieldType:o.fieldType||'',backgroundAsset:!!o.backgroundAsset,exactVisualMaster:!!o.exactVisualMaster,customerEditable:((o.backgroundAsset||o.exactVisualMaster)?false:o.customerEditable!==false),scaleX:o.scaleX,scaleY:o.scaleY,stroke:o.stroke,strokeWidth:o.strokeWidth,strokeDashArray:o.strokeDashArray,originX:o.originX||'left',originY:o.originY||'top',autoInvitationField:!!o.autoInvitationField,autoInvitationCover:!!o.autoInvitationCover,sourceNormalizedBox:o.sourceNormalizedBox||null,sourceConfidence:o.sourceConfidence??null,ocrOverlayPending:!!o.ocrOverlayPending,sourceText:o.sourceText||'',autoOcrText:!!o.autoOcrText,ocrCoverFor:o.ocrCoverFor||'',_zvPendingArtwork:!!o._zvPendingArtwork,visualFallback:!!o.visualFallback,manualReplacement:!!o.manualReplacement,manualTextPatch:!!o.manualTextPatch,replacementGroupId:o.replacementGroupId||'',adminTextEdited:!!o.adminTextEdited};
  if(isText(o)) return {...base,text:o.text,width:o.width,fontSize:o.fontSize,font:o.fontFamily,fontWeight:o.fontWeight,fontStyle:o.fontStyle,underline:o.underline,textAlign:o.textAlign,charSpacing:o.charSpacing,lineHeight:o.lineHeight};
  if(o.type==='image') return {...base,src:o.getSrc(),baseSrc:o.baseSrc||o.getSrc(),width:o.width,height:o.height,originalWidth:o.width,originalHeight:o.height,cropX:o.cropX||0,cropY:o.cropY||0,filters:(o.filters||[]).map(f=>f.toObject?f.toObject():f)};
  if(o.type==='polygon') return {...base,points:o.points,width:o.width,height:o.height};
  if(o.type==='line') return {...base,points:[o.x1,o.y1,o.x2,o.y2]};
  if(o.type==='path') return {...base,path:o.path,width:o.width,height:o.height};
  return {...base,width:o.width,height:o.height,radius:o.radius,rx:o.rx,ry:o.ry};
}
function sync(){
  if(loading)return;
  const oldPage=pages[activePage]||{};
  pages[activePage]={
    ...oldPage,
    background:canvas.backgroundColor||'#fff',
    editorCoordinates:true,editorWidth:W,editorHeight:H,
    // Visual proof only: keep references separate from printable artwork objects.
    previewReferenceObjects:canvas.getObjects().filter(o=>o.zvProductMockup&&o.visible!==false).map(o=>o.toObject()),
    objects:canvas.getObjects().filter(o=>!o.excludeFromExport&&!o.zvProductMockup).map(toData)
  };
}
function loadPage(i){
  i=Math.max(0,Math.min(Number(i)||0,pages.length-1));
  window.ZV_ACTIVE_PAGE=i;

  // ACTIVE PAGE GEOMETRY:
  // Admin print_width_in / print_height_in controls BOTH the outside rulers
  // and the white editor/artboard aspect ratio. No category-specific dimensions.
  const logical=zvLogicalSizeForPage(i,pages[i]);
  W=logical.width;
  H=logical.height;

  loading=true;
  activePage=i;
  // Update navigation immediately. Image/mockup loading is asynchronous and
  // must never leave the arrows pointing at the previous page.
  renderPages();
  window.dispatchEvent(new CustomEvent('zenvibe:pagechange',{detail:{pageIndex:i,physical:zvPhysicalForPage(i)}}));
  canvas.clear();

  // Establish final Admin-driven artboard geometry first.
  // Ruler is rendered only after page objects and final fit have settled.
  const zoomInput=document.getElementById('zoomRange');
  const requestedZoom=Number(zoomInput?.value)||100;
  setCanvasScale(requestedZoom);
  const p=pages[i]||newPage();
  const adminCfg=OPT.editor_config||OPT.editorConfig||{};
  canvas.backgroundColor=(adminCfg.enabled && adminCfg.mode==='print_area') ? 'rgba(255,255,255,0)' : (p.background||'#fff');
  // V48 defensive migration: older V39-V47 masters can contain duplicate OCR
  // detections from several recognition passes. Keep the strongest/first region only.
  const seenOcr=[];
  const overlap=(a,b)=>{if(!a||!b)return 0;const iw=Math.max(0,Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x)),ih=Math.max(0,Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y));return iw*ih/Math.max(1,Math.min(a.w*a.h,b.w*b.h));};
  const rawObjects=(p.objects||[]);
  const coverIds=new Set(rawObjects.filter(o=>o.fieldType==='ocr-inpaint'&&o.ocrCoverFor).map(o=>String(o.ocrCoverFor)));
  // Admin print-area mode: the physical product photo is the only locked base.
  // Old Award/template raster masters must never become the product background.
  // Keep only genuine customer-editable design objects above the blank product.
  const cfg=OPT.editor_config||OPT.editorConfig||{};
  const filteredRawObjects=(cfg.enabled && cfg.mode==='print_area')
    ? rawObjects.filter(o=>!(o && (o.backgroundAsset===true || o.exactVisualMaster===true || o.fieldType==='product-base-asset' || o.fieldType==='customer-product-asset')))
    : rawObjects;
  const preparedRawObjects=(!p.editorCoordinates && cfg.enabled && cfg.mode==='print_area' && Array.isArray(cfg.printAreas) && cfg.printAreas.length)
    ? (()=>{
        // Existing templates use their own full-document coordinates. In restricted
        // product mode map that complete design into the Admin print rectangle once,
        // while keeping every text/vector/image as an independent editable object.
        const matchingAreas=cfg.printAreas.filter(a=>!a.surfaceId || Number(a.surfaceId)===Number((OPT.print_surfaces||OPT.printSurfaces||[])[i]?.id||0));
        const areas=matchingAreas.length?matchingAreas:cfg.printAreas;
        const coasterSource=Number(P.id)===415 && Number(p.width)>0 && Number(p.height)>0;
        const srcW=Math.max(1,coasterSource?Number(p.width):(Number(ZV_BASE_W)||W)), srcH=Math.max(1,coasterSource?Number(p.height):(Number(ZV_BASE_H)||H));
        const mapIntoArea=(o,area,suffix)=>{
          let l=W*Number(area.leftPct||0)/100, t=H*Number(area.topPct||0)/100;
          let aw=W*Number(area.widthPct||0)/100, ah=H*Number(area.heightPct||0)/100;
          // Freshener (419) follows the same full-print-area mapping used by
          // keychain/product cut-outs. Do NOT shrink artwork into a central card.
          // The selected physical die clips the full template after it is loaded.
          const sx=aw/srcW, sy=ah/srcH;
          const x={...o};
          x.left=l+(Number(o.left??o.x??0)*sx);
          x.top=t+(Number(o.top??o.y??0)*sy);
          x.scaleX=(Number(o.scaleX)||1)*sx;
          x.scaleY=(Number(o.scaleY)||1)*sy;
          if(suffix){x.objectId=(o.objectId||o.id||uid())+'-'+suffix;x.id=x.objectId;}
          return x;
        };
        // A one-page product can expose several printable faces (for example
        // Heavy Duty Keychain Front + Back). A template is a product design, so
        // apply the same editable artwork/palette to every configured face.
        if(areas.length>1){
          return filteredRawObjects.flatMap(o=>{
            if(!o || o.customerEditable===false) return [o];
            return areas.map((area,n)=>mapIntoArea(o,area,'surface'+n));
          });
        }
        return filteredRawObjects.map(o=>{
          if(!o || o.customerEditable===false) return o;
          return mapIntoArea(o,areas[0],'');
        });
      })()
    : filteredRawObjects;
  const sourceObjects=preparedRawObjects.filter(o=>{const isOcr=['text','i-text','textbox'].includes(o.type)&&(o.autoOcrText||o.fieldType==='ocr-auto'||o.fieldType==='manual-ocr');if(!isOcr||!o.sourceNormalizedBox)return true;if(seenOcr.some(b=>overlap(b,o.sourceNormalizedBox)>.72))return false;seenOcr.push(o.sourceNormalizedBox);return true;}).map(o=>{
    // V54: OCR is only a hotspot until the original pixels underneath it have
    // actually been removed. This prevents the duplicate/overprinted text seen
    // in V53 and older saved masters.
    const isOcr=['text','i-text','textbox'].includes(o.type)&&(o.autoOcrText||o.fieldType==='ocr-auto'||o.fieldType==='manual-ocr');
    const id=String(o.id||o.objectId||'');
    if(isOcr&&o.sourceNormalizedBox&&!coverIds.has(id)){return {...o,opacity:o.sourceNormalizedBox.repair?0:0.001,ocrOverlayPending:true,customerEditable:true,selectable:true,evented:true};}
    return o;
  });
  let pending=0;sourceObjects.forEach(o=>{
    if((o.type==='svg'||o.type==='svg-group')&&o.src){
      pending++;
      fabric.loadSVGFromURL(o.src,(objects,options)=>{
        if(!objects||!objects.length){console.error('ZenVibe: editable SVG failed to load',o.src);pending--;finish();return;}
        const group=fabric.util.groupSVGElements(objects,options||{});
        const targetW=Number(o.width)||group.width||250, targetH=Number(o.height)||group.height||180;
        group.set({...common(o),scaleX:o.scaleX||targetW/Math.max(1,group.width||targetW),scaleY:o.scaleY||targetH/Math.max(1,group.height||targetH)});
        group.customerEditable=o.customerEditable!==false;group.selectable=group.customerEditable;group.evented=group.customerEditable;
        group.hasControls=group.customerEditable;group.name=o.name||'Editable SVG';
        // Imported SVG masters must not remain one opaque Fabric group. Expose their
        // child vectors/text as customer-editable objects while preserving placement.
        if(group.customerEditable && Array.isArray(group._objects) && group._objects.length){
          const children=group._objects.slice();
          group._restoreObjectsState();
          children.forEach((child,idx)=>{
            child.set({
              customerEditable:true,selectable:true,evented:true,hasControls:true,
              lockMovementX:false,lockMovementY:false,lockScalingX:false,lockScalingY:false,lockRotation:false,
              objectId:child.objectId||uid(),
              name:child.name||((o.name||'Editable SVG')+' '+(idx+1))
            });
            child.setCoords();
            canvas.add(child);
          });
        }else{
          canvas.add(group);
        }
        pending--;finish();
      });
    }else if(o.type==='image'&&o.src){pending++;fabric.Image.fromURL(o.src,img=>{
    // V55: never leave the page in a permanent loading/blank state if an old
    // MEDIA_URL changed. The Django view now embeds local master images, but this
    // defensive path also handles stale drafts or third-party image failures.
    if(!img || !img.width || !img.height){
      console.error('ZenVibe: template image failed to load',o.src);pending--;finish();return;
    }
    img.set({...common(o),scaleX:((o.width||img.width)/img.width)*(o.scaleX||1),scaleY:((o.height||img.height)/img.height)*(o.scaleY||1),cropX:o.cropX||0,cropY:o.cropY||0});
    // Fabric does not automatically revive nested clipPath in this custom loader.
    if(o.clipPath && o.clipPath.type==='polygon' && Array.isArray(o.clipPath.points)){
      const points=o.clipPath.points;
      const minX=Math.min(...points.map(p=>p.x)),minY=Math.min(...points.map(p=>p.y));
      img.clipPath=new fabric.Polygon(points.map(p=>({x:p.x-minX,y:p.y-minY})),{
        left:minX,top:minY,absolutePositioned:true,fill:'#000',
        selectable:false,evented:false
      });
    }
    img.baseSrc=o.baseSrc||o.src;img.exactVisualMaster=!!o.exactVisualMaster;const addImage=()=>{canvas.add(img);if(img.backgroundAsset || o.id==='illustrated-artwork' || o.objectId==='illustrated-artwork')canvas.sendToBack(img);pending--;finish()};if(o.filters&&o.filters.length&&fabric.util.enlivenObjects){fabric.util.enlivenObjects(o.filters,filters=>{img.filters=filters;img.applyFilters();addImage()})}else addImage()},{crossOrigin:'anonymous'})}else{const obj=fromData(o);if(obj){obj.set({scaleX:o.scaleX||1,scaleY:o.scaleY||1});canvas.add(obj)}}});
  function zvApplyCoasterShape(){
    if(Number(P.id)!==415)return;
    const shape=String(OPT.selected_shape||new URLSearchParams(location.search).get('shape')||'square').toLowerCase();
    const cfg=OPT.editor_config||OPT.editorConfig||{};
    const area=(Array.isArray(cfg.printAreas)&&cfg.printAreas.length)?cfg.printAreas[0]:null;
    const left=area?W*Number(area.leftPct||0)/100:0;
    const top=area?H*Number(area.topPct||0)/100:0;
    const aw=area?W*Number(area.widthPct||100)/100:W;
    const ah=area?H*Number(area.heightPct||100)/100:H;
    const radius=Math.max(1,Math.min(aw,ah)/2);
    const cx=left+aw/2,cy=top+ah/2;
    canvas.getObjects().forEach(o=>{
      if(!o||o.zvProductMockup||o.excludeFromExport)return;
      if(shape==='circle'){
        o.clipPath=new fabric.Circle({
          radius:radius,left:cx,top:cy,originX:'center',originY:'center',
          absolutePositioned:true,selectable:false,evented:false
        });
      }else{
        o.clipPath=null;
      }
      o.dirty=true;
    });
    const wrap=document.getElementById('canvasWrap');
    if(wrap)wrap.dataset.coasterShape=shape;
    canvas.requestRenderAll();
  }
  function zvFinishLoadedPage(){
    loading=false;
    zvApplyCoasterShape();
    zvApplyMousePadShape();
    zvFitGolfBallArtwork();
    setCanvasScale(requestedZoom);
    renderAll();
    checkEditableObjects();
    requestAnimationFrame(()=>requestAnimationFrame(zvRenderPhysicalRulers));
  }
  function finish(){if(pending===0){zvLoadProductMockup(()=>zvFinishLoadedPage());}}
  if(!pending){zvLoadProductMockup(()=>zvFinishLoadedPage());}
}
function checkEditableObjects(){
  const hasEditable=canvas.getObjects().some(o=>!o.zvProductMockup&&o.customerEditable!==false);
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
function renderPages(){
  const surfaces=zvAdminSurfaces();
  // Reconcile from the original published master only if a UI operation
  // unexpectedly collapsed the page array. Never overwrite edited pages.
  if(window.SOURCE_TEMPLATE_ID && zvPublishedPages.length>pages.length &&
     !window.EXISTING_DESIGN?.id){
    for(let i=pages.length;i<zvPublishedPages.length;i++){
      pages.push(clone(zvPublishedPages[i]));
    }
  }

  // Admin surfaces provide labels and dimensions, not permission to discard
  // template pages. Never truncate saved artwork during a UI refresh.
  if(surfaces.length){
    while(pages.length<surfaces.length) pages.push(newPage());
    pages.forEach((p,i)=>{
      const sf=surfaces[i];
      p.name=(sf&&sf.label)||p.name||('Page '+(i+1));
    });
  }

  const go=(i)=>{
    i=Number(i);
    if(!Number.isFinite(i)||i<0||i>=pages.length||i===activePage)return;
    // Preserve the outgoing artwork, then load the requested page.
    // The visible active tab and arrow states update before async assets finish.
    sync();
    loadPage(i);
  };

  // Existing/desktop page list.
  const h=$('pageButtons');
  if(h){
    h.innerHTML='';
    pages.forEach((p,i)=>{
      const b=document.createElement('button');
      b.type='button';
      b.className='page-btn'+(i===activePage?' active':'');
      b.textContent='Page '+(i+1);
      b.onclick=()=>go(i);
      h.appendChild(b);
    });
  }

  // Arrow-only pagination: never render a row of individual page buttons.
  // The existing left/right arrows call go() and load the next/previous artwork.
  const bottom=$('bottomPageButtons');
  if(bottom){
    bottom.innerHTML='';
    bottom.style.cssText='display:none;';
  }

  // Synchronize the visible footer with the actual loaded template pages.
  const countBadge=$('pageCountBadge');
  if(countBadge) countBadge.textContent=pages.length+' '+(pages.length===1?'page':'pages');
  const prevArrow=$('bottomPrevPage');
  if(prevArrow){prevArrow.disabled=activePage===0;prevArrow.onclick=()=>go(activePage-1);}
  const nextArrow=$('bottomNextPage');
  if(nextArrow){nextArrow.disabled=activePage>=pages.length-1;nextArrow.onclick=()=>go(activePage+1);}
  const label=$('activePageLabel');
  if(label) label.textContent='Page '+(activePage+1)+' of '+pages.length;

  // loadPage performs the authoritative ruler render after final canvas fit.
  if(!loading) requestAnimationFrame(zvRenderPhysicalRulers);
}

window.ZV_GO_TO_PAGE=function(i){
  i=Number(i);
  if(!Number.isFinite(i)) return;
  i=Math.max(0,Math.min(i,pages.length-1));
  if(i===activePage) return;
  sync();
  loadPage(i);
};
window.ZV_NEXT_PAGE=function(){
  if(activePage<pages.length-1) window.ZV_GO_TO_PAGE(activePage+1);
};
window.ZV_PREV_PAGE=function(){
  if(activePage>0) window.ZV_GO_TO_PAGE(activePage-1);
};

// Bind any existing footer arrow controls, including legacy markup.
document.addEventListener('click',function(e){
  const next=e.target.closest('[data-page-next],#nextPageBtn,#pageNextBtn');
  const prev=e.target.closest('[data-page-prev],#prevPageBtn,#pagePrevBtn');
  if(next){ e.preventDefault(); e.stopPropagation(); window.ZV_NEXT_PAGE(); }
  if(prev){ e.preventDefault(); e.stopPropagation(); window.ZV_PREV_PAGE(); }
});

function labelFor(o,i){return o.name||((isText(o)?(o.text||'Text').slice(0,22):o.type)+' '+(i+1))}
function renderLayers(){const h=$('layersPanel');h.innerHTML='';[...canvas.getObjects()].reverse().forEach((o,ri)=>{if(o.excludeFromExport||o.zvProductMockup)return;const i=canvas.getObjects().indexOf(o),row=document.createElement('div');row.className='layer-row'+(canvas.getActiveObject()===o?' active':'');row.innerHTML=`<button data-a="select">${labelFor(o,i)}</button><button data-a="visible">${o.visible===false?'◌':'◉'}</button><button data-a="lock">${o.lockMovementX?'🔒':'🔓'}</button><button data-a="up">↑</button><button data-a="down">↓</button>`;row.querySelectorAll('button').forEach(b=>b.onclick=()=>{const a=b.dataset.a;if(a==='select'){canvas.setActiveObject(o)}if(a==='visible'){o.visible=!o.visible}if(a==='lock')toggleLock(o);if(a==='up')canvas.bringForward(o);if(a==='down')canvas.sendBackwards(o);canvas.requestRenderAll();snapshot();renderLayers()});h.appendChild(row)})}
// Keep customer-editable objects physically inside the configured print region.
// Product references/guides are excluded. This applies during move + scale, so
// users cannot drag artwork onto the key ring/hardware or outside the strap.
function zvKeychainPrintBounds(){
  // Product 420's admin print-area percentages describe the old artboard and
  // must not be used after the 9 x 10 workspace was introduced. The printable
  // region is the fabric face itself, excluding the stitched edge/connector.
  return {
    left:W*.137,
    top:H*.4385,
    right:W*(.137+.6188),
    bottom:H*(.4385+.12)
  };
}
function zvActivePrintBounds(obj){
  const cfg=OPT.editor_config||OPT.editorConfig||{};
  if(!obj || obj.customerEditable===false || obj.zvProductMockup || obj.excludeFromExport) return null;
  if(Number(P.id)===420) return zvKeychainPrintBounds();
  if(Number(P.id)===427) return zvBadgePrintBounds();
  // Name-plate artwork is authored on the complete 10 x 2 plate face. Keep a
  // small production-safe inset and ignore the stale 10 x 3 admin print box.
  if(Number(P.id)===428) return {left:W*.025,top:H*.08,right:W*.975,bottom:H*.92};
  if(String(P?.name||'').toLowerCase().includes('golf ball')) return zvGolfBallPrintBounds();
  if(!(cfg.enabled && cfg.mode==='print_area' && Array.isArray(cfg.printAreas) && cfg.printAreas.length)) return null;
  const areas=cfg.printAreas;
  // Keep an object attached to the area containing its centre; otherwise choose nearest.
  const cx=obj.left||0, cy=obj.top||0;
  let area=areas.find(a=>{
    const l=W*Number(a.leftPct||0)/100,t=H*Number(a.topPct||0)/100;
    const r=l+W*Number(a.widthPct||0)/100,b=t+H*Number(a.heightPct||0)/100;
    return cx>=l&&cx<=r&&cy>=t&&cy<=b;
  });
  if(!area){
    area=areas.reduce((best,a)=>{
      const ax=W*(Number(a.leftPct||0)+Number(a.widthPct||0)/2)/100;
      const ay=H*(Number(a.topPct||0)+Number(a.heightPct||0)/2)/100;
      const d=(cx-ax)*(cx-ax)+(cy-ay)*(cy-ay);
      return !best||d<best.d?{a,d}:best;
    },null)?.a;
  }
  if(!area)return null;
  return {
    left:W*Number(area.leftPct||0)/100,
    top:H*Number(area.topPct||0)/100,
    right:W*(Number(area.leftPct||0)+Number(area.widthPct||0))/100,
    bottom:H*(Number(area.topPct||0)+Number(area.heightPct||0))/100
  };
}
function zvConstrainEditableToPrintArea(obj){
  const b=zvActivePrintBounds(obj); if(!b)return;
  obj.setCoords();
  let box=obj.getBoundingRect(true,true);
  const maxW=b.right-b.left,maxH=b.bottom-b.top;
  if(box.width>maxW||box.height>maxH){
    const factor=Math.min(maxW/Math.max(1,box.width),maxH/Math.max(1,box.height));
    obj.scaleX*=factor; obj.scaleY*=factor; obj.setCoords();
    box=obj.getBoundingRect(true,true);
  }
  let dx=0,dy=0;
  if(box.left<b.left)dx=b.left-box.left;
  else if(box.left+box.width>b.right)dx=b.right-(box.left+box.width);
  if(box.top<b.top)dy=b.top-box.top;
  else if(box.top+box.height>b.bottom)dy=b.bottom-(box.top+box.height);
  if(dx||dy){obj.left=(obj.left||0)+dx;obj.top=(obj.top||0)+dy;obj.setCoords();}
}
canvas.on('object:moving',e=>zvConstrainEditableToPrintArea(e.target));
canvas.on('object:scaling',e=>zvConstrainEditableToPrintArea(e.target));
canvas.on('object:modified',e=>zvConstrainEditableToPrintArea(e.target));

function drawHelpers(){canvas.getObjects().filter(o=>o.excludeFromExport&&!o.zvProductMockup).forEach(o=>canvas.remove(o));if(Number(P.id)===427){zvRefreshBadgeBody();return;}if(gridVisible){for(let x=50;x<W;x+=50)canvas.add(new fabric.Line([x,0,x,H],{stroke:'#cbd5e1',strokeWidth:1,selectable:false,evented:false,excludeFromExport:true,opacity:.45}));for(let y=50;y<H;y+=50)canvas.add(new fabric.Line([0,y,W,y],{stroke:'#cbd5e1',strokeWidth:1,selectable:false,evented:false,excludeFromExport:true,opacity:.45}))}if(guidesVisible){const safe=Math.max(18,W*(Number(P.safeMarginMm||5)/210)),bleed=Math.max(10,W*(Number(P.bleedMm||3)/210));canvas.add(new fabric.Rect({left:bleed,top:bleed,width:W-bleed*2,height:H-bleed*2,fill:'transparent',stroke:'#ef4444',strokeDashArray:[12,8],selectable:false,evented:false,excludeFromExport:true}));canvas.add(new fabric.Rect({left:safe,top:safe,width:W-safe*2,height:H-safe*2,fill:'transparent',stroke:'#22c55e',strokeDashArray:[12,8],selectable:false,evented:false,excludeFromExport:true}))}}
function add(o){o.objectId=uid();canvas.add(o);canvas.setActiveObject(o);snapshot();renderAll()}
function active(){return canvas.getActiveObject()}
function toggleLock(o=active()){if(!o)return;const v=!o.lockMovementX;o.set({lockMovementX:v,lockMovementY:v,lockScalingX:v,lockScalingY:v,lockRotation:v,hasControls:!v});canvas.requestRenderAll()}
function selectedObjects(){const a=active();return a?.type==='activeSelection'?a.getObjects():a?[a]:[]}
function modify(fn){selectedObjects().forEach(fn);canvas.requestRenderAll();snapshot();renderLayers()}
function duplicate(){const a=active();if(!a)return;a.clone(c=>{c.set({left:a.left+25,top:a.top+25,objectId:uid()});canvas.add(c);canvas.setActiveObject(c);snapshot();renderAll()})}
function group(){const a=active();if(!a)return;if(a.type==='activeSelection'){a.toGroup();snapshot()}else if(a.type==='group'){a.toActiveSelection();snapshot()}renderAll()}
function updateTransformLabels(){
 const opacity=$('opacity'),rotation=$('rotation');
 const opacityValue=$('opacityValue'),rotationValue=$('rotationValue');
 if(opacity&&opacityValue)opacityValue.textContent=Math.round(Number(opacity.value)*100)+'%';
 if(rotation&&rotationValue)rotationValue.textContent=Math.round(Number(rotation.value))+'°';
}
['opacity','rotation'].forEach(id=>{
 const control=$(id);
 if(control)control.addEventListener('input',updateTransformLabels);
});
function syncPanel(){const o=active();const imageBtn=$('editImageBtn');if(imageBtn)imageBtn.style.display=(o&&o.type==='image')?'inline-flex':'none';if(!o){if($('textValue'))$('textValue').value='';return;}if(isText(o)){$('textValue').value=o.text||'';$('fontSize').value=o.fontSize||32;$('fontFamily').value=o.fontFamily||'Arial'}if(typeof o.fill==='string'&&/^#[0-9a-f]{6}$/i.test(o.fill)){ $('fillColor').value=o.fill; if($('textPanelColor'))$('textPanelColor').value=o.fill; if($('textPanelHex'))$('textPanelHex').textContent=o.fill.toUpperCase(); }$('opacity').value=o.ocrOverlayPending?1:(o.opacity??1);$('rotation').value=o.angle||0;updateTransformLabels()}
function editorDocument(){return {version:3,document:{width:ZV_BASE_W,height:ZV_BASE_H,coordinateSpace:'editor'},pages};}
window.ZENVIBE_SAVE_CURRENT_DESIGN=()=>loading?Promise.reject(new Error('Wait for the current page to finish loading.')):save(false,false);
function localKey(){return 'zenvibe-autosave-'+P.id+'-'+(designId||('template-'+(window.SOURCE_TEMPLATE_ID||'blank')))}
function scheduleLocalSave(){clearTimeout(saveTimer);saveTimer=setTimeout(()=>{sync();localStorage.setItem(localKey(),JSON.stringify({...editorDocument(),name:$('designName').value,quantity:$('quantity').value,at:Date.now()}))},500)}
async function save(autosave=false,toCart=false){sync();const status=autosave?$('autosaveStatus'):$('saveStatus');status.textContent=autosave?'Autosaving…':'Saving…';let preview='';try{
  // Fabric's excludeFromExport flag affects JSON serialization, not raster
  // toDataURL(). Hide every editor-only helper (print-area guides, grid,
  // safe/bleed lines, selection overlays) while generating the cart proof.
  canvas.discardActiveObject();
  const helpers=canvas.getObjects().filter(o=>o.excludeFromExport||o.zvPrintAreaGuide);
  // Do not merely hide helpers: Fabric can still repaint an externally-managed
  // print-area guide during toDataURL(). Physically detach all editor-only
  // objects for the synchronous raster export, then put them back.
  const helperState=helpers.map(o=>({o,index:canvas.getObjects().indexOf(o)}));
  helpers.forEach(o=>canvas.remove(o));
  canvas.renderAll();
  preview=canvas.toDataURL({format:'png',multiplier:1});
  helperState.sort((a,b)=>a.index-b.index).forEach(x=>canvas.insertAt(x.o,Math.min(x.index,canvas.getObjects().length),false));
  canvas.renderAll();
  // Admin guard owns the green print-area overlay. Redraw it only after the
  // clean customer/cart preview has already been captured.
  if(window.ZVPrintAreaGuard?.drawGuides) window.ZVPrintAreaGuard.drawGuides();
}catch(e){console.error('ZenVibe preview generation failed',e)}const r=await fetch(window.ZENVIBE_SAVE_DESIGN_URL||'/api/save-design/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify({design_id:designId,source_template_id:window.SOURCE_TEMPLATE_ID,product_id:P.id,cart_key:window.ZENVIBE_EDIT_CART_KEY||'',name:$('designName').value,quantity:$('quantity').value,size_key:window.PRODUCT_OPTIONS?.selected_size||'',color_key:window.PRODUCT_OPTIONS?.selected_color||'',design_json:{...editorDocument(),...(Number(P.id)===419?{selectedShape:zvFreshenerShape(),selectedFragrance:String(window.PRODUCT_OPTIONS?.fragrance||new URLSearchParams(location.search).get('fragrance')||'vanilla')}: {})},preview_png:preview,autosave,status:toCart?'cart':'draft'})});const d=await r.json().catch(()=>{throw new Error('Save endpoint returned an invalid response (HTTP '+r.status+').')});if(!r.ok||!d.ok)throw new Error(d.error||'Unable to save design (HTTP '+r.status+').');designId=d.design_id;window.EXISTING_DESIGN={...(window.EXISTING_DESIGN||{}),id:designId};if(d.cart_key)window.ZENVIBE_EDIT_CART_KEY=d.cart_key;status.textContent=autosave?'Autosaved '+new Date().toLocaleTimeString():'Saved successfully';localStorage.removeItem(localKey());if(toCart)location.assign(d.cart_url||window.ZENVIBE_CART_URL)}
function printCheck(){sync();const issues=[];pages.forEach((p,pi)=>(p.objects||[]).forEach(o=>{const name=`Page ${pi+1}: ${o.text||o.type}`;if(o.type==='text'&&(o.fontSize||32)*(o.scaleY||1)<14)issues.push(name+' has very small text.');if((o.opacity??1)<.35)issues.push(name+' has very low opacity.');if(o.type==='image'){const displayed=(o.width||1)*(o.scaleX||1),dpi=((o.originalWidth||o.width||0)/Math.max(displayed,1))*96;if(dpi<P.minDpi)issues.push(name+` is approximately ${Math.round(dpi)} DPI; minimum is ${P.minDpi} DPI.`)}if((o.left||0)<0||(o.top||0)<0)issues.push(name+' extends outside the canvas.')}));$('printResults').innerHTML=(issues.length?issues:['Design passes the initial print check.']).map(x=>`<div>${x}</div>`).join('')}
async function ai(action){sync();const out=$('aiResults');out.textContent='Working…';const r=await fetch('/api/ai-assist/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify({action,text:$('aiPrompt').value,design:{pages}})});const d=await r.json();out.innerHTML=(d.result||[d.error||'Unable to process']).map(x=>`<button class="ai-result-item">${x}</button>`).join('');if(action==='tagline')out.querySelectorAll('button').forEach(b=>b.onclick=()=>add(new fabric.IText(b.textContent,{left:80,top:80,fontSize:34,fill:'#111827'})))}
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
  const r=box.repair&&box.textBox?box.textBox:box;
  return {left:(bg.left||0)+r.x*nw*sx,top:(bg.top||0)+r.y*nh*sy,width:Math.max(4,r.w*nw*sx),height:Math.max(4,r.h*nh*sy)};
}
function fitOcrTextToSourceBox(o){
  if(!o||!isText(o)||!o.sourceNormalizedBox)return;
  const r=sourceBoxCanvasRect(o);if(!r)return;
  o.set({scaleX:1,scaleY:1});o.initDimensions?.();
  let fs=Math.min(Number(o.fontSize||32),Math.max(7,r.height*.82));o.set('fontSize',fs);o.initDimensions?.();
  for(let i=0;i<40&&((o.width||1)>r.width*.94||(o.height||1)>r.height*1.05);i++){fs=Math.max(6,fs*.95);o.set('fontSize',fs);o.initDimensions?.()}
  if(o.sourceNormalizedBox.repair)o.set({left:r.left,top:r.top});
  else o.set({left:r.left+(r.width-(o.width||0))/2,top:r.top+(r.height-(o.height||0))/2});o.setCoords();
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
$('fillColor')?.addEventListener('input',async e=>{
 const colour=e.target.value;
 if($('textPanelColor'))$('textPanelColor').value=colour;
 if($('textPanelHex'))$('textPanelHex').textContent=colour.toUpperCase();
 if($('textPanelHexInput'))$('textPanelHexInput').value=colour.toUpperCase();
 const o=active();
 if(!o)return;
 if(isText(o)&&o.ocrOverlayPending)await activatePendingOcrText(o);
 if(isText(o)){o.set({fill:colour,opacity:1});snapshot();renderAll();}
 else if(typeof o.set==='function'){o.set('fill',colour);snapshot();renderAll();}
});
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
  // V52: deleting detected/reconstructed printed text must also remove the pixels
  // from the protected raster master. First create its cleanup patch, then delete
  // the editable text object. The patch remains, so the old printed wording does
  // not magically reappear.
  for(const o of list){
    if(isText(o)&&o.ocrOverlayPending) await activatePendingOcrText(o);
    if(o._zvPendingArtwork) await activatePendingArtwork(o);
  }
  list.forEach(o=>canvas.remove(o));canvas.discardActiveObject();snapshot();renderAll();
});bind('duplicateBtn',duplicate);bind('bringFrontBtn',()=>modify(o=>canvas.bringToFront(o)));bind('sendBackBtn',()=>modify(o=>canvas.sendToBack(o)));bind('flipXBtn',()=>modify(o=>o.set('flipX',!o.flipX)));bind('flipYBtn',()=>modify(o=>o.set('flipY',!o.flipY)));bind('lockBtn',()=>{toggleLock();snapshot();renderAll()});bind('groupBtn',group);
bind('leftBtn',()=>modify(o=>o.set({left:20})));bind('centerBtn',()=>modify(o=>o.set({left:(W-o.getScaledWidth())/2})));bind('rightBtn',()=>modify(o=>o.set({left:W-o.getScaledWidth()-20})));bind('topBtn',()=>modify(o=>o.set({top:20})));bind('middleBtn',()=>modify(o=>o.set({top:(H-o.getScaledHeight())/2})));bind('bottomBtn',()=>modify(o=>o.set({top:H-o.getScaledHeight()-20})));
bind('applyTextBtn',async()=>{
 const o=active();if(!o)return;
 const readValues=()=>({fill:$('fillColor').value,opacity:Number($('opacity').value),angle:Number($('rotation').value),text:$('textValue').value,fontSize:Number($('fontSize').value),fontFamily:$('fontFamily').value});
 // Repair activation refreshes the panel. Preserve the entered Paddle field values.
 const entered=o.sourceNormalizedBox?.repair?readValues():null;
 if(isText(o)&&o.ocrOverlayPending)await activatePendingOcrText(o);
 const values=entered||readValues();
 o.set({fill:values.fill,opacity:values.opacity,angle:values.angle});
 if(isText(o)){o.set({text:values.text,fontSize:values.fontSize,fontFamily:values.fontFamily,scaleX:1,scaleY:1});o.initDimensions?.();if(o.sourceNormalizedBox)fitOcrTextToSourceBox(o)}
 snapshot();renderAll();
});bind('boldBtn',()=>modify(o=>{if(isText(o)&&o.ocrOverlayPending)activatePendingOcrText(o);if(isText(o))o.set('fontWeight',o.fontWeight==='bold'?'normal':'bold')}));bind('italicBtn',()=>modify(o=>{if(isText(o)&&o.ocrOverlayPending)activatePendingOcrText(o);if(isText(o))o.set('fontStyle',o.fontStyle==='italic'?'normal':'italic')}));bind('underlineBtn',()=>modify(o=>{if(isText(o)&&o.ocrOverlayPending)activatePendingOcrText(o);if(isText(o))o.set('underline',!o.underline)}));bind('applyBackgroundBtn',()=>applyDocumentBackgroundColour($('backgroundColor').value));bind('openImageBlurBtn',()=>{
 const status=$('backgroundBlurStatus');
 const report=message=>{if(status){status.textContent=message;status.hidden=false;}};
 const selected=canvas.getActiveObject();
 if(!selected||selected.type!=='image'){
  report('Select a photo or raster image layer first. Vector text and shapes cannot use image blur.');
  return;
 }
 if(!window.ZenImageTools){
  report('Image adjustment tools could not load. Refresh the editor and try again.');
  return;
 }
 Promise.resolve(window.ZenImageTools.run(canvas,'adjust',selected)).then(ok=>{
  if(!ok){report('Unable to open image adjustments for this layer.');return;}
  if(status)status.hidden=true;
  const bar=$('zvImageToolsBar');
  if(bar){bar.scrollIntoView({block:'nearest',behavior:'smooth'});const slider=bar.querySelector('[data-filter="blur"]');if(slider)slider.focus({preventScroll:true});}
 }).catch(err=>{console.error('Background blur:',err);report('Could not open blur controls for this image.');});
});
bind('addPageBtn',()=>{sync();pages.push(newPage());loadPage(pages.length-1);snapshot()});bind('duplicatePageBtn',()=>{sync();pages.splice(activePage+1,0,clone(pages[activePage]));loadPage(activePage+1);snapshot()});bind('deletePageBtn',()=>{if(pages.length===1)return alert('At least one page is required.');pages.splice(activePage,1);loadPage(Math.max(0,activePage-1));snapshot()});bind('undoBtn',()=>restore(historyIndex-1));bind('redoBtn',()=>restore(historyIndex+1));bind('fitBtn',()=>{$('zoomRange').value=100;setCanvasScale(100)});$('zoomRange').oninput=e=>setCanvasScale(Number(e.target.value));bind('gridBtn',()=>{gridVisible=!gridVisible;renderAll()});bind('guidesBtn',()=>{guidesVisible=!guidesVisible;renderAll()});bind('fullscreenBtn',()=>document.querySelector('.editor-shell').requestFullscreen?.());bind('printCheckBtn',printCheck);bind('showAllBtn',()=>modify(o=>o.visible=true));bind('unlockAllBtn',()=>canvas.getObjects().forEach(o=>{if(o.excludeFromExport||o.customerEditable===false)return;o.set({selectable:true,evented:true,lockMovementX:false,lockMovementY:false,lockScalingX:false,lockScalingY:false,lockRotation:false,hasControls:true})}));bind('aiTaglineBtn',()=>ai('tagline'));bind('aiCritiqueBtn',()=>ai('critique'));bind('saveDraftBtn',()=>save(false,false).catch(e=>$('saveStatus').textContent=e.message));bind('saveBtn',()=>save(false,true).catch(e=>{console.error('Continue to cart failed',e);const status=$('saveStatus');if(status)status.textContent=e.message;alert('Unable to continue to cart: '+e.message)}));// Universal export uses a separate renderer and never switches or clears the active page.
if(window.ZenvibeExport){
  window.ZenvibeExport.install({
    button:'#downloadBtn',
    getCurrentPage:()=>activePage,
    getFilename:()=>($('designName')?.value||P.name||'zenvibe-design'),
    getPages:()=>{
      sync();
      return pages.map((p,i)=>{
        const size=zvLogicalSizeForPage(i,pages[i]);
        const physical=zvPhysicalForPage(i);
        // Keep the live page's Fabric serialization; stored pages use the editor's
        // own object schema, converted by universal-export.js.
        const json=i===activePage
          ? canvas.toJSON()
          : {background:p.background||'#fff',objects:clone(p.objects||[])};
        return {
          name:p.name||'Page '+(i+1),
          width:size.width,height:size.height,
          widthIn:physical.width,heightIn:physical.height,
          json
        };
      });
    }
  });
}else{
  // Preserve the original download behaviour if the optional module fails to load.
  bind('downloadBtn',()=>{sync();const a=document.createElement('a');a.download=($('designName').value||'zenvibe-design')+'.png';a.href=canvas.toDataURL({format:'png',multiplier:2});a.click()});
}bind('downloadJsonBtn',()=>{sync();const a=document.createElement('a');a.download='zenvibe-design.json';a.href=URL.createObjectURL(new Blob([JSON.stringify(editorDocument(),null,2)],{type:'application/json'}));a.click()});
const pdfBtn=document.getElementById("downloadPdfBtn");

if(pdfBtn){

    pdfBtn.onclick=downloadPDF;

}
async function downloadPDF(){

    const {jsPDF}=window.jspdf;

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

// V15: OCR fields are intentionally invisible until changed so the pristine admin
// artwork remains pixel-perfect. Route clicks through the full-page image to those
// invisible fields, making existing printed text behave like selectable text.
function ocrHotspotAtPointer(pointer){
  const bg=canvas.getObjects().find(x=>x.type==='image'&&x.backgroundAsset&&x.exactVisualMaster)||canvas.getObjects().find(x=>x.type==='image'&&x.backgroundAsset);if(!bg)return null;
  const el=bg.getElement(),nw=el.naturalWidth||bg.width||1,nh=el.naturalHeight||bg.height||1,sx=bg.scaleX||1,sy=bg.scaleY||1;
  const hits=canvas.getObjects().filter(o=>isText(o)&&o.customerEditable!==false&&o.sourceNormalizedBox&&(o.autoOcrText||o.fieldType==='ocr-auto'||o.fieldType==='manual-ocr'||o.fieldType==='manual-replace')).filter(o=>{const b=o.sourceNormalizedBox,l=(bg.left||0)+b.x*nw*sx,t=(bg.top||0)+b.y*nh*sy,w=b.w*nw*sx,h=b.h*nh*sy,pad=Math.max(5,Math.min(14,h*.45));return pointer.x>=l-pad&&pointer.x<=l+w+pad&&pointer.y>=t-pad&&pointer.y<=t+h+pad});
  // V36: prefer a full visual-fallback text band over tiny low-confidence OCR
  // fragments inside it. This makes script names/calligraphy selectable instead of
  // selecting garbage tokens such as "LV ." from nearby floral artwork.
  hits.sort((a,b)=>{
    // V41: an explicitly removed/replaced text region is authoritative. Always
    // select it before OCR/fallback hotspots that may overlap the same wording.
    const am=a.fieldType==='manual-replace'?1:0,bm=b.fieldType==='manual-replace'?1:0;
    if(am!==bm)return bm-am;
    const af=a.visualFallback?1:0,bf=b.visualFallback?1:0;
    if(af!==bf)return bf-af;
    const ac=Number(a.sourceConfidence||0),bc=Number(b.sourceConfidence||0);
    if((ac>=45)!==(bc>=45))return bc-ac;
    return (a.sourceNormalizedBox.w*a.sourceNormalizedBox.h)-(b.sourceNormalizedBox.w*b.sourceNormalizedBox.h);
  });
  if(hits[0])return hits[0];

  // V53: do not require the pointer to land inside an imperfect OCR box.
  // Pick the nearest text region on the same visual row. This is critical for
  // cursive names and OCR boxes that are a few pixels too small/offset.
  const near=canvas.getObjects().filter(o=>isText(o)&&o.customerEditable!==false&&o.sourceNormalizedBox&&(o.autoOcrText||o.fieldType==='ocr-auto'||o.fieldType==='manual-ocr'||o.fieldType==='manual-replace')).map(o=>{
    const b=o.sourceNormalizedBox,l=(bg.left||0)+b.x*nw*sx,t=(bg.top||0)+b.y*nh*sy,w=b.w*nw*sx,h=b.h*nh*sy,cx=l+w/2,cy=t+h/2;
    const dy=Math.abs(pointer.y-cy),dx=Math.max(0,Math.abs(pointer.x-cx)-w/2);
    return {o,score:dy+dx*.3,ok:dy<=Math.max(18,h*1.7)&&dx<=Math.max(34,w*.55)};
  }).filter(x=>x.ok).sort((a,b)=>a.score-b.score);
  return near[0]?.o||null;
}

// V53 universal missed-text fallback. If OCR did not create a hotspot, inspect
// the uploaded bitmap around the click, find the local horizontal ink band and
// turn that band into a real editable replacement. This keeps the admin upload
// workflow automatic while still giving the customer a reliable way to edit
// script/calligraphy that OCR cannot read.
function detectPrintedBandAtPointer(pointer){
  const bg=getMasterArtwork();if(!bg)return null;
  try{
    const el=bg.getElement(),nw=el.naturalWidth||bg.width||1,nh=el.naturalHeight||bg.height||1,sx=bg.scaleX||1,sy=bg.scaleY||1;
    const ix=Math.round((pointer.x-(bg.left||0))/sx),iy=Math.round((pointer.y-(bg.top||0))/sy);
    if(ix<0||iy<0||ix>=nw||iy>=nh)return null;

    // V57: detect a TIGHT text line around the click. Work on a local crop,
    // estimate paper colour from the crop border, then use projection runs.
    // This is intentionally independent of OCR so script/calligraphy names work.
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

window.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName))return;if(e.key==='PageDown'){e.preventDefault();sync();loadPage(Math.min(activePage+1,pages.length-1));return;}if(e.key==='PageUp'){e.preventDefault();sync();loadPage(Math.max(activePage-1,0));return;}if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();e.shiftKey?restore(historyIndex+1):restore(historyIndex-1)}else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='y'){e.preventDefault();restore(historyIndex+1)}else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='d'){e.preventDefault();duplicate()}else if(e.key==='Delete'||e.key==='Backspace'){$('deleteBtn').click()}else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){const d=e.shiftKey?10:1;modify(o=>o.set({left:o.left+(e.key==='ArrowRight'?d:e.key==='ArrowLeft'?-d:0),top:o.top+(e.key==='ArrowDown'?d:e.key==='ArrowUp'?-d:0)}))}});

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
document.querySelectorAll('.rail-tab').forEach(tab=>tab.onclick=()=>{document.querySelectorAll('.rail-tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.studio-panel-section').forEach(x=>x.classList.remove('active'));tab.classList.add('active');const panel=$(tab.dataset.panel);panel?.classList.add('active');$('panelTitle').textContent=tab.querySelector('b').textContent;document.querySelector('.studio-panel').classList.remove('panel-closed')});
$('closePanelBtn')?.addEventListener('click',()=>document.querySelector('.studio-panel').classList.toggle('panel-closed'));
document.querySelectorAll('#shapeLibrary [data-shape]').forEach(b=>b.onclick=()=>addLibraryShape(b.dataset.shape));
document.querySelectorAll('.text-preset').forEach(b=>b.onclick=()=>{const t=b.dataset.textPreset,settings=t==='heading'?{text:'Add a heading',fontSize:64,fontWeight:'bold'}:t==='subheading'?{text:'Add a subheading',fontSize:38,fontWeight:'600'}:{text:'Add a little bit of body text',fontSize:25,fontWeight:'normal'};add(new fabric.IText(settings.text,{left:80,top:80,fontSize:settings.fontSize,fontWeight:settings.fontWeight,fill:'#17233c',fontFamily:'Poppins'}));});
$('fontSearch')?.addEventListener('input',e=>buildFontLibrary(e.target.value));$('emojiSearch')?.addEventListener('input',e=>buildEmojiLibrary(e.target.value));
const customPageHex=$('customPageHex');
function syncCustomPageColour(value){
 const hex=String(value||'').trim().toUpperCase();
 if(!/^#[0-9A-F]{6}$/.test(hex))return;
 if(customPageHex)customPageHex.value=hex;
 if($('backgroundColor'))$('backgroundColor').value=hex;
}
if(customPageHex){
 customPageHex.addEventListener('change',e=>{
  let hex=String(e.target.value||'').trim();
  if(/^[0-9a-f]{6}$/i.test(hex))hex='#'+hex;
  if(/^#[0-9a-f]{6}$/i.test(hex)){
   syncCustomPageColour(hex);
   applyDocumentBackgroundColour(hex);
  }else{
   syncCustomPageColour($('backgroundColor')?.value||'#ffffff');
  }
 });
}
$('backgroundColor')?.addEventListener('input',e=>syncCustomPageColour(e.target.value));

function setBottomZoom(v){v=Math.max(20,Math.min(180,Number(v)));$('bottomZoomRange').value=v;$('zoomRange').value=v;$('zoomLabel').textContent=v+'%';setCanvasScale(v)}
$('bottomZoomRange')?.addEventListener('input',e=>setBottomZoom(e.target.value));$('bottomZoomOut')?.addEventListener('click',()=>setBottomZoom(Number($('bottomZoomRange').value)-10));$('bottomZoomIn')?.addEventListener('click',()=>setBottomZoom(Number($('bottomZoomRange').value)+10));
buildFontLibrary();buildEmojiLibrary();
// Do not download 15 Google font families during editor startup. Fonts load on demand when selected.

const recovered=localStorage.getItem(localKey());
// V27: a published template must always open from the exact latest admin master.
// Never let an old browser draft replace template JSON. Draft recovery is only for blank canvases.
if(window.SOURCE_TEMPLATE_ID && !window.EXISTING_DESIGN?.id){
  if(recovered) localStorage.removeItem(localKey());
}else if(recovered&&!window.EXISTING_DESIGN?.id){try{const d=JSON.parse(recovered);if(Date.now()-d.at<86400000&&confirm('Recover your personal unsaved draft?')){pages=d.pages;$('designName').value=d.name||$('designName').value;$('quantity').value=new URLSearchParams(location.search).has('quantity')?window.ZENVIBE_INITIAL_QUANTITY:(d.quantity||window.ZENVIBE_INITIAL_QUANTITY||1)}}catch(e){}}
setCanvasScale(100);loadPage(0);snapshot();setInterval(()=>save(true,false).catch(()=>{$('autosaveStatus').textContent='Autosave unavailable'}),30000);
$('clearLocalDraftBtn')?.addEventListener('click',()=>{localStorage.removeItem(localKey());location.reload()});
})();
/* Product image preview fallback. Never rotate a flat photograph as fake 3D.
 * GLB viewer may intercept the button separately when an approved model exists.
 * The Fabric document is not changed by this preview. */
(function(){
 const btn=document.getElementById('threeDViewBtn'), modal=document.getElementById('zv3dModal');
 if(!btn||!modal)return;
 const stage=document.getElementById('zv3dStage'),obj=document.getElementById('zv3dObject'),face=document.getElementById('zv3dFace');
 const productName=document.getElementById('zv3dProductName');
 const left=document.getElementById('zv3dLeft'),right=document.getElementById('zv3dRight'),reset=document.getElementById('zv3dReset');
 let zoom=1,yaw=0,pitch=0,dragging=false,lastX=0,lastY=0;
 function renderPose(){obj.style.transform='rotateX('+pitch+'deg) rotateY('+yaw+'deg) scale('+zoom+')';}
 function snapshot(){
   const canvas=document.querySelector('.canvas-container canvas.lower-canvas')||
     document.getElementById('designCanvas');
   if(!canvas||!canvas.width||!canvas.height)return null;
   try {
     // Export the actual current design, without editor selection borders.
     const upper=document.querySelector('.canvas-container canvas.upper-canvas');
     return {url:canvas.toDataURL('image/png'),ratio:canvas.width/canvas.height};
   }catch(err){console.warn('Product preview capture failed',err);return null;}
 }
 function fit(ratio){
   if(modal.hidden||!stage)return;
   const r=stage.getBoundingClientRect();
   const w=Math.min(r.width*.94,r.height*.94*ratio);
   obj.style.setProperty('width',Math.round(w)+'px','important');
   obj.style.setProperty('height',Math.round(w/ratio)+'px','important');
   obj.style.setProperty('max-width','none','important');
   obj.style.setProperty('max-height','none','important');
   obj.style.setProperty('aspect-ratio',String(ratio),'important');
   renderPose();
 }
 function open(){
   const shot=snapshot();
   if(!shot){alert('Preview is not ready. Please wait for the design to load.');return;}
   face.style.backgroundImage='url("'+shot.url+'")';
   face.style.backgroundSize='100% 100%';
   face.style.backgroundPosition='center';
   face.style.transform='none';
   face.style.backfaceVisibility='visible';
   obj.style.borderRadius='0';
   face.style.borderRadius='0';
   obj.querySelectorAll('.zv3d-edge').forEach(el=>el.style.display='none');
   productName.textContent=(window.PRODUCT&&window.PRODUCT.name)||'Current product';
   zoom=1;yaw=0;pitch=0;
   modal.hidden=false;modal.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
   modal.dataset.previewMode='photo';
   left.hidden=false;right.hidden=false;
   const instructions=modal.querySelector('.zv3d-controls span');
   if(instructions)instructions.textContent='Drag to tilt (front view ±65°) · mouse wheel to zoom';
   const title=document.getElementById('zv3dTitle');if(title)title.textContent='Product Preview';
   const onFit=()=>fit(shot.ratio);
   modal._zvPhotoFit=onFit;
   fit(shot.ratio);requestAnimationFrame(onFit);
 }
 function close(){
   if(modal.dataset.previewMode!=='photo')return;
   modal.hidden=true;modal.setAttribute('aria-hidden','true');document.body.style.overflow='';
   delete modal.dataset.previewMode;dragging=false;
   left.hidden=false;right.hidden=false;
 }
 function turn(delta){if(modal.dataset.previewMode!=='photo')return;yaw=Math.max(-65,Math.min(65,yaw+delta));renderPose();}
 left?.addEventListener('click',()=>turn(-20));right?.addEventListener('click',()=>turn(20));
 stage?.addEventListener('pointerdown',ev=>{if(modal.dataset.previewMode!=='photo')return;dragging=true;lastX=ev.clientX;lastY=ev.clientY;stage.setPointerCapture?.(ev.pointerId);});
 stage?.addEventListener('pointermove',ev=>{if(!dragging||modal.dataset.previewMode!=='photo')return;yaw=Math.max(-65,Math.min(65,yaw+(ev.clientX-lastX)*.3));pitch=Math.max(-35,Math.min(35,pitch-(ev.clientY-lastY)*.2));lastX=ev.clientX;lastY=ev.clientY;renderPose();});
 stage?.addEventListener('pointerup',()=>dragging=false);stage?.addEventListener('pointercancel',()=>dragging=false);
 btn.addEventListener('click',open);
 document.getElementById('zv3dClose')?.addEventListener('click',close);
 reset?.addEventListener('click',()=>{if(modal.dataset.previewMode==='photo'){zoom=1;yaw=0;pitch=0;modal._zvPhotoFit?.();}});
 modal.addEventListener('click',e=>{if(e.target===modal)close();});
 document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
 stage?.addEventListener('wheel',e=>{
   if(modal.dataset.previewMode!=='photo')return;
   e.preventDefault();zoom=Math.max(.5,Math.min(2.5,zoom+(e.deltaY<0?.1:-.1)));modal._zvPhotoFit?.();
 },{passive:false});
 window.addEventListener('resize',()=>{if(modal.dataset.previewMode==='photo')modal._zvPhotoFit?.();});
})();

const discardBtn=document.getElementById("discardBtn");

if(discardBtn){

    discardBtn.onclick=function(){

        if(confirm("Discard all unsaved changes?")){

            location.reload();

        }

    };

}


/* V38 TEXT-FIRST CUSTOMER SELECTION
 * Auto-extracted artwork regions must not sit above editable OCR/script text.
 * Keep them available to the object model, but make pending artwork ignore
 * pointer events until it is explicitly activated by an artwork tool. */
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
