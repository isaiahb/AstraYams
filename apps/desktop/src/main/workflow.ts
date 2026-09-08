// One bounded revision -> independent re-test. A finished chat is not a passed test.
export class EngineeringLoop {
  locks = new Set<string>();
  constructor(private state:any, private deps:{save:()=>Promise<void>, hash:(path:string,projectId:string)=>Promise<string>, start:(body:any)=>Promise<any>}){}
  item(id:string,projectId:string){const w=this.state.workitems.find((w:any)=>w.id===id&&w.projectId===projectId);if(!w)throw new Error('Unknown work item');return w;}
  async exclusive(id:string,fn:()=>Promise<any>){if(this.locks.has(id))throw new Error('This handoff is already in progress');this.locks.add(id);try{return await fn();}finally{this.locks.delete(id);}}
  async assign(id:string,projectId:string,criteria:string){return this.exclusive(id,async()=>{
    const w=this.item(id,projectId);
    if(w.status!=='planned')throw new Error('This item has already been assigned');
    if(typeof criteria!=='string'||!criteria.trim()||criteria.length>12000)throw new Error('Define a reproducible re-test and acceptance criteria');
    if(w.sourcePath&&await this.deps.hash(w.sourcePath,projectId)!==w.sourceHash)throw new Error('Source evidence changed. Create a new proposal from the current version.');
    w.criteria=criteria;w.history=[];w.status='revising';w.assignmentKey=crypto.randomUUID();await this.record(w,'Revision requested');
    return this.launch(w,'revision');
  });}
  async record(w:any,event:string){w.history??=[];w.history.push({event,at:new Date().toISOString()});await this.deps.save();}
  async launch(w:any,phase:string){
    const revision=phase==='revision';
    const prompt=`Engineering work item ${w.id}: ${w.title}\n${w.detail}\nOriginal evidence: ${w.sourcePath||'none'}; SHA-256: ${w.sourceHash||'none'}\nFixed re-test and acceptance criteria:\n${w.criteria}\n${revision?'Produce a separate revision artifact, preserving the original files and evidence. Do not change the evaluator or acceptance criteria. Submit the actual revision with submit_revision, including a summary and exact instructions for an independent re-test. If blocked, use report_blocker.':`Independently re-test revision ${w.revision.path} (SHA-256 ${w.revision.sha256}). Revision summary: ${w.revision.summary}\nReproduction instructions: ${w.revision.instructions}\nRead the revision and run the specified checks. Publish a separate report with commands, assumptions, observed metrics and limitations. Call submit_test_result with pass, fail, or blocked. Pass requires observed evidence satisfying the fixed criteria; a render or completed chat is insufficient.`}\nStay within this bounded task. No purchases, external messages, paid GPU jobs, or modifying other engineers' work. Do not weaken checks to obtain a pass.`;
    try{
      const a=await this.deps.start({projectId:w.projectId,role:revision?({Brief:'Lead engineer',ID:'Industrial design',ME:'Mechanical',EE:'Electrical',SW:'Software',MFG:'Manufacturing',SIM:'Simulation'} as any)[w.owner]:'Simulation',title:`${revision?'Revise':'Re-test'} · ${w.title}`,prompt,workItemId:w.id,phase,assignmentKey:w.assignmentKey});
      if(revision)w.revisionAgentId=a.id;else w.testAgentId=a.id;
      await this.deps.save();return w;
    }catch(e){w.status='blocked';w.blocker=String(e);await this.record(w,`${phase} launch failed; no automatic retry`);throw e;}
  }
  authorized(id:string,projectId:string,key:string|undefined,phase:string){const w=this.item(id,projectId);if(!key||key!==w.assignmentKey||w.status!==(phase==='revision'?'revising':'retesting'))throw new Error('This session does not own the active handoff');return w;}
  async submitRevision(b:any,projectId:string,key?:string){return this.exclusive(b.id,async()=>{
    const w=this.authorized(b.id,projectId,key,'revision');
    if(w.revision)throw new Error('A revision has already been submitted');
    if(typeof b.summary!=='string'||!b.summary.trim()||typeof b.instructions!=='string'||!b.instructions.trim()||b.path===w.sourcePath)throw new Error('Provide a separate revision, summary and re-test instructions');
    const sha256=await this.deps.hash(b.path,projectId);
    w.revision={path:b.path,sha256,summary:b.summary.slice(0,12000),instructions:b.instructions.slice(0,12000)};
    await this.record(w,'Revision submitted; waiting for engineer to finish');return w;
  });}
  async submitResult(b:any,projectId:string,key?:string){return this.exclusive(b.id,async()=>{
    const w=this.authorized(b.id,projectId,key,'test');
    if(w.result)throw new Error('A result has already been submitted');
    if(!['pass','fail','blocked'].includes(b.outcome)||typeof b.summary!=='string'||!b.summary.trim()||b.path===w.revision.path||b.path===w.sourcePath)throw new Error('Provide a separate evidence report, outcome and summary');
    if(await this.deps.hash(w.revision.path,projectId)!==w.revision.sha256)throw new Error('Revision changed during the re-test');
    const sha256=await this.deps.hash(b.path,projectId);
    w.result={path:b.path,sha256,outcome:b.outcome,summary:b.summary.slice(0,12000)};
    await this.record(w,'Re-test report submitted; waiting for tester to finish');return w;
  });}
  async block(b:any,projectId:string,key?:string){const w=this.item(b.id,projectId);if(!key||key!==w.assignmentKey||!['revising','retesting'].includes(w.status)||typeof b.reason!=='string'||!b.reason.trim())throw new Error('Invalid blocker');w.status='blocked';w.blocker=b.reason.slice(0,12000);await this.record(w,'Engineer reported a blocker');return w;}
  async completed(agent:any,turnStatus:string){
    if(!agent.workItemId)return;
    while(this.locks.has(agent.workItemId))await new Promise(r=>setTimeout(r,10));
    return this.exclusive(agent.workItemId,async()=>{
      const w=this.item(agent.workItemId,agent.projectId);
      if(!['revising','retesting'].includes(w.status)||agent.assignmentKey!==w.assignmentKey)return;
      try{
        if(w.sourcePath&&await this.deps.hash(w.sourcePath,w.projectId)!==w.sourceHash)throw new Error('Original evidence changed during this cycle');
        if(turnStatus!=='completed')throw new Error(`Session ended with ${turnStatus}; automatic handoff stopped`);
        if(agent.phase==='revision'){
          if(!w.revision)throw new Error('Engineer finished without submitting a revision');
          if(await this.deps.hash(w.revision.path,w.projectId)!==w.revision.sha256)throw new Error('Submitted revision changed before handoff');
          w.status='retesting';w.assignmentKey=crypto.randomUUID();await this.record(w,'Revision handed to independent re-test');await this.launch(w,'test');
        }else{
          if(!w.result)throw new Error('Tester finished without an evidence report');
          if(await this.deps.hash(w.result.path,w.projectId)!==w.result.sha256||await this.deps.hash(w.revision.path,w.projectId)!==w.revision.sha256)throw new Error('Evidence changed before re-test completion');
          w.status=w.result.outcome==='pass'?'passed':w.result.outcome==='fail'?'needs_revision':'blocked';
          await this.record(w,`Re-test ${w.result.outcome}; bounded cycle finished`);
        }
      }catch(e){w.status='blocked';w.blocker=String(e);await this.record(w,'Automatic handoff stopped');}
    });
  }
}
