import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {STLLoader} from 'three/examples/jsm/loaders/STLLoader.js';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';

export function ModelViewer({path,assetURL,presentation='assembled'}:{path:string,assetURL:(s:string)=>string,presentation?:'assembled'|'exploded'|'front'}){
 const host=useRef<HTMLDivElement>(null),api=useRef<any>(null);
 const [error,setError]=useState(''),[loading,setLoading]=useState(true),[rotating,setRotating]=useState(false);
 useEffect(()=>{api.current?.present(presentation);},[presentation]);
 useEffect(()=>{
  if(!host.current)return;let disposed=false;setLoading(true);setError('');setRotating(false);
  const scene=new THREE.Scene();scene.background=new THREE.Color('#e9ece8');
  const camera=new THREE.PerspectiveCamera(34,1,.0001,1000);camera.up.set(0,0,1);
  const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  host.current.appendChild(renderer.domElement);
  const pmrem=new THREE.PMREMGenerator(renderer),room=new RoomEnvironment(),environment=pmrem.fromScene(room,.04);scene.environment=environment.texture;scene.environmentIntensity=.85;room.dispose();pmrem.dispose();
  const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.07;controls.autoRotateSpeed=.7;controls.maxPolarAngle=Math.PI*.88;
  scene.add(new THREE.HemisphereLight(0xffffff,0x87958b,.7));
  const key=new THREE.DirectionalLight(0xfff8ee,2.8);key.castShadow=true;key.shadow.mapSize.set(2048,2048);key.shadow.normalBias=.0003;key.shadow.bias=-.0001;key.shadow.radius=4;scene.add(key);scene.add(key.target);
  const fill=new THREE.DirectionalLight(0xd7e8ff,1.1);scene.add(fill);
  const rim=new THREE.DirectionalLight(0xffffff,1.8);scene.add(rim);
  const group=new THREE.Group();scene.add(group);const loader=new STLLoader();
  const parts:{mesh:THREE.Mesh,home:THREE.Vector3,offset:THREE.Vector3}[]=[];let radius=1,center=new THREE.Vector3(),explode=0,targetExplode=presentation==='exploded'?1:0,currentMode=presentation;
  function material(file:string,fallback:number){
   const name=file.toLowerCase();let color=fallback,metalness=.55,roughness=.32;
   if(/actuator|motor|connector|wire_channel|clamp|guard/.test(name)){color=0x263737;metalness=.35;roughness=.4;}
   else if(/bearing|collar|spindle|shaft/.test(name)){color=0xa7b4b9;metalness=.85;roughness=.22;}
   else if(/[_/]m[234568]_|screw|bolt|fastener/.test(name)){color=0x59656a;metalness=.85;roughness=.26;}
   else if(/tube|tool_plate|spigot/.test(name)){color=0x467b76;metalness=.55;roughness=.3;}
   else if(/base|tower|yoke|platter|retainer/.test(name)){color=0xc9d0ce;}
   return new THREE.MeshStandardMaterial({color,metalness,roughness});
  }
  async function stl(file:string,color:number){const response=await fetch(assetURL(file));if(!response.ok)throw new Error('Mesh unavailable');const geometry=loader.parse(await response.arrayBuffer());geometry.computeVertexNormals();const mesh=new THREE.Mesh(geometry,material(file,color));mesh.name=file.split('/').at(-1)||'';mesh.castShadow=true;mesh.receiveShadow=true;return mesh;}
  function frame(front=false){const distance=radius*(targetExplode?3.0:2.2);controls.target.copy(center).add(new THREE.Vector3(0,0,targetExplode?radius*.25:0));camera.position.copy(controls.target).add((front?new THREE.Vector3(0,-1,.1):new THREE.Vector3(1.25,-1.9,1.15).normalize()).multiplyScalar(distance));controls.update();}
  api.current={present:(mode:typeof presentation)=>{currentMode=mode;targetExplode=mode==='exploded'?1:0;frame(mode==='front');},rotate:()=>{controls.autoRotate=!controls.autoRotate;setRotating(controls.autoRotate);},reset:()=>frame(currentMode==='front')};
  async function load(){
   if(path.toLowerCase().endsWith('.urdf')){
    const response=await fetch(assetURL(path));if(!response.ok)throw new Error('Assembly unavailable');const xml=new DOMParser().parseFromString(await response.text(),'application/xml');const links=new Map<string,THREE.Group>();const pending:Promise<void>[]=[];
    for(const link of xml.querySelectorAll('robot > link')){const g=new THREE.Group();g.name=link.getAttribute('name')!;links.set(g.name,g);
     for(const visual of link.querySelectorAll(':scope > visual')){const mesh=visual.querySelector('mesh');if(!mesh)continue;const full=new URL(mesh.getAttribute('filename')!,'http://workspace/'+path).pathname.slice(1);const color=visual.querySelector('color')?.getAttribute('rgba')?.split(/\s+/).map(Number);const c=color?new THREE.Color(color[0],color[1],color[2]).getHex():0xc9d0ce;
      pending.push(stl(full,c).then(m=>{const o=visual.querySelector('origin'),xyz=(o?.getAttribute('xyz')||'0 0 0').split(/\s+/).map(Number),rpy=(o?.getAttribute('rpy')||'0 0 0').split(/\s+/).map(Number),scale=(mesh.getAttribute('scale')||'1 1 1').split(/\s+/).map(Number);m.position.set(...xyz as [number,number,number]);m.rotation.set(rpy[0],rpy[1],rpy[2],'ZYX');m.scale.set(...scale as [number,number,number]);g.add(m);}));}
    }
    const children=new Set<string>();for(const joint of xml.querySelectorAll('robot > joint')){const child=joint.querySelector('child')!.getAttribute('link')!,parent=joint.querySelector('parent')!.getAttribute('link')!,g=links.get(child);if(!g||!links.get(parent))continue;const o=joint.querySelector('origin'),xyz=(o?.getAttribute('xyz')||'0 0 0').split(/\s+/).map(Number),rpy=(o?.getAttribute('rpy')||'0 0 0').split(/\s+/).map(Number);g.position.set(...xyz as [number,number,number]);g.rotation.set(rpy[0],rpy[1],rpy[2],'ZYX');links.get(parent)!.add(g);children.add(child);}
    for(const [name,g] of links)if(!children.has(name))group.add(g);await Promise.all(pending);
   }else if(/\.gl(b|tf)$/i.test(path)){const gltf=await new GLTFLoader().loadAsync(assetURL(path));group.add(gltf.scene);}
   else{group.add(await stl(path,0x467b76));if(path.endsWith('socket-cad.stl')){const peg=await stl(path.replace('socket-cad.stl','peg.stl'),0xc99a55);peg.position.z=.055;group.add(peg);}}
   if(disposed)return;
   const box=new THREE.Box3().setFromObject(group),size=box.getSize(new THREE.Vector3());center=box.getCenter(new THREE.Vector3());radius=Math.max(size.x,size.y,size.z,.01);
   scene.fog=new THREE.Fog('#e9ece8',radius*4,radius*12);camera.near=radius/1000;camera.far=radius*100;camera.updateProjectionMatrix();controls.minDistance=radius*.5;controls.maxDistance=radius*8;
   group.updateMatrixWorld(true);group.traverse(obj=>{if(!(obj instanceof THREE.Mesh))return;obj.castShadow=true;obj.receiveShadow=true;const c=new THREE.Box3().setFromObject(obj).getCenter(new THREE.Vector3());const offset=new THREE.Vector3((c.x-center.x)*.55,(c.y-center.y)*1.5,Math.max(0,c.z-box.min.z)*.85);const inverse=obj.parent!.getWorldQuaternion(new THREE.Quaternion()).invert();offset.applyQuaternion(inverse);parts.push({mesh:obj,home:obj.position.clone(),offset});});
   const floor=new THREE.Mesh(new THREE.PlaneGeometry(radius*200,radius*200),new THREE.MeshStandardMaterial({color:0xe9ece8,roughness:1,metalness:0}));floor.position.z=box.min.z-radius*.003;floor.receiveShadow=true;scene.add(floor);
   key.position.copy(center).add(new THREE.Vector3(-1,-1,2.5).multiplyScalar(radius));key.target.position.copy(center);key.shadow.camera.left=-radius*2;key.shadow.camera.right=radius*2;key.shadow.camera.top=radius*2;key.shadow.camera.bottom=-radius*2;key.shadow.camera.near=radius*.01;key.shadow.camera.far=radius*8;key.shadow.camera.updateProjectionMatrix();
   fill.position.copy(center).add(new THREE.Vector3(2,1,1).multiplyScalar(radius));rim.position.copy(center).add(new THREE.Vector3(-1,2,2).multiplyScalar(radius));frame(presentation==='front');setLoading(false);
  }
  load().catch(e=>{if(!disposed){setError(String(e));setLoading(false);}});
  const resize=new ResizeObserver(()=>{if(!host.current)return;const w=host.current.clientWidth,h=host.current.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();});resize.observe(host.current);
  renderer.setAnimationLoop(()=>{explode+=(targetExplode-explode)*.065;parts.forEach(p=>p.mesh.position.copy(p.home).addScaledVector(p.offset,explode));controls.update();renderer.render(scene,camera);});
  return()=>{disposed=true;api.current=null;resize.disconnect();renderer.setAnimationLoop(null);controls.dispose();scene.traverse(obj=>{if(obj instanceof THREE.Mesh){obj.geometry.dispose();(Array.isArray(obj.material)?obj.material:[obj.material]).forEach(m=>m.dispose());}});environment.dispose();renderer.dispose();renderer.domElement.remove();};
 },[path]);
 return <div className="model-host studio-model" ref={host}>{loading&&<div className="viewer-overlay">Loading geometry…</div>}{error&&<div className="viewer-overlay error">{error}</div>}<div className="studio-tools"><button onClick={()=>api.current?.rotate()} aria-pressed={rotating}>{rotating?'Pause rotation':'Rotate'}</button><button onClick={()=>api.current?.reset()}>Reset view</button><button onClick={()=>{if(document.fullscreenElement)document.exitFullscreen();else host.current?.requestFullscreen().catch(()=>{});}}>Expand</button></div><div className="viewer-legend"><span>{presentation==='exploded'?'Exploded assembly · illustrative separation':'CAD geometry · studio materials'}</span><small>Drag to orbit · Scroll to zoom</small></div></div>;
}
