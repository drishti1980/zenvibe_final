/* ==========================================================================
   ZenVibe 360° Product Viewer
   Usage: ZenVibe360.mount(containerEl, ["url1.jpg","url2.jpg", ...])
   With 1 image: shows it statically (no interaction needed).
   With 2+ images: click-drag horizontally to spin through frames.
   ========================================================================== */
(function(){
  'use strict';

  function mount(container, imageUrls, opts){
    opts = opts || {};
    if(!container || !imageUrls || !imageUrls.length) return null;

    container.innerHTML = '';
    container.classList.add('zv360-viewer');
    container.style.position = 'relative';
    container.style.userSelect = 'none';
    container.style.cursor = imageUrls.length > 1 ? 'ew-resize' : 'default';

    const img = document.createElement('img');
    img.src = imageUrls[0];
    img.draggable = false;
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'contain';
    img.style.pointerEvents = 'none';
    container.appendChild(img);

    if(imageUrls.length < 2){
      return { setFrame(){}, destroy(){ container.innerHTML = ''; } };
    }

    const badge = document.createElement('div');
    badge.textContent = '↔ Drag to rotate';
    badge.style.cssText = 'position:absolute;bottom:10px;left:50%;transform:translateX(-50%);background:rgba(16,24,40,.72);color:#fff;font:600 11px Inter,Arial,sans-serif;padding:5px 12px;border-radius:999px;pointer-events:none;transition:opacity .3s';
    container.appendChild(badge);

    let frame = 0;
    let dragging = false;
    let startX = 0;
    let startFrame = 0;
    const total = imageUrls.length;
    const sensitivity = opts.sensitivity || 6; // px of drag per frame step

    function setFrame(i){
      frame = ((i % total) + total) % total;
      img.src = imageUrls[frame];
    }

    function onDown(clientX){
      dragging = true;
      startX = clientX;
      startFrame = frame;
      badge.style.opacity = '0';
    }
    function onMove(clientX){
      if(!dragging) return;
      const dx = clientX - startX;
      const steps = Math.round(dx / sensitivity);
      setFrame(startFrame - steps);
    }
    function onUp(){ dragging = false; }

    container.addEventListener('mousedown', e => { onDown(e.clientX); e.preventDefault(); });
    window.addEventListener('mousemove', e => onMove(e.clientX));
    window.addEventListener('mouseup', onUp);

    container.addEventListener('touchstart', e => onDown(e.touches[0].clientX), { passive: true });
    container.addEventListener('touchmove', e => { onMove(e.touches[0].clientX); e.preventDefault(); }, { passive: false });
    container.addEventListener('touchend', onUp);

    return {
      setFrame,
      destroy(){ container.innerHTML = ''; }
    };
  }

  window.ZenVibe360 = { mount };
})();
