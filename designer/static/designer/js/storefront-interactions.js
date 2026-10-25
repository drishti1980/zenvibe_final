(function(){'use strict';
  function qs(s,c=document){return c.querySelector(s)} function qsa(s,c=document){return [...c.querySelectorAll(s)]}
  const forms=qsa('.zv71-search');
  forms.forEach(form=>{const input=qs('input[type="search"]',form);if(!input)return;let box=qs('.zv-search-suggest',form);if(!box){box=document.createElement('div');box.className='zv-search-suggest';form.appendChild(box)}let timer=null,controller=null;
    const close=()=>box.classList.remove('open');
    input.addEventListener('input',()=>{clearTimeout(timer);const q=input.value.trim();if(q.length<2){close();box.innerHTML='';return}timer=setTimeout(async()=>{try{controller?.abort();controller=new AbortController();const r=await fetch((document.getElementById('siteHeader')?.dataset.searchUrl || '/api/product-search/')+'?q='+encodeURIComponent(q),{signal:controller.signal});const d=await r.json();box.innerHTML='';if(!d.results?.length){box.innerHTML='<div class="empty">No matching products yet</div>';box.classList.add('open');return}d.results.forEach(x=>{const a=document.createElement('a');a.href=x.url;const media=x.image?`<img src="${x.image}" alt="">`:'<div></div>';a.innerHTML=media+`<span><strong>${x.name}</strong><small>${x.category}</small></span><b>From $${x.price}</b>`;box.appendChild(a)});box.classList.add('open')}catch(e){if(e.name!=='AbortError')close()}},180)});
    input.addEventListener('focus',()=>{if(box.children.length)box.classList.add('open')});document.addEventListener('click',e=>{if(!form.contains(e.target))close()});
  });
  const startProof=qs('.zv71-proof');if(startProof) startProof.style.whiteSpace='nowrap';
})();
