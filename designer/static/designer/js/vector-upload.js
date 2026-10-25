/* ZenVibe customer artwork vectorisation.
   Product/UI mockup images are deliberately excluded: this helper is called only
   from customer file-upload controls. */
(function(){
  function csrf(){
    const m=document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);return m?decodeURIComponent(m[1]):'';
  }
  async function toSvg(file){
    const fd=new FormData();fd.append('file',file);
    const r=await fetch('/zenvibe/api/vectorize-upload/',{method:'POST',headers:{'X-CSRFToken':csrf()},body:fd});
    let d={};try{d=await r.json()}catch(_e){}
    if(!r.ok||!d.ok)throw new Error(d.error||'Unable to convert artwork to editable SVG.');
    return d.svg;
  }
  function loadFabric(svg, canvas, opts){
    opts=opts||{};
    return new Promise((resolve,reject)=>{
      if(!window.fabric||!canvas)return reject(new Error('Designer canvas is not ready.'));
      fabric.loadSVGFromString(svg,(objects,options)=>{
        if(!objects||!objects.length)return reject(new Error('No editable vector paths were found.'));
        const group=fabric.util.groupSVGElements(objects,options||{});
        const maxW=opts.maxWidth||Math.max(160,(canvas.getWidth?canvas.getWidth():600)*.45);
        if(group.width&&group.width>maxW)group.scaleToWidth(maxW);
        if(opts.maxHeight&&group.getScaledHeight()>opts.maxHeight)group.scaleToHeight(opts.maxHeight);
        group.set({left:opts.left==null?80:opts.left,top:opts.top==null?80:opts.top,originX:opts.originX||'left',originY:opts.originY||'top',name:opts.name||'Editable SVG artwork',lockScalingFlip:true,zvVector:true});
        canvas.add(group);canvas.setActiveObject(group);group.setCoords();canvas.requestRenderAll();resolve(group);
      },function(_el,obj){if(obj)obj.zvVectorPath=true;});
    });
  }
  async function add(file,canvas,opts){
    if(!file)return null;
    if(file.size>15*1024*1024)throw new Error(file.name+' exceeds 15 MB.');
    const svg=await toSvg(file);return loadFabric(svg,canvas,Object.assign({name:file.name+' · editable SVG'},opts||{}));
  }
  window.ZVVectorUpload={toSvg,loadFabric,add};
})();
