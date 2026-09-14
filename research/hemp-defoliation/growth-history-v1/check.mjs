import {simulate} from './growth.mjs';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const sim=simulate();let priorNodes=new Map(),maxError=0;
for(const frame of sim.frames){const by=new Map(frame.axes.map(a=>[a.id,a]));
 const ids=new Set();for(const axis of frame.axes){assert(!ids.has(axis.id));ids.add(axis.id);
  assert(axis.born<=frame.time+1e-8);
  if(axis.parent){const parent=by.get(axis.parent);assert(parent);const p=parent.points[axis.parentNode];const err=Math.hypot(...p.map((x,i)=>x-axis.points[0][i]));maxError=Math.max(maxError,err);assert(err<1e-10)}
  for(const node of axis.nodes){assert(node.born<=frame.time+1e-8);if(priorNodes.has(node.id))assert(node.length+1e-10>=priorNodes.get(node.id));priorNodes.set(node.id,node.length)}
  for(const p of axis.points)assert(p.every(Number.isFinite));
 }
 for(const l of frame.leaves){const axis=by.get(l.axis);assert(axis);const err=Math.hypot(...l.at.map((x,i)=>x-axis.points[l.node][i]));maxError=Math.max(maxError,err);assert(err<1e-10);assert(l.born<frame.time);assert(l.length<=.115+1e-10)}
}
const end=sim.frames.at(-1),early=sim.frames.find(f=>f.time===7),half=simulate({step:.05}).frames.at(-1);
assert.equal(end.metrics.nodes,half.metrics.nodes);assert.equal(end.metrics.leaves,half.metrics.leaves);
const stepError=Math.max(...['skeletonWidth','skeletonDepth','height'].map(k=>Math.abs(end.metrics[k]-half.metrics[k])));
assert(stepError<.002,'Halving timestep changes skeleton dimensions by more than 2 mm');
assert(early.metrics.leaves<end.metrics.leaves);assert(end.metrics.shoots>10);
// A planar reconstruction should fail this scenario-specific smoke check.
assert(end.metrics.skeletonDepth>.25&&end.metrics.skeletonWidth>.25);
const off=simulate({branchResponse:0}).frames.at(-1);
assert(Math.abs(off.metrics.height-end.metrics.height)>.001||Math.abs(off.metrics.skeletonWidth-end.metrics.skeletonWidth)>.001);
assert.deepEqual(sim,simulate());
const report={status:'implementation checks passed; biological accuracy is unvalidated',
 frames:sim.frames.length,events:sim.events.length,maxAttachmentErrorM:maxError,maxHalfStepDimensionDifferenceM:stepError,
 finalMetrics:end.metrics,earlyMetrics:early.metrics,
 halfStepFinalMetrics:half.metrics,responseDisabledFinalMetrics:off.metrics,
 checked:['stable node identity and monotone segment extension','child and petiole attachment','finite coordinates','birth precedes appearance','deterministic replay','non-planar study geometry','direction-response ablation changes morphology'],
 notChecked:['biological growth rates','cultivar fit','self-collision','elastic bending','live tissue stiffness','light competition','root physiology']};
fs.writeFileSync(new URL('./checks.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
