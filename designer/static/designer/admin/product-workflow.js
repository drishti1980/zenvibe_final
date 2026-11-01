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

 // Compact inline edit cards. All Django inputs remain in the original form.
 document.querySelectorAll(".inline-group .inline-related").forEach(card=>{
   if(card.classList.contains("empty-form"))return;
   const heading=card.querySelector(":scope > h3");
   if(!heading)return;
   const collapse=document.createElement("button");collapse.type="button";collapse.className="zv-inline-toggle";
   collapse.textContent="Edit";collapse.setAttribute("aria-expanded","false");
   heading.appendChild(collapse);
   card.classList.add("zv-inline-collapsed");
   collapse.addEventListener("click",()=>{card.classList.toggle("zv-inline-collapsed");const expanded=!card.classList.contains("zv-inline-collapsed");collapse.textContent=expanded?"Collapse":"Edit";collapse.setAttribute("aria-expanded",String(expanded));});
   if(card.querySelector(".errorlist")){collapse.click();}
 });
 // Colour swatches: pick any HEX colour visually, without memorising codes.
 document.querySelectorAll('input[name$="-hex_value"]').forEach(input=>{
   const picker=document.createElement("input");picker.type="color";picker.className="zv-hex-picker";
   const ok=/^#[0-9a-f]{6}$/i.test(input.value||"");
   picker.value=ok?input.value:"#ffffff";picker.title="Choose a colour";
   input.parentNode.insertBefore(picker,input);
   picker.addEventListener("input",()=>{input.value=picker.value.toUpperCase();input.dispatchEvent(new Event("change",{bubbles:true}));});
   input.addEventListener("input",()=>{if(/^#[0-9a-f]{6}$/i.test(input.value))picker.value=input.value;});
 });
 // Add true navigation/search, without hiding Django validation or Save.
 const tools=document.createElement("div");tools.className="zv-admin-tools";
 const search=document.createElement("input");search.type="search";search.placeholder="Search product settings, variants or prices…";search.setAttribute("aria-label","Search product settings");
 const reset=document.createElement("button");reset.type="button";reset.textContent="Discard unsaved changes";reset.className="button";
 reset.addEventListener("click",()=>{if(window.confirm("Discard all unsaved changes and reload this product?"))window.location.reload();});
 tools.append(search,reset);nav.insertAdjacentElement("afterend",tools);
 search.addEventListener("input",()=>{
   const q=search.value.trim().toLowerCase();
   if(!q){show(nav.querySelector("button.active")?.dataset.tab||visible[0][0]);return;}
   visible.forEach(([,els])=>els.forEach(el=>{el.hidden=false;el.classList.remove("zv-config-inactive");}));
   sections.forEach(el=>{
     const txt=(el.querySelector(":scope > h2, :scope > h3")?.textContent||"")+" "+Array.from(el.querySelectorAll("label")).map(x=>x.textContent).join(" ");
     el.hidden=!txt.toLowerCase().includes(q);
   });
   if(q)nav.querySelectorAll("button").forEach(b=>b.classList.remove("active"));
 });
 // Restore visible field groups if user saves while on a tab.
 form.addEventListener("submit",()=>sections.forEach(el=>{el.hidden=false;el.classList.remove("zv-config-inactive");}));
 // Inline add buttons and regular Django form validation are unchanged.
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();