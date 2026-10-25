document.addEventListener('DOMContentLoaded', () => {
  const header = document.getElementById('siteHeader');
  const menuButton = document.getElementById('menuBtn');
  const navLinks = document.getElementById('navLinks');

  const updateHeader = () => header?.classList.toggle('scrolled', window.scrollY > 16);
  updateHeader();
  window.addEventListener('scroll', updateHeader, { passive: true });

  menuButton?.addEventListener('click', () => {
    const open = navLinks?.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(Boolean(open)));
  });
  document.querySelectorAll('#navLinks a').forEach(link => link.addEventListener('click', () => {
    navLinks?.classList.remove('open');
    menuButton?.setAttribute('aria-expanded', 'false');
  }));

  const observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -35px' }) : null;
  document.querySelectorAll('.reveal').forEach(element => observer ? observer.observe(element) : element.classList.add('revealed'));

  document.querySelectorAll('.z-accordion details').forEach(detail => detail.addEventListener('toggle', () => {
    if (!detail.open) return;
    document.querySelectorAll('.z-accordion details').forEach(other => {
      if (other !== detail) other.open = false;
    });
  }));

  const catalogueSearch = document.getElementById('productSearch');
  const catalogueGrid = document.getElementById('catalogGrid');
  const noCatalogueResults = document.getElementById('catalogNoResults');
  const filterButtons = [...document.querySelectorAll('#catalogFilterPills [data-filter]')];
  const queryFromHeader = new URLSearchParams(window.location.search).get('q') || '';
  let activeCategory = 'all';
  if (catalogueSearch && queryFromHeader) catalogueSearch.value = queryFromHeader;

  function filterCatalogue() {
    if (!catalogueGrid) return;
    const query = (catalogueSearch?.value || '').toLowerCase().trim();
    let visible = 0;
    catalogueGrid.querySelectorAll('.searchable').forEach(card => {
      const searchMatch = !query || (card.dataset.search || '').includes(query);
      const categoryMatch = activeCategory === 'all' || card.dataset.category === activeCategory;
      const show = searchMatch && categoryMatch;
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (noCatalogueResults) noCatalogueResults.hidden = visible !== 0;
  }
  catalogueSearch?.addEventListener('input', filterCatalogue);
  filterButtons.forEach(button => button.addEventListener('click', () => {
    activeCategory = button.dataset.filter || 'all';
    filterButtons.forEach(item => item.classList.toggle('active', item === button));
    filterCatalogue();
  }));
  document.getElementById('clearCatalogSearch')?.addEventListener('click', () => {
    if (catalogueSearch) catalogueSearch.value = '';
    activeCategory = 'all';
    filterButtons.forEach((button, index) => button.classList.toggle('active', index === 0));
    filterCatalogue();
    catalogueSearch?.focus();
  });
  if (catalogueGrid) filterCatalogue();

  document.querySelectorAll('.catalog-view-btn').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.catalog-view-btn').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
    catalogueGrid?.classList.toggle('list-view', button.dataset.view === 'list');
  }));

  document.addEventListener('keydown', event => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      const target = catalogueSearch || document.querySelector('.z-header-search input');
      if (target) { event.preventDefault(); target.focus(); }
    }
  });

  const productGrid = document.getElementById('productGrid');
  const productSearch = document.getElementById('categoryProductSearch');
  const productSort = document.getElementById('productSort');
  const productCount = document.getElementById('visibleProductCount');
  const productNoResults = document.getElementById('productNoResults');
  function updateProducts() {
    if (!productGrid) return;
    const query = (productSearch?.value || '').toLowerCase().trim();
    const cards = [...productGrid.querySelectorAll('.premium-product-card')];
    let visible = 0;
    cards.forEach(card => {
      const show = !query || (card.dataset.search || '').includes(query);
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (productCount) productCount.textContent = String(visible);
    if (productNoResults) productNoResults.hidden = visible !== 0;
  }
  function sortProducts() {
    if (!productGrid || !productSort) return;
    const cards = [...productGrid.querySelectorAll('.premium-product-card')];
    const mode = productSort.value;
    cards.sort((a, b) => {
      const nameA = a.dataset.name || '', nameB = b.dataset.name || '';
      const priceA = Number(a.dataset.price || 0), priceB = Number(b.dataset.price || 0);
      if (mode === 'name-asc') return nameA.localeCompare(nameB);
      if (mode === 'name-desc') return nameB.localeCompare(nameA);
      if (mode === 'price-asc') return priceA - priceB;
      if (mode === 'price-desc') return priceB - priceA;
      return 0;
    });
    cards.forEach(card => productGrid.appendChild(card));
  }
  productSearch?.addEventListener('input', updateProducts);
  productSort?.addEventListener('change', sortProducts);
  document.getElementById('clearProductSearch')?.addEventListener('click', () => {
    if (productSearch) productSearch.value = '';
    updateProducts();
    productSearch?.focus();
  });
});


// Premium product preview, pointer lighting and subtle 3D card motion.
(() => {
  const hero = document.querySelector('.z-home-hero');
  hero?.addEventListener('pointermove', event => {
    const rect = hero.getBoundingClientRect();
    hero.style.setProperty('--mouse-x', `${event.clientX - rect.left}px`);
    hero.style.setProperty('--mouse-y', `${event.clientY - rect.top}px`);
  });

  const canHover = window.matchMedia('(hover:hover) and (pointer:fine)').matches;
  if (canHover) {
    document.querySelectorAll('.z-tilt-card').forEach(card => {
      card.addEventListener('pointermove', event => {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - .5;
        const y = (event.clientY - rect.top) / rect.height - .5;
        card.style.transform = `perspective(950px) rotateX(${(-y * 3.5).toFixed(2)}deg) rotateY(${(x * 4.5).toFixed(2)}deg) translateY(-7px)`;
      });
      card.addEventListener('pointerleave', () => { card.style.transform = ''; });
    });
  }

  const modal = document.getElementById('quickPreviewModal');
  if (!modal) return;
  const image = document.getElementById('quickPreviewImage');
  const placeholder = document.getElementById('quickPreviewPlaceholder');
  const title = document.getElementById('quickPreviewTitle');
  const category = document.getElementById('quickPreviewCategory');
  const description = document.getElementById('quickPreviewDescription');
  const price = document.getElementById('quickPreviewPrice');
  const link = document.getElementById('quickPreviewLink');
  let lastTrigger = null;

  const closePreview = () => {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('z-modal-open');
    window.setTimeout(() => lastTrigger?.focus(), 100);
  };
  const openPreview = button => {
    lastTrigger = button;
    title.textContent = button.dataset.name || 'Custom product';
    category.textContent = button.dataset.category || 'CUSTOM PRODUCT';
    description.textContent = button.dataset.description || 'Personalize this product with your logo, artwork and message.';
    price.textContent = button.dataset.price || '';
    link.href = button.dataset.url || '#';
    const src = button.dataset.image || '';
    if (src) { image.src = src; image.alt = button.dataset.name || ''; image.hidden = false; placeholder.style.display = 'none'; }
    else { image.removeAttribute('src'); image.hidden = true; placeholder.style.display = 'block'; placeholder.textContent = (button.dataset.name || 'Z').charAt(0).toUpperCase(); }
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('z-modal-open');
    modal.querySelector('.z-quick-modal-close')?.focus();
  };
  document.querySelectorAll('[data-preview-product]').forEach(button => button.addEventListener('click', event => { event.preventDefault(); event.stopPropagation(); openPreview(button); }));
  modal.querySelectorAll('[data-close-preview]').forEach(button => button.addEventListener('click', closePreview));
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && modal.classList.contains('open')) closePreview(); });
})();
