/* ==========================================================================
   ZenVibe Arrange Tools — universal, delegation-based
   Fixes the Arrange panel not responding on Bags/Drinkware/Photo/T-Shirt/Pen.
   Uses event delegation on document, so it keeps working even if a
   customizer's own JS re-renders/rebuilds parts of the DOM at runtime —
   no dependency on binding listeners to elements that might get replaced.
   Safe to load alongside the existing per-page Arrange code: this only
   acts when the existing handlers don't (harmless if both fire).
   ========================================================================== */
(function(){
  'use strict';

  function getCanvas(){
    return window.designCanvas || window.__zenvibeCanvas || window.canvas || null;
  }

  function activeObj(canvas){
    return canvas ? canvas.getActiveObject() : null;
  }

  function selectedMany(canvas){
    return canvas ? canvas.getActiveObjects() : [];
  }

  function dims(canvas){
    const p = window.PRODUCT || {};
    return { W: p.width || (canvas ? canvas.getWidth() : 800), H: p.height || (canvas ? canvas.getHeight() : 600) };
  }

  function commit(canvas){
    canvas && canvas.requestRenderAll && canvas.requestRenderAll();
    // Best-effort: call whatever autosave/snapshot hook the page defines, if any.
    if(typeof window.snapshot === 'function'){ try{ window.snapshot(); }catch(e){} }
  }

  function doAlign(canvas, kind){
    const o = activeObj(canvas);
    if(!o) return;
    const { W, H } = dims(canvas);
    const margin = 20;
    const b = o.getBoundingRect(true, true);
    if(kind === 'left') o.left += (margin - b.left);
    if(kind === 'center') o.left += (W/2 - (b.left + b.width/2));
    if(kind === 'right') o.left += (W - margin - (b.left + b.width));
    if(kind === 'top') o.top += (margin - b.top);
    if(kind === 'middle') o.top += (H/2 - (b.top + b.height/2));
    if(kind === 'bottom') o.top += (H - margin - (b.top + b.height));
    o.setCoords();
    commit(canvas);
  }

  function doLayer(canvas, dir){
    const o = activeObj(canvas);
    if(!o) return;
    if(dir === 'forward') canvas.bringForward(o);
    else if(dir === 'backward') canvas.sendBackwards(o);
    else if(dir === 'front') canvas.bringToFront(o);
    else if(dir === 'back') canvas.sendToBack(o);
    commit(canvas);
  }

  function doFlip(canvas, axis){
    const o = activeObj(canvas);
    if(!o) return;
    if(axis === 'h') o.set('flipX', !o.flipX);
    if(axis === 'v') o.set('flipY', !o.flipY);
    commit(canvas);
  }

  function doGroup(canvas){
    const o = activeObj(canvas);
    if(!o) return;
    if(o.type === 'activeSelection'){
      o.toGroup();
    } else if(o.type === 'group'){
      o.toActiveSelection();
    } else {
      const many = selectedMany(canvas);
      if(many.length > 1) new fabric.ActiveSelection(many, { canvas }).toGroup();
    }
    commit(canvas);
  }

  function closeDropdown(root){
    if(!root) return;
    root.classList.remove('open');
    const btn = root.querySelector('#arrangeMenuBtn, [id$="ArrangeBtn"]');
    if(btn) btn.setAttribute('aria-expanded', 'false');
  }

  function placeMenu(trigger, menu){
    if(!trigger || !menu) return;
    const r = trigger.getBoundingClientRect(), w = menu.offsetWidth || 310;
    menu.style.left = Math.max(12, Math.min(window.innerWidth - w - 12, r.right - w)) + 'px';
    menu.style.top = (r.bottom + 7) + 'px';
  }

  // ---- Single delegated click handler covers every scheme in the codebase ----
  document.addEventListener('click', function(e){
    const canvas = getCanvas();

    // Scheme A: generic #arrangeDropdown / #arrangeMenuBtn / #arrangeMenu (editor, bags, photo, drinkware, awards)
    const genericTrigger = e.target.closest('#arrangeMenuBtn');
    if(genericTrigger){
      e.preventDefault(); e.stopPropagation();
      const root = document.getElementById('arrangeDropdown');
      if(root){
        root.classList.toggle('open');
        genericTrigger.setAttribute('aria-expanded', root.classList.contains('open') ? 'true' : 'false');
        if(root.classList.contains('open')) requestAnimationFrame(() => placeMenu(genericTrigger, document.getElementById('arrangeMenu')));
      }
      return;
    }

    // Scheme B: T-shirt / Pen — .zv-arrange / [id$="ArrangeBtn"] with data-zv-arrange actions
    const tshirtTrigger = e.target.closest('[id$="ArrangeBtn"]');
    if(tshirtTrigger && !genericTrigger){
      e.preventDefault(); e.stopPropagation();
      const root = tshirtTrigger.closest('.zv-arrange, .arrange-dropdown') || tshirtTrigger.parentElement;
      if(root) root.classList.toggle('open');
      return;
    }

    // Action buttons — generic ids used by editor/bags/photo/drinkware/awards
    const actionIds = {
      leftBtn:'align:left', centerBtn:'align:center', rightBtn:'align:right',
      topBtn:'align:top', middleBtn:'align:middle', bottomBtn:'align:bottom',
      bringFrontBtn:'layer:forward', sendBackBtn:'layer:backward',
      flipXBtn:'flip:h', flipYBtn:'flip:v', groupBtn:'group',
    };
    for(const id in actionIds){
      if(e.target.closest('#'+id)){
        const [kind, val] = actionIds[id].split(':');
        if(kind === 'align') doAlign(canvas, val);
        else if(kind === 'layer') doLayer(canvas, val);
        else if(kind === 'flip') doFlip(canvas, val);
        else if(kind === 'group') doGroup(canvas);
        const root = document.getElementById('arrangeDropdown');
        if(root) closeDropdown(root);
        return;
      }
    }

    // Action buttons — T-shirt/Pen scheme via data-zv-arrange
    const zvBtn = e.target.closest('[data-zv-arrange]');
    if(zvBtn){
      const a = zvBtn.dataset.zvArrange;
      if(['left','center','right','top','middle','bottom'].includes(a)) doAlign(canvas, a);
      else if(a === 'forward') doLayer(canvas, 'forward');
      else if(a === 'backward') doLayer(canvas, 'backward');
      else if(a === 'flipH') doFlip(canvas, 'h');
      else if(a === 'flipV') doFlip(canvas, 'v');
      else if(a === 'group') doGroup(canvas);
      const root = zvBtn.closest('.zv-arrange, .arrange-dropdown');
      if(root) root.classList.remove('open');
      return;
    }

    // Click outside any open dropdown closes it
    document.querySelectorAll('.arrange-dropdown.open, .zv-arrange.open').forEach(root => {
      if(!root.contains(e.target)) root.classList.remove('open');
    });
  }, true); // capture phase: fires even if an overlay would otherwise intercept the click first

  window.addEventListener('resize', function(){
    const root = document.getElementById('arrangeDropdown');
    if(root && root.classList.contains('open')){
      placeMenu(document.getElementById('arrangeMenuBtn'), document.getElementById('arrangeMenu'));
    }
  });
})();
