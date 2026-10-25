(() => {
  const header = document.getElementById('siteHeader');
  const backTop = document.getElementById('backToTop');
  const onScroll = () => {
    const scrolled = window.scrollY > 20;
    header?.classList.toggle('is-scrolled', scrolled);
    backTop?.classList.toggle('show', window.scrollY > 500);
  };
  window.addEventListener('scroll', onScroll, {passive:true}); onScroll();
  backTop?.addEventListener('click', () => window.scrollTo({top:0, behavior:'smooth'}));

  const menuBtn = document.getElementById('menuBtn');
  const nav = document.getElementById('navLinks');
  menuBtn?.addEventListener('click', () => nav?.classList.toggle('open'));
  nav?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => nav.classList.remove('open')));

  const revealObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('is-visible'); revealObserver.unobserve(entry.target); } });
  }, {threshold: .12, rootMargin: '0px 0px -35px'});
  document.querySelectorAll('.zv-reveal').forEach(el => revealObserver.observe(el));

  const modal = document.getElementById('quickPreviewModal');
  const image = document.getElementById('quickPreviewImage');
  const placeholder = document.getElementById('quickPreviewPlaceholder');
  const title = document.getElementById('quickPreviewTitle');
  const category = document.getElementById('quickPreviewCategory');
  const description = document.getElementById('quickPreviewDescription');
  const price = document.getElementById('quickPreviewPrice');
  const link = document.getElementById('quickPreviewLink');

  const closeModal = () => {
    if (!modal) return;
    modal.classList.remove('is-open'); modal.setAttribute('aria-hidden','true'); document.body.style.overflow='';
  };
  document.querySelectorAll('[data-preview-product]').forEach(btn => btn.addEventListener('click', e => {
    e.preventDefault(); e.stopPropagation();
    const d = btn.dataset;
    title.textContent = d.name || 'Product preview'; category.textContent = (d.category || 'Custom product').toUpperCase();
    description.textContent = d.description || 'Customize this product with your logo, colours and message.';
    price.textContent = d.price || 'Contact us'; link.href = d.url || '#';
    if (d.image) { image.src = d.image; image.alt = d.name || ''; image.style.display='block'; placeholder.style.display='none'; }
    else { image.removeAttribute('src'); image.style.display='none'; placeholder.style.display='grid'; }
    modal.classList.add('is-open'); modal.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden';
  }));
  document.querySelectorAll('[data-close-preview]').forEach(btn => btn.addEventListener('click', closeModal));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  document.querySelectorAll('.zv-product-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      if (window.innerWidth < 900) return;
      const r = card.getBoundingClientRect();
      const rx = ((e.clientY-r.top)/r.height-.5)*-4, ry=((e.clientX-r.left)/r.width-.5)*4;
      card.style.transform = `translateY(-9px) perspective(800px) rotateX(${rx}deg) rotateY(${ry}deg)`;
    });
    card.addEventListener('mouseleave', () => card.style.transform='');
  });
})();

// category carousel controls
document.addEventListener('DOMContentLoaded',()=>{const slider=document.getElementById('categorySlider');if(slider){const step=()=>Math.max(300,slider.clientWidth*.72);document.querySelector('.zv-slider-prev')?.addEventListener('click',()=>slider.scrollBy({left:-step(),behavior:'smooth'}));document.querySelector('.zv-slider-next')?.addEventListener('click',()=>slider.scrollBy({left:step(),behavior:'smooth'}));let down=false,startX=0,startScroll=0;slider.addEventListener('pointerdown',e=>{down=true;startX=e.clientX;startScroll=slider.scrollLeft;slider.setPointerCapture(e.pointerId)});slider.addEventListener('pointermove',e=>{if(down)slider.scrollLeft=startScroll-(e.clientX-startX)});slider.addEventListener('pointerup',()=>down=false);slider.addEventListener('pointercancel',()=>down=false)}});
