
(function(){
"use strict";
function isCanopy(){const p=window.PRODUCT||{},s=((p.name||"")+" "+(p.category||"")).toLowerCase();return /canopy|tent/.test(s)}
if(!isCanopy())return;
const qs=s=>document.querySelector(s),qsa=s=>[...document.querySelectorAll(s)];
function esc(s){return String(s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
function openT(id){const u=new URL(location.href);u.searchParams.delete("design");u.searchParams.set("template",id);u.searchParams.set("mode","template");location.href=u.toString()}
function activate(){
 const tab=qs('.rail-tab[data-panel="templatesPanel"],#zvV14TemplatesTab'),panel=qs('#templatesPanel,#zvV14TemplatesPanel');
 if(!tab||!panel)return;
 qsa(".rail-tab").forEach(x=>x.classList.remove("active"));tab.classList.add("active");
 qsa(".studio-panel-section").forEach(x=>{x.classList.remove("active");x.style.display="none"});
 panel.classList.add("active");panel.style.display="block";
}
function ensure(){
 const rail=qs(".studio-rail");if(!rail)return;
 let tab=qs('.rail-tab[data-panel="templatesPanel"]');
 if(!tab){tab=document.createElement("button");tab.type="button";tab.id="zvV14TemplatesTab";tab.className="rail-tab";tab.dataset.panel="templatesPanel";tab.innerHTML="<span>▦</span><b>Templates</b>";rail.prepend(tab)}
 tab.hidden=false;tab.style.display="flex";
 let panel=qs("#templatesPanel");
 if(!panel){const cur=qs(".studio-panel-section");if(!cur)return;panel=document.createElement("section");panel.id="templatesPanel";panel.className="studio-panel-section";cur.parentElement.prepend(panel)}
 panel.hidden=false;
 let box=qs("#zvV14TemplateBox");
 if(!box){box=document.createElement("div");box.id="zvV14TemplateBox";panel.innerHTML='<div class="panel-heading"><div><small>DESIGN STUDIO</small><h2>CANOPY TEMPLATES</h2></div></div>';panel.appendChild(box)}
 const list=(window.TEMPLATE_CATALOG||[]).filter(t=>/^Canopy V14 - /i.test(t.name||""));
 box.innerHTML='<input id="zvV14Search" class="zv14-search" placeholder="Search 20 canopy designs"><div id="zvV14Grid" class="zv14-grid"></div>';
 const grid=qs("#zvV14Grid");
 list.forEach(t=>{const b=document.createElement("button");b.type="button";b.className="zv14-card";b.dataset.n=(t.name||"").toLowerCase();b.innerHTML=(t.preview_url?'<img src="'+esc(t.preview_url)+'" alt="">':'<div class="zv14-ph"></div>')+'<strong>'+esc((t.name||"").replace(/^Canopy V14 - /i,""))+'</strong><span>7 redesigned canopy surfaces</span>';b.onclick=()=>openT(t.id);grid.appendChild(b)});
 if(!list.length)grid.innerHTML='<div class="zv14-empty"><b>No V14 canopy designs reached this editor.</b><br>Run seed_canopy_redesign_v14 --replace</div>';
 qs("#zvV14Search").oninput=e=>{const q=e.target.value.toLowerCase();qsa(".zv14-card").forEach(c=>c.hidden=q&&!c.dataset.n.includes(q))};
 tab.onclick=activate;
 const u=new URL(location.href);if(u.searchParams.get("mode")!=="template")activate();
 const init=window.INITIAL_TEMPLATE||{};if(Array.isArray(init.pages)&&init.pages.length&&window.ZVCanopyV10?.activateTemplate)window.ZVCanopyV10.activateTemplate(init);
}
function boot(){ensure();setTimeout(ensure,250);setTimeout(ensure,900)}
document.readyState==="loading"?document.addEventListener("DOMContentLoaded",boot):boot();
})();
