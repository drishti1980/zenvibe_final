(function(){
'use strict';
const cfg=window.DRINKWARE_CONFIG||{};
const canvas=window.designCanvas;
if(!canvas||!window.fabric)return;

const $=id=>document.getElementById(id);
const qa=(s,p=document)=>[...p.querySelectorAll(s)];
const currency=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(Number(n||0));
const csrf=()=>document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1]||'';
const catalogue=cfg.catalogue||[];
let selected=cfg.selected_key||catalogue[0]?.key||'ceramic-mug';
let side='front';
let colour=null;
let loadingState=false;
let drinkwareDesignId=window.EXISTING_DESIGN?.id||null;
const productStates={};

function product(){return catalogue.find(x=>x.key===selected)||catalogue[0]||{};}
function productImageUrl(p){return p?.image_url||p?.image||'';}
const imageCandidates=p=>[...(p?.image_urls||[]),p?.image_url,p?.image].filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i);
function firstWorkingImage(p,ok,fail){const urls=imageCandidates(p);let i=0;const next=()=>{if(i>=urls.length)return fail?.();const url=urls[i++],img=new Image();img.onload=()=>ok(url,img);img.onerror=next;img.src=url;};next();}
function bindFallbackImage(img,p){const urls=imageCandidates(p);let i=Math.max(0,urls.indexOf(img.src))+1;img.onerror=()=>{if(i<urls.length)img.src=urls[i++];else img.onerror=null;};}
function supportedSides(p=product()){
  const methods=p.methods||[];
  return ['front','back','wrap'].filter(x=>methods.includes(x));
}
function ensureProductState(key=selected){
  productStates[key] ||= {front:null,back:null,wrap:null};
  return productStates[key];
}
function userObjects(){return canvas.getObjects().filter(o=>!o.excludeFromExport&&!o.drinkwareGuide);}
function serialiseCurrent(){
  return {version:'5.3.0',objects:userObjects().map(o=>o.toObject(['objectId','name','fieldType','backgroundAsset','customerEditable']))};
}
function saveCurrent(){
  if(loadingState)return;
  ensureProductState()[side]=serialiseCurrent();
}
function areaFor(sideName=side,p=product()){
  return p.print_areas?.[sideName]||p.print_areas?.front||{left:210,top:220,width:300,height:260};
}
function clipForArea(a=areaFor()){
  return new fabric.Rect({left:a.left,top:a.top,width:a.width,height:a.height,absolutePositioned:true,selectable:false,evented:false});
}
function applyClip(o){
  if(!o||o.excludeFromExport||o.drinkwareGuide)return;
  o.clipPath=clipForArea();
  o.dirty=true;
}
function applyClips(){userObjects().forEach(applyClip);canvas.requestRenderAll();}
function removeHelpers(){canvas.getObjects().filter(o=>o.drinkwareGuide).forEach(o=>canvas.remove(o));}
function addGuide(){
  removeHelpers();
  const a=areaFor();
  const guide=new fabric.Rect({
    left:a.left,top:a.top,width:a.width,height:a.height,
    fill:'rgba(255,255,255,.06)',stroke:'#6848f5',strokeWidth:2,
    strokeDashArray:[10,7],selectable:false,evented:false,
    excludeFromExport:true,drinkwareGuide:true,name:`${side} printable area`
  });
  canvas.add(guide);
  canvas.bringToFront(guide);
  canvas.requestRenderAll();
  updateAreaLabel(a);
}
function updateAreaLabel(a){
  const label=$('drinkwareActiveArea');
  if(label)label.textContent=`${side.charAt(0).toUpperCase()+side.slice(1)} · ${Math.round(a.width)} × ${Math.round(a.height)} px`;
  updateDrinkwareContext();
}
function constrain(o){
  if(!o||o.drinkwareGuide||o.excludeFromExport)return;
  const a=areaFor();
  o.setCoords();
  let b=o.getBoundingRect(true,true);
  if(b.width>a.width||b.height>a.height){
    const ratio=Math.min(a.width/Math.max(b.width,1),a.height/Math.max(b.height,1));
    o.scaleX*=ratio;o.scaleY*=ratio;o.setCoords();b=o.getBoundingRect(true,true);
  }
  if(b.left<a.left)o.left+=a.left-b.left;
  if(b.top<a.top)o.top+=a.top-b.top;
  if(b.left+b.width>a.left+a.width)o.left-=b.left+b.width-(a.left+a.width);
  if(b.top+b.height>a.top+a.height)o.top-=b.top+b.height-(a.top+a.height);
  o.setCoords();applyClip(o);
}
function placeNewObject(o){
  if(!o||o.excludeFromExport||o.drinkwareGuide)return;
  const a=areaFor();
  const b=o.getBoundingRect(true,true);
  if(b.left<a.left||b.top<a.top||b.left+b.width>a.left+a.width||b.top+b.height>a.top+a.height){
    o.set({left:a.left+(a.width-o.getScaledWidth())/2,top:a.top+(a.height-o.getScaledHeight())/2});
  }
  constrain(o);
}
function backgroundTransform(p,img){
  const W=window.PRODUCT.width,H=window.PRODUCT.height;
  const t=p.preview||{};
  const maxW=t.max_width||W-28,maxH=t.max_height||H-28;
  const scale=Math.min(maxW/img.width,maxH/img.height);
  return {scale,left:W/2+(t.offset_x||0),top:H/2+(t.offset_y||0)};
}
function applyProductBackground(){
  const p=product();
  if(!imageCandidates(p).length)return;
  firstWorkingImage(p,(url,probe)=>{
    const img=new fabric.Image(probe);
    const t=backgroundTransform(p,img);
    img.set({originX:'center',originY:'center',left:t.left,top:t.top,scaleX:t.scale,scaleY:t.scale,
      flipX:side==='back',selectable:false,evented:false,excludeFromExport:true,name:'Drinkware product preview',sourceUrl:url});
    canvas.setBackgroundImage(img,()=>canvas.requestRenderAll());
  },()=>{
    canvas.setBackgroundImage(null,()=>canvas.requestRenderAll());
  });
  canvas.backgroundColor='#ffffff';
}
function restoreCurrent(){
  const data=ensureProductState()[side];
  loadingState=true;
  canvas.clear();
  canvas.backgroundColor='#ffffff';
  if(!data?.objects?.length){
    loadingState=false;applyProductBackground();addGuide();updateSideUI();return;
  }
  canvas.loadFromJSON(data,()=>{
    loadingState=false;
    applyProductBackground();applyClips();addGuide();updateSideUI();canvas.requestRenderAll();
  });
}
function setSide(next,force=false){
  if(!supportedSides().includes(next))next=supportedSides()[0]||'front';
  if(next===side&&!force)return;
  saveCurrent();side=next;
  if(['front','back','wrap'].includes(side)&&$('drinkwareBranding'))$('drinkwareBranding').value=side;
  restoreCurrent();
}
function updateSideUI(){
  qa('[data-drinkware-side],#drinkwareSideButtons [data-side]').forEach(b=>{
    const s=b.dataset.drinkwareSide||b.dataset.side;
    b.classList.toggle('active',s===side);
    b.hidden=!supportedSides().includes(s);
  });
  const badge=$('drinkwareViewName');if(badge)badge.textContent=side==='wrap'?'Full wrap':side.charAt(0).toUpperCase()+side.slice(1);
}
function updatePrice(){
  const p=product(),size=$('drinkwareSize')?.value||Object.keys(p.sizes||{})[0];
  const unit=(p.sizes||{})[size]||0,qty=Math.max(1,Number($('drinkwareQuantity')?.value)||1);
  if($('drinkwareUnitPrice'))$('drinkwareUnitPrice').textContent=currency(unit);
  if($('drinkwareTotal'))$('drinkwareTotal').textContent=currency(unit*qty);
  if($('quantity'))$('quantity').value=qty;
}
function updateOptions(){
  const p=product();
  const size=$('drinkwareSize');if(size)size.innerHTML=Object.keys(p.sizes||{}).map(s=>`<option>${s}</option>`).join('');
  colour=colour&&p.colours?.includes(colour)?colour:p.colours?.[0];
  const colours=$('drinkwareColours');if(colours){colours.innerHTML='';(p.colours||[]).forEach(c=>{const b=document.createElement('button');b.type='button';b.className='drinkware-colour'+(c===colour?' active':'');b.style.background=c;b.title=c;b.onclick=()=>{colour=c;qa('.drinkware-colour').forEach(x=>x.classList.toggle('active',x===b));};colours.appendChild(b);});}
  qa('#drinkwareBranding option').forEach(o=>o.disabled=!(p.methods||[]).includes(o.value));
  if($('drinkwareBranding')&&!(p.methods||[]).includes($('drinkwareBranding').value))$('drinkwareBranding').value=(p.methods||['front'])[0];
  if(!supportedSides().includes(side))side=supportedSides()[0]||'front';
  updatePrice();setSide(side,true);
}
function renderProducts(filter=''){
  const box=$('drinkwareProductGrid');if(!box)return;box.innerHTML='';
  catalogue.filter(p=>(p.name+' '+p.key).toLowerCase().includes(filter.toLowerCase())).forEach(p=>{
    const b=document.createElement('button');b.type='button';b.className='drinkware-product-card'+(p.key===selected?' active':'');
    b.innerHTML=`<img src="${productImageUrl(p)}" alt="${p.name}" loading="lazy"><b>${p.name}</b><small>${Object.keys(p.sizes||{}).join(' / ')}</small>`;
    const thumb=b.querySelector('img');if(thumb)bindFallbackImage(thumb,p);
    b.onclick=()=>{if(p.key===selected)return;saveCurrent();selected=p.key;colour=null;side='front';renderProducts($('drinkwareSearch')?.value||'');updateOptions();};box.appendChild(b);
  });
}
function completeDesignJSON(base={}){
  saveCurrent();
  const current=ensureProductState()[side]||serialiseCurrent();
  return {...base,version:3,pages:[{background:'#ffffff',objects:current.objects||[]}],drinkware:{selected_product:selected,active_side:side,colour,size:$('drinkwareSize')?.value||'',branding:$('drinkwareBranding')?.value||side,products:productStates}};
}
function loadSavedDesign(){
  const saved=window.INITIAL_TEMPLATE?.drinkware;
  if(!saved)return;
  if(saved.products&&typeof saved.products==='object')Object.assign(productStates,saved.products);
  if(saved.selected_product&&catalogue.some(p=>p.key===saved.selected_product))selected=saved.selected_product;
  side=saved.active_side||'front';colour=saved.colour||null;
}
function hideGuidesDuring(fn){
  const helpers=canvas.getObjects().filter(o=>o.drinkwareGuide),visibility=helpers.map(o=>o.visible);
  helpers.forEach(o=>o.visible=false);canvas.requestRenderAll();
  try{return fn();}finally{helpers.forEach((o,i)=>o.visible=visibility[i]);canvas.requestRenderAll();}
}
function installSaveAugmenter(){
  const nativeFetch=window.fetch.bind(window);
  window.fetch=async function(input,init={}){
    const url=typeof input==='string'?input:input?.url||'';
    if(url.includes('/api/save-design/')&&init.body){
      try{const body=JSON.parse(init.body);body.design_json=completeDesignJSON(body.design_json||{});body.quantity=$('drinkwareQuantity')?.value||body.quantity;init={...init,body:JSON.stringify(body)};}catch(e){console.warn('Drinkware save augmentation skipped',e);}
    }
    return nativeFetch(input,init);
  };
}
function installExportProtection(){
  const native=canvas.toDataURL.bind(canvas);
  canvas.toDataURL=function(options){return hideGuidesDuring(()=>native(options));};
}
function injectWorkspaceSwitcher(){ return; }
function bind(){
  $('drinkwareSearch')?.addEventListener('input',e=>renderProducts(e.target.value));
  qa('#drinkwareSideButtons [data-side]').forEach(b=>b.addEventListener('click',()=>setSide(b.dataset.side)));
  $('drinkwareSize')?.addEventListener('change',updatePrice);
  $('drinkwareQuantity')?.addEventListener('input',updatePrice);
  $('drinkwareBranding')?.addEventListener('change',e=>{if(['front','back','wrap'].includes(e.target.value))setSide(e.target.value);});
  canvas.on('object:moving',e=>constrain(e.target));
  canvas.on('object:scaling',e=>constrain(e.target));
  canvas.on('object:rotating',e=>constrain(e.target));
  canvas.on('object:modified',e=>{constrain(e.target);saveCurrent();});
  canvas.on('selection:created',updateSelectionToolbar);canvas.on('selection:updated',updateSelectionToolbar);canvas.on('selection:cleared',updateSelectionToolbar);
  canvas.on('object:added',e=>{if(!loadingState&&e.target&&!e.target.excludeFromExport&&!e.target.drinkwareGuide)setTimeout(()=>{placeNewObject(e.target);addGuide();saveCurrent();},0);});
}


function updateDrinkwareContext(){
  const p=product(),a=areaFor();
  const name=$('drinkwareContextName'),details=$('drinkwareContextDetails');
  if(name)name.textContent=p.name||'Drinkware product';
  if(details)details.textContent=`${side==='wrap'?'Full wrap':side.charAt(0).toUpperCase()+side.slice(1)} print · ${Math.round(a.width)} × ${Math.round(a.height)} px`;
}
function updateSelectionToolbar(){
  const toolbar=$('contextToolbar'),obj=canvas.getActiveObject();if(!toolbar)return;
  toolbar.classList.toggle('has-selection',!!obj);
  toolbar.classList.toggle('selection-text',!!obj&&['i-text','textbox','text'].includes(obj.type));
  toolbar.classList.toggle('selection-object',!!obj&&!['i-text','textbox','text'].includes(obj.type));
}
function installArrangeDropdown(){
  const root=$('arrangeDropdown'),trigger=$('arrangeMenuBtn'),menu=$('arrangeMenu');if(!root||!trigger||!menu)return;
  const place=()=>{const r=trigger.getBoundingClientRect(),w=menu.offsetWidth||310;menu.style.left=Math.max(12,Math.min(window.innerWidth-w-12,r.right-w))+'px';menu.style.top=(r.bottom+7)+'px';};
  trigger.addEventListener('click',e=>{e.stopPropagation();root.classList.toggle('open');trigger.setAttribute('aria-expanded',root.classList.contains('open'));if(root.classList.contains('open'))requestAnimationFrame(place);});
  menu.addEventListener('click',()=>{root.classList.remove('open');trigger.setAttribute('aria-expanded','false');});
  document.addEventListener('click',e=>{if(!root.contains(e.target)){root.classList.remove('open');trigger.setAttribute('aria-expanded','false');}});
  window.addEventListener('resize',()=>{if(root.classList.contains('open'))place();});
}

loadSavedDesign();
ensureProductState();
injectWorkspaceSwitcher();
installSaveAugmenter();
installExportProtection();
bind();
installArrangeDropdown();
updateSelectionToolbar();
renderProducts();
updateOptions();
setTimeout(()=>window.dispatchEvent(new Event('resize')),120);
})();
