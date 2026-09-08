import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {STLLoader} from 'three/examples/jsm/loaders/STLLoader.js';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
export function ModelViewer({path,assetURL}:{path:string,assetURL:(s:string)=>string}){
 const host=useRef<HTMLDivElement>(null);const [error,setError]=useState('');const [loading,setLoading]=useState(true);
 useEffect(()=>{
  if(!host.current)return;let disposed=false;setLoading(true);setError('');
  const scene=new THREE.Scene();scene.background=new THREE.Color('#10191c');
  const camera=new THREE.PerspectiveCamera(40,1,.0001,1000);camera.up.set(0,0,1);
  const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;
  host.current.appendChild(renderer.domElement);const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
  scene.add(new THREE.HemisphereLight(0xe5f4ff,0x334c40,2.7));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(1,-2,3);scene.add(light);
  const group=new THREE.Group();scene.add(group);const loader=new STLLoader();
  async function stl(file:string,color:number){const response=await fetch(assetURL(file));if(!response.ok)throw new Error('Mesh unavailable');const geometry=loader.parse(await response.arrayBuffer());geometry.computeVertexNormals();return new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color,roughness:.45,metalness:.3}));}
  async function load(){
   if(path.toLowerCase().endsWith('.urdf')){
    const text=await (await fetch(assetURL(path))).text();const xml=new DOMParser().parseFromString(text,'application/xml');const links=new Map<string,THREE.Group>();const pending:Promise<void>[]=[];
    for(const link of xml.querySelectorAll('robot > link')){const g=new THREE.Group();links.set(link.getAttribute('name')!,g);
     for(const visual of link.querySelectorAll(':scope > visual')){const mesh=visual.querySelector('mesh');if(!mesh)continue;const file=mesh.getAttribute('filename')!;const full=new URL(file,'http://workspace/'+path).pathname.slice(1);const color=visual.querySelector('color')?.getAttribute('rgba')?.split(/\s+/).map(Number);const c=color?new THREE.Color(color[0],color[1],color[2]).getHex():0xb7c9ce;
      pending.push(stl(full,c).then(m=>{const origin=visual.querySelector('origin');const xyz=(origin?.getAttribute('xyz')||'0 0 0').split(/\s+/).map(Number);const rpy=(origin?.getAttribute('rpy')||'0 0 0').split(/\s+/).map(Number);const scale=(mesh.getAttribute('scale')||'1 1 1').split(/\s+/).map(Number);m.position.set(xyz[0],xyz[1],xyz[2]);m.rotation.set(rpy[0],rpy[1],rpy[2],'ZYX');m.scale.set(scale[0],scale[1],scale[2]);g.add(m);}));}
    }
    const children=new Set<string>();for(const joint of xml.querySelectorAll('robot > joint')){const child=joint.querySelector('child')!.getAttribute('link')!;const parent=joint.querySelector('parent')!.getAttribute('link')!;const g=links.get(child);if(!g||!links.get(parent))continue;const o=joint.querySelector('origin');const xyz=(o?.getAttribute('xyz')||'0 0 0').split(/\s+/).map(Number);const rpy=(o?.getAttribute('rpy')||'0 0 0').split(/\s+/).map(Number);g.position.set(xyz[0],xyz[1],xyz[2]);g.rotation.set(rpy[0],rpy[1],rpy[2],'ZYX');links.get(parent)!.add(g);children.add(child);}
    for(const [name,g] of links)if(!children.has(name))group.add(g);await Promise.all(pending);
   }else if(path.endsWith('.glb')||path.endsWith('.gltf')){const gltf=await new GLTFLoader().loadAsync(assetURL(path));group.add(gltf.scene);}
   else {group.add(await stl(path,0x75aaba));if(path.endsWith('socket-cad.stl')){const peg=await stl(path.replace('socket-cad.stl','peg.stl'),0xe6b66b);peg.position.z=.055;group.add(peg);}}
   if(disposed)return;
   const box=new THREE.Box3().setFromObject(group),size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());const radius=Math.max(size.x,size.y,size.z,.01);
   controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(1.5,-2,1.3).multiplyScalar(radius));camera.near=radius/1000;camera.far=radius*100;camera.updateProjectionMatrix();
   const grid=new THREE.GridHelper(radius*3,24,0x41605c,0x233536);grid.rotation.x=Math.PI/2;grid.position.set(center.x,center.y,box.min.z-.001*radius);scene.add(grid);
   setLoading(false);
  }
  load().catch(e=>{if(!disposed){setError(String(e));setLoading(false);}});
  const resize=new ResizeObserver(()=>{if(!host.current)return;const w=host.current.clientWidth,h=host.current.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();});resize.observe(host.current);
  renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
  return()=>{disposed=true;resize.disconnect();renderer.setAnimationLoop(null);controls.dispose();scene.traverse(obj=>{if(obj instanceof THREE.Mesh){obj.geometry.dispose();const materials=Array.isArray(obj.material)?obj.material:[obj.material];materials.forEach(m=>m.dispose());}});renderer.dispose();renderer.domElement.remove();};
 },[path]);
 return <div className="model-host" ref={host}>{loading&&<div className="viewer-overlay">Loading geometry…</div>}{error&&<div className="viewer-overlay error">{error}</div>}<div className="viewer-legend">{path.endsWith('socket-cad.stl')?<><span><i className="gold"/>Held part</span><span><i/>Fixture</span></>:<span>CAD geometry</span>}<small>Drag to orbit · Scroll to zoom · CAD inspection</small></div></div>;
}
