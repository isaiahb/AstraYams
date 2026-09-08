import {test,expect} from 'bun:test';
import {mkdtemp,mkdir,writeFile,symlink,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {startServer} from '../src/main/server';
test('workspace auth, artifact boundary, MCP and exact-version reviews',async()=>{
 const root=await mkdtemp(join(tmpdir(),'astrafactory-test-'));
 await mkdir(join(root,'docs'));await writeFile(join(root,'docs/test.md'),'evidence');
 await writeFile(join(root,'private.md'),'private');await symlink(join(root,'private.md'),join(root,'docs/escape.md'));
 const app=await startServer({root});const base=app.url.split('/#')[0];const token=app.url.split('#')[1];
 const call=(path:string,body?:any)=>fetch(base+path,{method:body?'POST':'GET',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
 try{
  expect((await fetch(base+'/api/status')).status).toBe(401);
  expect((await call('/api/artifact?path=docs/escape.md')).status).toBe(400);
  expect((await call('/api/artifact?path=docs/../private.md')).status).toBe(400);
  const r=await(await call('/api/review',{path:'docs/test.md',verdict:'accepted',note:'Checked'})).json();expect(r.sha256).toBe(createHash('sha256').update('evidence').digest('hex'));
  await writeFile(join(root,'docs/test.md'),'changed');const s=await(await call('/api/status')).json();expect(s.state.reviews[0].sha256).toBe(r.sha256);
  const m=await(await call('/mcp',{jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'list_artifacts',arguments:{}}})).json();expect(JSON.parse(m.result.content[0].text).map((a:any)=>a.path)).toEqual(['docs/test.md']);
 }finally{app.close();await rm(root,{recursive:true,force:true});}
});

test('projects isolate artifacts and persist version-linked engineering feedback',async()=>{
 const root=await mkdtemp(join(tmpdir(),'astrafactory-projects-'));
 await mkdir(join(root,'docs'));await writeFile(join(root,'docs/legacy.md'),'legacy');
 let app=await startServer({root});
 const call=async(path:string,body?:any)=>fetch(app.url.split('/#')[0]+path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+app.url.split('#')[1],'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
 try{
  const p=await(await call('/api/projects',{title:'Fixture',brief:'Design a robot-assembled fixture.'})).json();
  const path=p.prefixes[0]+'BRIEF.md';
  expect((await(await call('/api/artifacts?projectId='+p.id)).json()).map((a:any)=>a.path)).toEqual([path]);
  expect((await call('/api/artifact?projectId='+p.id+'&path=docs/legacy.md')).status).toBe(400);
  await symlink(join(root,'docs/legacy.md'),join(p.directory,'alias.md'));
  expect((await call('/api/artifact?projectId='+p.id+'&path='+p.prefixes[0]+'alias.md')).status).toBe(400);
  const meta=await(await call('/api/publish',{projectId:p.id,path,owner:'ME',stage:'Research'})).json();
  expect(meta.registeredHash).toHaveLength(64);
  expect((await call('/api/publish',{projectId:p.id,path,owner:'ME',stage:'Schematic'})).status).toBe(400);
  const item=await(await call('/api/workitems',{projectId:p.id,kind:'change',owner:'EE',title:'Check power budget',detail:'Resolve peak power before selecting the supply.',sourcePath:path})).json();
  expect(item.sourceHash).toBe(meta.registeredHash);
  await writeFile(join(p.directory,'BRIEF.md'),'revised');
  expect((await call('/api/review',{projectId:p.id,path,verdict:'accepted',note:'stale review',expectedHash:meta.registeredHash})).status).toBe(400);
  const m=await(await call('/mcp?projectId='+p.id,{jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'read_artifact',arguments:{path:'docs/legacy.md',projectId:'robot-arm'}}})).json();
  expect(m.result.isError).toBe(true);
  app.close();app=await startServer({root});
  const state=(await(await call('/api/status')).json()).state;
  expect(state.projects.find((x:any)=>x.id===p.id).title).toBe('Fixture');
  expect(state.workitems[0].sourceHash).toBe(meta.registeredHash);
  expect((await(await call('/api/artifact-info?projectId='+p.id+'&path='+path)).json()).sha256).not.toBe(meta.registeredHash);
 }finally{app.close();await rm(root,{recursive:true,force:true});}
});
