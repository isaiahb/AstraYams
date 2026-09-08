import {resolve} from 'node:path';
import {mkdir} from 'node:fs/promises';
import {listSkills,saveSkill,archiveSkills} from './catalog';
const here=import.meta.dir;
const upstream=await Bun.file(resolve(here,'../desktop/.local/connection.json')).json();
const origin=new URL(upstream.url).origin;
const server=Bun.serve({hostname:'127.0.0.1',port:Number(process.env.PORT||0),async fetch(req){
 const u=new URL(req.url);
 if(u.pathname==='/studio-api/archive'&&req.method==='POST'){if(req.headers.get('authorization')!=='Bearer '+upstream.token)return Response.json({error:'Unauthorized'},{status:401});try{const b=await req.json();return Response.json(await archiveSkills(here,b.ids,b.archived!==false));}catch{return Response.json({error:'Unable to update archive'},{status:400});}}
 if(u.pathname==='/studio-api/skills'){if(req.headers.get('authorization')!=='Bearer '+upstream.token)return Response.json({error:'Unauthorized'},{status:401});try{if(req.method==='GET')return Response.json(await listSkills(here));if(req.method==='POST')return Response.json(await saveSkill(here,await req.json()));return new Response('Method not allowed',{status:405});}catch{return Response.json({error:'Unable to save skill'},{status:400});}}
 if(u.pathname.startsWith('/api/'))return fetch(origin+u.pathname+u.search,{method:req.method,headers:req.headers,body:['GET','HEAD'].includes(req.method)?undefined:req.body,redirect:'manual'});
 if(u.pathname==='/index.js'||u.pathname==='/index.css')return new Response(Bun.file(resolve(here,'dist',u.pathname.slice(1))));
 if(u.pathname!=='/')return new Response('Not found',{status:404});
 return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Astra — Skill Studio</title><link rel="stylesheet" href="/index.css"></head><body><div id="root"></div><script>window.ASTRA_WORKSPACE=${JSON.stringify(origin)}</script><script type="module" src="/index.js"></script></body></html>`,{headers:{'Content-Type':'text/html; charset=utf-8'}});
}});
await mkdir(resolve(here,'.local'),{recursive:true});await Bun.write(resolve(here,'.local/connection.json'),JSON.stringify({url:`http://127.0.0.1:${server.port}/#${upstream.token}`,port:server.port}));console.log(`Skill Studio ready on port ${server.port}. Authenticated URL saved in .local/connection.json.`);
