import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
const $=id=>document.getElementById(id),host=$('host');
try {
const checks=await(await fetch('checks.json')).json();
const [baseline,added]=await Promise.all([checks.baseline,'additions.json'].map(async url=>{const r=await fetch(url);if(!r.ok)throw Error(`${r.status}: ${url}`);return r.json()}));
const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.25));renderer.setScissorTest(true);host.prepend(renderer.domElement);
const scenes=[new T.Scene(),new T.Scene()];
for(const scene of scenes){scene.background=new T.Color('#dce3d3');scene.add(new T.AmbientLight(0xffffff,1.5));const key=new T.DirectionalLight(0xfff8df,2);key.position.set(-1,-2,3);scene.add(key);}
// Merge by material and organ kind, so thousands of organs do not mean
// thousands of draw calls. Both views share the baseline mesh buffers.
function pack(parts,isAdded){const buckets=new Map();for(const p of parts){const key=`${p.kind}:${p.color}`;if(!buckets.has(key))buckets.set(key,[]);const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(p.positions,3));g.setIndex(p.indices);g.computeVertexNormals();buckets.get(key).push(g)}const group=new T.Group();for(const [key,geoms]of buckets){const split=key.indexOf(':'),kind=key.slice(0,split),color=key.slice(split+1);const merged=mergeGeometries(geoms);geoms.forEach(g=>g.dispose());const mat=new T.MeshStandardMaterial({color,roughness:.95,side:T.DoubleSide});const mesh=new T.Mesh(merged,mat);mesh.userData={kind,original:color,isAdded};group.add(mesh)}return group}
const before=pack(baseline.parts,false),after=before.clone(),extra=pack(added.parts,true);scenes[0].add(before);scenes[1].add(after,extra);
const cameras=[0,1].map(()=>{const c=new T.OrthographicCamera(-1,1,1,-1,.01,20);c.up.set(0,0,1);return c});
const controls=new OrbitControls(cameras[0],renderer.domElement);controls.enableDamping=false;controls.minZoom=.5;controls.maxZoom=5;
const bound=new T.Box3().setFromObject(before);bound.expandByObject(extra);const center=bound.getCenter(new T.Vector3());
const height=bound.getSize(new T.Vector3()).z*1.18;let activeView='front',highlight=false,skeleton=false;
function size(){const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);const aspect=w*.5/h,span=Math.max(height,bound.getSize(new T.Vector3()).x/aspect*1.12);const c=cameras[0];c.left=-span*aspect/2;c.right=span*aspect/2;c.top=span/2;c.bottom=-span/2;c.updateProjectionMatrix();render()}
function render(){cameras[1].copy(cameras[0]);const w=host.clientWidth,h=host.clientHeight;for(let i=0;i<2;i++){renderer.setViewport(i*w/2,0,w/2,h);renderer.setScissor(i*w/2,0,w/2,h);renderer.render(scenes[i],cameras[i])}}
function setView(id){activeView=id;cameras[0].zoom=1;cameras[0].up.set(...(id==='top'?[0,1,0]:[0,0,1]));const delta=id==='side'?[4,0,0]:id==='top'?[0,-.001,4]:id==='three'?[2,-4,1]:[0,-4,0];cameras[0].position.copy(center).add(new T.Vector3(...delta));controls.target.copy(center);controls.update();for(const key of ['front','side','three','top'])$(key).setAttribute('aria-pressed',String(id===key));size()}
for(const key of ['front','side','three','top'])$(key).onclick=()=>setView(key);
$('highlight').onclick=()=>{highlight=!highlight;extra.children.forEach(m=>m.material.color.set(highlight?'#b86019':m.userData.original));$('highlight').setAttribute('aria-pressed',String(highlight));render()};
$('skeleton').onclick=()=>{skeleton=!skeleton;for(const group of [before,after,extra])group.children.forEach(m=>m.visible=!skeleton||m.userData.kind==='axis'||m.userData.kind==='petiole');$('skeleton').setAttribute('aria-pressed',String(skeleton));render()};
$('beforeCount').textContent=`${checks.baseline_leaves} compound leaves`;
$('afterCount').textContent=`${checks.total_leaves} compound leaves · +${checks.added_leaves}`;
$('facts').textContent=`${checks.added_axes} connected side shoots added · ${checks.max_attachment_error_m*1000} mm attachment mismatch · Original geometry unchanged`;
controls.addEventListener('change',render);new ResizeObserver(size).observe(host);setView('front');
document.documentElement.dataset.ready='true';
// Event-driven rendering: no continuous animation loop when the review is idle.
}catch(e){$('error').textContent=e.message;console.error(e)}
