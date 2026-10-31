/* ZenVibe universal export. Isolated renderer: never changes the live Fabric canvas. */
(function(w){
'use strict';
const q=s=>document.querySelector(s), safe=s=>String(s||'zenvibe-design').replace(/[^a-z0-9_-]+/gi,'-').slice(0,75);
const wait=()=>new Promise(r=>setTimeout(r,0));
function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000)}
function fabricJson(page){
 const data=page.json||page;
 if(data.objects && !data.version){
  return {version:'5.3.0',background:data.background||'#fff',objects:data.objects.map(o=>{
   const x={...o};
   if(x.type==='text' && !x.fontFamily)x.fontFamily=x.font||'Arial';
   if(x.type==='image' && !x.src)x.src=x.baseSrc;
   return x;
  })};
 }
 return data;
}
async function render(page,index,settings){
 const f=w.fabric;if(!f?.StaticCanvas)throw Error('Fabric.js is unavailable');
 const width=Number(page.width),height=Number(page.height);
 const wi=Number(page.widthIn),hi=Number(page.heightIn);
 if(!(width>0&&height>0&&wi>0&&hi>0))throw Error('Missing admin dimensions on page '+(index+1));
 const el=document.createElement('canvas'),c=new f.StaticCanvas(el,{width,height,renderOnAddRemove:false});
 try{
  const data=fabricJson(page);
  // Fabric clips the final export using the same teardrop die as the editor.
  // Apply it again for *every* page, including saved non-active pages, because
  // those pages may use the simpler ZenVibe object serialization.
  const teardrop=page.printShape==='teardrop';
  if(teardrop){
   data.background='rgba(0,0,0,0)';
   data.backgroundColor='rgba(0,0,0,0)';
  }
  await new Promise((resolve,reject)=>{
   let settled=false;
   const done=()=>{if(!settled){settled=true;resolve()}};
   try{const result=c.loadFromJSON(data,done);if(result?.then)result.then(done,reject)}catch(e){reject(e)}
  });
  c.setWidth(width);c.setHeight(height);
  if(teardrop){
   const coords=[
    [.08,.995],[.08,.43],[.10,.31],[.17,.20],[.28,.12],
    [.42,.065],[.59,.035],[.75,.04],[.88,.09],[.97,.17],
    [.985,.26],[.955,.34],[.89,.44],[.79,.56],[.67,.69],
    [.53,.81],[.37,.92]
   ];
   const points=coords.map(([x,y])=>({x:x*width,y:y*height}));
   c.backgroundColor='rgba(0,0,0,0)';
   c.getObjects().forEach(o=>{
    if(o.excludeFromExport)return;
    o.clipPath=new f.Polygon(points,{
      absolutePositioned:true,fill:'#000',selectable:false,evented:false
    });
    o.dirty=true;
   });
  }
  c.renderAll();
  return {canvas:c,width,height,wi,hi};
 }catch(e){c.dispose();throw e}
}
// Canva-style raster download: one complete image per page. The output size
// is independent of product physical inches and of the editor's screen zoom.
async function rasterImage(c,width,height,scale,format,filename,status){
 const MAX_SIDE=8192,MAX_PIXELS=40000000;
 const requested=Math.max(.25,Number(scale)||1);
 const safeScale=Math.min(requested,MAX_SIDE/Math.max(width,height),Math.sqrt(MAX_PIXELS/(width*height)));
 if(!(safeScale>0))throw Error('Invalid design dimensions');
 const pw=Math.max(1,Math.round(width*safeScale)),ph=Math.max(1,Math.round(height*safeScale));
 status.textContent='Rendering '+pw+' × '+ph+' px…';
 await wait();
 const url=c.toDataURL({format:format==='jpg'?'jpeg':'png',quality:.98,multiplier:safeScale,enableRetinaScaling:false});
 const blob=await (await fetch(url)).blob();
 return {blob,width:pw,height:ph,limited:safeScale<requested-.001};
}
// Production preflight: check native image resolution at final physical size.
// Vector text/paths are not subject to DPI limits.
function preflight(c,width,height,wi,hi){
 const warnings=[];
 const dpiTarget=100; // Advisory only: printer specifications take precedence.
 c.getObjects().forEach((o,index)=>{
  if(o.type!=='image')return;
  const sourceW=Number(o._originalElement?.naturalWidth||o._element?.naturalWidth||o.width)||0;
  const sourceH=Number(o._originalElement?.naturalHeight||o._element?.naturalHeight||o.height)||0;
  const scaledW=Math.abs(Number(o.getScaledWidth?.()||o.width)||0);
  const scaledH=Math.abs(Number(o.getScaledHeight?.()||o.height)||0);
  if(!(sourceW>0&&sourceH>0&&scaledW>0&&scaledH>0))return;
  const effective=Math.min(sourceW/(scaledW/width*wi),sourceH/(scaledH/height*hi));
  if(effective<dpiTarget)warnings.push('Image '+(index+1)+': approximately '+Math.round(effective)+' effective DPI at print size');
 });
 return warnings;
}
async function run(pages,ids,format,mode,scale,name,status){
 // JPEG has no alpha channel. A shaped flag exported as JPEG would turn the
 // transparent die-cut surroundings into a misleading rectangular white area.
 if(format==='jpg' && ids.some(i=>pages[i]?.printShape==='teardrop'))
  throw Error('Teardrop flags need a transparent print file. Choose PNG, SVG, or PDF instead of JPG.');
 if(format==='pdf'&&!w.jspdf?.jsPDF)throw Error('PDF engine did not load. Check your internet connection or browser blockers, then refresh.');
 const zipNeeded=mode==='separate'||(format!=='pdf'&&ids.length>1);
 if(zipNeeded&&!w.JSZip)throw Error('ZIP library unavailable');
 const zip=zipNeeded?new w.JSZip():null;
 let pdf=null;
 for(const i of ids){
  status.textContent='Rendering page '+(i+1)+' of '+pages.length+'…';await wait();
  const {canvas:c,width,height,wi,hi}=await render(pages[i],i);
  try{
   if(format==='pdf'){
    const warnings=preflight(c,width,height,wi,hi);
    if(warnings.length){
     const ok=w.confirm('Print quality warning for page '+(i+1)+':\\n'+warnings.slice(0,8).join('\\n')+'\\n\\nThese images may look blurry when printed. Continue anyway?');
     if(!ok)throw Error('Print export cancelled: replace low-resolution artwork first');
    }
   }
   const filename=name+'-page-'+String(i+1).padStart(2,'0');
   let blob=null,ext=format;
   if(format==='svg'){
    blob=new Blob([c.toSVG({suppressPreamble:false,width:wi+'in',height:hi+'in',viewBox:{x:0,y:0,width,height}})],{type:'image/svg+xml;charset=utf-8'});
   }else if(format==='pdf'){
    // svg2pdf converts supported Fabric vectors/text into PDF vector instructions.
    // Embedded photographs remain raster images at their native resolution.
    if(!w.jspdf?.jsPDF?.API?.svg)throw Error('Vector PDF engine did not load. Refresh the page and check browser network errors.');
    const orientation=wi>hi?'landscape':'portrait';
    // jsPDF internally limits user units; 120in is below the standard 200in PDF page limit.
    let target;
    if(mode==='combined'){
      if(!pdf)pdf=new w.jspdf.jsPDF({unit:'in',format:[wi,hi],orientation,compress:true});
      else pdf.addPage([wi,hi],orientation);
      target=pdf;
    }else target=new w.jspdf.jsPDF({unit:'in',format:[wi,hi],orientation,compress:true});
    const svgText=c.toSVG({suppressPreamble:false,width:wi+'in',height:hi+'in',viewBox:{x:0,y:0,width,height}});
    const parsed=new DOMParser().parseFromString(svgText,'image/svg+xml');
    if(parsed.querySelector('parsererror'))throw Error('Invalid vector artwork on page '+(i+1));
    const svg=parsed.documentElement;
    svg.setAttribute('width',String(wi*96));
    svg.setAttribute('height',String(hi*96));
    // SVG user coordinates stay at the editor's logical size; physical PDF size
    // is determined by the Admin inch ruler, never by the editor zoom.
    svg.setAttribute('viewBox','0 0 '+width+' '+height);
    await target.svg(svg,{x:0,y:0,width:wi,height:hi});
    if(mode!=='combined')blob=target.output('blob');
   }else{
    const result=await rasterImage(c,width,height,scale,format,filename,status);
    blob=result.blob;
    if(result.limited)status.textContent='Image size capped at '+result.width+' × '+result.height+' px for browser safety';
   }

   if(blob){if(zip)zip.file(filename+'.'+ext,blob);else save(blob,filename+'.'+ext)}
  }finally{c.dispose()}
 }
 if(pdf)save(pdf.output('blob'),name+'.pdf');
 if(zip)save(await zip.generateAsync({type:'blob',compression:'DEFLATE'}),name+'-pages.zip');
}
function install(config){
 const button=q(config.button||'#downloadBtn');
 if(!button)return;
 let overlay=null;
 async function open(){
  const pages=await config.getPages();
  if(!Array.isArray(pages)||!pages.length)throw Error('No pages available');
  const current=Math.max(0,Math.min(pages.length-1,Number(config.getCurrentPage())||0));
  overlay?.remove();
  overlay=document.createElement('div');overlay.className='zv-universal-export';
  overlay.innerHTML='<section role="dialog" aria-modal="true" aria-label="Download design"><header><strong>Download design</strong><button data-close type="button" aria-label="Close">×</button></header><label>Format<select data-format><option value="pdf">PDF Print</option><option value="png">PNG (lossless)</option><option value="jpg">JPG</option><option value="svg">SVG (vector where supported)</option></select></label><label>Pages<select data-scope><option value="all">All pages ('+pages.length+')</option><option value="current">Current page ('+(current+1)+')</option><option value="selected">Select pages</option></select></label><div data-pages hidden></div><label>Delivery<select data-mode><option value="combined">Combined PDF / ZIP images</option><option value="separate">Separate files (ZIP)</option></select></label><label data-dpi-label>Image size<select data-dpi><option value="1">1× Original</option><option value="2" selected>2× High quality</option><option value="3">3× Extra high</option><option value="4">4× Maximum</option></select></label><p>For production printing, choose PDF Print or SVG. Supported text and paths stay scalable. PDF checks raster image resolution against physical print dimensions and warns about low-quality images.</p><footer><span data-status role="status"></span><button type="button" data-go>Download</button></footer></section>';
  document.body.appendChild(overlay);
  const el=s=>overlay.querySelector(s);
  const choices=el('[data-pages]');
  pages.forEach((p,i)=>{const label=document.createElement('label'),box=document.createElement('input');box.type='checkbox';box.value=i;box.checked=true;label.append(box,document.createTextNode(' '+(p.name||'Page '+(i+1))));choices.appendChild(label)});
  el('[data-close]').onclick=()=>{overlay.remove();overlay=null};
  overlay.onclick=e=>{if(e.target===overlay){overlay.remove();overlay=null}};
  el('[data-scope]').onchange=()=>choices.hidden=el('[data-scope]').value!=='selected';
  const updateFormat=()=>{el('[data-dpi-label]').hidden=['pdf','svg'].includes(el('[data-format]').value)};
  el('[data-format]').onchange=updateFormat;updateFormat();
  el('[data-go]').onclick=async()=>{
   const go=el('[data-go]'),status=el('[data-status]'),scope=el('[data-scope]').value;
   const ids=scope==='current'?[current]:scope==='selected'?[...choices.querySelectorAll('input:checked')].map(x=>Number(x.value)):pages.map((_,i)=>i);
   if(!ids.length){status.textContent='Select at least one page';return}
   go.disabled=true;
   try{await run(pages,ids,el('[data-format]').value,el('[data-mode]').value,Number(el('[data-dpi]').value),safe(config.getFilename?.()||'zenvibe-design'),status);status.textContent='Download ready'}
   catch(e){console.error('Zenvibe export',e);status.textContent=e.message||'Export failed'}
   finally{go.disabled=false}
  };
 }
 button.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();open().catch(err=>alert(err.message))},true);
 return {open};
}
const style=document.createElement('style');style.textContent='.zv-universal-export{position:fixed;inset:0;z-index:999999;background:#121529b5;display:grid;place-items:center;padding:15px}.zv-universal-export section{box-sizing:border-box;width:min(470px,100%);max-height:92vh;overflow:auto;border-radius:16px;background:#fff;color:#222;padding:22px;box-shadow:0 24px 70px #0004;font:14px Arial,sans-serif}.zv-universal-export header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;font-size:20px}.zv-universal-export header button{border:0;background:transparent;font-size:28px;cursor:pointer}.zv-universal-export section>label{display:block;font-weight:600;margin:12px 0}.zv-universal-export select{display:block;box-sizing:border-box;width:100%;padding:10px;margin-top:7px;border:1px solid #d4d6df;border-radius:8px;background:#fff}.zv-universal-export [data-pages]{max-height:135px;overflow:auto;border:1px solid #ddd;border-radius:8px;padding:8px}.zv-universal-export [data-pages] label{display:block;margin:6px}.zv-universal-export [hidden]{display:none!important}.zv-universal-export p{font-size:12px;line-height:1.5;color:#666}.zv-universal-export footer{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-top:20px}.zv-universal-export footer button{border:0;border-radius:8px;background:#5537c4;color:#fff;padding:12px 18px;cursor:pointer}.zv-universal-export footer button:disabled{opacity:.5}';
document.head.appendChild(style);
w.ZenvibeExport={install};
})(window);
