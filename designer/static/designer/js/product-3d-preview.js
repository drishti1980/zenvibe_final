/* Zenvibe product-aware WebGL preview. Does not modify Fabric documents. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const button = $('threeDViewBtn'), modal = $('zv3dModal'), stage = $('zv3dStage');
  if (!button || !modal || !stage) return;
  let renderer, scene, camera, root, raf, pointer, angle=0.32, pitch=0.08, distance=5.5;
  const T = () => window.THREE;
  const product = () => window.PRODUCT || {};
  function material(color, metalness=0, roughness=.4) {
    return new (T().MeshStandardMaterial)({color, metalness, roughness});
  }
  function mesh(geometry, mat, x=0,y=0,z=0) {
    const o=new (T().Mesh)(geometry,mat);o.position.set(x,y,z);root.add(o);return o;
  }
  function box(w,h,d,mat,x=0,y=0,z=0){return mesh(new (T().BoxGeometry)(w,h,d),mat,x,y,z);}
  function cylinder(top,bottom,h,mat,x=0,y=0,z=0){
    return mesh(new (T().CylinderGeometry)(top,bottom,h,48),mat,x,y,z);
  }
  function artTexture() {
    const c=document.querySelector('.canvas-container canvas.lower-canvas') || $('designCanvas');
    if(!c || !c.width || !c.height) return null;
    try {
      const tex=new (T().CanvasTexture)(c);tex.colorSpace=T().SRGBColorSpace;
      tex.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());return tex;
    } catch(e) {return null;}
  }
  function award() {
    const gold=material('#e9b832',.8,.22), dark=material('#111319',.12,.27);
    box(1.45,.28,.78,dark,0,-1.35,0);
    box(1.18,.18,.65,gold,0,-1.12,0);
    cylinder(.25,.42,1.18,gold,0,-.45,0);
    cylinder(.13,.23,.35,gold,0,.30,0);
    // Extruded five-point star: actual geometry and visible side faces.
    const shape=new (T().Shape)(),outer=.75,inner=.34;
    for(let i=0;i<10;i++){
      const r=i%2?inner:outer,theta=Math.PI/2+i*Math.PI/5;
      const x=Math.cos(theta)*r,y=Math.sin(theta)*r;
      if(i===0)shape.moveTo(x,y);else shape.lineTo(x,y);
    }
    shape.closePath();
    const star=mesh(new (T().ExtrudeGeometry)(shape,{depth:.16,bevelEnabled:true,bevelSize:.055,bevelThickness:.055,bevelSegments:2}),gold,0,1.12,-.08);
    const tex=artTexture();
    if(tex) {
      const plaque=new (T().MeshBasicMaterial)({map:tex,transparent:true,side:T().DoubleSide});
      box(.95,.39,.018,plaque,0,-1.34,.405);
    }
    return star;
  }
  function drinkware(){
    const silver=material('#dedee1',.45,.25), tex=artTexture();
    const body=cylinder(.58,.48,2.35,silver,0,0,0);
    if(tex){const wrap=new (T().MeshStandardMaterial)({map:tex,roughness:.42,metalness:.12});
      body.material=[wrap,silver,silver];}
    cylinder(.57,.57,.12,silver,0,1.23,0);
    return body;
  }
  function card(){
    const tex=artTexture(),mat=tex?new (T().MeshStandardMaterial)({map:tex,roughness:.65}):material('#f8f8f8');
    return box(2.7,1.65,.055,mat);
  }
  function generic(){
    const tex=artTexture(),mat=tex?new (T().MeshStandardMaterial)({map:tex,roughness:.65}):material('#ffffff');
    return box(2.3,2.3,.16,mat);
  }
  function build(){
    const THREE=T();scene=new THREE.Scene();scene.background=new THREE.Color('#eff0f5');
    camera=new THREE.PerspectiveCamera(40,1,.1,100);
    root=new THREE.Group();scene.add(root);
    scene.add(new THREE.HemisphereLight('#ffffff','#8c91a2',2.2));
    const light=new THREE.DirectionalLight('#ffffff',3);light.position.set(3,6,7);scene.add(light);
    const fill=new THREE.DirectionalLight('#fff0ce',1.4);fill.position.set(-4,2,-3);scene.add(fill);
    const name=(product().name+' '+product().category).toLowerCase();
    // Never fabricate a different physical product. This WebGL renderer is
    // disabled until a verified product-specific model is configured.
    // The existing editor preview remains the faithful fallback.
    generic();
    const bounds=new THREE.Box3().setFromObject(root),center=bounds.getCenter(new THREE.Vector3());
    root.position.sub(center);
    const size=bounds.getSize(new THREE.Vector3()),radius=Math.max(size.x,size.y,size.z);
    distance=Math.max(3.4,radius*2.2);
    $('zv3dProductName').textContent=product().name||'Product';
    let note=$('zv3dGeometryNotice');
    if(!note){note=document.createElement('div');note.id='zv3dGeometryNotice';note.style.cssText='position:absolute;bottom:12px;left:16px;color:#596275;font-size:12px;pointer-events:none';stage.appendChild(note);}
    note.textContent='Interactive 3D approximation · accurate product geometry requires a GLB model';
  }
  function resize(){
    if(!renderer)return;
    const rect=stage.getBoundingClientRect(),w=Math.max(1,rect.width),h=Math.max(1,rect.height);
    renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();
  }
  function frame(){
    if(!renderer||modal.hidden)return;
    root.rotation.y=angle;root.rotation.x=pitch;
    camera.position.set(0,0,distance);camera.lookAt(0,0,0);
    renderer.render(scene,camera);raf=requestAnimationFrame(frame);
  }
  function close(){
    cancelAnimationFrame(raf);raf=0;
    renderer?.dispose();renderer?.domElement.remove();renderer=null;
    modal.hidden=true;modal.setAttribute('aria-hidden','true');document.body.style.overflow='';
    stage.querySelector('#zv3dGeometryNotice')?.remove();
  }
  button.addEventListener('click', e=>{
    // No verified 3D model has been provided for this product. Keep the
    // actual-image preview rather than substituting invented geometry.
    if(!product().model3dUrl || !T()) return;
    e.preventDefault();e.stopImmediatePropagation();
    try {
      if(renderer)close();
      modal.hidden=false;modal.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
      stage.querySelector('#zv3dScene')?.setAttribute('hidden','');
      renderer=new (T().WebGLRenderer)({antialias:true,alpha:false});
      renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
      renderer.outputColorSpace=T().SRGBColorSpace;
      stage.appendChild(renderer.domElement);
      renderer.domElement.style.cssText='position:absolute;inset:0;width:100%;height:100%;display:block';
      stage.style.position='relative';
      angle=.32;pitch=.08;build();resize();frame();
    }catch(err){console.error('3D preview unavailable',err);close();alert('3D rendering is unavailable on this device.');}
  },true);
  $('zv3dClose')?.addEventListener('click',()=>{if(renderer)close();},true);
  $('zv3dLeft')?.addEventListener('click',e=>{if(!renderer)return;e.stopImmediatePropagation();angle-=Math.PI/9;},true);
  $('zv3dRight')?.addEventListener('click',e=>{if(!renderer)return;e.stopImmediatePropagation();angle+=Math.PI/9;},true);
  $('zv3dReset')?.addEventListener('click',e=>{if(!renderer)return;e.stopImmediatePropagation();angle=.32;pitch=.08;distance=Math.max(distance,3.4);},true);
  stage.addEventListener('pointerdown',e=>{if(!renderer)return;pointer={x:e.clientX,y:e.clientY,id:e.pointerId};stage.setPointerCapture?.(e.pointerId);},true);
  stage.addEventListener('pointermove',e=>{if(!renderer||!pointer)return;e.stopImmediatePropagation();angle+=(e.clientX-pointer.x)*.008;pitch=Math.max(-1,Math.min(1,pitch+(e.clientY-pointer.y)*.006));pointer.x=e.clientX;pointer.y=e.clientY;},true);
  stage.addEventListener('pointerup',()=>pointer=null,true);
  stage.addEventListener('wheel',e=>{if(!renderer)return;e.preventDefault();e.stopImmediatePropagation();distance=Math.max(2.2,Math.min(13,distance+(e.deltaY>0?.28:-.28)));},{capture:true,passive:false});
  window.addEventListener('resize',resize);
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&renderer)close();},true);
})();
