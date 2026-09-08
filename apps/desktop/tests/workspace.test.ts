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
