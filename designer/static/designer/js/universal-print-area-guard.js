/* ZENVIBE_UNIVERSAL_PRINT_AREA_GUARD_V1
   Admin EditorSizeProfile is authoritative for ruler, canvas and editable print region. */
(function(){
  'use strict';
  function profile(){ return window.ZV_EDITOR_PROFILE || null; }
  function canvas(){ return window.designCanvas || null; }

  function mountOverlay(){
    const p=profile();
    const wrap=document.getElementById('canvasWrap') || document.querySelector('.canvas-wrap');
    if(!p || !wrap || !p.printArea) return;
    wrap.style.position='relative';
    let box=wrap.querySelector('.zv-live-print-area');
    if(!box){
      box=document.createElement('div');
      box.className='zv-live-print-area';
      box.innerHTML='<span>Editable / print area</span>';
      wrap.appendChild(box);
    }
    const a=p.printArea;
    Object.assign(box.style,{left:a.left+'%',top:a.top+'%',width:a.width+'%',height:a.height+'%'});
    const label=document.getElementById('zvArtboardSizeLabel');
    if(label){
      const n=(v)=>Number(v).toFixed(Number(v)%1?2:0);
      label.textContent=n(p.physicalWidth)+' × '+n(p.physicalHeight)+' '+p.unit;
    }
  }

  function areaPx(){
    const p=profile();
    if(!p || !p.printArea) return null;
    return {
      left:p.canvasWidth*p.printArea.left/100,
      top:p.canvasHeight*p.printArea.top/100,
      width:p.canvasWidth*p.printArea.width/100,
      height:p.canvasHeight*p.printArea.height/100
    };
  }

  function clampObject(o){
    const c=canvas(), a=areaPx();
    if(!c || !a || !o || o.customerEditable===false || o.backgroundAsset || o.exactVisualMaster || o.fullBleed || o.allowOutsidePrintArea) return;
    o.setCoords();
    let b=o.getBoundingRect(true,true);
    let dx=0,dy=0;
    const right=a.left+a.width,bottom=a.top+a.height;
    if(b.width>a.width || b.height>a.height){
      const sx=Math.min(1,a.width/Math.max(1,b.width)), sy=Math.min(1,a.height/Math.max(1,b.height)), s=Math.min(sx,sy);
      if(s<1){o.scaleX*=s;o.scaleY*=s;o.setCoords();b=o.getBoundingRect(true,true);}
    }
    if(b.left<a.left)dx=a.left-b.left;
    if(b.top<a.top)dy=a.top-b.top;
    if(b.left+b.width>right)dx=right-(b.left+b.width);
    if(b.top+b.height>bottom)dy=bottom-(b.top+b.height);
    if(dx||dy){o.left+=dx;o.top+=dy;o.setCoords();}
  }

  function hideEmptyTemplates(){
    const items=Array.isArray(window.TEMPLATE_CATALOG)?window.TEMPLATE_CATALOG:[];
    if(items.length) return;
    const tab=document.querySelector('.rail-tab[data-panel="templatesPanel"]');
    const panel=document.getElementById('templatesPanel');
    if(tab)tab.style.display='none';
    if(panel && panel.classList.contains('active')){
      panel.classList.remove('active');
      const next=document.getElementById('elementsPanel');
      if(next)next.classList.add('active');
      const title=document.getElementById('panelTitle');if(title)title.textContent='Elements';
      document.querySelector('.rail-tab[data-panel="elementsPanel"]')?.classList.add('active');
    }
  }

  function bind(){
    mountOverlay();hideEmptyTemplates();
    const c=canvas();
    if(!c || c.__zvPrintAreaBound)return;
    c.__zvPrintAreaBound=true;
    c.on('object:moving',e=>clampObject(e.target));
    c.on('object:scaling',e=>clampObject(e.target));
    c.on('object:modified',e=>clampObject(e.target));
    c.on('object:added',e=>{
      const o=e.target;
      if(o && o.customerEditable!==false && !o.excludeFromExport)setTimeout(()=>clampObject(o),0);
    });
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(bind,0));
  else setTimeout(bind,0);
  document.addEventListener('zenvibe:profile-ready',()=>setTimeout(bind,0));
  window.addEventListener('resize',mountOverlay);
})();
