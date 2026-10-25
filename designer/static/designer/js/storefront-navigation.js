(function(){
  const drawer=document.getElementById('zv71Drawer');
  const backdrop=document.getElementById('zv71DrawerBackdrop');
  const openers=[document.getElementById('zv71DrawerOpen'),document.getElementById('zv71AllProducts')].filter(Boolean);
  const closer=document.getElementById('zv71DrawerClose');
  function open(){if(!drawer)return;drawer.classList.add('open');backdrop&&backdrop.classList.add('open');drawer.setAttribute('aria-hidden','false');document.body.style.overflow='hidden'}
  function close(){if(!drawer)return;drawer.classList.remove('open');backdrop&&backdrop.classList.remove('open');drawer.setAttribute('aria-hidden','true');document.body.style.overflow=''}
  openers.forEach(x=>x.addEventListener('click',open)); closer&&closer.addEventListener('click',close); backdrop&&backdrop.addEventListener('click',close); document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});

  document.querySelectorAll('[data-drawer-category]').forEach(group=>{
    const btn=group.querySelector('.zv71-drawer-toggle');
    const children=group.querySelector('.zv71-drawer-children');
    if(!btn||!children)return;
    if(group.classList.contains('open')){children.hidden=false;btn.setAttribute('aria-expanded','true');}
    btn.addEventListener('click',e=>{
      e.preventDefault();e.stopPropagation();
      const opening=children.hidden;
      children.hidden=!opening;group.classList.toggle('open',opening);btn.setAttribute('aria-expanded',opening?'true':'false');
    });
  });

  document.querySelectorAll('.studio-app .panel-help,.studio-app .upload-note,.studio-app .panel-callout,.studio-app .view-legend').forEach(el=>{
    const text=(el.innerText||el.textContent||'').replace(/\s+/g,' ').trim();
    if(!text||el.dataset.compactHelp==='1')return;
    const tip=document.createElement('span');tip.className='zv-help-tip';tip.tabIndex=0;tip.setAttribute('role','note');tip.setAttribute('aria-label',text);tip.dataset.tip=text;tip.textContent='?';
    el.replaceWith(tip);
  });

  const filterToggle=document.getElementById('zv71FilterToggle'); const sidebar=document.querySelector('.zv71-shop-sidebar'); filterToggle&&filterToggle.addEventListener('click',()=>sidebar&&sidebar.classList.toggle('open'));
  document.querySelectorAll('[data-shop-view]').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('[data-shop-view]').forEach(b=>b.classList.remove('active'));btn.classList.add('active');const content=document.querySelector('.zv71-shop-content');if(content)content.classList.toggle('list-view',btn.dataset.shopView==='list')}));
  const search=document.getElementById('productSearch'); const cards=[...document.querySelectorAll('#catalogGrid .searchable')]; const count=document.getElementById('visibleProductCount');
  if(search&&cards.length){search.addEventListener('input',()=>{const q=search.value.trim().toLowerCase();let n=0;cards.forEach(c=>{const show=!q||(c.dataset.search||'').includes(q);c.style.display=show?'':'none';if(show)n++});if(count)count.textContent=n})}
})();
