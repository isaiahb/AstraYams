import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {makePlant,snapshot,defaultSpecs,families,observedHeight} from './plant.mjs';
const $=id=>document.getElementById(id),host=$('view');
const reference=await(await fetch('reference-data.json')).json(),data={profiles:reference.profiles};
const scene=new T.Scene();scene.background=new T.Color('#e5ebdd');
const camera=new T.OrthographicCamera(-3,3,2.2,-2.2,.01,50);camera.up.set(0,0,1);
const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.4));renderer.outputColorSpace=T.SRGBColorSpace;host.prepend(renderer.domElement);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;
scene.add(new T.HemisphereLight(0xfaffdf,0x667653,1.5));const light=new T.DirectionalLight(0xfff6df,2);light.position.set(-2,-3,5);scene.add(light);
const gradient=new T.DataTexture(new Uint8Array([130,187,231,255]),4,1,T.RedFormat);gradient.needsUpdate=true;gradient.minFilter=gradient.magFilter=T.NearestFilter;
let mode='gallery',selected='front',selectedIndex=2,playing=false,last=0,bladeRows=12;
const inputs=defaultSpecs();let specimens=inputs.map(x=>makePlant(reference,x));
const model=new T.Group();scene.add(model);const v=x=>new T.Vector3(...x),vec=(x,y,z)=>new T.Vector3(x,y,z),mix=(a,b,t)=>a.clone().lerp(b,t);
const labels=[];let day=114,groups;
function frame(a){const b=new T.Vector3().crossVectors(a,Math.abs(a.z)<.96?vec(0,0,1):vec(0,1,0)).normalize(),n=new T.Vector3().crossVectors(a,b).normalize();return[b,n]}

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
 for(let i=0;i<=bladeRows;i++){const t=i/bladeRows,k=Math.round(i/bladeRows*80);rows.push([-1,0,1].map(s=>{const width=s<0?profile.low[k]*widthFactor*(1-asymmetry):s>0?profile.high[k]*widthFactor*(1+asymmetry):0;return center(t).addScaledVector(br,width*length).addScaledVector(nr,.09*Math.abs(width)*length)}))}
 for(let i=0;i<bladeRows;i++)for(let j=0;j<2;j++){tri('leaf',rows[i][j],rows[i+1][j],rows[i+1][j+1],col);tri('leaf',rows[i][j],rows[i+1][j+1],rows[i][j+1],col)}
 if(mode==='single')tube(Array.from({length:9},(_,i)=>center(i/8).addScaledVector(nr,.00015)),length*.004,length*.0005,'vein',col.clone().lerp(new T.Color('#b8cb84'),.26),4);
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

function dispose(){model.traverse(m=>{if(m.geometry)m.geometry.dispose();if(m.material){if(m.material.map)m.material.map.dispose();m.material.dispose()}});model.clear();labels.splice(0).forEach(l=>l.element.remove())}
function pot(group){const mat=new T.MeshToonMaterial({color:'#666657',gradientMap:gradient,side:T.DoubleSide});const p=new T.Mesh(new T.CylinderGeometry(.13,.10,.23,32,1,true),mat);p.rotation.x=Math.PI/2;p.position.z=-.115;group.add(p);const r=new T.Mesh(new T.TorusGeometry(.13,.006,6,32),new T.MeshToonMaterial({color:'#474f40',gradientMap:gradient}));r.position.z=-.002;group.add(r);const soil=new T.Mesh(new T.CircleGeometry(.125,32),new T.MeshLambertMaterial({color:'#5b5141'}));soil.position.z=-.012;group.add(soil)}
function drawPlant(spec,s,group){
 groups={};const lookup=new Map(spec.axes.map(a=>[a.id,a])),leaflookup=new Map(spec.leaves.map(a=>[a.id,a]));
 for(const a of s.axes){const points=a.points.map(v);for(let j=0;j<points.length-1;j++){if(points[j].distanceTo(points[j+1])<.00008)continue;const col=$('ages').checked?ageColor(a.fractions[j]*65):new T.Color(a.order===0?'#82774e':'#738948');tube([points[j],points[j+1]],a.radii[j],a.radii[Math.min(j+1,a.radii.length-1)],'stem',col,6)}
 if($('flowers').checked&&a.flower_scale>.02){const count=a.order===0?4:a.order===1?3:2;const start=Math.max(1,points.length-count);for(let j=start;j<points.length;j++){if(a.fractions[j-1]<.8)continue;const tangent=points[j].clone().sub(points[j-1]);flower(points[j],tangent,a.flower_scale*(j===points.length-1?1.25:.8));}}}
 if($('leaves').checked)for(const l of s.leaves){if(!l.active)continue;const d=leaflookup.get(l.id),origin=v(l.at),size=d.length*l.scale,phi=d.phi,radial=vec(Math.cos(phi),Math.sin(phi),0),plen=size*d.petiole_ratio;
 const tip=origin.clone().addScaledVector(radial,plen).add(vec(0,0,plen*(.25-.22*Math.min(1,l.age/55))));
 const col=$('ages').checked?ageColor(l.age):new T.Color('#477e38').multiplyScalar(d.tone).lerp(new T.Color('#a99b4f'),l.senescence);
 tube([origin,mix(origin,tip,.5).add(vec(0,0,plen*.07)),tip],size*.013,size*.006,'petiole',new T.Color('#819550'),4);
 const patterns={7:[[-88,-58,-29,0,28,60,91],[.36,.64,.87,1,.86,.62,.34],[0,1,2,3,4,5,6]],5:[[-62,-30,0,32,64],[.60,.87,1,.85,.60],[1,2,3,4,5]],3:[[-37,0,38],[.72,1,.71],[2,3,4]]};
 const[angles,rel,ids]=patterns[d.leaflets];for(let k=0;k<ids.length;k++)leafBlade(tip,phi,size*rel[k],ids[k],d.roll,d.droop*(.3+.7*Math.min(1,l.age/55)),col,d.pitch,d.width_factor,d.asymmetry,angles[k]*Math.PI/180);
 }
 for(const[k,g]of Object.entries(groups)){const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(g.p,3));geo.setAttribute('color',new T.Float32BufferAttribute(g.c,3));geo.computeVertexNormals();group.add(new T.Mesh(geo,new T.MeshToonMaterial({vertexColors:true,gradientMap:gradient,side:T.DoubleSide})))}
 pot(group);
}
function build(){dispose();bladeRows=mode==='gallery'?12:32;const indices=mode==='gallery'?specimens.map((_,i)=>i):[selectedIndex];let totalLeaves=0;const t0=performance.now();
 for(const i of indices){const s=snapshot(specimens[i],day),g=new T.Group();if(mode==='gallery')g.position.set((i%4-1.5)*1.4,0,i<4?2.10:0);drawPlant(specimens[i],s,g);model.add(g);totalLeaves+=s.metrics.leaves;
 if(mode==='gallery'){const el=document.createElement('button');el.className='plant-label';el.textContent=`${i+1} · ${families[specimens[i].family].name.split(' · ')[0]} / ${s.metrics.height.toFixed(2)} m`;el.onclick=()=>{selectedIndex=i;mode='single';syncControls();build();camView('front')};host.append(el);labels.push({element:el,point:g.position.clone().add(vec(0,0,-.33))})}}
 const spec=specimens[selectedIndex],s=snapshot(spec,day);$('ageValue').textContent=day;$('heightValue').textContent=s.metrics.height.toFixed(2)+' m';$('branchValue').textContent=s.axes.filter(a=>a.id!=='main'&&a.fractions.some(f=>f>.01)).length;$('leafValue').textContent=s.metrics.leaves;$('widthValue').textContent=s.metrics.width.toFixed(2)+' m';
 $('stage').textContent=day<58?'Vegetative reference interval':day<68?'Transition / extension interval':day<88?'Continued extension + reproductive expansion':'Late reference interval · height approaches plateau';
 $('status').textContent=mode==='gallery'?`8 distinct scaffolds · ${totalLeaves} visible leaf organs · same scale`:`Plant ${selectedIndex+1} · ${spec.name}`;
 $('readout').textContent=spec.description;$('curveNote').textContent=`Height timing: ${reference.curves[spec.curve].name}, greenhouse cohort median. Geometry scale ×${(families[spec.family].height*spec.params.height).toFixed(2)} is a scenario choice.`;
 $('renderCost').textContent=`Geometry rebuilt in ${Math.round(performance.now()-t0)} ms. No mechanics solver.`;
 $('gallery').classList.toggle('active',mode==='gallery');$('single').classList.toggle('active',mode==='single');
 drawCurve();
}
function camView(key){selected=key;camera.zoom=1;camera.up.set(0,0,1);const center=mode==='gallery'?vec(0,0,1.65):vec(0,0,specimens[selectedIndex].H*.44-.02);let pos=center.clone().add(vec(0,-10,0));if(key==='three')pos=center.clone().add(vec(5,-9,4));if(key==='side')pos=center.clone().add(vec(10,0,0));if(key==='top'){pos=center.clone().add(vec(0,-.001,10));camera.up.set(0,1,0)}camera.position.copy(pos);orbit.target.copy(center);resize();orbit.update();document.querySelectorAll('#views button').forEach(b=>b.classList.toggle('active',b.dataset.view===key))}
function resize(){renderer.setSize(host.clientWidth,host.clientHeight);const ar=host.clientWidth/host.clientHeight;const span=mode==='gallery'?Math.max(2.22,3.05/ar):Math.max(.70,specimens[selectedIndex].H*.70);camera.left=-span*ar;camera.right=span*ar;camera.top=span;camera.bottom=-span;camera.updateProjectionMatrix()}
function syncControls(){const x=inputs[selectedIndex];$('plant').value=selectedIndex;$('family').value=x.family;$('curve').value=x.curve;for(const id of ['height','spread','density','leafWidth']){$(id).value=x[id];$(id+'Output').textContent=Number(x[id]).toFixed(2)}$('seedValue').textContent=x.seed;}
function remake(){const x=inputs[selectedIndex];for(const id of ['height','spread','density','leafWidth']){x[id]=+$(id).value;$(id+'Output').textContent=x[id].toFixed(2)}x.family=+$('family').value;x.curve=+$('curve').value;specimens[selectedIndex]=makePlant(reference,x);build();if(mode==='single')camView(selected);}
function drawCurve(){const c=$('curvePlot'),ctx=c.getContext('2d'),W=c.width,H=c.height;ctx.clearRect(0,0,W,H);ctx.fillStyle='#f2f4e9';ctx.fillRect(0,0,W,H);const x=d=>32+(d-31)/83*(W-45),y=h=>H-28-h/1.55*(H-43);const colors=['#759767','#42614e','#b39354','#6579a0','#a2706c'];
 ctx.strokeStyle='#cad3bd';ctx.lineWidth=1;for(let h=0;h<=1.5;h+=.5){ctx.beginPath();ctx.moveTo(32,y(h));ctx.lineTo(W-8,y(h));ctx.stroke();ctx.fillStyle='#586650';ctx.font='11px system-ui';ctx.fillText(h.toFixed(1),3,y(h)+4)}
 reference.curves.forEach((curve,i)=>{ctx.strokeStyle=colors[i];ctx.lineWidth=i===specimens[selectedIndex].curve?2.8:1;ctx.beginPath();curve.points.forEach((p,j)=>j?ctx.lineTo(x(p.day),y(p.median_m)):ctx.moveTo(x(p.day),y(p.median_m)));ctx.stroke();curve.points.forEach(p=>{ctx.fillStyle=colors[i];ctx.beginPath();ctx.arc(x(p.day),y(p.median_m),2,0,Math.PI*2);ctx.fill()})});
 ctx.strokeStyle='#253b32';ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(x(day),10);ctx.lineTo(x(day),H-25);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='#586650';ctx.fillText('31',x(31)-6,H-8);ctx.fillText('77',x(77)-6,H-8);ctx.fillText('114 DAS',W-54,H-8);ctx.fillText('metres · source medians',36,11);
}
for(let i=0;i<8;i++)$('plant').add(new Option(`Plant ${i+1}`,i));families.forEach((f,i)=>$('family').add(new Option(f.name,i)));reference.curves.forEach((c,i)=>$('curve').add(new Option(c.name,i)));
$('plant').onchange=()=>{selectedIndex=+$('plant').value;syncControls();build();if(mode==='single')camView(selected)};
for(const id of ['family','curve'])$(id).onchange=remake;for(const id of ['height','spread','density','leafWidth'])$(id).onchange=remake;
$('resample').onclick=()=>{inputs[selectedIndex].seed+=313;specimens[selectedIndex]=makePlant(reference,inputs[selectedIndex]);syncControls();build()};
$('reset').onclick=()=>{inputs.splice(0,8,...defaultSpecs());specimens=inputs.map(x=>makePlant(reference,x));syncControls();build();camView('front')};
$('gallery').onclick=()=>{mode='gallery';build();camView('front')};$('single').onclick=()=>{mode='single';build();camView('front')};
for(const id of ['leaves','ages','flowers'])$(id).onchange=build;
$('time').oninput=()=>{playing=false;$('play').textContent='Play development';day=+$('time').value;build()};
$('play').onclick=()=>{playing=!playing;if(playing&&day===114){day=31;$('time').value=day;build()}$('play').textContent=playing?'Pause':'Play development'};
for(const b of document.querySelectorAll('[data-day]'))b.onclick=()=>{playing=false;$('play').textContent='Play development';day=+b.dataset.day;$('time').value=day;build()};
for(const b of document.querySelectorAll('#views button'))b.onclick=()=>camView(b.dataset.view);
$('save').onclick=()=>{renderer.render(scene,camera);const a=document.createElement('a');a.download=`hemp-v3-${mode}-${selected}-day-${day}-plant-${selectedIndex+1}.png`;a.href=renderer.domElement.toDataURL('image/png');a.click()};
$('export').onclick=()=>{const b=new Blob([JSON.stringify({source:reference.doi,reference_time:'DAS in Anderson et al. cohort; generated topology is hypothetical',day,inputs},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='hemp-v3-scenario.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
syncControls();build();camView('front');new ResizeObserver(resize).observe(host);
renderer.setAnimationLoop(t=>{if(playing&&t-last>400){last=t;day=Math.min(114,day+2);$('time').value=day;build();if(day===114){playing=false;$('play').textContent='Play development'}}orbit.update();renderer.render(scene,camera);for(const l of labels){const q=l.point.clone().project(camera);l.element.style.left=((q.x+1)/2*host.clientWidth)+'px';l.element.style.top=((1-q.y)/2*host.clientHeight)+'px';l.element.style.display=q.z>1?'none':''}});
