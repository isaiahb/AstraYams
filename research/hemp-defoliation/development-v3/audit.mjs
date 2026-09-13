import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {makePlant,snapshot,defaultSpecs} from './plant.mjs';
const dir=path.dirname(fileURLToPath(import.meta.url));const data=JSON.parse(fs.readFileSync(path.join(dir,'reference-data.json')));
const cases=defaultSpecs();for(let f=0;f<4;f++)for(const extreme of [.65,1.3])cases.push({family:f,seed:713+f,curve:f,height:extreme===.65?.75:1.25,spread:extreme,density:extreme,leafWidth:extreme===.65?.7:1.25});
const dist=(a,b)=>Math.hypot(...a.map((x,i)=>x-b[i]));let reports=[];let maxAttachment=0,maxBackwardGrowth=0;
for(const [index,options]of cases.entries()){
 const p=makePlant(data,options),again=makePlant(data,options);if(JSON.stringify(p.axes)!==JSON.stringify(again.axes)||JSON.stringify(p.leaves)!==JSON.stringify(again.leaves))throw Error('Unstable seed');
 if(new Set(p.axes.map(a=>a.id)).size!==p.axes.length||new Set(p.leaves.map(l=>l.id)).size!==p.leaves.length)throw Error('Duplicate organs');
 const desc=new Map(p.axes.map(a=>[a.id,a]));let prev;let prevHeight=0,final,early;
 for(let day=31;day<=114;day++){
  const s=snapshot(p,day),lookup=new Map(s.axes.map(a=>[a.id,a]));
  if(s.metrics.height+1e-8<prevHeight)throw Error('Backward height growth');prevHeight=s.metrics.height;
  for(const a of s.axes){if(!a.points.flat().every(Number.isFinite)||!a.radii.every(x=>Number.isFinite(x)&&x>=0))throw Error('Nonfinite state');const d=desc.get(a.id);
   if(d.parent)maxAttachment=Math.max(maxAttachment,dist(a.points[0],lookup.get(d.parent).points[d.parent_node]));
   for(let j=0;j<a.points.length-1;j++)if(prev){const old=prev.get(a.id);const backwards=dist(old.points[j+1],old.points[j])-dist(a.points[j+1],a.points[j]);maxBackwardGrowth=Math.max(maxBackwardGrowth,backwards);}
  }
  const ld=new Map(p.leaves.map(l=>[l.id,l]));for(const l of s.leaves){const d=ld.get(l.id);maxAttachment=Math.max(maxAttachment,dist(l.at,lookup.get(d.axis).points[d.node]));}
  prev=lookup;if(day===31)early=s.metrics;if(day===114)final=s.metrics;
 }
 const nAt={};for(const a of p.axes.filter(a=>a.parent==='main'))nAt[a.parent_node]=(nAt[a.parent_node]||0)+1;
 if(Math.max(...Object.values(nAt))>2)throw Error('More than two primary lateral shoots at a main node');
 reports.push({index,options,axes:p.axes.length,leaves:p.leaves.length,early,final});
}
if(maxAttachment>1e-8||maxBackwardGrowth>1e-8)throw Error('Attachment or monotonic extension failure');
const signatures=reports.slice(0,8).map(x=>[x.axes,x.leaves,x.final.height.toFixed(4),x.final.width.toFixed(4)].join('/'));if(new Set(signatures).size!==8)throw Error('Default specimens not distinct');
const hash=f=>crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,f))).digest('hex');
const report={status:'Generator invariants passed; no biological or physical validation claimed',case_count:cases.length,states_checked:cases.length*84,deterministic:true,persistent_unique_ids:true,max_attachment_error_m:maxAttachment,max_internode_shrinkage_m:maxBackwardGrowth,distinct_default_scaffolds:8,assumed_parent_topology:true,growth_physically_validated:false,commercial_distribution_fitted:false,geometry_hash:hash('plant.mjs'),viewer_hash:hash('viewer.js'),reference_hash:hash('reference-data.json'),cases:reports};
fs.writeFileSync(path.join(dir,'evidence/audit.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({...report,cases:reports.slice(0,8).map(x=>({i:x.index,axes:x.axes,leaves:x.leaves,height:x.final.height,width:x.final.width}))},null,2));
