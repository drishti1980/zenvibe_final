(function () {
  function init() {
    const source = document.getElementById('id_body');
    const shell = source?.closest('.zv-rich-shell');
    if (!shell) return;
    shell.classList.add('zv-email-designer');
    const editor = shell.querySelector('.zv-rich-editor');
    const toolbar = shell.querySelector('.zv-rt-toolbar');
    let range = null, block = null;
    function sync() { source.value = editor.innerHTML; }
    function remember() {
      const selection = getSelection();
      if (!selection.rangeCount || !editor.contains(selection.anchorNode)) return;
      range = selection.getRangeAt(0).cloneRange();
      const node = selection.anchorNode.nodeType === 3 ? selection.anchorNode.parentElement : selection.anchorNode;
      block = node.closest('td,div,p,h2,h3');
      if (block === editor) block = editor.firstElementChild;
    }
    editor.addEventListener('mouseup', remember);
    editor.addEventListener('keyup', remember);
    function restore() { editor.focus(); if (range) { const s = getSelection(); s.removeAllRanges(); s.addRange(range); } }
    function color(label, initial, apply) {
      const wrapper = document.createElement('label'); wrapper.textContent = label + ' ';
      const input = document.createElement('input'); input.type = 'color'; input.value = initial;
      input.addEventListener('input', () => { restore(); apply(input.value); sync(); });
      wrapper.append(input); toolbar.append(wrapper);
    }
    color('Text', '#24364d', value => document.execCommand('foreColor', false, value));
    color('Section background', '#0d3057', value => { if (block && editor.contains(block)) block.style.backgroundColor = value; });
    color('Email background', '#ffffff', value => { if (editor.firstElementChild) editor.firstElementChild.style.backgroundColor = value; });
    const upload = document.createElement('input'); upload.type = 'file'; upload.accept = 'image/png,image/jpeg'; upload.hidden = true;
    const button = document.createElement('button'); button.type = 'button'; button.textContent = 'Upload image'; button.className = 'zv-rt-btn';
    const message = document.createElement('span'); message.setAttribute('role','status');
    button.addEventListener('click', () => upload.click());
    upload.addEventListener('change', async () => {
      if (!upload.files.length) return;
      button.disabled = true; message.textContent = 'Uploading…';
      try {
        const data = new FormData(); data.append('image', upload.files[0]);
        const response = await fetch(source.dataset.uploadUrl, {method:'POST', body:data, headers:{'X-CSRFToken':source.form.querySelector('[name=csrfmiddlewaretoken]').value}});
        const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Upload failed');
        restore();
        const img = document.createElement('img'); img.src = result.url; img.alt = 'Email image'; img.style.cssText = 'max-width:100%;height:auto';
        if (range && editor.contains(range.commonAncestorContainer)) { range.deleteContents(); range.insertNode(img); } else editor.append(img);
        sync(); message.textContent = 'Image added. Save the template to keep your design.';
      } catch (error) { message.textContent = error.message; }
      finally { button.disabled = false; upload.value = ''; }
    });
    toolbar.append(button, upload, message);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
