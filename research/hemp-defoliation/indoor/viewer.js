import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const host=document.getElementById('view'),scene=new T.Scene();
scene.background=new T.Color('#e2e8db');
const cam=new T.PerspectiveCamera(36,1,.005,40);cam.up.set(0,0,1);
const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));host.appendChild(renderer.domElement);
renderer.outputColorSpace=T.SRGBColorSpace;
const orbit=new OrbitControls(cam,renderer.domElement);orbit.enableDamping=true;orbit.minDistance=.04;orbit.maxDistance=8;
scene.add(new T.HemisphereLight(0xfffff0,0x677e57,1.2));
const light=new T.DirectionalLight(0xfff8e8,1.3);light.position.set(-2,-3,5);scene.add(light);
const gradient=new T.DataTexture(new Uint8Array([115,170,218,255]),4,1,T.RedFormat);
gradient.needsUpdate=true;gradient.minFilter=gradient.magFilter=T.NearestFilter;
const floor=new T.Mesh(new T.PlaneGeometry(30,30),new T.MeshLambertMaterial({color:0xdce2d7}));floor.position.z=-.008;scene.add(floor);
// A strip establishes the assumed aisle without obscuring the specimen.
const aisle=new T.Mesh(new T.PlaneGeometry(2.7,.90),new T.MeshLambertMaterial({color:0xcad4c6}));aisle.position.set(0,-.93,-.004);scene.add(aisle);
const full={},detail={},materials={};let data,lookup,selectedView='whole';
const hardware=['bench','rack','light','diffuser','irrigation','trellis'];
const semantics={stem:0x907044,branch:0x907044,petiole:0xad6184,leaf:0x509655,small_leaf:0x81ac67,vein:0xaacb75,stipule:0x52b7a8,flower_axis:0xb69550,bract:0xc9b74c,stigma:0xf5ecbe,root:0xb59877,pot:0x647773,substrate:0x655b4a};
const copy={
 whole:['Indoor CBD hemp · layout candidate','Three distinct whole plants. Bench, lighting and irrigation geometry are assumed; plant mechanics are not solved.'],
 specimen:['Specimen B · isolated for inspection','The same plant geometry used in the bench scene. Neighboring plants and hardware are hidden.'],
 access:['Approach from the aisle','Neighboring leaves, pot rims, tubing and bench edges constrain access. This is a static clearance study, not a robot reachability result.'],
 structure:['Specimen B · connected branches','Foliage and flowers hidden. Node attachments connect the main shoot, branches, petioles and stipules.'],
 node:['Specimen B · stem node','Purple petiole, brown branch and teal stipules. Dimensions and angles remain assumptions.'],
 flower:['Specimen B · flower structures','Simplified external bracts and stigmas; no calibrated contact or detailed tissue model.'],
 roots:['Specimen B · root hypothesis','Rooted-cutting anatomy is assumed. Pot and substrate hidden to inspect the structure.'],
 top:['Neighboring canopies','Overhead fixtures hidden to inspect leaf overlap. These distinct candidates are not validated domain randomization.']
};
const q=id=>document.getElementById(id);
function camera(pos,target){cam.up.set(0,0,1);cam.position.set(...pos);orbit.target.set(...target);orbit.update();}
camera([2.75,-4.4,3.30],[0,0,1.16]);
function inContext(){return ['whole','access','top'].includes(selectedView);}
function visibility(){
 const context=inContext();aisle.visible=context;floor.visible=context;
 for(const [kind,m] of Object.entries(full))m.visible=context;
 for(const [kind,m] of Object.entries(detail))m.visible=!context;
 const active=context?full:detail;
 for(const [kind,m] of Object.entries(active)){
  if(['leaf','small_leaf','vein'].includes(kind))m.visible=q('leaves').checked;
  if(['bract','stigma','flower_axis'].includes(kind))m.visible=q('flowers').checked;
  if(kind==='root')m.visible=selectedView==='roots';
  if(kind==='trellis')m.visible=context&&q('trellis').checked;
  if(selectedView==='top'&&['rack','light','diffuser'].includes(kind))m.visible=false;
  if(selectedView==='roots')m.visible=['root','stem'].includes(kind);
 }
}
function colors(){for(const [kind,m] of Object.entries(materials)){const on=q('colors').checked&&!hardware.includes(kind);m.vertexColors=!on;m.color.set(on?semantics[kind]:0xffffff);m.needsUpdate=true;}}
function view(key){
 selectedView=key;document.querySelectorAll('#views button').forEach(b=>b.classList.toggle('active',b.dataset.view===key));
 q('caption').innerHTML=`<strong>${copy[key][0]}</strong>${copy[key][1]}`;q('selection').style.display='none';
 q('leaves').checked=key!=='structure';q('flowers').checked=key!=='structure';q('colors').checked=['node','structure'].includes(key);
 colors();visibility();
 if(key==='whole')camera([2.75,-4.4,3.30],[0,0,1.16]);
 if(key==='access')camera([.20,-3.25,1.20],[0,0,1.17]);
 if(['specimen','structure'].includes(key))camera([1.35,-2.1,1.83],[0,-.025,1.13]);
 if(key==='top'){camera([0,-.001,5.1],[0,0,1]);cam.up.set(0,1,0);orbit.update();}
 if(key==='roots')camera([.42,-.48,.85],[0,-.025,.66]);
 if(key==='node'){const p=data.organs.find(o=>o.specimen==='B'&&o.kind==='node'&&o.rank===6).attachment;camera([p[0]+.21,p[1]-.27,p[2]+.12],p);}
 if(key==='flower'){const p=data.organs.filter(o=>o.specimen==='B'&&o.kind==='inflorescence_axis').at(-1).attachment;camera([p[0]+.2,p[1]-.24,p[2]+.14],[p[0],p[1],p[2]+.055]);}
}
try{
 const [metadata,gltf]=await Promise.all([fetch('review-data.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}),new GLTFLoader().loadAsync('plant.glb')]);
 data=metadata;lookup=new Map(data.organs.map(o=>[o.id,o]));
 gltf.scene.traverse(m=>{
  if(!m.isMesh)return;const kind=m.name,g=data.groups[kind];if(!g)throw Error('Unknown mesh '+kind);
  m.geometry.computeVertexNormals();const mat=new T.MeshToonMaterial({vertexColors:true,side:T.DoubleSide,gradientMap:gradient});
  m.material=mat;m.userData={kind,ranges:g.organs};full[kind]=m;materials[kind]=mat;
  if(hardware.includes(kind))return;
  const geom=new T.BufferGeometry();for(const [name,a] of Object.entries(m.geometry.attributes))geom.setAttribute(name,a);
  const indices=[],ranges=[],source=m.geometry.index.array;
  for(const r of g.organs){if(!r.id.startsWith('B/'))continue;const first=indices.length/3;for(let i=r.first_face*3;i<r.end_face*3;i++)indices.push(source[i]);ranges.push({id:r.id,first_face:first,end_face:indices.length/3});}
  geom.setIndex(indices);const one=new T.Mesh(geom,mat);one.userData={kind,ranges};detail[kind]=one;scene.add(one);
 });
 scene.add(gltf.scene);q('status').textContent='Three distinct anatomy candidates · per-plant organ IDs · static geometry · no contact solver or policy';view('whole');
}catch(e){q('status').textContent='Model load failed: '+e;}
document.querySelectorAll('#views button').forEach(b=>b.onclick=()=>data&&view(b.dataset.view));
for(const id of ['leaves','flowers','trellis'])q(id).onchange=visibility;q('colors').onchange=colors;
const ray=new T.Raycaster(),pointer=new T.Vector2();let down;
renderer.domElement.addEventListener('pointerdown',e=>down=[e.clientX,e.clientY]);
renderer.domElement.addEventListener('pointerup',e=>{
 if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>4||!data)return;
 const r=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,cam);
 const hit=ray.intersectObjects([...Object.values(full),...Object.values(detail)].filter(m=>m.visible))[0];if(!hit)return;
 const range=hit.object.userData.ranges.find(r=>hit.faceIndex>=r.first_face&&hit.faceIndex<r.end_face);if(!range)return;
 const o=lookup.get(range.id),p=lookup.get(o.parent),box=q('selection');box.style.display='block';box.style.whiteSpace='pre-line';box.textContent=`${o.specimen?'Specimen '+o.specimen:'Scene hardware'} · ${o.kind}\n${o.id}\nParent: ${p?p.id:'scene/root boundary'}\n${o.representation||'Geometry assumed; mechanics unvalidated.'}`;
});
new ResizeObserver(()=>{renderer.setSize(host.clientWidth,host.clientHeight);cam.aspect=host.clientWidth/host.clientHeight;cam.updateProjectionMatrix();}).observe(host);
renderer.setAnimationLoop(()=>{orbit.update();renderer.render(scene,cam);});
