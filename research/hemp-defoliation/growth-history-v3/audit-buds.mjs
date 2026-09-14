// Lightweight audit of the existing model, not an inference or parameter search.
import {simulate} from './growth.mjs';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const history=simulate(),last=history.frames.at(-1);
const rows=last.buds.filter(b=>b.axis==='main').map(b=>{
 const child=last.axes.find(a=>a.id===b.id+'/shoot');
 return {bud:b.id,parentNode:b.node,initiated:b.born,activated:b.activatedAt??null,
  state:b.state,childNodes:child?.nodes.length??0,
  explanation:b.activationEligible?'Eligible under inherited scripted rank rule':'Held inactive by scripted rank rule'};
});
for(const row of rows)if(row.activated!==null)assert(row.activated>=row.initiated);
const report={units:'uncalibrated development units, not days',
 interpretation:'Existing model audit only. Does not establish when real lower buds form or grow.',
 finding:'Basal nodes 1–2 remain inactive by rule; eligible main-axis nodes 3–12 activate after fixed delay. Later nodes remain inactive. This spatial pattern is authored, not inferred from observations.',rows};
fs.writeFileSync(new URL('./bud-history-audit.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
