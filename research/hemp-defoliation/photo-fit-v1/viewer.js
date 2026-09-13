import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const $=id=>document.getElementById(id),host=$('canvasHost');
const manifest=await(await fetch('manifest.json')).json();
const scene=new T.Scene();scene.background=new T.Color('#10160e');
const camera=new T.OrthographicCamera(-1,1,1,-1,.001,30);camera.up.set(0,0,1);
const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=T.SRGBColorSpace;host.prepend(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
scene.add(new T.AmbientLight(0xffffff,.9));scene.add(new T.HemisphereLight(0xf4ffe0,0x3a4830,2));let light=new T.DirectionalLight(0xffffff,2.5);light.position.set(-1,-3,3);scene.add(light);
const group=new T.Group();scene.add(group);let token=0,axesOnly=false,view='front',model;
const cam=manifest.camera,scale=cam.m_per_pixel,center=new T.Vector3((cam.width/2-cam.root_pixel[0])*scale,0,(cam.root_pixel[1]-cam.height/2)*scale);
function resize(){const h=host.clientHeight,w=h*cam.width/cam.height;renderer.setSize(w,h);camera.left=-cam.width*scale/2;camera.right=cam.width*scale/2;camera.top=cam.height*scale/2;camera.bottom=-cam.height*scale/2;camera.updateProjectionMatrix()}
function setView(id){view=id;camera.zoom=1;camera.up.set(0,0,1);const delta=id==='side'?[4,0,0]:id==='top'?[0,-.001,4]:id==='three'?[2,-4,1.7]:[0,-4,0];if(id==='top')camera.up.set(0,1,0);camera.position.copy(center).add(new T.Vector3(...delta));controls.target.copy(center);camera.lookAt(center);resize();controls.update();for(const key of ['front','side','three','top'])$(key).classList.toggle('active',key===id);$('overlayImage').style.display='none';$('overlay').classList.remove('active');}
async function load(){const request=++token;const id=$('variant').value;$('status').textContent='Loading '+id+'…';try{const data=await(await fetch(id+'.json')).json();if(request!==token)return;group.traverse(o=>{o.geometry?.dispose();o.material?.dispose()});group.clear();model=data;
for(const p of data.parts){const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(p.positions,3));g.setIndex(p.indices);g.computeVertexNormals();const m=new T.Mesh(g,new T.MeshStandardMaterial({color:p.color,roughness:.88,side:T.DoubleSide}));m.name=p.id;m.userData.kind=p.kind;m.visible=!axesOnly||p.kind==='axis';group.add(m);}
const v=manifest.variants.find(v=>v.id===id);$('iou').textContent=(100*v.metrics.raw_iou).toFixed(1)+'%';$('coarse').textContent=(100*v.metrics.coarse_iou).toFixed(1)+'%';$('attach').textContent=(manifest.checks.max_attachment_error_m*1000).toFixed(3)+' mm';$('status').textContent=`${v.axis_count} axes · ${v.leaf_count} leaf organs · ${id}`;
if($('difference').classList.contains('active'))$('reference').src=id+'-difference.png';window.plantReview={manifest,model:data,renderer,scene,camera,controls,setView,load};document.documentElement.dataset.ready='true';renderer.render(scene,camera);
}catch(e){$('error').textContent=e.stack;throw e;}}
for(const key of ['front','side','three','top'])$(key).onclick=()=>setView(key);
$('variant').onchange=load;
$('skeleton').onclick=()=>{axesOnly=!axesOnly;group.children.forEach(m=>m.visible=!axesOnly||m.userData.kind==='axis');$('skeleton').classList.toggle('active',axesOnly)};
$('overlay').onclick=()=>{if(view!=='front')setView('front');const on=$('overlayImage').style.display!=='block';$('overlayImage').style.display=on?'block':'none';$('overlay').classList.toggle('active',on)};
for(const id of ['photo','annotations','difference'])$(id).onclick=()=>{for(const k of ['photo','annotations','difference'])$(k).classList.toggle('active',id===k);$('reference').src=id==='photo'?'reference.jpg':id==='annotations'?'annotations.png':$('variant').value+'-difference.png';$('referenceLabel').textContent=id==='photo'?'Published photograph · CC BY':id==='annotations'?'Orange axes inferred in occluded regions · cyan leaf directions':'Fitting residual · same photograph'};
new ResizeObserver(resize).observe(host);setView('front');await load();renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera)});
