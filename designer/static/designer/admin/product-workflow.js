(function(){
"use strict";
function init(){
 const form=document.querySelector("body.model-product.change-form form");
 if(!form || document.querySelector(".zv-product-nav"))return;
 const sections=Array.from(form.querySelectorAll(":scope > div > fieldset.module, :scope > fieldset.module, .inline-group")).filter(el=>!el.closest(".inline-related"));
 if(!sections.length)return;
 const nav=document.createElement("nav");nav.className="zv-product-nav";nav.setAttribute("aria-label","Product configuration sections");
 const tabs=[
  ["Essentials",/Storefront product details|Availability/i],
  ["Content & FAQs",/Product content|FAQ/i],
  ["Colours & sizes",/variants|Product price tiers/i],
  ["Print & editor",/print|editor configuration|editable/i],
  ["Sales & delivery",/Sale|Fastest delivery/i],
  ["Other",/.*/]
 ];
 const groups=new Map(tabs.map(t=>[t[0],[]]));
 sections.forEach(section=>{
  const text=(section.querySelector(":scope > h2, :scope > h3")?.textContent || "").trim();
  const match=tabs.find(t=>t[1].test(text));groups.get(match?.[0]||"Other").push(section);
 });
 const visible=Array.from(groups).filter(([,arr])=>arr.length);
 if(visible.length<2)return;
 function show(name){
  visible.forEach(([key,els])=>els.forEach(el=>{el.hidden=key!==name;el.classList.toggle("zv-config-inactive",key!==name);}));
  nav.querySelectorAll("button").forEach(button=>{const selected=button.dataset.tab===name;button.setAttribute("aria-selected",String(selected));button.classList.toggle("active",selected);});
 }
 visible.forEach(([name])=>{
  const b=document.createElement("button");b.type="button";b.dataset.tab=name;b.textContent=name;b.setAttribute("role","tab");b.addEventListener("click",()=>show(name));nav.appendChild(b);
 });
 nav.setAttribute("role","tablist");
 const first=sections[0];first.parentNode.insertBefore(nav,first);
 // If errors are present, open their section so they are not hidden.
 const errorSection=sections.find(section=>section.querySelector(".errorlist"));
 const firstTab=errorSection ? visible.find(([,els])=>els.includes(errorSection))?.[0] : visible[0][0];
 show(firstTab||visible[0][0]);
 // Inline add buttons and regular Django form validation are unchanged.
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();