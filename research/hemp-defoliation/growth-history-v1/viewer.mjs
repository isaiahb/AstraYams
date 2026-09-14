import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {simulate} from './growth.mjs';
const $=id=>document.getElementById(id),host=$('host'),V=a=>new T.Vector3(...a);
try{
const profiles=(await(await fetch('/research/hemp-defoliation/development-v3/reference-data.json')).json()).profiles;
let history=simulate(),time=34,skeleton=false,ages=false,comparison=false,playing=false,view='three',groups;
const scene=new T.Scene();scene.background=new T.Color('#dce6d5');
const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.25));host.prepend(renderer.domElement);
scene.add(new T.HemisphereLight(0xf7ffe8,0x657a58,2.1));const key=new T.DirectionalLight(0xfff5df,2.2);key.position.set(-1,-2,4);scene.add(key);
const camera=new T.OrthographicCamera(-1,1,1,-1,.001,20);camera.up.set(0,0,1);const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=false;
const gradient=new T.DataTexture(new Uint8Array([140,195,240,255]),4,1,T.RedFormat);gradient.needsUpdate=true;gradient.minFilter=gradient.magFilter=T.NearestFilter;
const plant=new T.Group();scene.add(plant);const pots=new T.Group();scene.add(pots);const old=new T.Group();scene.add(old);old.visible=false;
let span=1.45,center=new T.Vector3(0,0,.40),oldLoaded=false;
function tri(kind,a,b,c,color){const g=groups[kind]??={p:[],c:[]};for(const v of [a,b,c]){g.p.push(v.x,v.y,v.z);g.c.push(color.r,color.g,color.b)}}
function tube(points,r0,r1,color,kind='stem',sides=7){if(points.length<2)return;const rings=[];for(let i=0;i<points.length;i++){const d=points[Math.min(i+1,points.length-1)].clone().sub(points[Math.max(0,i-1)]).normalize();if(d.lengthSq()<1e-12)return;const u=new T.Vector3().crossVectors(d,Math.abs(d.z)<.95?new T.Vector3(0,0,1):new T.Vector3(1,0,0)).normalize(),v=d.clone().cross(u),r=T.MathUtils.lerp(r0,r1,i/(points.length-1));rings.push(Array.from({length:sides},(_,j)=>points[i].clone().addScaledVector(u,r*Math.cos(j*Math.PI*2/sides)).addScaledVector(v,r*Math.sin(j*Math.PI*2/sides))))}for(let i=0;i<rings.length-1;i++)for(let j=0;j<sides;j++){const k=(j+1)%sides;tri(kind,rings[i][j],rings[i][k],rings[i+1][k],color);tri(kind,rings[i][j],rings[i+1][k],rings[i+1][j],color)}}
const colorFor=(age,kind)=>ages?new T.Color().setHSL(.12+.24*Math.min(age/20,1),.65,.42):new T.Color(kind==='stem'?'#6e8150':age<3?'#7ca84d':'#3d7837');
function leaf(l){const junction=V(l.junction),d=V(l.direction),normal=V(l.normal),side=normal.clone().cross(d).normalize(),col=colorFor(l.age,'leaf');
 const n=l.leaflets,indices=n===1?[3]:n===3?[2,3,4]:n===5?[1,2,3,4,5]:[0,1,2,3,4,5,6];
 const angle=n===1?[0]:n===3?[-.62,0,.62]:n===5?[-1.05,-.5,0,.5,1.05]:[-1.40,-.97,-.49,0,.49,.97,1.40];
 const rel=n===1?[1]:n===3?[.73,1,.73]:n===5?[.52,.81,1,.81,.52]:[.33,.58,.84,1,.84,.58,.33];
 tube([V(l.at),V(l.at).lerp(junction,.5).addScaledVector(normal,.002*l.expansion),junction],.00055*l.expansion,.0003*l.expansion,col,'petiole',5);
 for(let k=0;k<n;k++){
  const dir=d.clone().multiplyScalar(Math.cos(angle[k])).addScaledVector(side,Math.sin(angle[k]));const lateral=normal.clone().cross(dir).normalize(),L=l.length*rel[k],rows=[];
  for(let j=0;j<=24;j++){const t=j/24,profile=profiles[indices[k]],index=Math.round(t*80);
   // Measured leaflet outline transfer, with a medial strip inside the outline.
   // Cotyledons use a smooth oval illustration rather than serrated true leaves.
   const half=l.kind==='cotyledon'?.25*Math.pow(Math.sin(Math.PI*t),.7):(profile.high[index]-profile.low[index])*.5;
   const bend=.045*Math.sin(Math.PI*t)-.12*t*t*l.expansion;
   const mid=junction.clone().addScaledVector(dir,L*t).addScaledVector(normal,L*bend);
   rows.push([-1,0,1].map(s=>mid.clone().addScaledVector(lateral,s*half*L*(.3+.7*l.expansion)).addScaledVector(normal,-Math.abs(s)*half*L*.10)));
  }
  for(let j=0;j<24;j++)for(let m=0;m<2;m++){tri('leaf',rows[j][m],rows[j+1][m],rows[j+1][m+1],col);tri('leaf',rows[j][m],rows[j+1][m+1],rows[j][m+1],col)}
  tube(rows.filter((_,j)=>j%3===0).map(r=>r[1].clone().addScaledVector(normal,.00012)),L*.003,L*.0003,col.clone().lerp(new T.Color('#bed18b'),.32),'vein',4);
 }
}
function pot(x=0){const mat=new T.MeshToonMaterial({color:'#858376',gradientMap:gradient,side:T.DoubleSide});const shell=new T.Mesh(new T.CylinderGeometry(.13,.1,.21,40,1,true),mat);shell.rotation.x=Math.PI/2;shell.position.set(x,0,-.11);pots.add(shell);const soil=new T.Mesh(new T.CircleGeometry(.124,40),new T.MeshLambertMaterial({color:'#5c5442'}));soil.position.set(x,0,-.01);pots.add(soil);const rim=new T.Mesh(new T.TorusGeometry(.13,.006,7,40),mat);rim.position.set(x,0,-.005);pots.add(rim)}
pot();
function state(){return history.frames[Math.max(0,Math.min(history.frames.length-1,Math.round(time*2)))]}
function build(){const start=performance.now(),s=state();plant.children.forEach(m=>{m.geometry.dispose();m.material.dispose()});plant.clear();groups={};
 if(s.hypocotyl>.0001)tube([new T.Vector3(0,0,0),new T.Vector3(0,0,s.hypocotyl)],.0012,.0008,colorFor(time,'stem'));
 for(const a of s.axes)for(let j=0;j<a.nodes.length;j++)if(a.nodes[j].length>.00005)tube([V(a.points[j]),V(a.points[j+1])],a.radii[j],a.radii[j]*.78,colorFor(time-a.nodes[j].born,'stem'));
 if(!skeleton)for(const l of s.leaves)if(l.length>.0004)leaf(l);
 for(const [kind,g]of Object.entries(groups)){const geom=new T.BufferGeometry();geom.setAttribute('position',new T.Float32BufferAttribute(g.p,3));geom.setAttribute('color',new T.Float32BufferAttribute(g.c,3));geom.computeVertexNormals();const mesh=new T.Mesh(geom,new T.MeshToonMaterial({vertexColors:true,side:T.DoubleSide,gradientMap:gradient}));mesh.name=kind;plant.add(mesh)}
 if(time<1){const seed=new T.Mesh(new T.SphereGeometry(.003,12,8),new T.MeshLambertMaterial({color:'#8c7150'}));seed.position.z=.002;plant.add(seed)}
 $('height').textContent=(s.axes[0].points.at(-1)[2]*100).toFixed(1)+' cm';$('nodes').textContent=s.metrics.nodes;$('shoots').textContent=s.metrics.shoots;$('leaves').textContent=s.metrics.leaves;
 $('volume').textContent=`${(s.metrics.skeletonWidth*100).toFixed(0)} / ${(s.metrics.skeletonDepth*100).toFixed(0)} cm`;
 $('phase').textContent=comparison?'Previous reconstruction ←  |  → Developmental model':time<2.5?'Emergence · seed leaves':time<10?'Juvenile nodes and unfolding leaves':time<22?'Axillary shoots extending':'Branched vegetative architecture';
 $('timeValue').textContent=time.toFixed(1);$('time').value=time;
 const events=history.events.filter(e=>e.time<=time).slice(-5).reverse();$('events').replaceChildren(...events.map(e=>{const el=document.createElement('div');el.className='event';el.textContent=`${e.time.toFixed(1)} · ${e.type}`;const label=document.createElement('span');label.textContent=e.id;el.append(label);return el}));
 $('cost').textContent=`${Math.round(performance.now()-start)} ms geometry update · renders only on interaction`;
 render();document.documentElement.dataset.ready='true';
}
function resize(){const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);const aspect=w/h;camera.left=-span*aspect/2;camera.right=span*aspect/2;camera.top=span/2;camera.bottom=-span/2;camera.updateProjectionMatrix();render()}
function render(){renderer.render(scene,camera)}
function setView(id){view=id;camera.up.set(...(id==='top'?[0,1,0]:[0,0,1]));const delta=id==='side'?[4,0,0]:id==='top'?[0,-.001,4]:id==='front'?[0,-4,0]:[2,-4,1.6];camera.position.copy(center).add(new T.Vector3(...delta));controls.target.copy(center);camera.zoom=1;controls.update();for(const key of ['front','side','three','top'])$(key).setAttribute('aria-pressed',String(key===id));resize()}
function fit(){const box=new T.Box3().setFromObject(plant);if(comparison)box.expandByObject(old);if(box.isEmpty()){center.set(0,0,.025);span=.16}else{center=box.getCenter(new T.Vector3());const dim=box.getSize(new T.Vector3());span=view==='top'?Math.max(.16,dim.y*1.3,dim.x*1.3/(host.clientWidth/host.clientHeight)):Math.max(.16,dim.z*1.28,Math.hypot(dim.x,dim.y)*1.12/(host.clientWidth/host.clientHeight));}setView(view)}
function pause(){playing=false;$('play').textContent='Grow from the beginning'}
let timer;
function advance(){if(!playing)return;time=Math.min(34,time+.5);build();if(time>=34)pause();else timer=setTimeout(advance,210)}
$('play').onclick=()=>{if(playing){pause();clearTimeout(timer);return}time=0;playing=true;$('play').textContent='Pause growth';center.set(0,0,.40);span=comparison?1.8:1.45;setView(view);advance()};
$('time').oninput=()=>{pause();clearTimeout(timer);time=+$('time').value;build()};
for(const b of document.querySelectorAll('[data-time]'))b.onclick=()=>{pause();clearTimeout(timer);time=+b.dataset.time;build();if(!comparison)fit()};
for(const key of ['front','side','three','top'])$(key).onclick=()=>setView(key);
$('fit').onclick=fit;
$('skeleton').onclick=()=>{skeleton=!skeleton;$('skeleton').setAttribute('aria-pressed',String(skeleton));old.children.forEach(m=>m.visible=!skeleton||m.name==='axis');build()};
$('ages').onclick=()=>{ages=!ages;$('ages').setAttribute('aria-pressed',String(ages));build()};
$('response').onchange=()=>{pause();clearTimeout(timer);history=simulate({branchResponse:+$('response').value});build()};
$('compare').onclick=async()=>{comparison=!comparison;$('compare').setAttribute('aria-pressed',String(comparison));if(comparison&&!oldLoaded){const b=await(await fetch('/runs/hemp-photo-fit-v1/shape-constrained.json')).json();groups={};for(const p of b.parts){const col=new T.Color(p.color);for(let i=0;i<p.indices.length;i+=3){const points=p.indices.slice(i,i+3).map(j=>V(p.positions.slice(j*3,j*3+3)));tri(p.kind,...points,col)}}for(const [kind,g]of Object.entries(groups)){const geom=new T.BufferGeometry();geom.setAttribute('position',new T.Float32BufferAttribute(g.p,3));geom.setAttribute('color',new T.Float32BufferAttribute(g.c,3));geom.computeVertexNormals();const mesh=new T.Mesh(geom,new T.MeshToonMaterial({vertexColors:true,side:T.DoubleSide,gradientMap:gradient}));mesh.name=kind;old.add(mesh)}oldLoaded=true;pot(-.68)}old.visible=comparison;old.position.x=-.68;old.children.forEach(m=>m.visible=!skeleton||m.name==='axis');plant.position.x=comparison?.60:0;pots.children.forEach((m,i)=>{m.visible=i<3||comparison;if(i<3)m.position.x=comparison?.60:0});build();fit()};
$('export').onclick=()=>{const blob=new Blob([JSON.stringify(history)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='hemp-growth-history-v1.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
document.addEventListener('visibilitychange',()=>{if(document.hidden){pause();clearTimeout(timer)}});
controls.addEventListener('change',render);new ResizeObserver(resize).observe(host);build();setView('three');
}catch(e){$('error').textContent=e.stack;console.error(e)}
