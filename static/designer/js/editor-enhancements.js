(function(){
'use strict';
const canvas=window.designCanvas;if(!canvas)return;
const $=id=>document.getElementById(id);const P=window.PRODUCT||{},W=P.width||1050,H=P.height||600;
const fireChange=o=>{canvas.requestRenderAll();canvas.fire('object:modified',{target:o||canvas.getActiveObject()});};

// Clear document-colour meaning and keep the swatch synced with the actual page.
function syncBackgroundUI(){const c=String(canvas.backgroundColor||'#ffffff');if(/^#[0-9a-f]{6}$/i.test(c)){$('backgroundColor').value=c;$('backgroundHex').textContent=c.toUpperCase();}}
$('backgroundColor')?.addEventListener('input',e=>$('backgroundHex').textContent=e.target.value.toUpperCase());
$('applyBackgroundBtn')?.addEventListener('click',()=>setTimeout(syncBackgroundUI,0));canvas.on('after:render',syncBackgroundUI);

// ============================================================
// ZENVIBE PHYSICAL RULER
// Display unit: inches
// Canvas/template coordinates remain pixels.
// ============================================================

function niceInchStep(totalInches, displayPixels) {
    if (!totalInches || !displayPixels) return 1;

    const pxPerInch = displayPixels / totalInches;

    // Automatically choose a readable ruler interval.
    const steps = [
        0.125,  // 1/8"
        0.25,   // 1/4"
        0.5,    // 1/2"
        1,
        2,
        5,
        10,
        20,
        50,
        100
    ];

    for (const step of steps) {
        if (step * pxPerInch >= 70) {
            return step;
        }
    }

    return 100;
}

function formatInches(value) {
    if (Math.abs(value - Math.round(value)) < 0.0001) {
        return String(Math.round(value));
    }

    return Number(value.toFixed(3)).toString();
}

function drawRulers() {
    const hr = $('horizontalRuler');
    const vr = $('verticalRuler');
    const stage = document.querySelector('.canvas-stage');
    const canvasEl = canvas.upperCanvasEl || canvas.lowerCanvasEl;

    if (!hr || !vr || !stage || !canvasEl) return;

    const sr = stage.getBoundingClientRect();
    const cr = canvasEl.getBoundingClientRect();

    const left = cr.left - sr.left;
    const top = cr.top - sr.top;
    const displayWidth = cr.width;
    const displayHeight = cr.height;

        /*
    * ============================================================
    * PAGE-SPECIFIC PHYSICAL PRINT DIMENSIONS
    * ============================================================
    *
    * P.width / P.height
    *     = internal Fabric editor coordinate system.
    *
    * surface.printWidth / surface.printHeight
    *     = real physical dimensions in inches for ACTIVE page.
    *
    * Example:
    * Front -> 117" x 38"
    * Roof  -> 120" x 120"
    *
    * Product-level P.printWidth/P.printHeight remain fallback only.
    */

  const activeSurface =
      typeof window.getZenVibeActiveSurface === 'function'
          ? window.getZenVibeActiveSurface()
          : null;

  const physicalWidth = Number(
      activeSurface?.printWidth ||
      P.printWidth ||
      0
  );

  const physicalHeight = Number(
      activeSurface?.printHeight ||
      P.printHeight ||
      0
  );

    // Product has not been migrated to inch settings yet.
    // Keep old pixel ruler so existing products don't break.
    if (
        !physicalWidth ||
        !physicalHeight ||
        physicalWidth <= 0 ||
        physicalHeight <= 0
    ) {
        drawLegacyPixelRulers(
            hr,
            vr,
            left,
            top,
            displayWidth,
            displayHeight
        );
        return;
    }

    hr.innerHTML = '';
    vr.innerHTML = '';

    Object.assign(hr.style, {
        left: left + 'px',
        top: Math.max(0, top - 28) + 'px',
        width: displayWidth + 'px',
        height: '28px'
    });

    Object.assign(vr.style, {
        left: Math.max(0, left - 28) + 'px',
        top: top + 'px',
        width: '28px',
        height: displayHeight + 'px'
    });

    const pxPerInchX = displayWidth / physicalWidth;
    const pxPerInchY = displayHeight / physicalHeight;

    const majorX = niceInchStep(physicalWidth, displayWidth);
    const majorY = niceInchStep(physicalHeight, displayHeight);

    const minorX = majorX / 4;
    const minorY = majorY / 4;

    // Horizontal ruler
    for (
        let value = 0;
        value <= physicalWidth + 0.0001;
        value += minorX
    ) {
        const x = value * pxPerInchX;

        if (x > displayWidth + 1) break;

        const tick = document.createElement('span');

        const isMajor =
            Math.abs(
                value / majorX -
                Math.round(value / majorX)
            ) < 0.001;

        tick.className = isMajor ? 'major' : 'minor';
        tick.style.left = x + 'px';

        tick.innerHTML =
            '<i></i>' +
            (
                isMajor
                    ? '<b>' + formatInches(value) + '</b>'
                    : ''
            );

        hr.appendChild(tick);
    }

    // Vertical ruler
    for (
        let value = 0;
        value <= physicalHeight + 0.0001;
        value += minorY
    ) {
        const y = value * pxPerInchY;

        if (y > displayHeight + 1) break;

        const tick = document.createElement('span');

        const isMajor =
            Math.abs(
                value / majorY -
                Math.round(value / majorY)
            ) < 0.001;

        tick.className = isMajor ? 'major' : 'minor';
        tick.style.top = y + 'px';

        tick.innerHTML =
            '<i></i>' +
            (
                isMajor
                    ? '<b>' + formatInches(value) + '</b>'
                    : ''
            );

        vr.appendChild(tick);
    }

    const guide = $('smartGuideLayer');

    if (guide) {
        guide.style.left = left + 'px';
        guide.style.top = top + 'px';
        guide.style.width = displayWidth + 'px';
        guide.style.height = displayHeight + 'px';
    }
}


// ============================================================
// LEGACY PIXEL RULER
// Used only when product inch dimensions are not configured.
// ============================================================

function niceRulerStep(zoom) {
    const targetPixels = 82;
    const raw = targetPixels / Math.max(zoom, .01);
    const power = Math.pow(
        10,
        Math.floor(Math.log10(raw))
    );

    const normal = raw / power;
    const factor =
        normal <= 1 ? 1 :
        normal <= 2 ? 2 :
        normal <= 5 ? 5 : 10;

    return factor * power;
}

function drawLegacyPixelRulers(
    hr,
    vr,
    left,
    top,
    width,
    height
) {
    const zoom = canvas.getZoom() || 1;

    const major = niceRulerStep(zoom);
    const minor = major / 5;

    hr.innerHTML = '';
    vr.innerHTML = '';

    Object.assign(hr.style, {
        left: left + 'px',
        top: Math.max(0, top - 28) + 'px',
        width: width + 'px',
        height: '28px'
    });

    Object.assign(vr.style, {
        left: Math.max(0, left - 28) + 'px',
        top: top + 'px',
        width: '28px',
        height: height + 'px'
    });

    const maxX = Math.ceil(W / minor) * minor;
    const maxY = Math.ceil(H / minor) * minor;

    for (let v = 0; v <= maxX + .001; v += minor) {
        const x = v * zoom;

        if (x > width + 1) break;

        const tick = document.createElement('span');

        const isMajor =
            Math.abs(
                (v / major) -
                Math.round(v / major)
            ) < .001;

        tick.className = isMajor ? 'major' : 'minor';
        tick.style.left = x + 'px';

        tick.innerHTML =
            '<i></i>' +
            (
                isMajor
                    ? '<b>' + Math.round(v) + '</b>'
                    : ''
            );

        hr.appendChild(tick);
    }

    for (let v = 0; v <= maxY + .001; v += minor) {
        const y = v * zoom;

        if (y > height + 1) break;

        const tick = document.createElement('span');

        const isMajor =
            Math.abs(
                (v / major) -
                Math.round(v / major)
            ) < .001;

        tick.className = isMajor ? 'major' : 'minor';
        tick.style.top = y + 'px';

        tick.innerHTML =
            '<i></i>' +
            (
                isMajor
                    ? '<b>' + Math.round(v) + '</b>'
                    : ''
            );

        vr.appendChild(tick);
    }

    const guide = $('smartGuideLayer');

    if (guide) {
        guide.style.left = left + 'px';
        guide.style.top = top + 'px';
        guide.style.width = width + 'px';
        guide.style.height = height + 'px';
    }
}

const rulerObserver=new ResizeObserver(()=>requestAnimationFrame(drawRulers));
if($('canvasWrap'))rulerObserver.observe($('canvasWrap'));
const stageScroll=document.querySelector('.studio-canvas-scroll');
stageScroll?.addEventListener('scroll',()=>requestAnimationFrame(drawRulers),{passive:true});
canvas.on('after:render',()=>requestAnimationFrame(drawRulers));
window.addEventListener(
    'resize',
    () => requestAnimationFrame(drawRulers)
);

window.addEventListener(
    'zenvibe:zoom',
    () => requestAnimationFrame(drawRulers)
);

/*
 * editor.js dispatches this whenever Front / Roof / another
 * configured print surface becomes active.
 */
window.addEventListener(
    'zenvibe:pagechange',
    () => {
        requestAnimationFrame(drawRulers);
    }
);

setTimeout(drawRulers,80);

// Smart alignment lines and live X/Y/size labels while dragging with mouse or touchpad.
const layer=$('smartGuideLayer'),badge=$('measurementBadge');
function clearGuides(){if(layer)layer.innerHTML='';if(badge)badge.hidden=true}
function line(cls,pos){const d=document.createElement('div');d.className='smart-guide '+cls;if(cls==='vertical')d.style.left=pos+'px';else d.style.top=pos+'px';layer.appendChild(d)}
canvas.on('object:moving',e=>{const o=e.target;if(!o||!layer)return;layer.innerHTML='';const z=canvas.getZoom(),r=o.getBoundingRect(true,true),cx=r.left+r.width/2,cy=r.top+r.height/2,tol=7/z;const candidatesX=[0,W/2,W],candidatesY=[0,H/2,H];let snappedX=null,snappedY=null;candidatesX.forEach(x=>{if(Math.abs(cx-x)<tol){o.left+=(x-cx);snappedX=x;line('vertical',x*z)}});candidatesY.forEach(y=>{if(Math.abs(cy-y)<tol){o.top+=(y-cy);snappedY=y;line('horizontal',y*z)}});if(badge){badge.hidden=false;badge.textContent=`X ${Math.round(o.left)}   Y ${Math.round(o.top)}   W ${Math.round(r.width)}   H ${Math.round(r.height)}`;badge.style.left=Math.min((o.left*z)+20,(canvas.getWidth()-220))+'px';badge.style.top=Math.max(8,(o.top*z)-34)+'px'}o.setCoords()});
canvas.on('object:scaling',e=>{const o=e.target,r=o.getBoundingRect(true,true);if(badge){badge.hidden=false;badge.textContent=`W ${Math.round(r.width)}   H ${Math.round(r.height)}`}});canvas.on('object:rotating',e=>{if(badge){badge.hidden=false;badge.textContent=`${Math.round(e.target.angle||0)}°`}});canvas.on('object:modified',clearGuides);canvas.on('mouse:up',clearGuides);

// Expanded searchable SVG/path shape catalogue.
const shapes=[
 ['square','Square','rect'],['rounded','Rounded square','roundRect'],['circle','Circle','circle'],['ellipse','Oval','ellipse'],['triangle','Triangle','triangle'],['diamond','Diamond','diamond'],['pentagon','Pentagon','pentagon'],['hexagon','Hexagon','hexagon'],['octagon','Octagon','poly8'],['star','Five-point star','star'],['starburst','Starburst','star12'],['heart','Heart','heart'],['arrow-right','Right arrow','arrowRight'],['arrow-left','Left arrow','arrowLeft'],['arrow-up','Up arrow','arrowUp'],['arrow-down','Down arrow','arrowDown'],['double-arrow','Double arrow','doubleArrow'],['speech','Speech bubble','speech'],['cloud','Cloud','cloud'],['lightning','Lightning bolt','lightning'],['drop','Water drop','drop'],['moon','Crescent moon','moon'],['sun','Sun','sun'],['shield','Shield','shield'],['badge','Badge','badge'],['ribbon','Ribbon','ribbon'],['banner','Banner','banner'],['chevron','Chevron','chevron'],['plus','Plus','cross'],['minus','Minus','line'],['line','Solid line','line'],['dashed','Dashed line','dashLine'],['dotted','Dotted line','dotLine'],['wave','Wave','wave'],['zigzag','Zigzag','zigzag'],['arc','Arc','arc'],['bracket','Bracket','bracket'],['blob-1','Organic blob','blob1'],['blob-2','Organic blob 2','blob2'],['flower','Flower','flower'],['leaf','Leaf','leaf'],['location','Location pin','pin'],['check','Check mark','check'],['x','Cross mark','xmark'],['play','Play button','play'],['camera','Camera','camera'],['phone','Phone','phone'],['mail','Envelope','mail'],['home','Home','home'],['person','Person','person'],['building','Building','building'],['cart','Shopping cart','cart'],['gift','Gift','gift'],['crown','Crown','crown'],['sparkle','Sparkle','sparkle'],['frame','Photo frame','frame'],['quote','Quotation marks','quote'],['label','Price label','label'],['ticket','Ticket','ticket'],['hex-frame','Hexagon frame','hexframe']
];
const paths={
 arrowLeft:'M180 35H70V0L0 70l70 70v-35h110z',arrowUp:'M35 180V70H0L70 0l70 70h-35v110z',arrowDown:'M35 0v110H0l70 70 70-70h-35V0z',doubleArrow:'M0 70l55-55v35h70V15l55 55-55 55V90H55v35z',
 cloud:'M42 125C8 125 0 82 26 67c-2-39 47-57 70-28 30-23 76-1 72 38 31 9 29 48-5 48z',lightning:'M80 0L20 95h55l-20 85 105-115h-65l35-65z',drop:'M90 0C70 42 25 82 25 125a65 65 0 00130 0C155 82 110 42 90 0z',moon:'M145 10A80 80 0 1180 155 67 67 0 00145 10z',
 shield:'M90 0l75 28v55c0 48-30 80-75 107C45 163 15 131 15 83V28z',ribbon:'M0 25h180v95H0l28-47z M180 25l-28 48 28 47z',banner:'M0 25h180v110H0l28-55z',chevron:'M0 35l45 55-45 55h55l45-55-45-55z',
 zigzag:'M0 80l35-50 35 100 35-100 35 100 35-50',arc:'M0 100Q90 0 180 100',bracket:'M50 0H10v180h40 M130 0h40v180h-40',blob1:'M45 15C85-8 145 5 165 48c23 50-10 113-65 125-49 11-101-20-96-76 4-43 9-61 41-82z',blob2:'M20 52C38 5 101-12 145 18c43 29 45 93 9 131-34 36-103 32-134-7-25-32-15-55 0-90z',
 leaf:'M170 10C75 5 15 55 20 155c72 8 135-34 150-145z M35 142L145 30',pin:'M90 0a65 65 0 0165 65c0 48-65 120-65 120S25 113 25 65A65 65 0 0190 0zm0 38a27 27 0 100 54 27 27 0 000-54z',check:'M10 90l45 45L170 20',xmark:'M20 20l140 140M160 20L20 160',play:'M35 10l130 80-130 80z',
 home:'M10 85L90 10l80 75v85H110v-55H70v55H10z',gift:'M10 70h160v100H10z M0 45h180v35H0z M90 45v125 M90 45C55 45 35 30 40 13c7-24 43 4 50 32zm0 0c35 0 55-15 50-32-7-24-43 4-50 32z',crown:'M10 145L0 35l48 40L90 5l42 70 48-40-10 110z',sparkle:'M90 0l18 62 62 18-62 18-18 62-18-62-62-18 62-18z',quote:'M15 25h65v65H45c0 25-10 45-30 60 12-20 14-38 0-60zm90 0h65v65h-35c0 25-10 45-30 60 12-20 14-38 0-60z',label:'M0 20v140h115l65-70-65-70z',ticket:'M0 20h180v45a25 25 0 000 50v45H0v-45a25 25 0 000-50z'
};
function poly(n,r=80){let a=[];for(let i=0;i<n;i++){let q=-Math.PI/2+i*2*Math.PI/n;a.push({x:r+Math.cos(q)*r,y:r+Math.sin(q)*r})}return a}function star(n=12,ro=85,ri=62){let a=[];for(let i=0;i<n*2;i++){let r=i%2?ri:ro,q=-Math.PI/2+i*Math.PI/n;a.push({x:ro+Math.cos(q)*r,y:ro+Math.sin(q)*r})}return a}
function addEnhancedShape(type,name){let o,b={left:W/2-90,top:H/2-80,fill:'#6546d7',stroke:'#6546d7',strokeWidth:0,name};if(type==='poly8')o=new fabric.Polygon(poly(8),b);else if(type==='star12'||type==='badge')o=new fabric.Polygon(star(type==='badge'?18:12),b);else if(type==='sun'){o=new fabric.Polygon(star(16,85,66),b)}else if(type==='flower'){o=new fabric.Polygon(star(8,85,42),b)}else if(type==='frame'){o=new fabric.Rect({...b,width:180,height:140,fill:'transparent',strokeWidth:12})}else if(type==='hexframe'){o=new fabric.Polygon(poly(6),{...b,fill:'transparent',strokeWidth:12})}else if(type==='dotLine'){o=new fabric.Line([0,0,220,0],{left:W/2-110,top:H/2,stroke:'#17233c',strokeWidth:5,strokeDashArray:[2,12],strokeLineCap:'round',name})}else if(paths[type]){o=new fabric.Path(paths[type],{...b,fill:['zigzag','arc','bracket','check','xmark'].includes(type)?'transparent':b.fill,strokeWidth:['zigzag','arc','bracket','check','xmark'].includes(type)?7:0,strokeLineCap:'round',strokeLineJoin:'round'})}else return false;o.objectId='o'+Math.random().toString(36).slice(2,10);canvas.add(o);canvas.setActiveObject(o);fireChange(o);return true}
function renderShapes(filter=''){const lib=$('shapeLibrary');if(!lib)return;lib.innerHTML='';shapes.filter(x=>(x[0]+' '+x[1]).includes(filter.toLowerCase())).forEach(([key,name,type])=>{const b=document.createElement('button');b.title=name;b.dataset.enhancedShape=type;b.innerHTML=`<span class="shape-symbol">${({'square':'■','rounded':'▰','circle':'●','ellipse':'⬭','triangle':'▲','diamond':'◆','pentagon':'⬟','hexagon':'⬢','octagon':'⯃','star':'★','starburst':'✹','heart':'♥','arrow-right':'➜','arrow-left':'⬅','arrow-up':'⬆','arrow-down':'⬇','double-arrow':'↔','speech':'▰','cloud':'☁','lightning':'ϟ','drop':'💧','moon':'☾','sun':'☀','shield':'⬟','badge':'✺','ribbon':'🎗','banner':'⚑','chevron':'❯','plus':'✚','minus':'━','line':'━','dashed':'┅','dotted':'⋯','wave':'〰','zigzag':'〽','arc':'⌒','bracket':'[ ]','flower':'✿','leaf':'❧','location':'⌖','check':'✓','x':'×','play':'▶','camera':'▣','phone':'☎','mail':'✉','home':'⌂','person':'♟','building':'▥','cart':'🛒','gift':'🎁','crown':'♛','sparkle':'✦','frame':'▣','quote':'❝','label':'⬖','ticket':'🎟','hex-frame':'⬡'})[key]||'●'}</span><small>${name}</small>`;b.onclick=()=>{if(!addEnhancedShape(type,name)){const old=document.querySelector(`[data-shape="${type}"]`);old?.click()}};lib.appendChild(b)})}
$('elementSearch')?.addEventListener('input',e=>renderShapes(e.target.value));renderShapes();

// Larger font list. Fonts are lazy-loaded only when selected to keep initial load fast.
const fonts=['ABeeZee','Abel','Abril Fatface','Alegreya','Alegreya Sans','Alfa Slab One','Amatic SC','Anton','Archivo','Archivo Black','Arimo','Arvo','Asap','Assistant','Bangers','Barlow','Barlow Condensed','Bebas Neue','Bitter','Bodoni Moda','Cabin','Cairo','Cardo','Catamaran','Caveat','Cinzel','Comfortaa','Cormorant Garamond','Crimson Text','Dancing Script','DM Sans','Domine','EB Garamond','Exo 2','Fira Sans','Fjalla One','Fredoka','Great Vibes','Heebo','IBM Plex Sans','Inconsolata','Inter','Josefin Sans','Karla','Lato','League Spartan','Libre Baskerville','Libre Franklin','Lobster','Lora','Manrope','Merriweather','Merriweather Sans','Montserrat','Mukta','Noto Sans','Noto Serif','Nunito','Nunito Sans','Open Sans','Orbitron','Oswald','Overpass','Pacifico','Permanent Marker','Playfair Display','Poppins','PT Sans','PT Serif','Quicksand','Raleway','Righteous','Roboto','Roboto Condensed','Roboto Mono','Roboto Slab','Rubik','Sacramento','Satisfy','Signika','Slabo 27px','Source Sans 3','Source Serif 4','Space Grotesk','Teko','Titillium Web','Ubuntu','Varela Round','Work Sans','Yanone Kaffeesatz','Zilla Slab'];
function loadFont(f){if(['Arial','Georgia','Verdana'].includes(f))return;const id='font-'+f.replace(/\W/g,'-');if($(id))return;const l=document.createElement('link');l.id=id;l.rel='stylesheet';l.href='https://fonts.googleapis.com/css2?family='+encodeURIComponent(f).replace(/%20/g,'+')+':wght@300;400;500;600;700;800&display=swap';document.head.appendChild(l)}
function renderFonts(q=''){const lib=$('fontLibrary'),sel=$('fontFamily');if(!lib)return;sel.innerHTML='';['Arial','Georgia','Verdana',...fonts].forEach(f=>sel.add(new Option(f,f)));lib.innerHTML='';fonts.filter(f=>f.toLowerCase().includes(q.toLowerCase())).forEach(f=>{const b=document.createElement('button');b.innerHTML=`<span style="font-family:'${f}',sans-serif">${f}</span><small>${/Script|Caveat|Pacifico|Lobster|Vibes|Sacramento|Satisfy/.test(f)?'Handwriting':'Google font'}</small>`;b.onclick=()=>{loadFont(f);const o=canvas.getActiveObject();if(o&&['i-text','text','textbox'].includes(o.type)){o.set('fontFamily',f);fireChange(o)}sel.value=f};lib.appendChild(b)})}
$('fontSearch')?.addEventListener('input',e=>renderFonts(e.target.value));renderFonts();

// Broad emoji catalogue with categories and instant search.
const groups={Smileys:'😀 😃 😄 😁 😆 😅 😂 🤣 😊 😇 🙂 🙃 😉 😌 😍 🥰 😘 😗 😙 😚 😋 😛 😝 😜 🤪 🤨 🧐 🤓 😎 🥸 🤩 🥳 😏 😒 😞 😔 😟 😕 🙁 ☹️ 😣 😖 😫 😩 🥺 😢 😭 😤 😠 😡 🤬 🤯 😳 🥵 🥶 😱 😨 😰 😥 😓 🤗 🤔 🫣 🤭 🫢 🫡 🤫 🫠 🤥 😶 🫥 😐 🫤 😑 😬 🙄 😯 😦 😧 😮 😲 🥱 😴 🤤 😪 😵 🤐 🥴 🤢 🤮 🤧 😷 🤒 🤕',Hands:'👋 🤚 🖐️ ✋ 🖖 🫱 🫲 🫳 🫴 👌 🤌 🤏 ✌️ 🤞 🫰 🤟 🤘 🤙 👈 👉 👆 👇 ☝️ 🫵 👍 👎 ✊ 👊 🤛 🤜 👏 🙌 🫶 👐 🤲 🤝 🙏 ✍️ 💅 🤳 💪',Hearts:'❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 ❣️ 💕 💞 💓 💗 💖 💘 💝 💟 ♥️ 🩷 🩵 🩶',Celebration:'🎉 🎊 🎈 🎁 🎀 🪄 ✨ 🌟 ⭐ 💫 🔥 🚀 🥳 🏆 🥇 🥈 🥉 🎖️ 🏅 👑 💎',Business:'💼 📊 📈 📉 🗂️ 📁 📂 📝 📌 📍 📎 🖇️ ✂️ 🔒 🔑 🛒 🛍️ 💳 💰 💵 💸 🧾 🏢 🏬 🏦 🏠 🏡 🏗️',Communication:'☎️ 📞 📱 💻 🖥️ ⌨️ 🖨️ ✉️ 📧 📨 📩 📤 📥 📮 📢 📣 🔔 🔕 💬 🗨️ 🗯️',Food:'🍏 🍎 🍐 🍊 🍋 🍌 🍉 🍇 🍓 🫐 🍈 🍒 🍑 🥭 🍍 🥥 🥝 🍅 🥑 🥦 🥕 🌽 🌶️ 🍞 🥐 🥖 🧀 🍔 🍟 🍕 🌭 🥪 🌮 🍣 🍰 🎂 🍪 ☕ 🧋',Nature:'🌸 🌼 🌻 🌺 🌹 🪻 🌷 🌱 🪴 🌲 🌳 🌴 🌵 🌿 ☘️ 🍀 🍁 🍂 🍃 🌍 🌎 🌏 ☀️ 🌤️ 🌈 🌙 ⭐ ⚡ ❄️ 💧 🌊',Travel:'🚗 🚕 🚌 🚎 🏎️ 🚓 🚑 🚒 🚐 🛻 🚚 🚛 🚜 🛵 🏍️ 🚲 ✈️ 🛫 🛬 🚀 🚁 🚂 🚆 🚇 🚢 ⚓ 🗺️ 🧳 🏖️ 🏕️',Symbols:'✅ ❌ ❗ ❓ ⚠️ ⛔ 🚫 ✔️ ☑️ ➕ ➖ ✖️ ➗ ♾️ 💯 🔴 🟠 🟡 🟢 🔵 🟣 ⚫ ⚪ 🟤 🔺 🔻 🔸 🔹 🔶 🔷 🔳 🔲'};
const emojiNames={heart:'❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 💕 💖',star:'⭐ 🌟 ✨ 💫',fire:'🔥',rocket:'🚀',phone:'☎️ 📞 📱',mail:'✉️ 📧 📨 📩',location:'📍 🗺️',gift:'🎁 🎀',coffee:'☕',food:'🍕 🍔 🍟 🍰',flower:'🌸 🌼 🌻 🌹',leaf:'🌿 🍃 🍀',business:'💼 🏢 📊',truck:'🚚 🚛',check:'✅ ✔️ ☑️',warning:'⚠️ ❗'};
function renderEmoji(q=''){const lib=$('emojiLibrary');if(!lib)return;lib.innerHTML='';let entries=[];if(q.trim()){const match=emojiNames[q.toLowerCase().trim()];const all=Object.entries(groups);entries=match?[['Search results',match]]:all.map(([g,s])=>[g,s]).filter(([g,s])=>g.toLowerCase().includes(q.toLowerCase())||s.includes(q))}else entries=Object.entries(groups);entries.forEach(([g,s])=>{const h=document.createElement('h4');h.textContent=g;lib.appendChild(h);const row=document.createElement('div');row.className='emoji-category';[...new Intl.Segmenter(undefined,{granularity:'grapheme'}).segment(s.replace(/ /g,''))].map(x=>x.segment).filter(Boolean).forEach(e=>{const b=document.createElement('button');b.textContent=e;b.onclick=()=>{const o=new fabric.IText(e,{left:W/2-40,top:H/2-40,fontSize:80,fontFamily:'Arial',name:'Emoji'});o.objectId='o'+Math.random().toString(36).slice(2);canvas.add(o);canvas.setActiveObject(o);fireChange(o)};row.appendChild(b)});lib.appendChild(row)})}
$('emojiSearch')?.addEventListener('input',e=>renderEmoji(e.target.value));renderEmoji();

// Live suggestions from real admin templates for this product.
function renderTemplates(q=''){const host=$('templateSuggestions'),items=window.TEMPLATE_CATALOG||[];if(!host)return;host.innerHTML='';const matches=items.filter(t=>!q||String(t.name||'').toLowerCase().includes(q.toLowerCase()));if(!matches.length){host.innerHTML='<div class="empty-suggestion">No matching templates for this product.</div>';return}matches.forEach(t=>{const a=document.createElement('a');a.href=`/zenvibe/editor/${P.id}/?template=${t.id}`;a.className='template-suggestion-card';a.innerHTML=t.preview_url?`<img src="${t.preview_url}" alt=""><span>${t.name}</span>`:`<div class="template-placeholder">${t.name.slice(0,1)}</div><span>${t.name}</span>`;a.onclick=e=>{e.preventDefault();window.ZENVIBE_REQUEST_TEMPLATE_SWITCH(t.id)};host.appendChild(a)})}
$('templateSearch')?.addEventListener('input',e=>renderTemplates(e.target.value));renderTemplates();
setTimeout(()=>{drawRulers();syncBackgroundUI()},500);
})();

// Shared Arrange dropdown controller for Awards, Business Cards, Invitations and generic editors.
(function installSharedArrangeDropdown(){
  function init(){
    const root=document.getElementById('arrangeDropdown');
    const trigger=document.getElementById('arrangeMenuBtn');
    const menu=document.getElementById('arrangeMenu');
    if(!root||!trigger||!menu||root.dataset.ready==='1')return;
    root.dataset.ready='1';
    const close=()=>{root.classList.remove('open');trigger.setAttribute('aria-expanded','false');};
    const place=()=>{const r=trigger.getBoundingClientRect(),w=menu.offsetWidth||310;menu.style.left=Math.max(12,Math.min(window.innerWidth-w-12,r.right-w))+'px';menu.style.top=(r.bottom+7)+'px';};
    trigger.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();root.classList.toggle('open');trigger.setAttribute('aria-expanded',root.classList.contains('open')?'true':'false');if(root.classList.contains('open'))requestAnimationFrame(place);});
    menu.addEventListener('click',close);
    document.addEventListener('click',e=>{if(!root.contains(e.target))close();});
    window.addEventListener('resize',()=>{if(root.classList.contains('open'))place();});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
