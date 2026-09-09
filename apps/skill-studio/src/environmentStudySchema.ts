export type StudySource = {
  id:string; title:string; feature:string; publisher:string; url:string;
  image_path?:string; model_path?:string; observation:string; application:string; boundary:string; credit:string;
};
export type StudyRevision = {
  id:string; title:string; disposition:'kept'|'rejected'|'under-review';
  observation:string; decision:string; change:string; evidence:string;
  source_ids:string[]; before_path?:string; after_path?:string; artifact_path?:string;
};
export type StudyExperiment = {
  id:string; title:string; question:string; method:string; outcome:'passed-diagnostic'|'failed'|'pending';
  path?:string; replay_path?:string; poster_path?:string; result_path?:string; control_path?:string;
  metrics:{label:string;value:string}[]; finding:string; limitation:string;
};
export type EnvironmentStudy = {
  schema_version:1; title:string; provenance:'recorded'|'current-run';
  status:string; scope:string; objective:string; updated_at?:string;
  preview_path?:string; checkpoint?:{label:string;sha256?:string;report_path?:string};
  sources:StudySource[]; revisions:StudyRevision[]; experiments:StudyExperiment[];
  assumptions:{subject:string;basis:'observed'|'inferred'|'assumed'|'measured';value:string;consequence:string}[];
  next_steps:string[];
};

// Validate at the publication boundary. A malformed update must not erase the
// last inspectable record, or turn an absent result into a passing test.
export function readEnvironmentStudy(data:unknown):EnvironmentStudy {
  const d=data as EnvironmentStudy;
  const fail=(message:string):never=>{throw new Error('Invalid research record: '+message);};
  const str=(v:unknown)=>typeof v==='string'&&v.trim().length>0;
  if(!d||d.schema_version!==1)fail('unsupported schema version');
  if(!['recorded','current-run'].includes(d.provenance))fail('missing provenance');
  for(const k of ['title','status','scope','objective'] as const)if(!str(d[k]))fail('missing '+k);
  for(const k of ['sources','revisions','experiments','assumptions','next_steps'] as const)if(!Array.isArray(d[k]))fail('missing '+k);
  const paths=(row:object)=>{for(const [key,value] of Object.entries(row)){
    if((key==='path'||key.endsWith('_path'))&&value!==undefined&&(!str(value)||typeof value!=='string'||value.startsWith('/')||value.split('/').includes('..')||/^[a-z]+:/i.test(value)))fail('artifact paths must be repository-relative strings');
  }};
  paths(d);
  if(d.checkpoint){
    if(!str(d.checkpoint.label))fail('checkpoint label');
    if(d.checkpoint.sha256!==undefined&&!/^[a-f0-9]{64}$/.test(d.checkpoint.sha256))fail('checkpoint hash');
    paths(d.checkpoint);
  }
  for(const rows of [d.sources,d.revisions,d.experiments]){
    const ids=new Set<string>();
    for(const row of rows){if(!row||!str(row.id)||ids.has(row.id)||!str(row.title))fail('invalid or duplicate record');ids.add(row.id);paths(row);}
  }
  for(const s of d.sources){
    for(const k of ['feature','publisher','observation','application','boundary','credit'] as const)if(!str(s[k]))fail('incomplete source '+s.id);
    try{if(!['https:','http:'].includes(new URL(s.url).protocol))fail('source URL');}catch{fail('source URL');}
  }
  for(const r of d.revisions){
    if(!['kept','rejected','under-review'].includes(r.disposition))fail('revision disposition');
    for(const k of ['observation','decision','change','evidence'] as const)if(!str(r[k]))fail('incomplete revision '+r.id);
    if(!Array.isArray(r.source_ids)||r.source_ids.some(id=>!d.sources.some(s=>s.id===id)))fail('unknown source reference');
  }
  for(const e of d.experiments){
    if(!['passed-diagnostic','failed','pending'].includes(e.outcome)||!Array.isArray(e.metrics))fail('experiment outcome');
    for(const k of ['question','method','finding','limitation'] as const)if(!str(e[k]))fail('incomplete experiment '+e.id);
    if(e.outcome!=='pending'&&!str(e.result_path))fail('test outcome without a result artifact');
    if(e.metrics.some(m=>!str(m.label)||!str(m.value)))fail('invalid metric');
  }
  for(const a of d.assumptions)if(!['observed','inferred','assumed','measured'].includes(a.basis)||![a.subject,a.value,a.consequence].every(str))fail('invalid assumption');
  if(!d.next_steps.every(str))fail('invalid next steps');
  return d;
}
