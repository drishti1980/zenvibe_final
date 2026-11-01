(function(){
"use strict";
function ready(){
 const form=document.querySelector("#content-main form, form#product_form, body.model-product form");
 if(!form || document.getElementById("zv-admin-tools"))return;
 const groups=[...form.querySelectorAll("fieldset.module, .inline-group")].filter(el=>!el.closest(".inline-related") && !el.parentElement?.closest("fieldset.module"));
 const nav=document.createElement("div");nav.id="zv-admin-tools";nav.className="zv-admin-tools";
 const search=document.createElement("input");search.type="search";search.placeholder="Search settings, colour, shape, material, price…";search.setAttribute("aria-label","Search product settings");
 const discard=document.createElement("button");discard.type="button";discard.textContent="Discard unsaved changes";discard.className="button";
 discard.addEventListener("click",()=>{if(confirm("Discard unsaved changes? The saved product will be reloaded."))location.reload();});
 nav.append(search,discard);
 const anchor=form.querySelector("fieldset.module, .inline-group");
 if(anchor)anchor.parentNode.insertBefore(nav,anchor);else form.prepend(nav);
 let selected="";
 const tabbar=document.createElement("div");tabbar.className="zv-product-nav";
 const labels=[["Details",/storefront|availability/i],["Content & FAQs",/content|faq/i],["Variants & pricing",/variants|tiers|images/i],["Print & editor",/print|editor|editable/i],["Sales & delivery",/sale|delivery/i],["Other",/.*/]];
 const category=el=>{const title=el.querySelector(":scope > h2, :scope > h3")?.textContent||"";return labels.find(([_,re])=>re.test(title))?.[0]||"Other";};
 const present=[...new Set(groups.map(category))];
 const buttons=[];
 function apply(){
  const term=search.value.trim().toLowerCase();
  groups.forEach(el=>{
   let match;
   if(term){
    const heading=el.querySelector(":scope > h2, :scope > h3")?.textContent||"";
    const names=[...el.querySelectorAll("label")].map(x=>x.textContent).join(" ");
    match=(heading+" "+names).toLowerCase().includes(term);
   }else match=category(el)===selected;
   el.classList.toggle("zv-config-inactive",!match);
  });
  buttons.forEach(b=>b.classList.toggle("active",b.dataset.tab===selected&&!term));
 }
 present.forEach(name=>{const b=document.createElement("button");b.type="button";b.dataset.tab=name;b.textContent=name;b.addEventListener("click",()=>{selected=name;search.value="";apply();});buttons.push(b);tabbar.appendChild(b);});
 if(groups.length && present.length>1){nav.insertAdjacentElement("afterend",tabbar);selected=category(groups.find(el=>el.querySelector(".errorlist"))||groups[0]);apply();}
 search.addEventListener("input",apply);
 // Inline cards should be collapsed only after their existing fields are initialized.
 function cardControls(root){
  root.querySelectorAll(".inline-group .inline-related").forEach(card=>{
   if(card.classList.contains("empty-form")||card.dataset.zvCompact)return;
   const heading=card.querySelector(":scope > h3");if(!heading)return;
   card.dataset.zvCompact="1";const button=document.createElement("button");button.type="button";button.className="zv-inline-toggle";button.textContent="Collapse";
   heading.appendChild(button);
   button.addEventListener("click",()=>{const collapsed=card.classList.toggle("zv-inline-collapsed");button.textContent=collapsed?"Expand":"Collapse";});
   // Do not hide new records or rows with errors, and do not default-collapse images.
  });
 }
 cardControls(form);
 document.addEventListener("formset:added",e=>cardControls(e.target||form));
 form.addEventListener("submit",()=>groups.forEach(el=>el.classList.remove("zv-config-inactive")));
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",ready);else ready();
})();