import { readdir, realpath, stat } from 'node:fs/promises';
import { resolve, relative, extname, basename, sep } from 'node:path';
export type Artifact={path:string,name:string,kind:string,bytes:number,modified:string};
const extensions=new Set(['.stl','.urdf','.glb','.gltf','.png','.jpg','.mp4','.webm','.json','.md','.csv','.xml']);
export async function listArtifacts(root:string):Promise<Artifact[]>{
 const rows:Artifact[]=[];
 async function walk(dir:string,depth=0){
  if(depth>7)return;
  for(const entry of await readdir(dir,{withFileTypes:true}).catch(()=>[])){
   if(entry.name.startsWith('.')||['node_modules','__pycache__','checkpoints'].includes(entry.name)||entry.isSymbolicLink())continue;
   const path=resolve(dir,entry.name);
   if(entry.isDirectory())await walk(path,depth+1);
   else if(extensions.has(extname(path).toLowerCase())){
    const s=await stat(path);const ext=extname(path).toLowerCase();
    rows.push({path:relative(root,path),name:basename(path),kind:['.mp4','.webm'].includes(ext)?'video':['.stl','.urdf','.glb','.gltf'].includes(ext)?'model':['.png','.jpg'].includes(ext)?'image':'document',bytes:s.size,modified:s.mtime.toISOString()});
   }
  }
 }
 for(const folder of ['tasks','runs','docs','assets/robots'])await walk(resolve(root,folder));
 return rows.sort((a,b)=>b.modified.localeCompare(a.modified));
}
export async function artifactPath(root:string,path:string){
 if(!path||path.includes('\0'))throw new Error('Invalid artifact path');
 const canonicalRoot=await realpath(root);const target=await realpath(resolve(root,path));
 if(!target.startsWith(canonicalRoot+sep))throw new Error('Artifact must be inside the workspace');
 const rel=relative(canonicalRoot,target);
 if(!['tasks/','runs/','docs/','assets/robots/'].some(p=>rel.startsWith(p))||rel.split(sep).some(p=>p.startsWith('.')))throw new Error('Artifact location is not exposed');
 if(!extensions.has(extname(target).toLowerCase()))throw new Error('Unsupported artifact type');
 return target;
}
