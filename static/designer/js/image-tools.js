// ZENVIBE IMAGE TOOLS
(function () {
'use strict';

const controllers = new WeakMap();

function attach(canvas, opts) {
    opts = opts || {};

    if (!canvas || !window.fabric) return null;

    if (controllers.has(canvas)) {
        return controllers.get(canvas);
    }

    let bar = document.getElementById('zvImageToolsBar');

    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'zvImageToolsBar';
        bar.className = 'zv-imgtools-bar';
        bar.style.display = 'none';

        bar.innerHTML = `
            <button type="button" data-act="crop">Crop</button>

            <button type="button" data-act="erase">Erase Object</button>

            <button type="button" data-act="rotateLeft">
                ↶ Rotate
            </button>

            <button type="button" data-act="rotateRight">
                ↷ Rotate
            </button>

            <button type="button" data-act="flipX">
                Flip H
            </button>

            <button type="button" data-act="flipY">
                Flip V
            </button>

            <button type="button" data-act="removeBg">
                Remove Background
            </button>

            <button type="button" data-act="panel">
                Adjust
            </button>

            <button type="button" data-act="reset">
                Reset
            </button>

            <button
                type="button"
                data-act="close"
                aria-label="Close image tools"
            >
                ×
            </button>

            <div class="zv-adjust-panel" hidden>

                <label>
                    Blur
                    <input
                        data-filter="blur"
                        type="range"
                        min="0"
                        max="100"
                        value="0"
                    >
                </label>

                <label>
                    Brightness
                    <input
                        data-filter="brightness"
                        type="range"
                        min="-100"
                        max="100"
                        value="0"
                    >
                </label>

                <label>
                    Contrast
                    <input
                        data-filter="contrast"
                        type="range"
                        min="-100"
                        max="100"
                        value="0"
                    >
                </label>

                <label>
                    Saturation
                    <input
                        data-filter="saturation"
                        type="range"
                        min="-100"
                        max="100"
                        value="0"
                    >
                </label>

                <label>
                    Opacity
                    <input
                        data-filter="opacity"
                        type="range"
                        min="0"
                        max="100"
                        value="100"
                    >
                </label>

            </div>
        `;

        document.body.appendChild(bar);
    }

    const panel = bar.querySelector('.zv-adjust-panel');

    let target = null;
    let rect = null;
    let mode = '';

    const isImg = o => o && o.type === 'image';

    const changed = o => {
        canvas.requestRenderAll();

        if (opts.onChange) {
            opts.onChange(o);
        }
    };

    const active = () => {
        const o = canvas.getActiveObject();

        return isImg(o)
            ? o
            : (isImg(target) ? target : null);
    };

    function csrf() {
        const match = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));

        return match
            ? decodeURIComponent(match.split('=')[1])
            : '';
    }

    function positionBar() {

        const side = document.getElementById('toolsPanel') || document.querySelector('.studio-panel');

        const anchor = side ? side.querySelector('.editor-tool-grid') : null;

        if (side && bar.parentElement !== side) {

            if (anchor) {
                anchor.insertAdjacentElement(
                    'afterend',
                    bar
                );
            } else {
                side.prepend(bar);
            }
        }

        bar.style.cssText = `
            display:grid;
            position:static;
            z-index:auto;
            width:100%;
            margin:8px 0 10px;
            gap:6px;
        `;
    }

    function rememberOriginal(o) {

        if (!o._zvOriginalSrc) {
            o._zvOriginalSrc = o.getSrc();
        }

        if (!o._zvOriginalGeometry) {

            o._zvOriginalGeometry = {
                left: o.left,
                top: o.top,
                scaleX: o.scaleX,
                scaleY: o.scaleY,
                angle: o.angle,
                opacity: o.opacity,
                flipX: o.flipX,
                flipY: o.flipY,
                originX: o.originX,
                originY: o.originY
            };
        }
    }

    function open(o) {

        o = o || active();

        if (!isImg(o)) {
            return false;
        }

        target = o;

        const toolsTab = document.querySelector('.rail-tab[data-panel="toolsPanel"]');
        if (toolsTab && !document.getElementById('toolsPanel')?.classList.contains('active')) toolsTab.click();

        rememberOriginal(target);

        panel.hidden = true;

        syncControlsFromTarget(target);

        positionBar();

        return true;
    }

    function finishLock() {

        if (
            target &&
            opts.lockBackgroundAfterEdit &&
            target.backgroundAsset
        ) {

            target.set({
                selectable: false,
                evented: false,
                hasControls: false,
                lockMovementX: true,
                lockMovementY: true,
                lockScalingX: true,
                lockScalingY: true,
                lockRotation: true
            });

            if (canvas.getActiveObject() === target) {
                canvas.discardActiveObject();
            }
        }
    }

    function removeCropControls() {
        const c = document.getElementById('zvCropConfirm');
        if (c) c.remove();
    }

    function close() {

        if (rect) {
            canvas.remove(rect);
        }

        rect = null;
        mode = '';

        removeCropControls();

        bar.style.display = 'none';
        panel.hidden = true;

        finishLock();

        canvas.requestRenderAll();
    }

    function controls() {

        let c =
            document.getElementById('zvCropConfirm');

        if (!c) {

            c = document.createElement('div');

            c.id = 'zvCropConfirm';

            c.className =
                'zv-imgtools-bar zv-crop-confirm';

            document.body.appendChild(c);
        }

        return c;
    }

    function startCrop() {

        removeCropControls();

        if (rect) {
            canvas.remove(rect);
            rect = null;
        }

        const o = target || active();

        if (!isImg(o)) return;

        target = o;

        const toolsTab = document.querySelector('.rail-tab[data-panel="toolsPanel"]');
        if (toolsTab && !document.getElementById('toolsPanel')?.classList.contains('active')) toolsTab.click();

        rememberOriginal(target);

        mode = 'crop';

        const b =
            o.getBoundingRect(true, true);

        rect = new fabric.Rect({
            left: b.left + (b.width * 0.1),
            top: b.top + (b.height * 0.1),

            width: b.width * 0.8,
            height: b.height * 0.8,

            fill: 'rgba(37,99,235,.10)',

            stroke: '#2563eb',

            strokeWidth: 2,

            strokeDashArray: [7, 5],

            transparentCorners: false,

            cornerColor: '#2563eb',

            cornerSize: 12,

            name: 'Crop area',

            excludeFromExport: true,

            objectCaching: false
        });

        canvas.add(rect);
        canvas.setActiveObject(rect);
        canvas.requestRenderAll();

        bar.style.display = 'none';

        const c = controls();

        c.innerHTML = `
            <b>Crop image</b>

            <button type="button" data-ok>
                Apply
            </button>

            <button type="button" data-cancel>
                Cancel
            </button>
        `;

        c.style.cssText = `
            display:flex;
            position:fixed;
            left:50%;
            bottom:24px;
            transform:translateX(-50%);
            z-index:100001;
        `;

        c.querySelector('[data-ok]').onclick =
            applyCrop;

        c.querySelector('[data-cancel]').onclick =
            cancelCrop;
    }

    function cancelCrop() {

        if (rect) {
            canvas.remove(rect);
        }

        rect = null;
        mode = '';

        removeCropControls();

        if (target) {
            canvas.setActiveObject(target);
        }

        bar.style.display = 'none';
        panel.hidden = true;
        canvas.requestRenderAll();
    }

    async function startErase() {
        const o = target || active();
        if (!isImg(o)) return;
        target = o;
        rememberOriginal(target);

        let modal = document.getElementById('zvEraseModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'zvEraseModal';
            modal.className = 'zv-erase-modal';
            modal.hidden = true;
            modal.innerHTML = `
                <div class="zv-erase-backdrop"></div>
                <section class="zv-erase-card" role="dialog" aria-modal="true" aria-label="Erase object from image">
                    <header><h2>Erase object</h2><button type="button" data-erase-close aria-label="Close">×</button></header>
                    <div class="zv-erase-work"><canvas id="zvEraseCanvas"></canvas></div>
                    <div class="zv-erase-controls">
                        <span class="zv-erase-help">Paint over anything you want to remove. Erased pixels become transparent.</span>
                        <label>Brush <input id="zvEraseSize" type="range" min="5" max="160" value="42"></label>
                        <button type="button" data-erase-undo>Undo</button>
                        <button type="button" data-erase-reset>Reset</button>
                        <button type="button" data-erase-cancel>Cancel</button>
                        <button type="button" class="primary" data-erase-apply>Apply</button>
                    </div>
                </section>`;
            document.body.appendChild(modal);
        }

        const work = document.getElementById('zvEraseCanvas');
        const ctx = work.getContext('2d', { willReadFrequently: true });
        const el = o.getElement();
        const nw = el.naturalWidth || el.width || o.width;
        const nh = el.naturalHeight || el.height || o.height;
        work.width = nw;
        work.height = nh;
        ctx.clearRect(0,0,nw,nh);
        ctx.drawImage(el,0,0,nw,nh);

        const original = work.toDataURL('image/png');
        const history = [original];
        let drawing = false;
        let last = null;

        function loadData(url){
            return new Promise(resolve=>{const im=new Image();im.onload=()=>{ctx.clearRect(0,0,nw,nh);ctx.drawImage(im,0,0,nw,nh);resolve();};im.src=url;});
        }
        function pointer(ev){
            const r=work.getBoundingClientRect();
            return {x:(ev.clientX-r.left)*(nw/r.width),y:(ev.clientY-r.top)*(nh/r.height)};
        }
        function eraseLine(a,b){
            const size=Number(document.getElementById('zvEraseSize').value)||42;
            ctx.save();ctx.globalCompositeOperation='destination-out';ctx.lineCap='round';ctx.lineJoin='round';ctx.lineWidth=size;
            ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();ctx.restore();
        }
        work.onpointerdown=ev=>{drawing=true;last=pointer(ev);work.setPointerCapture?.(ev.pointerId);eraseLine(last,last);ev.preventDefault();};
        work.onpointermove=ev=>{if(!drawing)return;const pt=pointer(ev);eraseLine(last,pt);last=pt;ev.preventDefault();};
        const endDraw=()=>{if(!drawing)return;drawing=false;last=null;history.push(work.toDataURL('image/png'));if(history.length>25)history.shift();};
        work.onpointerup=endDraw;work.onpointercancel=endDraw;work.onpointerleave=endDraw;

        const closeErase=()=>{modal.hidden=true;document.body.classList.remove('zv-modal-open');};
        modal.querySelector('[data-erase-close]').onclick=closeErase;
        modal.querySelector('.zv-erase-backdrop').onclick=closeErase;
        modal.querySelector('[data-erase-cancel]').onclick=closeErase;
        modal.querySelector('[data-erase-undo]').onclick=async()=>{if(history.length>1){history.pop();await loadData(history[history.length-1]);}};
        modal.querySelector('[data-erase-reset]').onclick=async()=>{history.splice(1);await loadData(original);};
        modal.querySelector('[data-erase-apply]').onclick=async()=>{
            const btn=modal.querySelector('[data-erase-apply]');btn.disabled=true;btn.textContent='Applying…';
            try{await replace(o,work.toDataURL('image/png'));closeErase();bar.style.display='none';panel.hidden=true;}
            catch(err){console.error(err);alert('The erased image could not be applied.');}
            finally{btn.disabled=false;btn.textContent='Apply';}
        };

        bar.style.display='none';panel.hidden=true;modal.hidden=false;document.body.classList.add('zv-modal-open');
    }

    function copyMeta(a, b) {

        [
            'objectId',
            'name',
            'fieldType',
            'backgroundAsset',
            'customerEditable',
            'baseSrc',
            'workingSrc',
            '_zvPendingArtwork',
            'sourceNormalizedBox',
            'sourceConfidence',
            'sourceText',
            'isBase',
            'printZone',
            'lockScalingFlip'
        ].forEach(k => {

            if (a[k] !== undefined) {
                b[k] = a[k];
            }

        });

        b._zvOriginalSrc =
            a._zvOriginalSrc || a.getSrc();

        b._zvOriginalGeometry = a._zvOriginalGeometry;
        if (a.clipPath) b.clipPath = a.clipPath;
    }

    function replace(o, url, geom) {

        return new Promise((resolve, reject) => {

            fabric.Image.fromURL(
                url,

                n => {

                    if (!n) {

                        reject(
                            new Error(
                                'Unable to rebuild edited image'
                            )
                        );

                        return;
                    }

                    copyMeta(o, n);

                    n.set(
                        geom || {
                            left: o.left,
                            top: o.top,

                            originX: o.originX,
                            originY: o.originY,

                            scaleX: o.scaleX,
                            scaleY: o.scaleY,

                            angle: o.angle,

                            opacity: o.opacity,

                            flipX: o.flipX,
                            flipY: o.flipY,

                            selectable: true,
                            evented: true,
                            hasControls: true
                        }
                    );

                    const z =
                        canvas
                            .getObjects()
                            .indexOf(o);

                    canvas.remove(o);

                    canvas.insertAt(
                        n,
                        Math.max(0, z),
                        false
                    );

                    target = n;

                    canvas.setActiveObject(n);

                    changed(n);

                    resolve(n);
                },

                {
                    crossOrigin: 'anonymous'
                }
            );
        });
    }

    async function applyCrop() {

        if (!target || !rect) {
            cancelCrop();
            return;
        }

        const ib =
            target.getBoundingRect(true, true);

        const rb =
            rect.getBoundingRect(true, true);

        const x =
            Math.max(ib.left, rb.left);

        const y =
            Math.max(ib.top, rb.top);

        const x2 =
            Math.min(
                ib.left + ib.width,
                rb.left + rb.width
            );

        const y2 =
            Math.min(
                ib.top + ib.height,
                rb.top + rb.height
            );

        if (x2 <= x || y2 <= y) {

            cancelCrop();
            return;
        }

        const el =
            target.getElement();

        const nw =
            el.naturalWidth || el.width;

        const nh =
            el.naturalHeight || el.height;

        let sx =
            Math.round(
                ((x - ib.left) / ib.width) * nw
            );

        let sy =
            Math.round(
                ((y - ib.top) / ib.height) * nh
            );

        let sw =
            Math.max(
                1,
                Math.round(
                    ((x2 - x) / ib.width) * nw
                )
            );

        let sh =
            Math.max(
                1,
                Math.round(
                    ((y2 - y) / ib.height) * nh
                )
            );

        sx =
            Math.max(
                0,
                Math.min(nw - 1, sx)
            );

        sy =
            Math.max(
                0,
                Math.min(nh - 1, sy)
            );

        sw =
            Math.min(sw, nw - sx);

        sh =
            Math.min(sh, nh - sy);

        try {

            const out =
                document.createElement('canvas');

            out.width = sw;
            out.height = sh;

            out
                .getContext('2d')
                .drawImage(
                    el,
                    sx,
                    sy,
                    sw,
                    sh,
                    0,
                    0,
                    sw,
                    sh
                );

            const old = target;

            await replace(
                old,
                out.toDataURL('image/png'),
                {
                    left: x,
                    top: y,

                    originX: 'left',
                    originY: 'top',

                    scaleX:
                        (x2 - x) / sw,

                    scaleY:
                        (y2 - y) / sh,

                    angle: old.angle || 0,

                    opacity: old.opacity,

                    flipX: old.flipX,
                    flipY: old.flipY,

                    selectable: true,
                    evented: true,
                    hasControls: true
                }
            );

        } catch (e) {

            console.error(
                'ZenVibe crop failed',
                e
            );

            alert(
                'Crop could not be applied.'
            );
        }

        cancelCrop();
    }

    function filterValue(name) {

        const input =
            bar.querySelector(
                `[data-filter="${name}"]`
            );

        return Number(input.value);
    }

    function adjust() {

        const o =
            target || active();

        if (!isImg(o)) {
            return;
        }

        rememberOriginal(o);

        const filters = [];

        const blur =
            filterValue('blur');

        const brightness =
            filterValue('brightness');

        const contrast =
            filterValue('contrast');

        const saturation =
            filterValue('saturation');

        const opacity =
            filterValue('opacity');

        if (blur) {

            filters.push(
                new fabric.Image.filters.Blur({
                    blur:
                        Math.max(
                            0.01,
                            blur / 100
                        )
                })
            );
        }

        if (brightness) {

            filters.push(
                new fabric.Image.filters.Brightness({
                    brightness:
                        brightness / 100
                })
            );
        }

        if (contrast) {

            filters.push(
                new fabric.Image.filters.Contrast({
                    contrast:
                        contrast / 100
                })
            );
        }

        if (saturation) {

            filters.push(
                new fabric.Image.filters.Saturation({
                    saturation:
                        saturation / 100
                })
            );
        }

        o.filters = filters;

        o.opacity =
            opacity / 100;

        o.applyFilters();

        changed(o);
    }

    function syncControlsFromTarget(o) {

        if (!o) return;

        bar.querySelector(
            '[data-filter="blur"]'
        ).value = 0;

        bar.querySelector(
            '[data-filter="brightness"]'
        ).value = 0;

        bar.querySelector(
            '[data-filter="contrast"]'
        ).value = 0;

        bar.querySelector(
            '[data-filter="saturation"]'
        ).value = 0;

        bar.querySelector(
            '[data-filter="opacity"]'
        ).value =
            Math.round(
                (o.opacity ?? 1) * 100
            );
    }

    async function removeBackground() {

        const o =
            target || active();

        if (!isImg(o)) {
            alert(
                'Please select an image first.'
            );
            return;
        }

        rememberOriginal(o);

        const btn =
            bar.querySelector(
                '[data-act="removeBg"]'
            );

        const oldText =
            btn.textContent;

        btn.disabled = true;
        btn.textContent =
            'Removing...';

        try {

            const el =
                o.getElement();

            const w =
                el.naturalWidth || el.width;

            const h =
                el.naturalHeight || el.height;

            const temp =
                document.createElement('canvas');

            temp.width = w;
            temp.height = h;

            const ctx =
                temp.getContext('2d');

            ctx.drawImage(
                el,
                0,
                0,
                w,
                h
            );

            const source =
                temp.toDataURL(
                    'image/png'
                );

            const response =
                await fetch(
                    '/zenvibe/api/image/remove-background/',
                    {
                        method: 'POST',

                        credentials:
                            'same-origin',

                        headers: {
                            'Content-Type':
                                'application/json',

                            'X-CSRFToken':
                                csrf(),

                            'X-Requested-With':
                                'XMLHttpRequest'
                        },

                        body:
                            JSON.stringify({
                                image: source
                            })
                    }
                );

            const contentType =
                response.headers.get(
                    'content-type'
                ) || '';

            if (
                !contentType.includes(
                    'application/json'
                )
            ) {

                const text =
                    await response.text();

                console.error(
                    'Background removal invalid response:',
                    response.status,
                    text
                );

                throw new Error(
                    `Background removal failed (${response.status}).`
                );
            }

            const data =
                await response.json();

            if (
                !response.ok ||
                !data.ok
            ) {

                throw new Error(
                    data.error ||
                    'Background removal failed.'
                );
            }

            await replace(
                o,
                data.image
            );

            positionBar();

        } catch (error) {

            console.error(
                'Background removal error:',
                error
            );

            alert(
                error.message ||
                'Background removal failed.'
            );

        } finally {

            btn.disabled = false;
            btn.textContent =
                oldText;
        }
    }

    async function resetImage() {

        const o =
            target || active();

        if (!o) return;

        const originalSrc =
            o._zvOriginalSrc;

        const originalGeometry =
            o._zvOriginalGeometry;

        if (
            originalSrc &&
            originalSrc !== o.getSrc()
        ) {

            try {

                const restored =
                    await replace(
                        o,
                        originalSrc,
                        originalGeometry || undefined
                    );

                restored.filters = [];
                restored.opacity = 1;
                restored.applyFilters();

                target = restored;

            } catch (e) {

                console.error(
                    'Image reset failed',
                    e
                );
            }

        } else {

            o.filters = [];
            o.opacity = 1;

            if (originalGeometry) {

                o.set({
                    angle:
                        originalGeometry.angle || 0,

                    flipX:
                        !!originalGeometry.flipX,

                    flipY:
                        !!originalGeometry.flipY
                });
            }

            o.applyFilters();

            changed(o);
        }

        syncControlsFromTarget(
            target || o
        );
    }

    bar
        .querySelectorAll(
            '[data-filter]'
        )
        .forEach(input => {

            input.addEventListener(
                'input',
                adjust
            );
        });

    bar.onclick = async e => {

        const act =
            e.target.dataset.act;

        if (!act) {
            return;
        }

        const o =
            target || active();

        if (act === 'crop') {

            startCrop();

        } else if (act === 'erase') {

            await startErase();

        } else if (
            act === 'panel'
        ) {

            panel.hidden =
                !panel.hidden;

        } else if (
            act === 'rotateLeft' &&
            o
        ) {

            rememberOriginal(o);

            o.rotate(
                ((o.angle || 0) - 90) % 360
            );

            o.setCoords();

            changed(o);

        } else if (
            act === 'rotateRight' &&
            o
        ) {

            rememberOriginal(o);

            o.rotate(
                ((o.angle || 0) + 90) % 360
            );

            o.setCoords();

            changed(o);

        } else if (
            act === 'flipX' &&
            o
        ) {

            rememberOriginal(o);

            o.set(
                'flipX',
                !o.flipX
            );

            o.setCoords();

            changed(o);

        } else if (
            act === 'flipY' &&
            o
        ) {

            rememberOriginal(o);

            o.set(
                'flipY',
                !o.flipY
            );

            o.setCoords();

            changed(o);

        } else if (
            act === 'removeBg'
        ) {

            await removeBackground();

        } else if (
            act === 'reset'
        ) {

            await resetImage();

        } else if (
            act === 'close'
        ) {

            close();
        }
    };

    const onSelection = () => {

        if (rect) return;

        const o =
            canvas.getActiveObject();

        if (
            target &&
            o !== target
        ) {

            bar.style.display =
                'none';

            panel.hidden = true;

            target = null;
        }
    };

    canvas.on(
        'selection:created',
        onSelection
    );

    canvas.on(
        'selection:updated',
        onSelection
    );

    canvas.on(
        'selection:cleared',
        () => {

            if (!rect) {

                bar.style.display =
                    'none';

                panel.hidden = true;

                target = null;
            }
        }
    );

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && mode === 'crop') {
            cancelCrop();
        }
    });

    async function run(action, o) {
        if (o && isImg(o)) {
            target = o;
            rememberOriginal(target);
        } else if (!target) {
            target = active();
        }
        if (!isImg(target)) return false;
        bar.style.display = 'none';
        panel.hidden = true;
        if (action === 'crop') startCrop();
        else if (action === 'erase') await startErase();
        else if (action === 'removeBg') await removeBackground();
        else if (action === 'adjust') { open(target); panel.hidden = false; bar.style.display = 'grid'; }
        else if (action === 'rotateLeft') { rememberOriginal(target); target.rotate(((target.angle||0)-90)%360); target.setCoords(); changed(target); }
        else if (action === 'rotateRight') { rememberOriginal(target); target.rotate(((target.angle||0)+90)%360); target.setCoords(); changed(target); }
        else if (action === 'flipX') { rememberOriginal(target); target.set('flipX',!target.flipX); target.setCoords(); changed(target); }
        else if (action === 'flipY') { rememberOriginal(target); target.set('flipY',!target.flipY); target.setCoords(); changed(target); }
        else if (action === 'reset') await resetImage();
        return true;
    }

    const api = {
        open,
        close,
        run,
        getTarget: () => target
    };

    controllers.set(
        canvas,
        api
    );

    return api;
}

function open(canvas, target) {

    const c =
        controllers.get(canvas) ||
        attach(canvas, {});

    return c &&
        c.open(target);
}

function close(canvas) {

    const c = controllers.get(canvas);
    if (c) c.close();
}

function run(canvas, action, target) {
    const c = controllers.get(canvas) || attach(canvas, {});
    return c && c.run(action, target);
}

window.ZenImageTools = {
    attach,
    open,
    close,
    run
};

})();