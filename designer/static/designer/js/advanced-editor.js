(function(){
  'use strict';
  const FONTS=['Arial','Arial Black','Avenir','Baskerville','Calibri','Cambria','Candara','Century Gothic','Comic Sans MS','Courier New','Didot','Futura','Garamond','Georgia','Gill Sans','Helvetica','Impact','Lato','Montserrat','Open Sans','Oswald','Palatino','Poppins','Roboto','Tahoma','Times New Roman','Trebuchet MS','Verdana'];
  function enhanceFonts(){document.querySelectorAll('select').forEach(sel=>{const hint=((sel.id||'')+' '+(sel.name||'')+' '+(sel.className||'')).toLowerCase();if(!hint.includes('font')) return;const existing=new Set([...sel.options].map(o=>o.value.toLowerCase()));FONTS.forEach(f=>{if(!existing.has(f.toLowerCase())){const o=document.createElement('option');o.value=f;o.textContent=f;sel.appendChild(o)}})})}
  function numericSafety(){document.querySelectorAll('input[type="number"]').forEach(i=>{if(/font|size/i.test((i.id||'')+' '+(i.name||''))){if(!i.min)i.min='6';if(!i.max)i.max='300';i.step=i.step||'1'}})}
  function colorSafety(){document.querySelectorAll('input[type="color"]').forEach(i=>{i.setAttribute('aria-label',i.getAttribute('aria-label')||'Choose colour')})}
  function run(){enhanceFonts();numericSafety();colorSafety()}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
  new MutationObserver(()=>{clearTimeout(window.__zvEditorEnhance);window.__zvEditorEnhance=setTimeout(run,120)}).observe(document.documentElement,{childList:true,subtree:true});
})();
