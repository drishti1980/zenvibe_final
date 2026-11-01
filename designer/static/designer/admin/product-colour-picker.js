(function(){
"use strict";
function upgrade(root){
 (root||document).querySelectorAll('input[name$="-hex_value"]').forEach(field=>{
  if(field.closest(".empty-form") || field.name.includes("__prefix__") || field.dataset.zvPicker)return;
  field.dataset.zvPicker="1";
  const shell=document.createElement("span");shell.className="zv-colour-input";
  const swatch=document.createElement("input");swatch.type="color";swatch.className="zv-colour-swatch";
  swatch.setAttribute("aria-label","Choose colour visually");swatch.value=/^#[0-9a-f]{6}$/i.test(field.value)?field.value:"#ffffff";
  field.parentNode.insertBefore(shell,field);shell.append(swatch,field);
  field.placeholder="#RRGGBB";field.setAttribute("aria-label","Colour hex value");
  swatch.addEventListener("input",()=>{field.value=(swatch.value + (/^#[0-9a-f]{8}$/i.test(field.value) ? field.value.slice(7) : "")).toUpperCase();field.dispatchEvent(new Event("input",{bubbles:true}));});
  field.addEventListener("input",()=>{let v=field.value.trim();if(/^#[0-9a-f]{6}$/i.test(v))swatch.value=v;});
 });
}
function ready(){
 upgrade(document);
 document.addEventListener("formset:added",e=>upgrade(e.target));
 // Django's admin fires a jQuery event on some versions; observer handles both.
 const host=document.querySelector("body.model-product.change-form");
 if(host){let pending=false;new MutationObserver(()=>{if(!pending){pending=true;requestAnimationFrame(()=>{pending=false;upgrade(host);});}}).observe(host,{childList:true,subtree:true});}
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",ready);else ready();
})();