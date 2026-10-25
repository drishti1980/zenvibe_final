(function(){
'use strict';
const canvas=window.designCanvas;if(!canvas)return;const $=id=>document.getElementById(id);const P=window.PRODUCT||{},W=P.width||1050,H=P.height||600;
const uid=()=>`pro-${Math.random().toString(36).slice(2,10)}`;
const fire=o=>{canvas.requestRenderAll();canvas.fire('object:modified',{target:o||canvas.getActiveObject()});};

// Larger Google-font catalogue. Fonts are loaded only when clicked.
const FONT_GROUPS={
 'Popular':['Poppins','Montserrat','Inter','Roboto','Open Sans','Lato','Nunito','DM Sans','Manrope','Raleway','Figtree','Plus Jakarta Sans','Outfit','Urbanist','Work Sans','Source Sans 3','Noto Sans','Rubik','Quicksand','Mulish'],
 'Display':['Anton','Bebas Neue','Oswald','Archivo Black','Alfa Slab One','Black Ops One','Bowlby One SC','Bungee','Changa One','Concert One','Fjalla One','Francois One','Graduate','Kanit','League Spartan','Lilita One','Luckiest Guy','Passion One','Paytone One','Rammetto One','Righteous','Russo One','Staatliches','Teko','Titan One','Ultra'],
 'Serif':['Playfair Display','Merriweather','Lora','Libre Baskerville','Cormorant Garamond','Bitter','Arvo','Bodoni Moda','Cardo','Cinzel','Crimson Text','DM Serif Display','EB Garamond','Fraunces','Libre Bodoni','Noto Serif','Old Standard TT','PT Serif','Prata','Roboto Slab','Spectral','Vollkorn','Zilla Slab'],
 'Handwriting':['Pacifico','Lobster','Dancing Script','Great Vibes','Caveat','Permanent Marker','Amatic SC','Architects Daughter','Bad Script','Berkshire Swash','Courgette','Covered By Your Grace','Gloria Hallelujah','Handlee','Kaushan Script','Marck Script','Merienda','Nanum Pen Script','Parisienne','Patrick Hand','Sacramento','Satisfy','Shadows Into Light','Yellowtail'],
 'Clean':['Arial','Verdana','Trebuchet MS','Georgia','Courier New','Abel','ABeeZee','Arimo','Asap','Assistant','Barlow','Barlow Condensed','Cabin','Karla','Maven Pro','Prompt','Public Sans','Roboto Condensed','Saira','Ubuntu','Varela Round']
};
const ALL_FONTS=[...new Set(Object.values(FONT_GROUPS).flat())];
function loadFont(f){if(['Arial','Verdana','Trebuchet MS','Georgia','Courier New'].includes(f))return;const id='pro-font-'+f.replace(/\W/g,'-');if(document.getElementById(id))return;const l=document.createElement('link');l.id=id;l.rel='stylesheet';l.href='https://fonts.googleapis.com/css2?family='+f.trim().replace(/ /g,'+')+':wght@300;400;500;600;700;800;900&display=swap';document.head.appendChild(l)}
function applyFont(f){loadFont(f);const o=canvas.getActiveObject();if(o&&['i-text','textbox','text'].includes(o.type)){o.set('fontFamily',f);fire(o)}const select=$('fontFamily');if(select)select.value=f}
function setupFontPicker(){const input=$('fontSearch'),list=$('fontSearchOptions');if(!input||!list)return;list.innerHTML='';ALL_FONTS.forEach(f=>list.appendChild(new Option(f,f)));const choose=()=>{const q=input.value.trim().toLowerCase();const exact=ALL_FONTS.find(f=>f.toLowerCase()===q);if(exact)applyFont(exact)};input.addEventListener('change',choose);input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();choose();input.blur()}})}
setupFontPicker();
const ff=$('fontFamily');if(ff){ff.innerHTML='';ALL_FONTS.forEach(f=>ff.add(new Option(f,f)))}
ALL_FONTS.slice(0,18).forEach(loadFont);

// Full-feeling categorized emoji library (hundreds of commonly used Unicode emoji).
const EMOJI_GROUPS={
 'Smileys':'😀 😃 😄 😁 😆 😅 😂 🤣 😊 😇 🙂 🙃 😉 😌 😍 🥰 😘 😗 😙 😚 😋 😛 😝 😜 🤪 🤨 🧐 🤓 😎 🥸 🤩 🥳 😏 😒 😞 😔 😟 😕 🙁 ☹️ 😣 😖 😫 😩 🥺 😢 😭 😤 😠 😡 🤬 🤯 😳 🥵 🥶 😱 😨 😰 😥 😓 🤗 🤔 🫣 🤭 🫢 🫡 🤫 🫠 🤥 😶 🫥 😐 🫤 😑 😬 🙄 😯 😦 😧 😮 😲 🥱 😴 🤤 😪 😵 🤐 🥴 🤢 🤮 🤧 😷 🤒 🤕',
 'People':'👋 🤚 🖐️ ✋ 🖖 🫱 🫲 🫳 🫴 👌 🤌 🤏 ✌️ 🤞 🫰 🤟 🤘 🤙 👈 👉 👆 👇 ☝️ 🫵 👍 👎 ✊ 👊 🤛 🤜 👏 🙌 🫶 👐 🤲 🤝 🙏 ✍️ 💅 🤳 💪 🦾 🦿 🦵 🦶 👂 👃 🧠 🫀 🫁 🦷 👀 👁️ 👅 👄 🫦 👶 🧒 👦 👧 🧑 👱 👨 🧔 👩 🧓 👴 👵 🙍 🙎 🙅 🙆 💁 🙋 🧏 🙇 🤦 🤷 👮 👷 💂 🕵️ 👩‍⚕️ 👩‍🌾 👩‍🍳 👩‍🎓 👩‍🎤 👩‍🏫 👩‍🏭 👩‍💻 👩‍💼 👩‍🔧 👩‍🔬 👩‍🎨 👩‍🚒 👩‍✈️ 👩‍🚀 👩‍⚖️',
 'Animals':'🐶 🐱 🐭 🐹 🐰 🦊 🐻 🐼 🐻‍❄️ 🐨 🐯 🦁 🐮 🐷 🐸 🐵 🙈 🙉 🙊 🐒 🐔 🐧 🐦 🐤 🦆 🦅 🦉 🦇 🐺 🐗 🐴 🦄 🐝 🪱 🐛 🦋 🐌 🐞 🐜 🪰 🪲 🪳 🦟 🦗 🕷️ 🦂 🐢 🐍 🦎 🦖 🦕 🐙 🦑 🦐 🦞 🦀 🐡 🐠 🐟 🐬 🐳 🐋 🦈 🦭 🐊 🐅 🐆 🦓 🦍 🦧 🐘 🦛 🦏 🐪 🐫 🦒 🦬 🐃 🐂 🐄 🐎 🐖 🐏 🐑 🦙 🐐 🦌 🐕 🐩 🦮 🐈 🐓 🦃 🦚 🦜 🦢 🦩 🕊️ 🐇 🦝 🦨 🦡 🦫 🦦 🦥 🐁 🐀 🐿️ 🦔',
 'Food':'🍏 🍎 🍐 🍊 🍋 🍌 🍉 🍇 🍓 🫐 🍈 🍒 🍑 🥭 🍍 🥥 🥝 🍅 🍆 🥑 🥦 🥬 🥒 🌶️ 🫑 🌽 🥕 🫒 🧄 🧅 🥔 🍠 🥐 🥯 🍞 🥖 🥨 🧀 🥚 🍳 🧈 🥞 🧇 🥓 🥩 🍗 🍖 🌭 🍔 🍟 🍕 🫓 🥪 🥙 🧆 🌮 🌯 🫔 🥗 🥘 🫕 🥫 🍝 🍜 🍲 🍛 🍣 🍱 🥟 🦪 🍤 🍙 🍚 🍘 🍥 🥠 🥮 🍢 🍡 🍧 🍨 🍦 🥧 🧁 🍰 🎂 🍮 🍭 🍬 🍫 🍿 🍩 🍪 🌰 🥜 🍯 🥛 ☕ 🫖 🍵 🧃 🥤 🧋 🍶 🍺 🍻 🥂 🍷 🍸 🍹',
 'Objects':'⌚ 📱 💻 ⌨️ 🖥️ 🖨️ 🖱️ 🕹️ 🗜️ 💽 💾 💿 📀 📷 📸 📹 🎥 📞 ☎️ 📟 📠 📺 📻 🎙️ 🎚️ 🎛️ 🧭 ⏱️ ⏲️ ⏰ 🕰️ ⌛ ⏳ 📡 🔋 🪫 🔌 💡 🔦 🕯️ 🧯 🛢️ 💸 💵 💴 💶 💷 🪙 💳 🧾 💎 ⚖️ 🪜 🧰 🪛 🔧 🔨 ⚒️ 🛠️ ⛏️ 🪚 🔩 ⚙️ 🧱 ⛓️ 🧲 🔫 💣 🧨 🪓 🔪 🗡️ 🛡️ 🚬 ⚰️ 🪦 ⚱️ 🏺 🔮 📿 🧿 🪬 💈 ⚗️ 🔭 🔬 🕳️ 🩹 🩺 💊 💉 🩸 🧬 🦠 🧫 🧪 🌡️ 🧹 🪠 🧺 🧻 🚽 🚿 🛁 🪥 🧼 🫧 🪒 🧽 🪣 🧴 🔑 🗝️ 🚪 🪑 🛋️ 🛏️ 🧸 🪆 🖼️ 🪞 🪟 🛍️ 🛒 🎁 🎈 🎏 🎀 🪄 🪅 🎊 🎉',
 'Symbols':'❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 ❤️‍🔥 ❤️‍🩹 ❣️ 💕 💞 💓 💗 💖 💘 💝 💟 ☮️ ✝️ ☪️ 🕉️ ☸️ ✡️ 🔯 🕎 ☯️ ☦️ 🛐 ⛎ ♈ ♉ ♊ ♋ ♌ ♍ ♎ ♏ ♐ ♑ ♒ ♓ 🆔 ⚛️ 🉑 ☢️ ☣️ 📴 📳 🈶 🈚 🈸 🈺 🈷️ ✴️ 🆚 💮 🉐 ㊙️ ㊗️ 🈴 🈵 🈹 🈲 🅰️ 🅱️ 🆎 🆑 🅾️ 🆘 ❌ ⭕ 🛑 ⛔ 📛 🚫 💯 💢 ♨️ 🚷 🚯 🚳 🚱 🔞 📵 🚭 ❗ ❕ ❓ ❔ ‼️ ⁉️ 🔅 🔆 〽️ ⚠️ 🚸 🔱 ⚜️ 🔰 ♻️ ✅ 🈯 💹 ❇️ ✳️ ❎ 🌐 💠 Ⓜ️ 🌀 💤 🏧 🚾 ♿ 🅿️ 🛗 🈳 🈂️ 🛂 🛃 🛄 🛅 🚹 🚺 🚼 ⚧️ 🚻 🚮 🎦 📶 🈁 🔣 ℹ️ 🔤 🔡 🔠 🆖 🆗 🆙 🆒 🆕 🆓 0️⃣ 1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣ 8️⃣ 9️⃣ 🔟'
};
function renderEmoji(q=''){const host=$('emojiLibrary');if(!host)return;host.innerHTML='';Object.entries(EMOJI_GROUPS).forEach(([name,line])=>{const arr=line.split(' ').filter(Boolean).filter(e=>(name+' '+e).toLowerCase().includes(q.toLowerCase()));if(!arr.length)return;const h=document.createElement('h4');h.textContent=name;host.appendChild(h);const g=document.createElement('div');g.className='emoji-category';arr.forEach(e=>{const b=document.createElement('button');b.textContent=e;b.onclick=()=>{const o=new fabric.IText(e,{left:W/2-35,top:H/2-35,fontSize:72,fontFamily:'Arial',name:'Emoji',objectId:uid()});canvas.add(o);canvas.setActiveObject(o);fire(o)};g.appendChild(b)});host.appendChild(g)})}
const es=$('emojiSearch');if(es){es.oninput=e=>renderEmoji(e.target.value);renderEmoji()}

// Searchable vector icons made from Unicode glyphs; they stay editable like text and need no external API.
const ICONS={Business:'☎ ✉ ⌂ ⌖ ⚙ ⚒ ⚖ ★ ✓ ✔ ✦ ✧ ◆ ◇ ● ○ ■ □ ▲ △ ▶ ◀ ↑ ↓ ↔ ↕ ➜ ➤ ➔ ➝ ➞ ➟ ➠ ➡ ⬅ ⬆ ⬇',Social:'f in X ▶ ◎ ◉ ♬ ♫ ☁ ☎ ✉ ☺ ♥ ★',Commerce:'🛒 🛍️ 💳 💰 💵 💸 🧾 🏷️ 🎁 📦 🚚 🏪 🏬 🏢 🏭',Contact:'📞 ☎️ 📱 ✉️ 📧 📍 🗺️ 🌐 🔗 🔔 🕒 📅',Creative:'✎ ✏ ✒ 🖌️ 🖍️ 🎨 📷 🎥 🎬 🎵 🎧 🎤 🎹 🎸',Interface:'⌕ ☰ ⋮ ⋯ + − × ✓ ← → ↑ ↓ ↶ ↷ ⤢ ⤡ ⛶ 🔒 🔓 👁 ⚙ 🗑️ 📋 ⧉'};
function addGlyph(g){const o=new fabric.IText(g,{left:W/2-40,top:H/2-40,fontSize:76,fontFamily:'Arial',fill:'#17233c',name:'Icon',objectId:uid()});canvas.add(o);canvas.setActiveObject(o);fire(o)}
function renderIcons(q=''){const host=$('iconLibrary');if(!host)return;host.innerHTML='';Object.entries(ICONS).forEach(([cat,line])=>line.split(' ').filter(Boolean).filter(x=>(cat+' '+x).toLowerCase().includes(q.toLowerCase())).forEach(g=>{const b=document.createElement('button');b.innerHTML=`<span>${g}</span><small>${cat}</small>`;b.onclick=()=>addGlyph(g);host.appendChild(b)}))}
const is=$('iconSearch');if(is){is.oninput=e=>renderIcons(e.target.value);renderIcons()}

// Working stock-image and background library.
const STATIC_BASE=(window.ZENVIBE_STATIC_URL||'/static/').replace(/\/?$/,'/');
const stockSrc=name=>STATIC_BASE+'designer/img/stock/'+name;
const STOCK_PHOTOS=[
 {name:'Ocean light',tags:'blue modern corporate abstract',src:stockSrc('ocean.jpg')},
 {name:'Sunset glow',tags:'orange warm creative bright',src:stockSrc('sunset.jpg')},
 {name:'Forest calm',tags:'green nature organic wellness',src:stockSrc('forest.jpg')},
 {name:'Royal violet',tags:'purple luxury premium elegant',src:stockSrc('royal.jpg')},
 {name:'Midnight',tags:'dark navy technology professional',src:stockSrc('midnight.jpg')},
 {name:'Candy',tags:'pink purple beauty fashion vibrant',src:stockSrc('candy.jpg')},
 {name:'Ice blue',tags:'pale blue clean medical minimal',src:stockSrc('ice.jpg')},
 {name:'Warm paper',tags:'cream beige paper wedding neutral',src:stockSrc('paper.jpg')},
 {name:'Rose bloom',tags:'rose pink floral romantic',src:stockSrc('rose.jpg')},
 {name:'Fresh mint',tags:'mint green fresh health',src:stockSrc('mint.jpg')},
 {name:'Lavender',tags:'lavender soft beauty spa',src:stockSrc('lavender.jpg')},
 {name:'Golden hour',tags:'gold yellow premium celebration',src:stockSrc('gold.jpg')}
];
const GENERATED_BACKGROUNDS=[
 {name:'Ocean gradient',tags:'blue gradient modern',type:'gradient',colors:['#0ea5e9','#4f46e5']},
 {name:'Sunset gradient',tags:'orange pink gradient',type:'gradient',colors:['#fb7185','#f59e0b']},
 {name:'Forest gradient',tags:'green gradient nature',type:'gradient',colors:['#14532d','#22c55e']},
 {name:'Royal gradient',tags:'purple gradient luxury',type:'gradient',colors:['#312e81','#7c3aed']},
 {name:'Soft dots',tags:'dots pattern subtle',type:'dots',colors:['#ffffff','#cbd5e1']},
 {name:'Fine grid',tags:'grid pattern alignment',type:'grid',colors:['#ffffff','#dbe3ef']},
 {name:'Diagonal paper',tags:'diagonal stripe pattern',type:'stripes',colors:['#f8fafc','#e2e8f0']},
 {name:'Dark lines',tags:'dark stripe pattern',type:'stripes',colors:['#17233c','#263653']}
];
function removeGeneratedBackgrounds(){
 canvas.getObjects().slice().forEach(o=>{if(o.backgroundAsset&&o.generatedByEditor)canvas.remove(o)});
}
function fullPageRectCandidate(){
 return canvas.getObjects().find(o=>{
  if(o.type!=='rect')return false;
  const w=o.getScaledWidth?.()||0,h=o.getScaledHeight?.()||0;
  return Math.abs(o.left||0)<8&&Math.abs(o.top||0)<8&&w>=W*.94&&h>=H*.94&&(o.backgroundAsset||o.lockMovementX||o.selectable===false);
 });
}
function hexRgb(hex){const m=String(hex||'').trim().match(/^#?([0-9a-f]{6})$/i);return m?{r:parseInt(m[1].slice(0,2),16),g:parseInt(m[1].slice(2,4),16),b:parseInt(m[1].slice(4,6),16)}:null}
function median(a){if(!a.length)return 255;a.sort((x,y)=>x-y);return a[Math.floor(a.length/2)]}
function recolorFlatArtworkPaper(img,color){
 return new Promise(resolve=>{
  try{
   const el=img.getElement(),w=el.naturalWidth||el.width||img.width,h=el.naturalHeight||el.height||img.height;if(!w||!h){resolve(false);return}
   const off=document.createElement('canvas');off.width=w;off.height=h;const ctx=off.getContext('2d',{willReadFrequently:true});ctx.drawImage(el,0,0,w,h);
   const data=ctx.getImageData(0,0,w,h),px=data.data,rs=[],gs=[],bs=[],step=Math.max(1,Math.floor(Math.min(w,h)/180));
   // Estimate the paper/background colour from the image border instead of assuming pure white.
   for(let y=0;y<h;y+=step)for(let x=0;x<w;x+=step){if(x>w*.12&&x<w*.88&&y>h*.12&&y<h*.88)continue;const i=(y*w+x)*4;if(px[i+3]<180)continue;rs.push(px[i]);gs.push(px[i+1]);bs.push(px[i+2])}
   const base={r:median(rs),g:median(gs),b:median(bs)},target=hexRgb(color);if(!target){resolve(false);return}
   const threshold=72;
   for(let i=0;i<px.length;i+=4){if(px[i+3]<10)continue;const dr=px[i]-base.r,dg=px[i+1]-base.g,db=px[i+2]-base.b,dist=Math.sqrt(dr*dr+dg*dg+db*db);if(dist>threshold)continue;const strength=Math.max(0,1-dist/threshold);px[i]=Math.round(px[i]*(1-strength)+target.r*strength);px[i+1]=Math.round(px[i+1]*(1-strength)+target.g*strength);px[i+2]=Math.round(px[i+2]*(1-strength)+target.b*strength)}
   ctx.putImageData(data,0,0);const src=off.toDataURL('image/png');
   fabric.Image.fromURL(src,n=>{
    ['objectId','name','fieldType','backgroundAsset','generatedByEditor','customerEditable','flipX','flipY','visible','opacity'].forEach(k=>{if(img[k]!==undefined)n[k]=img[k]});
    n.set({left:img.left,top:img.top,scaleX:img.scaleX,scaleY:img.scaleY,angle:img.angle||0,originX:img.originX||'left',originY:img.originY||'top',cropX:img.cropX||0,cropY:img.cropY||0,selectable:true,evented:true,lockMovementX:false,lockMovementY:false,lockScalingX:false,lockScalingY:false,lockRotation:false,hasControls:true});n.filters=img.filters||[];if(n.filters.length)n.applyFilters();
    canvas.remove(img);canvas.add(n);canvas.sendToBack(n);canvas.requestRenderAll();resolve(true);
   });
  }catch(e){resolve(false)}
 });
}
async function setPageColor(color){
 removeGeneratedBackgrounds();
 canvas.setBackgroundColor(color,canvas.requestRenderAll.bind(canvas));
 const rect=fullPageRectCandidate();if(rect){rect.set({fill:color});rect.setCoords()}
 // Flat PNG/JPG templates often contain an opaque white/cream paper background.
 // Recolour only pixels close to the dominant border colour so flowers, logos and dark text remain intact.
 const artwork=canvas.getObjects().find(o=>o.type==='image'&&o.backgroundAsset&&!o.generatedByEditor);
 if(artwork)await recolorFlatArtworkPaper(artwork,color);
 const picker=$('backgroundColor');if(picker)picker.value=color;
 if(typeof snapshot==='function')snapshot();
}
window.zenvibeSetPageColor=setPageColor;
function makeGeneratedBackground(def){
 const c=document.createElement('canvas');c.width=W;c.height=H;const x=c.getContext('2d');
 if(def.type==='gradient'){
  const g=x.createLinearGradient(0,0,W,H);g.addColorStop(0,def.colors[0]);g.addColorStop(1,def.colors[1]);x.fillStyle=g;x.fillRect(0,0,W,H);
 }else{
  x.fillStyle=def.colors[0];x.fillRect(0,0,W,H);x.strokeStyle=def.colors[1];x.fillStyle=def.colors[1];
  if(def.type==='dots'){for(let yy=12;yy<H;yy+=24)for(let xx=12;xx<W;xx+=24){x.beginPath();x.arc(xx,yy,2,0,Math.PI*2);x.fill()}}
  if(def.type==='grid'){x.lineWidth=1;for(let xx=0;xx<W;xx+=28){x.beginPath();x.moveTo(xx,0);x.lineTo(xx,H);x.stroke()}for(let yy=0;yy<H;yy+=28){x.beginPath();x.moveTo(0,yy);x.lineTo(W,yy);x.stroke()}}
  if(def.type==='stripes'){x.lineWidth=18;for(let xx=-H;xx<W+H;xx+=44){x.beginPath();x.moveTo(xx,0);x.lineTo(xx-H,H);x.stroke()}}
 }
 return c.toDataURL('image/png');
}
function placeImage(src,asBackground=false,name='Photo'){
 fabric.Image.fromURL(src,img=>{
  if(!img){alert('This photo could not be loaded.');return}
  if(asBackground){
   removeGeneratedBackgrounds();
   const scale=Math.max(W/img.width,H/img.height);
   img.set({left:(W-img.width*scale)/2,top:(H-img.height*scale)/2,scaleX:scale,scaleY:scale,selectable:true,evented:true,backgroundAsset:true,generatedByEditor:true,customerEditable:true,lockMovementX:false,lockMovementY:false,lockScalingX:false,lockScalingY:false,lockRotation:false,hasControls:true,name:'Page photo background',objectId:uid()});
   canvas.add(img);canvas.sendToBack(img);
  }else{
   const maxW=W*.55,maxH=H*.55,scale=Math.min(maxW/img.width,maxH/img.height,1);
   img.set({left:(W-img.width*scale)/2,top:(H-img.height*scale)/2,scaleX:scale,scaleY:scale,name,objectId:uid(),customerEditable:true});
   canvas.add(img);canvas.setActiveObject(img);
  }
  canvas.requestRenderAll();if(typeof snapshot==='function')snapshot();
 },{crossOrigin:'anonymous'});
}
function renderPhotos(q=''){
 const host=$('photoLibrary');if(!host)return;host.innerHTML='';
 const term=q.trim().toLowerCase();
 STOCK_PHOTOS.filter(p=>(p.name+' '+p.tags).toLowerCase().includes(term)).forEach(photo=>{
  const card=document.createElement('article');card.className='photo-card';
  card.innerHTML=`<img src="${photo.src}" alt="${photo.name}" loading="lazy"><strong>${photo.name}</strong><div><button type="button" data-action="add">Add photo</button><button type="button" data-action="background">Use as background</button></div>`;
  card.querySelector('[data-action="add"]').onclick=()=>placeImage(photo.src,false,photo.name);
  card.querySelector('[data-action="background"]').onclick=()=>placeImage(photo.src,true,photo.name);
  host.appendChild(card);
 });
 const title=document.createElement('h4');title.className='photo-section-title';title.textContent='Generated backgrounds';host.appendChild(title);
 GENERATED_BACKGROUNDS.filter(p=>(p.name+' '+p.tags).toLowerCase().includes(term)).forEach(def=>{
  const data=makeGeneratedBackground(def);const card=document.createElement('article');card.className='photo-card compact';
  card.innerHTML=`<img src="${data}" alt="${def.name}"><strong>${def.name}</strong><div><button type="button">Apply background</button></div>`;
  card.querySelector('button').onclick=()=>placeImage(data,true,def.name);host.appendChild(card);
 });
 if(!host.children.length)host.innerHTML='<p class="panel-help">No photos matched your search.</p>';
}
const ps=$('photoSearch');if(ps){ps.placeholder='Search photos, gradients and patterns';ps.oninput=e=>renderPhotos(e.target.value);renderPhotos()}
// Route the original background controls through the reliable page-background implementation.
$('applyBackgroundBtn')?.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();setPageColor($('backgroundColor')?.value||'#ffffff')},true);
document.querySelectorAll('#backgroundSwatches button').forEach(b=>{b.onclick=()=>setPageColor(b.title||getComputedStyle(b).backgroundColor)});
// QR and barcode tools.
function addDataImage(data,name,width=220){fabric.Image.fromURL(data,img=>{img.scaleToWidth(width);img.set({left:W/2-width/2,top:H/2-width/2,name,objectId:uid()});canvas.add(img);canvas.setActiveObject(img);fire(img)})}
$('addQrBtn')?.addEventListener('click',()=>{const box=document.createElement('div');new QRCode(box,{text:$('qrValue').value||'https://zenvibe.ca',width:512,height:512,correctLevel:QRCode.CorrectLevel.H});setTimeout(()=>{const img=box.querySelector('img'),c=box.querySelector('canvas');addDataImage(img?.src||c?.toDataURL(),'QR code',180)},80)});
$('addBarcodeBtn')?.addEventListener('click',()=>{const c=document.createElement('canvas');try{JsBarcode(c,$('barcodeValue').value||'123456789012',{format:'CODE128',displayValue:true,fontSize:24,height:100,margin:12});addDataImage(c.toDataURL(),'Barcode',280)}catch(e){alert('Please enter a valid barcode value.')}});

// Better measurement and direct position panel.
function syncPosition(){const o=canvas.getActiveObject();if(!o)return;const r=o.getBoundingRect(true,true);[['positionX',o.left],['positionY',o.top],['positionW',r.width],['positionH',r.height]].forEach(([id,v])=>{if($(id))$(id).value=Math.round(v||0)})}
canvas.on('selection:created',syncPosition);canvas.on('selection:updated',syncPosition);canvas.on('object:moving',syncPosition);canvas.on('object:scaling',syncPosition);
$('applyPositionBtn')?.addEventListener('click',()=>{const o=canvas.getActiveObject();if(!o)return;const targetW=Math.max(1,Number($('positionW').value)||o.getScaledWidth()),targetH=Math.max(1,Number($('positionH').value)||o.getScaledHeight());o.set({left:Number($('positionX').value)||0,top:Number($('positionY').value)||0,scaleX:targetW/o.width,scaleY:targetH/o.height});o.setCoords();fire(o)});

// Ruler visibility and draggable guide lines.
let rulersVisible=true;const guideEls=[];
function toggleRulers(){rulersVisible=!rulersVisible;document.querySelector('.canvas-stage')?.classList.toggle('rulers-hidden',!rulersVisible)}
$('toggleRulersBtn')?.addEventListener('click',toggleRulers);$('viewMenuBtn')?.addEventListener('click',toggleRulers);
$('clearGuidesBtn')?.addEventListener('click',()=>{guideEls.splice(0).forEach(e=>e.remove())});
function makeGuide(axis,pos){const g=document.createElement('div');g.className='manual-guide '+axis;g.style[axis==='vertical'?'left':'top']=pos+'px';document.querySelector('.canvas-stage')?.appendChild(g);guideEls.push(g);let start=0;g.onpointerdown=e=>{g.setPointerCapture(e.pointerId);start=axis==='vertical'?e.clientX:e.clientY};g.onpointermove=e=>{if(!g.hasPointerCapture(e.pointerId))return;const now=axis==='vertical'?e.clientX:e.clientY;const key=axis==='vertical'?'left':'top';g.style[key]=(parseFloat(g.style[key])+now-start)+'px';start=now};return g}
$('horizontalRuler')?.addEventListener('dblclick',e=>makeGuide('horizontal',e.offsetY+59));$('verticalRuler')?.addEventListener('dblclick',e=>makeGuide('vertical',e.offsetX+60));

// Improve initial visual scale. The 100% label represents fit; raise it on large desktop screens.
// setTimeout(()=>{const range=$('bottomZoomRange');if(range&&window.innerWidth>1250){range.value='128';range.dispatchEvent(new Event('input',{bubbles:true}))}},450);

// Menu affordances.
$('fileMenuBtn')?.addEventListener('click',()=>$('saveDraftBtn')?.click());
$('resizeMenuBtn')?.addEventListener('click',()=>alert(`Current print canvas: ${W} × ${H} px. Product dimensions are controlled by the administrator to protect print accuracy.`));
})();
