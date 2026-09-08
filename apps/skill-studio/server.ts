import {resolve} from 'node:path';
import {mkdir,realpath} from 'node:fs/promises';
import {listSkills,saveSkill,archiveSkills,deleteSkill} from './catalog';
const here=import.meta.dir;
const upstream=await Bun.file(resolve(here,'../desktop/.local/connection.json')).json();
const origin=new URL(upstream.url).origin;
const server=Bun.serve({hostname:'127.0.0.1',port:Number(process.env.PORT||0),async fetch(req){
 const u=new URL(req.url);
 if(u.pathname==='/studio-api/asset'){
 if(req.headers.get('authorization')!=='Bearer '+upstream.token&&u.searchParams.get('token')!==upstream.token)return new Response('Unauthorized',{status:401});
 try{const path=u.searchParams.get('path')||'',root=resolve(here,'../..');if(!path.startsWith('assets/workcells/')&&!path.startsWith('apps/skill-studio/evidence/'))throw Error('Invalid asset');const full=await realpath(resolve(root,path));const allowed=[resolve(root,'assets/workcells')+'/',resolve(here,'evidence')+'/'];if(!allowed.some(p=>full.startsWith(p)))throw Error('Invalid asset');return new Response(Bun.file(full),{headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});}catch{return new Response('Asset unavailable',{status:404});}}
 if(u.pathname==='/studio-api/attachments'&&req.method==='POST'){
 if(req.headers.get('authorization')!=='Bearer '+upstream.token)return Response.json({error:'Unauthorized'},{status:401});
 try{const form=await req.formData(),project=String(form.get('projectId')||'');if(!/^[a-f0-9-]{36}$/.test(project))throw new Error('Invalid project');
 const dir=resolve(here,'../desktop/workspaces',project);if(!await Bun.file(resolve(dir,'BRIEF.md')).exists())throw new Error('Project not found');
 const files=form.getAll('files');if(!files.length||files.length>10)throw new Error('Choose 1–10 files');
 let total=0;for(const f of files){if(!(f instanceof File)||! /\.(png|jpe?g|webp|gif|step|stp|obj|stl|glb|gltf|urdf|xml|mtl)$/i.test(f.name))throw new Error('Unsupported file type');total+=f.size;}if(total>50*1024*1024)throw new Error('Attachments must total less than 50 MB');
 await mkdir(resolve(dir,'inputs'),{recursive:true});const paths=[];for(const file of files){const f=file as File,name=crypto.randomUUID().slice(0,8)+'-'+f.name.replace(/[^a-zA-Z0-9._-]/g,'_');await Bun.write(resolve(dir,'inputs',name),f);paths.push('apps/desktop/workspaces/'+project+'/inputs/'+name);}return Response.json({paths});
 }catch(e){return Response.json({error:e instanceof Error?e.message:'Upload failed'},{status:400});}}
 if(u.pathname==='/studio-api/delete'&&req.method==='POST'){if(req.headers.get('authorization')!=='Bearer '+upstream.token)return Response.json({error:'Unauthorized'},{status:401});try{return Response.json(await deleteSkill(here,(await req.json()).id));}catch{return Response.json({error:'Unable to remove skill'},{status:400});}}
 if(u.pathname==='/studio-api/archive'&&req.method==='POST'){if(req.headers.get('authorization')!=='Bearer '+upstream.token)return Response.json({error:'Unauthorized'},{status:401});try{const b=await req.json();return Response.json(await archiveSkills(here,b.ids,b.archived!==false));}catch{return Response.json({error:'Unable to update archive'},{status:400});}}
 if(u.pathname==='/studio-api/skills'){if(req.headers.get('authorization')!=='Bearer '+upstream.token)return Response.json({error:'Unauthorized'},{status:401});try{if(req.method==='GET')return Response.json(await listSkills(here));if(req.method==='POST')return Response.json(await saveSkill(here,await req.json()));return new Response('Method not allowed',{status:405});}catch{return Response.json({error:'Unable to save skill'},{status:400});}}
 if(u.pathname.startsWith('/api/'))return fetch(origin+u.pathname+u.search,{method:req.method,headers:req.headers,body:['GET','HEAD'].includes(req.method)?undefined:req.body,redirect:'manual'});
 if(u.pathname==='/icon.png')return new Response(Bun.file(resolve(here,'assets/icon.png')));
 if(u.pathname==='/index.js'||u.pathname==='/index.css')return new Response(Bun.file(resolve(here,'dist',u.pathname.slice(1))));
 if(u.pathname!=='/')return new Response('Not found',{status:404});
 return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Astra Yams</title><link rel="stylesheet" href="/index.css"></head><body><div id="root"></div><script>window.ASTRA_WORKSPACE=${JSON.stringify(origin)}</script><script type="module" src="/index.js"></script></body></html>`,{headers:{'Content-Type':'text/html; charset=utf-8'}});
}});
await mkdir(resolve(here,'.local'),{recursive:true});await Bun.write(resolve(here,'.local/connection.json'),JSON.stringify({url:`http://127.0.0.1:${server.port}/#${upstream.token}`,port:server.port}));console.log(`Skill Studio ready on port ${server.port}. Authenticated URL saved in .local/connection.json.`);
