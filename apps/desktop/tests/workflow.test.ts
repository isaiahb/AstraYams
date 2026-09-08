import {test,expect} from 'bun:test';
import {EngineeringLoop} from '../src/main/workflow';
function fixture(){
 const w:any={id:'w',projectId:'p',owner:'ME',title:'Improve fixture',detail:'Preserve the envelope',status:'planned',sourcePath:'source.md',sourceHash:'original'};
 const hashes:Record<string,string>={'source.md':'original','revision.md':'revision','report.md':'report'};
 const agents:any[]=[];
 const loop=new EngineeringLoop({workitems:[w]},{save:async()=>{},hash:async p=>{if(!hashes[p])throw new Error('Missing artifact');return hashes[p];},start:async b=>{const a={...b,id:'agent-'+agents.length};agents.push(a);return a;}});
 return {w,hashes,agents,loop};
}
async function revision(f:ReturnType<typeof fixture>){await f.loop.assign('w','p','Run the fixed clearance check; clearance must be >= 2 mm.');await f.loop.submitRevision({id:'w',path:'revision.md',summary:'Separate geometry revision',instructions:'Run the fixed check'},'p',f.w.assignmentKey);}
test('automatic revision-to-test handoff waits for submitted evidence and a completed turn',async()=>{
 const f=fixture();await revision(f);
 expect(f.w.status).toBe('revising');expect(f.agents).toHaveLength(1);
 await f.loop.completed(f.agents[0],'completed');expect(f.w.status).toBe('retesting');expect(f.agents).toHaveLength(2);
 expect(f.agents[1].role).toBe('Simulation');expect(f.agents[1].prompt).toContain('clearance must be >= 2 mm');
 await expect(f.loop.submitResult({id:'w',path:'report.md',outcome:'pass',summary:'Measured 3 mm'},'p',f.agents[0].assignmentKey)).rejects.toThrow('does not own');
 await f.loop.submitResult({id:'w',path:'report.md',outcome:'pass',summary:'Measured 3 mm'},'p',f.w.assignmentKey);
 expect(f.w.status).toBe('retesting');await f.loop.completed(f.agents[1],'completed');expect(f.w.status).toBe('passed');
 await f.loop.completed(f.agents[0],'completed');expect(f.agents).toHaveLength(2);
});
test('completed chats without evidence and interrupted turns cannot pass',async()=>{
 for(const status of ['completed','interrupted','failed']){const f=fixture();await f.loop.assign('w','p','Fixed check');await f.loop.completed(f.agents[0],status);expect(f.w.status).toBe('blocked');expect(f.agents).toHaveLength(1);}
});
test('stale evidence, invalid ownership and duplicate starts are rejected',async()=>{
 const f=fixture();f.hashes['source.md']='changed';await expect(f.loop.assign('w','p','Fixed check')).rejects.toThrow('changed');expect(f.agents).toHaveLength(0);
 f.hashes['source.md']='original';await f.loop.assign('w','p','Fixed check');
 await expect(f.loop.assign('w','p','Different criteria')).rejects.toThrow('already');
 await expect(f.loop.submitRevision({id:'w',path:'revision.md',summary:'x',instructions:'y'},'other',f.w.assignmentKey)).rejects.toThrow('Unknown');
 expect(f.w.criteria).toBe('Fixed check');
});
test('mutated revision or test evidence stops automatic completion',async()=>{
 const f=fixture();await revision(f);f.hashes['revision.md']='mutated';await f.loop.completed(f.agents[0],'completed');expect(f.w.status).toBe('blocked');expect(f.agents).toHaveLength(1);
 const g=fixture();await revision(g);await g.loop.completed(g.agents[0],'completed');await g.loop.submitResult({id:'w',path:'report.md',outcome:'pass',summary:'Observed result'},'p',g.w.assignmentKey);g.hashes['report.md']='mutated';await g.loop.completed(g.agents[1],'completed');expect(g.w.status).toBe('blocked');
});
test('failed re-test ends the cycle without silently changing criteria or retrying',async()=>{
 const f=fixture();await revision(f);await f.loop.completed(f.agents[0],'completed');await f.loop.submitResult({id:'w',path:'report.md',outcome:'fail',summary:'Measured 1 mm'},'p',f.w.assignmentKey);await f.loop.completed(f.agents[1],'completed');expect(f.w.status).toBe('needs_revision');expect(f.agents).toHaveLength(2);expect(f.w.result.sha256).toBe('report');
});
test('explicit retry retains criteria and prior evidence and cannot accept stale-session submissions',async()=>{
 const f=fixture();await f.loop.assign('w','p','Frozen check');const oldKey=f.w.assignmentKey;
 await f.loop.block({id:'w',reason:'Instruction conflict'},'p',oldKey);
 await f.loop.retry('w','p');expect(f.w.criteria).toBe('Frozen check');expect(f.w.attempts[0].blocker).toBe('Instruction conflict');expect(f.w.sourceHash).toBe('original');expect(f.agents).toHaveLength(2);
 await expect(f.loop.submitRevision({id:'w',path:'revision.md',summary:'x',instructions:'y'},'p',oldKey)).rejects.toThrow('does not own');
});
