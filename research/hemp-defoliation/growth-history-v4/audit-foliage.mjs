// Inventory the model's connected organs. Counts are not projected coverage or leaf area.
import {simulate} from './growth.mjs';
import fs from 'node:fs';
function inventory(mode){const frame=simulate({activationMode:mode}).frames.at(-1),axes=new Map(frame.axes.map(a=>[a.id,a])),height=frame.axes[0].points.at(-1)[2];
 const bins=Array.from({length:5},(_,i)=>({heightFraction:[i/5,(i+1)/5],mainAxisLeaves:0,lateralLeaves:0}));
 const origins={};
 for(const leaf of frame.leaves.filter(l=>l.kind==='leaf')){const index=Math.max(0,Math.min(4,Math.floor(leaf.junction[2]/height*5)));bins[index][leaf.axis==='main'?'mainAxisLeaves':'lateralLeaves']++;
 let axis=axes.get(leaf.axis);if(axis.parent){while(axes.get(axis.parent)?.parent)axis=axes.get(axis.parent);const key=axis.parentNode;origins[key]=(origins[key]??0)+1;}}
 return {mode,height_m:height,bins,leavesByMainAxisBranchOrigin:origins,totalLeaves:frame.metrics.leaves};}
const report={meaning:'Leaf junction counts by height and branch ancestry. Not silhouette coverage, leaf area, observed data, or a biological forecast.',finding:'The legacy scenario excludes main-axis nodes 1 and 2 from branch activation; the unresolved preset forecasts no branches. Both can produce sparse basal foliage for modeling reasons alone.',next:'Fit visible lower-branch topology and projected foliage coverage to a suitable pre-removal reference; do not infer activation dates from one image.',presets:['unresolved','legacy-scenario'].map(inventory)};
for(const p of report.presets){if(p.bins.reduce((n,b)=>n+b.mainAxisLeaves+b.lateralLeaves,0)!==p.totalLeaves)throw Error('Inventory does not conserve leaf count');}
fs.writeFileSync(new URL('./foliage-inventory.json',import.meta.url),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
