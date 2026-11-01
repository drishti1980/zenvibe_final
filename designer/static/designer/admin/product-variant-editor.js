(function(){
"use strict";
function setup(fieldId,label){
 const original=document.getElementById(fieldId);
 if(!original || original.dataset.variantEditor)return;
 original.dataset.variantEditor="1";
 const root=document.createElement("div");root.className="zv-simple-variant-editor";
 const entries=document.createElement("div");entries.className="zv-variant-entries";
 const add=document.createElement("button");add.type="button";add.className="button";add.textContent="+ Add "+label;
 root.append(entries,add);original.parentNode.insertBefore(root,original);
 const rows=[];
 const toKey=name=>name.toLowerCase().trim().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");
 function sync(){
  original.value=rows.map(r=>r.name.value.trim()+" | "+r.key.value.trim()).filter(x=>x!==" | ").join("\n");
  original.dispatchEvent(new Event("input",{bubbles:true}));
 }
 function newRow(name="",key=""){
  const row=document.createElement("div");row.className="zv-variant-entry";
  const n=document.createElement("input");n.type="text";n.placeholder=label+" name";n.setAttribute("aria-label",label+" name");n.value=name;
  const k=document.createElement("input");k.type="text";k.placeholder="Unique key";k.setAttribute("aria-label",label+" key");k.value=key;
  const del=document.createElement("button");del.type="button";del.className="button";del.textContent="Remove";
  const obj={element:row,name:n,key:k};rows.push(obj);
  n.addEventListener("input",()=>{if(!k.dataset.manual)k.value=toKey(n.value);sync();});
  k.addEventListener("input",()=>{k.dataset.manual="1";sync();});
  del.addEventListener("click",()=>{rows.splice(rows.indexOf(obj),1);row.remove();sync();});
  row.append(n,k,del);entries.appendChild(row);
 }
 original.value.split(/\r?\n/).forEach(line=>{
   const [name,key]=line.split("|").map(x=>x.trim());
   if(name&&key)newRow(name,key);
 });
 add.addEventListener("click",()=>{newRow();rows[rows.length-1].name.focus();});
 original.style.display="none";
 // Keep the actual Django textarea as the form submission source.
}
function init(){setup("id_shape_variant_options","shape");setup("id_material_variant_options","material");}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();