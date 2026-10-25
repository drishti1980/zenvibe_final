(function(){
  'use strict';
  const root=document.querySelector('.zv-editor,.pen-editor');
  if(!root)return;
  const isShirt=root.classList.contains('zv-editor');
  const byId=id=>document.getElementById(id);
  function click(id){const el=byId(id); if(el) el.click();}
  function downloadProof(){
    const canvas=byId(isShirt?'tshirtCanvas':'penCanvas');
    if(!canvas)return;
    const a=document.createElement('a');
    a.download=((root.dataset.productName||'design').replace(/[^a-z0-9]+/gi,'-').toLowerCase())+'-proof.png';
    a.href=canvas.toDataURL('image/png'); a.click();
  }
  byId('unifiedPrintBtn')?.addEventListener('click',()=>click('processBtn'));
  byId('unifiedDownloadBtn')?.addEventListener('click',downloadProof);
  byId('unifiedSaveBtn')?.addEventListener('click',()=>{click('processBtn');setTimeout(()=>click('saveDraft'),100)});
  if(isShirt){
    const main=byId('shirtSizeMain'), modal=byId('shirtSize');
    if(main&&modal){main.value=modal.value;main.addEventListener('change',()=>{modal.value=main.value;modal.dispatchEvent(new Event('change',{bubbles:true}))});modal.addEventListener('change',()=>main.value=modal.value)}
    const front=byId('frontSideBtn'),back=byId('backSideBtn'),side=byId('sideTopBtn');
    function setActive(n){front?.classList.toggle('active',n===1);back?.classList.toggle('active',n===2)}
    front?.addEventListener('click',()=>{if((side?.textContent||'').includes('2'))click('sideTopBtn');setActive(1)});
    back?.addEventListener('click',()=>{if(!(side?.textContent||'').includes('2'))click('sideTopBtn');setActive(2)});
    const obs=new MutationObserver(()=>setActive((side?.textContent||'').includes('2')?2:1));if(side)obs.observe(side,{childList:true,subtree:true,characterData:true});
  }
})();
