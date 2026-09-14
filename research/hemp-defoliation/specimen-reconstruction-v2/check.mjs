import fs from 'node:fs';import assert from 'node:assert/strict';
const d=JSON.parse(fs.readFileSync(new URL('./specimen.json',import.meta.url))),h=d.root[1]-d.tip[1];let maxError=0;
for(const a of [...d.axes,...d.regions])for(const p of a.points){assert.ok(p[0]>=0&&p[0]<230&&p[1]>=0&&p[1]<434);const x=(p[0]-d.root[0])/h,z=(d.root[1]-p[1])/h;maxError=Math.max(maxError,Math.hypot(x*h+d.root[0]-p[0],d.root[1]-z*h-p[1]));}
for(const a of d.axes.filter(a=>a.parent)){const parent=d.axes.find(p=>p.id===a.parent);assert.ok(parent.points.some(p=>p.every((v,i)=>v===a.points[0][i])));}
assert.ok(maxError<1e-9);const r={coordinateRoundTripMaxPixels:maxError,attachmentCheck:'Declared branch paths start on parent path vertices',biologicalValidation:false,depthRecovered:false,physics:false};fs.writeFileSync(new URL('./checks.json',import.meta.url),JSON.stringify(r,null,2));console.log(r);
