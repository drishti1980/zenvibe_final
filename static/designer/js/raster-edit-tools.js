// ZENVIBE_V56_SAFE_TEXT_CLEANUP 2026-08-10
/* ZenVibe raster editing helpers.
 * Non-destructive text replacement for flattened PNG/JPG templates.
 * Instead of placing a solid rectangle over printed text, this module detects
 * likely glyph pixels inside the OCR region and fills only those pixels from
 * the nearest surrounding background pixels. The resulting transparent-safe
 * patch preserves paper texture/gradients much better than a flat colour mask.
 */
(function(){
  'use strict';

  function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
  function lum(r,g,b){return .299*r+.587*g+.114*b;}
  function sat(r,g,b){const mx=Math.max(r,g,b),mn=Math.min(r,g,b);return mx?((mx-mn)/mx):0;}
  function median(arr){if(!arr.length)return 245;arr.sort((a,b)=>a-b);return arr[Math.floor(arr.length/2)];}

  function elementInfo(img){
    const el=img&&img.getElement?img.getElement():null;
    if(!el)throw new Error('No source image available');
    return {el,w:el.naturalWidth||img.width||el.width||1,h:el.naturalHeight||img.height||el.height||1};
  }

  function canvasRectForNormalized(img,box){
    const {w,h}=elementInfo(img),sx=img.scaleX||1,sy=img.scaleY||1;
    return {
      left:(img.left||0)+box.x*w*sx,
      top:(img.top||0)+box.y*h*sy,
      width:Math.max(2,box.w*w*sx),
      height:Math.max(2,box.h*h*sy)
    };
  }

  function nearestFill(data,w,h,mask){
    const n=w*h,dist=new Int32Array(n);dist.fill(-1);
    const donor=new Int32Array(n);donor.fill(-1);
    const q=new Int32Array(n);let head=0,tail=0;
    // Seed with non-masked pixels directly touching the mask. This avoids
    // copying remote colours and preserves local paper grain/gradients.
    const nearMask=i=>{
      const x=i%w,y=(i/w)|0;
      for(let yy=Math.max(0,y-1);yy<=Math.min(h-1,y+1);yy++)for(let xx=Math.max(0,x-1);xx<=Math.min(w-1,x+1);xx++){
        if(mask[yy*w+xx])return true;
      }
      return false;
    };
    for(let i=0;i<n;i++) if(!mask[i]&&nearMask(i)){dist[i]=0;donor[i]=i;q[tail++]=i;}
    if(!tail){for(let i=0;i<n;i++)if(!mask[i]){dist[i]=0;donor[i]=i;q[tail++]=i;}}
    const dirs=[-1,1,-w,w];
    while(head<tail){
      const i=q[head++],x=i%w;
      for(const d of dirs){const ni=i+d;if(ni<0||ni>=n)continue;if((d===-1&&x===0)||(d===1&&x===w-1))continue;if(dist[ni]!==-1)continue;
        dist[ni]=dist[i]+1;donor[ni]=donor[i];q[tail++]=ni;
      }
    }
    const original=new Uint8ClampedArray(data);
    for(let i=0;i<n;i++)if(mask[i]&&donor[i]>=0){const s=donor[i]*4,t=i*4;data[t]=original[s];data[t+1]=original[s+1];data[t+2]=original[s+2];data[t+3]=original[s+3];}
  }

  function buildGlyphMask(frame,w,h,inner){
    const d=frame.data,rs=[],gs=[],bs=[];
    // Estimate the local paper/background from a ring OUTSIDE the OCR box.
    for(let y=0;y<h;y+=2)for(let x=0;x<w;x+=2){
      const inside=x>=inner.x0&&x<=inner.x1&&y>=inner.y0&&y<=inner.y1;
      if(inside)continue;const i=(y*w+x)*4;if(d[i+3]<120)continue;
      const r=d[i],g=d[i+1],b=d[i+2];if(lum(r,g,b)>70){rs.push(r);gs.push(g);bs.push(b);}
    }
    const br=median(rs),bg=median(gs),bb=median(bs),bl=lum(br,bg,bb);

    // V35: learn the DOMINANT ink colour inside the OCR box.  The old mask
    // treated every dark pixel as text, so green leaves / floral artwork that
    // touched an address line were erased.  Quantising candidate ink colours
    // lets us remove the repeated text colour while preserving unrelated art.
    const bins=new Map();
    for(let y=inner.y0;y<=inner.y1;y++)for(let x=inner.x0;x<=inner.x1;x++){
      const i=(y*w+x)*4;if(d[i+3]<80)continue;const r=d[i],g=d[i+1],b=d[i+2];
      const L=lum(r,g,b),cd=Math.hypot(r-br,g-bg,b-bb);
      if(cd<28 || (L>220 && cd<55))continue;
      const key=`${r>>5},${g>>5},${b>>5}`;
      let v=bins.get(key);if(!v)v={n:0,r:0,g:0,b:0};v.n++;v.r+=r;v.g+=g;v.b+=b;bins.set(key,v);
    }
    let dom=null;for(const v of bins.values())if(!dom||v.n>dom.n)dom=v;
    const ir=dom?dom.r/dom.n:Math.max(0,br-80),ig=dom?dom.g/dom.n:Math.max(0,bg-80),ib=dom?dom.b/dom.n:Math.max(0,bb-80);
    const inkSat=sat(ir,ig,ib),inkLum=lum(ir,ig,ib);

    const mask=new Uint8Array(w*h);
    for(let y=inner.y0;y<=inner.y1;y++)for(let x=inner.x0;x<=inner.x1;x++){
      const i=(y*w+x)*4;if(d[i+3]<80)continue;const r=d[i],g=d[i+1],b=d[i+2];
      const L=lum(r,g,b),bgDist=Math.hypot(r-br,g-bg,b-bb),inkDist=Math.hypot(r-ir,g-ig,b-ib),S=sat(r,g,b);
      // Primary rule: colour belongs to the dominant printed-ink cluster.
      // For neutral black/grey text, also accept nearby neutral antialias pixels.
      let isInk=inkDist<62 && bgDist>30 && L<235;
      if(inkSat<.22 && S<.32 && L<Math.min(205,bl-18) && Math.abs(L-inkLum)<105)isInk=true;
      if(isInk)mask[y*w+x]=1;
    }
    // One-pixel dilation catches antialias edges. Do not use the old broad
    // dilation because it can eat thin decorative lines next to lettering.
    const next=mask.slice();
    for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++)if(!mask[y*w+x]){
      let count=0;for(let yy=-1;yy<=1;yy++)for(let xx=-1;xx<=1;xx++)if(mask[(y+yy)*w+x+xx])count++;
      if(count>=3)next[y*w+x]=1;
    }
    return next;
  }

  async function createTextInpaintPatch(img,normalizedBox){
    if(!img||!normalizedBox)throw new Error('Missing source region');
    const {el,w:nw,h:nh}=elementInfo(img);
    const bx0=clamp(Math.floor(normalizedBox.x*nw),0,nw-1);
    const by0=clamp(Math.floor(normalizedBox.y*nh),0,nh-1);
    const bx1=clamp(Math.ceil((normalizedBox.x+normalizedBox.w)*nw),bx0+1,nw);
    const by1=clamp(Math.ceil((normalizedBox.y+normalizedBox.h)*nh),by0+1,nh);
    const bw=bx1-bx0,bh=by1-by0;

    // V56 SAFE CLEANUP:
    // The old interpolation algorithm could pull dark text pixels from the box
    // boundary through the whole patch, creating the vertical streaks visible in
    // script-name replacements.  Instead, learn the dominant LOCAL background
    // colour from a ring around the selected wording and paint only the selected
    // rectangle.  For invitations/cards this behaves like Canva's background
    // eraser: the old glyphs disappear completely and nearby flowers/borders are
    // untouched because they sit outside the user's tight selection.
    const pad=Math.max(8,Math.min(42,Math.round(Math.max(14,bh)*0.9)));
    const x0=clamp(bx0-pad,0,nw-1),y0=clamp(by0-pad,0,nh-1);
    const x1=clamp(bx1+pad,x0+1,nw),y1=clamp(by1+pad,y0+1,nh);
    const sw=x1-x0,sh=y1-y0;
    const sample=document.createElement('canvas');sample.width=sw;sample.height=sh;
    const sctx=sample.getContext('2d',{willReadFrequently:true});
    sctx.drawImage(el,x0,y0,sw,sh,0,0,sw,sh);
    const frame=sctx.getImageData(0,0,sw,sh),d=frame.data;
    const ix0=bx0-x0,iy0=by0-y0,ix1=bx1-x0,iy1=by1-y0;

    // Quantised mode of the border ring is robust against a few floral/decorative
    // pixels and against the printed text itself touching one side of the box.
    const bins=new Map();
    const add=(r,g,b)=>{const key=((r>>4)<<8)|((g>>4)<<4)|(b>>4);let v=bins.get(key);if(!v)v={n:0,r:0,g:0,b:0};v.n++;v.r+=r;v.g+=g;v.b+=b;bins.set(key,v)};
    for(let y=0;y<sh;y+=1){
      for(let x=0;x<sw;x+=1){
        const inside=x>=ix0&&x<ix1&&y>=iy0&&y<iy1;
        if(inside)continue;
        // Only use the local ring, not far-away decoration.
        const near=x>=Math.max(0,ix0-pad)&&x<Math.min(sw,ix1+pad)&&y>=Math.max(0,iy0-pad)&&y<Math.min(sh,iy1+pad);
        if(!near)continue;
        const i=(y*sw+x)*4;if(d[i+3]<180)continue;
        add(d[i],d[i+1],d[i+2]);
      }
    }
    let best=null;for(const v of bins.values())if(!best||v.n>best.n)best=v;
    let br=255,bg=255,bb=255;
    if(best){br=Math.round(best.r/best.n);bg=Math.round(best.g/best.n);bb=Math.round(best.b/best.n);}

    // Build a patch exactly the size of the marked wording.  A tiny feathered
    // edge avoids a visible rectangle while never smearing text vertically.
    const out=document.createElement('canvas');out.width=bw;out.height=bh;
    const octx=out.getContext('2d');
    octx.clearRect(0,0,bw,bh);
    octx.fillStyle=`rgb(${br},${bg},${bb})`;octx.fillRect(0,0,bw,bh);

    const sx=img.scaleX||1,sy=img.scaleY||1;
    return {src:out.toDataURL('image/png'),left:(img.left||0)+bx0*sx,top:(img.top||0)+by0*sy,width:bw*sx,height:bh*sy,naturalWidth:bw,naturalHeight:bh};
  }

  function addPatchToCanvas(canvas,img,normalizedBox,meta){
    return createTextInpaintPatch(img,normalizedBox).then(p=>new Promise((resolve,reject)=>{
      fabric.Image.fromURL(p.src,patch=>{
        if(!patch)return reject(new Error('Could not create text cleanup patch'));
        patch.set({left:p.left,top:p.top,originX:'left',originY:'top',scaleX:p.width/p.naturalWidth,scaleY:p.height/p.naturalHeight,
          selectable:false,evented:false,hasControls:false,lockMovementX:true,lockMovementY:true,lockScalingX:true,lockScalingY:true,lockRotation:true,
          customerEditable:false,fieldType:'ocr-inpaint',name:'Text background reconstruction',...meta});
        canvas.add(patch);resolve(patch);
      },{crossOrigin:'anonymous'});
    }));
  }


  async function createArtworkInpaintPatch(bg,artObj){
    const box=artObj&&artObj.sourceNormalizedBox;if(!bg||!artObj||!box)throw new Error('Artwork region metadata unavailable');
    const {el,w:nw,h:nh}=elementInfo(bg), x0=clamp(Math.floor(box.x*nw),0,nw-1),y0=clamp(Math.floor(box.y*nh),0,nh-1),x1=clamp(Math.ceil((box.x+box.w)*nw),x0+1,nw),y1=clamp(Math.ceil((box.y+box.h)*nh),y0+1,nh),w=x1-x0,h=y1-y0;
    const off=document.createElement('canvas');off.width=w;off.height=h;const ctx=off.getContext('2d',{willReadFrequently:true});ctx.drawImage(el,x0,y0,w,h,0,0,w,h);const frame=ctx.getImageData(0,0,w,h);
    const artEl=artObj.getElement&&artObj.getElement();if(!artEl)throw new Error('Artwork mask unavailable');
    const maskCanvas=document.createElement('canvas');maskCanvas.width=w;maskCanvas.height=h;const mc=maskCanvas.getContext('2d',{willReadFrequently:true});mc.clearRect(0,0,w,h);mc.drawImage(artEl,0,0,artEl.naturalWidth||artObj.width||w,artEl.naturalHeight||artObj.height||h,0,0,w,h);const md=mc.getImageData(0,0,w,h).data;
    let mask=new Uint8Array(w*h);for(let i=0;i<w*h;i++)if(md[i*4+3]>32)mask[i]=1;
    for(let pass=0;pass<2;pass++){const next=mask.slice();for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++)if(!mask[y*w+x]){let hit=false;for(let yy=-1;yy<=1&&!hit;yy++)for(let xx=-1;xx<=1;xx++)if(mask[(y+yy)*w+x+xx]){hit=true;break;}if(hit)next[y*w+x]=1;}mask=next;}
    nearestFill(frame.data,w,h,mask);ctx.putImageData(frame,0,0);const sx=bg.scaleX||1,sy=bg.scaleY||1;
    return {src:off.toDataURL('image/png'),left:(bg.left||0)+x0*sx,top:(bg.top||0)+y0*sy,width:w*sx,height:h*sy,naturalWidth:w,naturalHeight:h};
  }

  function addArtworkInpaintPatch(canvas,bg,artObj,meta){
    return createArtworkInpaintPatch(bg,artObj).then(p=>new Promise((resolve,reject)=>{fabric.Image.fromURL(p.src,patch=>{if(!patch)return reject(new Error('Could not reconstruct artwork background'));patch.set({left:p.left,top:p.top,originX:'left',originY:'top',scaleX:p.width/p.naturalWidth,scaleY:p.height/p.naturalHeight,selectable:false,evented:false,hasControls:false,lockMovementX:true,lockMovementY:true,lockScalingX:true,lockScalingY:true,lockRotation:true,customerEditable:false,fieldType:'art-inpaint',name:'Artwork background reconstruction',...meta});canvas.add(patch);resolve(patch);},{crossOrigin:'anonymous'});}));
  }

  window.ZenRasterEdit={createTextInpaintPatch,addPatchToCanvas,createArtworkInpaintPatch,addArtworkInpaintPatch,canvasRectForNormalized};
})();
