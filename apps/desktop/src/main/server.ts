import { resolve, dirname, extname } from 'node:path';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash, randomBytes } from 'node:crypto';
import { Codex } from './codex';
import { listArtifacts, artifactPath } from './artifacts';

export async function startServer(options:{root?:string,dist?:string,port?:number}={}) {
 const root=resolve(options.root||process.env.ASTRAFACTORY_ROOT||resolve(import.meta.dir,'../../../..'));
 const stateDir=resolve(root,'apps/desktop/.local');await mkdir(stateDir,{recursive:true});
 const stateFile=resolve(stateDir,'workspace.json');
 let state:any={brief:'Design a custom keyed interface and teach a robot the insertion skill it is missing.',agents:[],reviews:[]};
 try{state=JSON.parse(await readFile(stateFile,'utf8'));}catch{}
 for(const a of state.agents){if(a.turnId){a.status='disconnected';a.turnId=null;}}
 const save=()=>writeFile(stateFile,JSON.stringify(state,null,2));
 const token=randomBytes(24).toString('hex');
 const codex=new Codex();const events:any[]=[];let sequence=0;const approvals=new Map<number,any>();
 const emit=(method:string,params:any)=>{events.push({id:++sequence,time:new Date().toISOString(),method,params});if(events.length>1500)events.shift();};
 codex.notifications=message=>{
  const p=message.params||{};const tid=p.threadId||p.thread?.id;
  if(tid&&!state.agents.some((a:any)=>a.id===tid))return;
  if(['account/updated','account/rateLimits/updated'].includes(message.method))return;
  emit(message.method,p);
  const agent=state.agents.find((a:any)=>a.id===tid);
  if(agent&&message.method==='turn/started'){agent.status='working';agent.turnId=p.turn.id;void save();}
  if(agent&&message.method==='turn/completed'){agent.status=p.turn.status;agent.turnId=null;void save();}
 };
 codex.approval=message=>{approvals.set(message.id,message);emit('approval/requested',{id:message.id,method:message.method,params:message.params});};
 const json=(data:any,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
 let account:any=null;let models:any[]=[];
 async function connect(){await codex.start();const a=await codex.request('account/read',{refreshToken:false});account=a.account?{type:a.account.type,planType:a.account.planType}:null;const m=await codex.request('model/list',{});models=m.data||[];return {connected:codex.ready,account,models};}
 async function readArtifact(path:string){const p=await artifactPath(root,path);const file=Bun.file(p);if(file.size>2_000_000)throw new Error('Use the viewer for large artifacts');return {path,sha256:createHash('sha256').update(await file.bytes()).digest('hex'),content:await file.text()};}
 async function review(body:any){if(!['accepted','changes_requested','note'].includes(body.verdict)||typeof body.note!=='string'||body.note.length>10000)throw new Error('Invalid review');const p=await artifactPath(root,body.path);const hash=createHash('sha256').update(await Bun.file(p).bytes()).digest('hex');const row={id:crypto.randomUUID(),path:body.path,sha256:hash,verdict:body.verdict,note:body.note,author:body.author||'Human',at:new Date().toISOString()};state.reviews.push(row);await save();emit('artifact/reviewed',row);return row;}
 async function mcp(request:any){
  const result=(value:any)=>json({jsonrpc:'2.0',id:request.id,result:value});
  if(request.id===undefined)return new Response(null,{status:202});
  if(request.method==='initialize')return result({protocolVersion:'2024-11-05',capabilities:{tools:{}},serverInfo:{name:'astrafactory',version:'0.1.0'}});
  if(request.method==='ping')return result({});
  const tools=[{name:'workspace_status',description:'Read project brief, engineering sessions and artifact reviews.',inputSchema:{type:'object',properties:{}}},{name:'list_artifacts',description:'List CAD, simulation recordings and reports in the project.',inputSchema:{type:'object',properties:{}}},{name:'read_artifact',description:'Read a small text artifact and its content hash.',inputSchema:{type:'object',properties:{path:{type:'string'}},required:['path']}},{name:'review_artifact',description:'Attach a review to the current exact artifact version.',inputSchema:{type:'object',properties:{path:{type:'string'},verdict:{type:'string',enum:['accepted','changes_requested','note']},note:{type:'string'},author:{type:'string'}},required:['path','verdict','note']}}];
  if(request.method==='tools/list')return result({tools});
  if(request.method==='tools/call'){
   try{const name=request.params.name;const args=request.params.arguments||{};const value=name==='workspace_status'?state:name==='list_artifacts'?await listArtifacts(root):name==='read_artifact'?await readArtifact(args.path):name==='review_artifact'?await review(args):(()=>{throw new Error('Unknown tool');})();return result({content:[{type:'text',text:JSON.stringify(value)}]});}catch(e){return result({isError:true,content:[{type:'text',text:String(e)}]});}
  }
  return json({jsonrpc:'2.0',id:request.id,error:{code:-32601,message:'Method not found'}});
 }
 const dist=resolve(options.dist||resolve(import.meta.dir,'../../dist'));
 const server=Bun.serve({hostname:'127.0.0.1',port:options.port||0,idleTimeout:60,async fetch(req){
  const url=new URL(req.url);const path=url.pathname;
  try{
   if(path.startsWith('/api/')||path==='/mcp'){
    const auth=req.headers.get('authorization');const queryToken=url.searchParams.get('token');
    if(auth!==`Bearer ${token}`&&!(req.method==='GET'&&queryToken===token))return json({error:'Unauthorized'},401);
    const origin=req.headers.get('origin');if(origin&&origin!==url.origin)return json({error:'Origin rejected'},403);
   }
   if(path==='/api/status'&&req.method==='GET')return json({root,connected:codex.ready,error:codex.error,account,models,state,approvals:[...approvals.values()]});
   if(path==='/api/connect'&&req.method==='POST')return json(await connect());
   if(path==='/api/events')return json(events.filter(e=>e.id>Number(url.searchParams.get('after')||0)));
   if(path==='/api/brief'&&req.method==='POST'){const body=await req.json();if(typeof body.text!=='string'||body.text.length>20000)throw new Error('Invalid brief');state.brief=body.text;await save();return json({ok:true});}
   if(path==='/api/agents'&&req.method==='POST'){
    const body=await req.json();if(typeof body.prompt!=='string'||!body.prompt.trim()||body.prompt.length>30000)throw new Error('Provide a task');
    await codex.start();const roles=['Lead engineer','Industrial design','Mechanical','Electrical','Sourcing','Robotics','Reviewer'];if(!roles.includes(body.role))throw new Error('Unknown role');
    const result=await codex.request('thread/start',{cwd:root,model:body.model||undefined,approvalPolicy:'on-request',sandbox:'workspace-write',developerInstructions:`You are the ${body.role} for AstraFactory. Work only on the assigned task. Respect other engineers' files. Publish inspectable artifacts and distinguish proposed, tested and completed work. Do not contact people or purchase resources. Project brief: ${state.brief}`,config:{'mcp_servers.astrafactory':{url:`http://127.0.0.1:${server.port}/mcp`,http_headers:{Authorization:`Bearer ${token}`}}}});
    const agent={id:result.thread.id,role:body.role,title:body.title||body.role,status:'starting',model:result.model,created:new Date().toISOString(),turnId:null};state.agents.push(agent);await save();
    await codex.request('thread/name/set',{threadId:agent.id,name:`AstraFactory · ${agent.title}`});
    const turn=await codex.request('turn/start',{threadId:agent.id,input:[{type:'text',text:body.prompt,text_elements:[]}]});agent.turnId=turn.turn.id;agent.status='working';await save();return json(agent);
   }
   if(path==='/api/thread'&&req.method==='GET'){const id=url.searchParams.get('id');if(!state.agents.some((a:any)=>a.id===id))throw new Error('Unknown project session');await codex.start();return json(await codex.request('thread/read',{threadId:id,includeTurns:true}));}
   if(path==='/api/message'&&req.method==='POST'){const b=await req.json();const a=state.agents.find((a:any)=>a.id===b.id);if(!a||typeof b.text!=='string'||!b.text.trim())throw new Error('Invalid message');await codex.start();if(a.turnId)return json(await codex.request('turn/steer',{threadId:a.id,expectedTurnId:a.turnId,input:[{type:'text',text:b.text,text_elements:[]}]}));await codex.request('thread/resume',{threadId:a.id,config:{'mcp_servers.astrafactory':{url:`http://127.0.0.1:${server.port}/mcp`,http_headers:{Authorization:`Bearer ${token}`}}}});return json(await codex.request('turn/start',{threadId:a.id,input:[{type:'text',text:b.text,text_elements:[]}]}));}
   if(path==='/api/interrupt'&&req.method==='POST'){const b=await req.json();const a=state.agents.find((a:any)=>a.id===b.id);if(!a?.turnId)throw new Error('No active turn');return json(await codex.request('turn/interrupt',{threadId:a.id,turnId:a.turnId}));}
   if(path==='/api/approval'&&req.method==='POST'){const b=await req.json();const a=approvals.get(b.id);if(!a)throw new Error('Unknown approval');let result:any;if(a.method==='mcpServer/elicitation/request'&&a.params?._meta?.codex_approval_kind==='mcp_tool_call'){result={action:b.accept?'accept':'decline',content:b.accept?{}:null,_meta:null};}else if(a.method.endsWith('/requestApproval')){result={decision:b.accept?'accept':'decline'};}else throw new Error('Unsupported interactive request');codex.send({id:a.id,result});approvals.delete(a.id);return json({ok:true});}
   if(path==='/api/artifacts')return json(await listArtifacts(root));
   if(path==='/api/artifact'){const p=await artifactPath(root,url.searchParams.get('path')||'');return new Response(Bun.file(p),{headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});}
   if(path==='/api/review'&&req.method==='POST')return json(await review(await req.json()));
   if(path==='/mcp'){if(req.method!=='POST')return new Response(null,{status:405});return mcp(await req.json());}
   if(path==='/index.js'||path==='/index.css')return new Response(Bun.file(resolve(dist,path.slice(1))));
   if(path==='/')return new Response('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AstraFactory</title><link rel="stylesheet" href="/index.css"></head><body><div id="root"></div><script type="module" src="/index.js"></script></body></html>',{headers:{'Content-Type':'text/html'}});
   return new Response('Not found',{status:404});
  }catch(e){return json({error:e instanceof Error?e.message:String(e)},400);}
 }});
 const url=`http://127.0.0.1:${server.port}/#${token}`;
 await writeFile(resolve(stateDir,'connection.json'),JSON.stringify({url,port:server.port,token,pid:process.pid}),{mode:0o600});
 return {server,codex,url,root,close(){server.stop();codex.close();}};
}
if(import.meta.main){const app=await startServer();console.log(`AstraFactory listening on 127.0.0.1:${app.server.port}`);process.on('SIGINT',()=>{app.close();process.exit();});}
