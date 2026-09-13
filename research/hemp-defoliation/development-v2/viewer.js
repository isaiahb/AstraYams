import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const $=id=>document.getElementById(id),host=$('view'),scene=new T.Scene();scene.background=new T.Color('#e5ebdd');
const camera=new T.OrthographicCamera(-.65,.65,.60,-.60,.005,20);camera.up.set(0,0,1);
const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=T.SRGBColorSpace;host.prepend(renderer.domElement);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.minDistance=.12;orbit.maxDistance=5;
scene.add(new T.HemisphereLight(0xfaffdf,0x667653,1.35));const light=new T.DirectionalLight(0xfff6df,2);light.position.set(-2,-3,4);scene.add(light);
const gradient=new T.DataTexture(new Uint8Array([125,187,231,255]),4,1,T.RedFormat);gradient.needsUpdate=true;gradient.minFilter=gradient.magFilter=T.NearestFilter;
const floor=new T.Mesh(new T.PlaneGeometry(10,10),new T.MeshBasicMaterial({color:0xe5ebdd}));floor.position.z=-.202;scene.add(floor);
const pot=new T.Mesh(new T.CylinderGeometry(.108,.081,.20,64,1,true),new T.MeshToonMaterial({color:0x555d51,side:T.DoubleSide,gradientMap:gradient}));pot.rotation.x=Math.PI/2;pot.position.z=-.1;scene.add(pot);
const rim=new T.Mesh(new T.TorusGeometry(.108,.004,8,64),new T.MeshLambertMaterial({color:0x414b40}));rim.position.z=-.002;scene.add(rim);
const soil=new T.Mesh(new T.CircleGeometry(.104,64),new T.MeshLambertMaterial({color:0x514434}));soil.position.z=-.012;scene.add(soil);
const model=new T.Group();scene.add(model);let data,latest,baseline,playing=false,last=0,selected='front';
const v=x=>new T.Vector3(...x),vec=(x,y,z)=>new T.Vector3(x,y,z),mix=(a,b,t)=>a.clone().lerp(b,t);
function camView(key){selected=key;camera.up.set(0,0,1);camera.zoom=key==='base'?2.3:1;let pos,target=[.035,0,.34];if(key==='front')pos=[.035,-3,.34];if(key==='side')pos=[3,0,.34];if(key==='three')pos=[1.6,-2.5,1.25];if(key==='top'){pos=[0,-.001,3];target=[0,0,.3];camera.up.set(0,1,0)}if(key==='base'){pos=[.55,-1,.28];target=[0,0,.13]}camera.position.set(...pos);orbit.target.set(...target);camera.updateProjectionMatrix();orbit.update();document.querySelectorAll('#views button').forEach(b=>b.classList.toggle('active',b.dataset.view===key))}camView('front');

function frame(a){const b=new T.Vector3().crossVectors(a,Math.abs(a.z)<.96?vec(0,0,1):vec(0,1,0)).normalize(),n=new T.Vector3().crossVectors(a,b).normalize();return[b,n]}
let groups;
function tri(kind,a,b,c,color){const g=groups[kind]??={p:[],c:[]};for(const p of [a,b,c]){g.p.push(p.x,p.y,p.z);g.c.push(color.r,color.g,color.b)}}
function tube(points,r0,r1,kind,color,sides=7){if(points.length<2)return;const rings=[];for(let i=0;i<points.length;i++){let d=points[Math.min(i+1,points.length-1)].clone().sub(points[Math.max(i-1,0)]);if(d.length()<1e-8)d=vec(0,0,1);d.normalize();const[b,n]=frame(d),r=r0+(r1-r0)*i/(points.length-1);rings.push(Array.from({length:sides},(_,j)=>points[i].clone().addScaledVector(b,r*Math.cos(2*Math.PI*j/sides)).addScaledVector(n,r*Math.sin(2*Math.PI*j/sides))))}for(let i=0;i<rings.length-1;i++)for(let j=0;j<sides;j++){const k=(j+1)%sides;tri(kind,rings[i][j],rings[i][k],rings[i+1][k],color);tri(kind,rings[i][j],rings[i+1][k],rings[i+1][j],color)}}
function ageColor(age){return new T.Color().setHSL(.14+Math.min(1,age/70)*.21,.48,.47-Math.min(1,age/70)*.15)}
function leafBlade(origin,phi,length,index,roll,droop,col,pitch=0,widthFactor=1,asymmetry=0,fanAngle=0){
 if(length<.0005)return;
 // All leaflets share one compound-leaf plane before individual curvature.
 const mid=vec(Math.cos(phi)*Math.cos(pitch),Math.sin(phi)*Math.cos(pitch),Math.sin(pitch));
 const lateral=vec(-Math.sin(phi),Math.cos(phi),0),normal=mid.clone().cross(lateral).normalize();
 const fan=lateral.clone().multiplyScalar(Math.cos(roll)).addScaledVector(normal,Math.sin(roll));
 const nr=normal.clone().multiplyScalar(Math.cos(roll)).addScaledVector(lateral,-Math.sin(roll));
 const a=mid.clone().multiplyScalar(Math.cos(fanAngle)).addScaledVector(fan,Math.sin(fanAngle));
 const br=nr.clone().cross(a).normalize(),profile=data.profiles[index],rows=[];
 const center=t=>origin.clone().addScaledVector(a,length*t).addScaledVector(nr,length*(.08*Math.sin(Math.PI*t)-droop*t*t));
 for(let i=0;i<=40;i++){const t=i/40,k=i*2;rows.push([-1,0,1].map(s=>{const width=s<0?profile.low[k]*widthFactor*(1-asymmetry):s>0?profile.high[k]*widthFactor*(1+asymmetry):0;return center(t).addScaledVector(br,width*length).addScaledVector(nr,.09*Math.abs(width)*length)}))}
 for(let i=0;i<40;i++)for(let j=0;j<2;j++){tri('leaf',rows[i][j],rows[i+1][j],rows[i+1][j+1],col);tri('leaf',rows[i][j],rows[i+1][j+1],rows[i][j+1],col)}
 tube(Array.from({length:9},(_,i)=>center(i/8).addScaledVector(nr,.00015)),length*.004,length*.0005,'vein',col.clone().lerp(new T.Color('#b8cb84'),.26),4);
}

function flowerLobe(at,axis,scale){
  // A closed envelope only: no invented isolated bracts or tissue contact claim.
  if(scale<.01||axis.lengthSq()<1e-12)return;
  const dir=axis.clone().normalize(),[b,n]=frame(dir),len=.042*scale;
  const rings=[],color=new T.Color('#64833c'),rows=18,sides=14;
  for(let row=0;row<=rows;row++){
    const t=row/rows,rad=.012*scale*Math.pow(Math.sin(Math.PI*t),.72)*(1-.32*t);
    rings.push(Array.from({length:sides},(_,j)=>{
      const ph=j*2*Math.PI/sides,r=rad*(1+.10*Math.cos(ph*5+t*12));
      return at.clone().addScaledVector(dir,len*t).addScaledVector(b,r*Math.cos(ph)).addScaledVector(n,r*Math.sin(ph));
    }));
  }
  for(let i=0;i<rows;i++)for(let j=0;j<sides;j++){
    const k=(j+1)%sides;
    tri('flower',rings[i][j],rings[i+1][j],rings[i+1][k],color);
    tri('flower',rings[i][j],rings[i+1][k],rings[i][k],color);
  }
}

function flower(at,axis,scale){
 if(axis.lengthSq()<1e-12)return;const dir=axis.clone().normalize(),[b,n]=frame(dir);
 flowerLobe(at,dir,scale*.82);
 for(let j=0;j<5;j++){const f=j/5,ph=j*2.399;const radial=b.clone().multiplyScalar(Math.cos(ph)).addScaledVector(n,Math.sin(ph));
 const center=at.clone().addScaledVector(dir,.026*scale*f).addScaledVector(radial,.006*scale);
 flowerLobe(center,dir.clone().addScaledVector(radial,.55).normalize(),scale*(.38-.1*f));
 const tip=center.clone().addScaledVector(radial,.014*scale).addScaledVector(dir,.008*scale);
 const width=dir.clone().cross(radial).normalize().multiplyScalar(.0025*scale);
 tri('flower',center.clone().sub(width),tip,center.clone().add(width),new T.Color('#46752f'));
 }
}

function build(){if(!data)return;groups={};while(model.children.length){const m=model.children[0];m.geometry.dispose();m.material.dispose();model.remove(m)}const variant=data.variants[+$('seed').value],step=+$('time').value,s=variant.states[step/2],lookup=new Map(variant.specimen.axes.map(a=>[a.id,a]));const leaflookup=new Map(variant.specimen.leaves.map(a=>[a.id,a])),isEvent=$('history').checked&&step>=data.config.event.at_step,removed=new Set(isEvent?variant.removed_ids:[]);for(const ax of s.axes){const desc=lookup.get(ax.id),points=ax.points.map(v);for(let j=0;j<points.length-1;j++){if(points[j].distanceTo(points[j+1])<.00005)continue;const col=$('ages').checked?ageColor(Math.max(0,step-desc.births[j])):new T.Color('#75864b').lerp(new T.Color('#7d7351'),Math.min(1,ax.age/130));tube([points[j],points[j+1]],ax.radii[j],ax.radii[Math.min(j+1,ax.radii.length-1)],'stem',col,9)}if($('flowers').checked&&ax.flower_scale>0){const start=Math.max(1,points.length-(desc.order===0?6:3));for(let j=start;j<points.length;j++){const tangent=points[j].clone().sub(points[j-1]);flower(points[j],tangent,ax.flower_scale*(j===points.length-1?1:.56));}}}
let count=0,area=0,mass=0;for(const l of s.leaves){if(!l.active||removed.has(l.id))continue;count++;area+=l.area_m2;mass+=l.mass_kg;if(!$('leaves').checked)continue;const desc=leaflookup.get(l.id),origin=v(l.at),size=desc.length*l.scale,phi=desc.phi,radial=vec(Math.cos(phi),Math.sin(phi),0);const plen=size*(desc.petiole_ratio??.39),tip=origin.clone().addScaledVector(radial,plen).add(vec(0,0,plen*(.32-.27*Math.min(1,l.age/55))));const col=$('ages').checked?ageColor(l.age):new T.Color('#407b34').multiplyScalar(desc.tone).lerp(new T.Color('#a09549'),l.senescence*.6);tube([origin,mix(origin,tip,.5).add(vec(0,0,plen*.07)),tip],size*.013,size*.006,'petiole',new T.Color('#779057'));const patterns={7:[[-88,-58,-29,0,28,60,91],[.36,.64,.87,1,.86,.62,.34],[0,1,2,3,4,5,6]],5:[[-62,-30,0,32,64],[.60,.87,1,.85,.60],[1,2,3,4,5]],3:[[-37,0,38],[.72,1,.71],[2,3,4]]};const[angles,rel,indices]=patterns[desc.leaflets];for(let k=0;k<angles.length;k++)leafBlade(tip,phi,size*rel[k],indices[k],desc.roll,desc.droop*(.3+.7*Math.min(1,l.age/55)),col,desc.pitch??0,desc.width_factor??1,desc.asymmetry??0,angles[k]*Math.PI/180)}
for(const[k,g]of Object.entries(groups)){const geom=new T.BufferGeometry();geom.setAttribute('position',new T.Float32BufferAttribute(g.p,3));geom.setAttribute('color',new T.Float32BufferAttribute(g.c,3));geom.computeVertexNormals();model.add(new T.Mesh(geom,new T.MeshToonMaterial({vertexColors:true,gradientMap:gradient,side:T.DoubleSide})))}$('span').textContent=s.metrics.axis_width_m.toFixed(2)+' / '+(s.metrics.axis_depth_m===undefined?'—':s.metrics.axis_depth_m.toFixed(2));$('internode').textContent=s.metrics.mean_main_internode_m? (s.metrics.mean_main_internode_m*100).toFixed(1):'—';$('step-value').textContent=step;$('leafcount').textContent=count;$('height').textContent=s.metrics.axis_height_m.toFixed(2);$('area').textContent=area.toFixed(2);$('mass').textContent=(mass*1000).toFixed(1);$('status').textContent=`Specimen ${'ABC'[+$('seed').value]} · ${s.axes.length} persistent axes · ${isEvent?'recorded event applied':'no recorded leaf removal'}`;$('event').textContent=isEvent?`${removed.size} specified leaf organs removed at step 82. Retained axis coordinates and material ages are unchanged by that event.`:`${$('history').checked?'Event pending at step 82. ':''}Compare with / without the same event. This is a recorded boundary change, not contact cutting.`;}
try{latest=await(await fetch('development.json')).json();baseline=await(await fetch('/runs/hemp-development-v1/development.json')).json();data=latest;build()}catch(e){$('status').textContent='Load failed: '+e;throw e}
$('model').onchange=()=>{data=$('model').value==='v1'?baseline:latest;$('model-evidence').textContent=$('model').value==='v1'?'Previous procedural geometry':'Single-view reconstruction · depth assumed';build()};
for(const id of ['seed','leaves','ages','history','flowers'])$(id).onchange=build;$('time').oninput=()=>{playing=false;$('play').textContent='Play hypothesis';build()};$('play').onclick=()=>{playing=!playing;if(playing&&+$('time').value>=100)$('time').value=0;$('play').textContent=playing?'Pause':'Play hypothesis'};$('early').onclick=()=>{playing=false;$('play').textContent='Play hypothesis';$('time').value=30;build()};$('mature').onclick=()=>{playing=false;$('play').textContent='Play hypothesis';$('time').value=100;build()};document.querySelectorAll('#views button').forEach(b=>b.onclick=()=>camView(b.dataset.view));new ResizeObserver(()=>{renderer.setSize(host.clientWidth,host.clientHeight);const ar=host.clientWidth/host.clientHeight;camera.left=-.60*ar;camera.right=.60*ar;camera.top=.60;camera.bottom=-.60;camera.updateProjectionMatrix()}).observe(host);renderer.setAnimationLoop(t=>{if(playing&&t-last>220){last=t;const time=+$('time').value;if(time<100){$('time').value=time+2;build()}else{playing=false;$('play').textContent='Play hypothesis'}}orbit.update();renderer.render(scene,camera)});

$('save').onclick=()=>{renderer.render(scene,camera);const a=document.createElement('a');a.download=`hemp-development-v2-${$('model').value}-${'ABC'[+$('seed').value]}-${$('time').value}-${$('history').checked?'event':'intact'}-${selected}.png`;a.href=renderer.domElement.toDataURL('image/png');a.click()};
