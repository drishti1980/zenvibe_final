(function () {
"use strict";

const PRODUCT = window.PRODUCT || {};
const CATALOG = window.TEMPLATE_CATALOG || [];
let currentPageIndex = 0;
let pages = [];

function getCanvas() {
    return window.canvas || window.fabricCanvas || window.editorCanvas || null;
}
function isCanopy() {
    const n = String(PRODUCT.name || PRODUCT.product_name || "").toLowerCase();
    const c = String(PRODUCT.category || PRODUCT.category_name || "").toLowerCase();
    const cfg = PRODUCT.customizer_config || window.ZV_PRODUCT_CONFIG || {};
    return cfg.editorType === "canopy" || n.includes("canopy") || n.includes("tent") ||
           c.includes("canopy") || c.includes("tent");
}
if (!isCanopy()) return;

function num(v, fallback) {
    v = Number(v);
    return Number.isFinite(v) && v > 0 ? v : fallback;
}
function productPhysical() {
    const name = String(PRODUCT.name || "").toLowerCase();
    const pw = num(PRODUCT.width, name.includes("10x20") ? 240 : 120);
    const ph = num(PRODUCT.height, 120);
    return {w: pw, h: ph};
}
function normalizePage(p, i) {
    p = p || {};
    const phys = productPhysical();
    let physicalWidth = num(p.physicalWidth, null);
    let physicalHeight = num(p.physicalHeight, null);

    if (!physicalWidth || !physicalHeight) {
        if (i === 0) {
            physicalWidth = phys.w; physicalHeight = phys.h;
        } else if (i === 5) {
            physicalWidth = phys.w >= 200 ? 233 : 117; physicalHeight = 80;
        } else if (i === 6) {
            physicalWidth = 117; physicalHeight = 40;
        } else {
            physicalWidth = phys.w >= 200 && (i === 1 || i === 2) ? 233 : 117;
            physicalHeight = 14;
        }
    }

    return {
        name: p.name || ["Canopy Top","Front Valance","Back Valance","Left Valance",
                         "Right Valance","Full Back Wall","Side / Half Wall"][i] || ("Page " + (i+1)),
        canvasWidth: num(p.canvasWidth, num(p.width, 1200)),
        canvasHeight: num(p.canvasHeight, num(p.height, 1200)),
        physicalWidth: physicalWidth,
        physicalHeight: physicalHeight,
        unit: p.unit || "in",
        background: p.background || "#ffffff",
        objects: Array.isArray(p.objects) ? p.objects : []
    };
}
function normalizeTemplate(raw) {
    const d = (raw && (raw.json_data || raw.json || raw.data)) || raw || {};
    if (!Array.isArray(d.pages) || !d.pages.length) return null;
    return {
        template_type: "canopy-multipage",
        name: d.templateName || d.name || "Canopy template",
        pages: d.pages.map(normalizePage)
    };
}

function hideOldPrintArea() {
    document.querySelectorAll(".zv-live-print-area,.zv-print-area-label,.editable-print-area,[data-print-area-overlay],[data-zv-print-area]")
        .forEach(el => el.style.display = "none");
}
function cleanRulerLabels() {
    document.querySelectorAll(".zv-ruler-label,.ruler-label,[data-ruler-label]").forEach((el,index) => {
        if (index % 5 !== 0) el.style.display = "none";
    });
}
function buildNavigator() {
    if (document.getElementById("zv-canopy-surface-nav")) return;
    const nav = document.createElement("div");
    nav.id = "zv-canopy-surface-nav";
    nav.innerHTML = '<button type="button" id="zv-canopy-prev">↑</button>' +
                    '<div id="zv-canopy-counter">1 / 7</div>' +
                    '<button type="button" id="zv-canopy-next">↓</button>' +
                    '<button type="button" id="zv-canopy-reset">↻</button>';
    const workspace = document.querySelector(".editor-workspace,.canvas-stage,.workspace") || document.body;
    workspace.appendChild(nav);
    document.getElementById("zv-canopy-prev").onclick = () => changePage(-1);
    document.getElementById("zv-canopy-next").onclick = () => changePage(1);
    document.getElementById("zv-canopy-reset").onclick = () => loadPage(currentPageIndex);
}
function fitCanvasToWorkspace(canvas,page) {
    const parent = canvas.wrapperEl?.parentElement || canvas.lowerCanvasEl?.parentElement;
    if (!parent) return;
    const aw = Math.max(300,parent.clientWidth-120), ah = Math.max(300,parent.clientHeight-100);
    const cw = num(page.canvasWidth,1200), ch = num(page.canvasHeight,1200);
    const scale = Math.min(aw/cw,ah/ch,1);
    canvas.setDimensions({width:cw,height:ch},{backstoreOnly:true});
    canvas.setDimensions({width:Math.round(cw*scale),height:Math.round(ch*scale)},{cssOnly:true});
    canvas.calcOffset(); canvas.requestRenderAll();
}
function updatePhysicalProfile(page) {
    window.ZV_EDITOR_PROFILE = {
        ...(window.ZV_EDITOR_PROFILE || {}),
        physicalWidth: page.physicalWidth, physicalHeight: page.physicalHeight,
        unit: page.unit || "in", canvasWidth: page.canvasWidth, canvasHeight: page.canvasHeight,
        printArea:{left:0,top:0,width:100,height:100}
    };
    window.dispatchEvent(new CustomEvent("zv:editor-profile-change",{detail:window.ZV_EDITOR_PROFILE}));
}
function updateCounter(page) {
    const c=document.getElementById("zv-canopy-counter");
    if(c) c.innerHTML="<strong>"+(currentPageIndex+1)+" / "+pages.length+"</strong><small>"+page.name+"</small>";
}
function loadPage(index) {
    const canvas=getCanvas();
    if(!canvas || !pages.length) return;
    currentPageIndex=Math.max(0,Math.min(pages.length-1,index));
    const page=pages[currentPageIndex];
    canvas.clear();
    canvas.setWidth(page.canvasWidth); canvas.setHeight(page.canvasHeight);
    canvas.backgroundColor=page.background || "#fff";
    canvas.loadFromJSON({version:"5.3.0",objects:page.objects||[],background:page.background||"#fff"},function(){
        canvas.renderAll(); fitCanvasToWorkspace(canvas,page); updateCounter(page);
        updatePhysicalProfile(page); hideOldPrintArea(); cleanRulerLabels();
    });
}
function changePage(dir) {
    if(!pages.length)return;
    let n=currentPageIndex+dir;
    if(n<0)n=pages.length-1;
    if(n>=pages.length)n=0;
    loadPage(n);
}
function activateTemplate(raw) {
    const d=normalizeTemplate(raw);
    if(!d)return false;
    pages=d.pages; currentPageIndex=0; buildNavigator(); loadPage(0);
    return true;
}

/* ---------- REAL TEMPLATE PANEL ---------- */
function esc(s){return String(s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function openTemplate(id) {
    const u=new URL(location.href);
    u.searchParams.delete("design");
    u.searchParams.set("template",id);
    u.searchParams.set("mode","template");
    location.href=u.toString();
}
function showPanel(panelId) {
    document.querySelectorAll(".rail-tab").forEach(b=>b.classList.toggle("active",b.dataset.panel===panelId));
    document.querySelectorAll(".studio-panel-section").forEach(p=>{
        const on=p.id===panelId; p.classList.toggle("active",on); p.style.display=on?"":"none";
    });
}
function buildTemplateGallery() {
    const tab=document.querySelector('.rail-tab[data-panel="templatesPanel"]');
    const panel=document.getElementById("templatesPanel");
    if(!tab || !panel) return;

    tab.style.display="";
    tab.onclick=()=>showPanel("templatesPanel");

    let host=document.getElementById("zv-canopy-template-grid");
    if(!host){
        const old=document.getElementById("templateSuggestions");
        host=document.createElement("div");
        host.id="zv-canopy-template-grid";
        host.className="zv-canopy-template-grid";
        if(old) old.replaceWith(host); else panel.appendChild(host);
    }

    const list=CATALOG.filter(t=>/^Canopy V1[23] - /i.test(t.name||""));
    host.innerHTML="";
    list.forEach(t=>{
        const b=document.createElement("button");
        b.type="button"; b.className="zv-canopy-template-card";
        b.dataset.search=String(t.name||"").toLowerCase();
        b.innerHTML=(t.preview_url?'<img src="'+esc(t.preview_url)+'" alt="">':'<div class="zv-canopy-template-placeholder"></div>')+
                    '<strong>'+esc(String(t.name||"").replace(/^Canopy V1[23] - /i,""))+'</strong>'+
                    '<span>7 coordinated surfaces</span>';
        b.onclick=()=>openTemplate(t.id);
        host.appendChild(b);
    });
    if(!list.length){
        host.innerHTML='<div class="zv-canopy-template-empty"><b>No canopy templates reached TEMPLATE_CATALOG.</b><br>Database templates exist, so check live_templates_for(product).</div>';
    }

    const search=panel.querySelector('input[type="search"],input[placeholder*="Search"],input');
    if(search){
        search.oninput=()=>{const q=search.value.toLowerCase();host.querySelectorAll(".zv-canopy-template-card").forEach(x=>x.hidden=q&&!x.dataset.search.includes(q));};
    }

    // Blank canopy editor must open on Templates, not Elements.
    const mode=new URL(location.href).searchParams.get("mode") || "blank";
    if(mode==="blank" || !new URL(location.href).searchParams.get("template")){
        showPanel("templatesPanel");
    }
}

/* Public compatibility hook */
window.ZVCanopyV10={activateTemplate,loadPage,nextPage(){changePage(1)},previousPage(){changePage(-1)},
 getPages(){return pages},getCurrentPage(){return pages[currentPageIndex]},getCurrentPageIndex(){return currentPageIndex}};

function boot() {
    hideOldPrintArea(); buildNavigator(); buildTemplateGallery();

    // CRITICAL FIX: editor() puts selected template JSON in INITIAL_TEMPLATE.
    // Old V10 never activated it.
    const initial=window.INITIAL_TEMPLATE || {};
    if(initial && Array.isArray(initial.pages) && initial.pages.length){
        activateTemplate(initial);
    }

    // Retry once because editor.js/fabric may initialise after this defer script.
    setTimeout(()=>{
        buildTemplateGallery();
        if(pages.length && getCanvas()) loadPage(currentPageIndex);
    },350);
}
if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",boot); else boot();

new MutationObserver(()=>hideOldPrintArea()).observe(document.body,{childList:true,subtree:true});
window.addEventListener("resize",()=>{const c=getCanvas(),p=pages[currentPageIndex];if(c&&p)fitCanvasToWorkspace(c,p);});
})();