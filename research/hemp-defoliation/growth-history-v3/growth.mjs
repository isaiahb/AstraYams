// Organ-scale developmental hypothesis. Lengths in metres; time in uncalibrated
// development units. No photosynthesis, live-tissue elasticity or contact solver.
export const defaults=Object.freeze({duration:34,step:.1,mainInterval:1.55,lateralInterval:1.9,
  expansion:4.2,budDelay:5.2,transitionNode:6,alternateAngle:145,
  mainNodes:18,lateralNodes:6,secondaryNodes:3,branchResponse:.22});
export const clamp=x=>Math.max(0,Math.min(1,x));
export const smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
export const add=(a,b)=>a.map((v,i)=>v+b[i]),mul=(a,s)=>a.map(v=>v*s);
export const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
export const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
export const unit=a=>mul(a,1/Math.max(1e-12,Math.hypot(...a)));
function localFrame(tangent){const t=unit(tangent),k=1/Math.max(1e-8,1+t[2]);
 // Minimal rotation from +Z transports +X continuously for our upward shoots.
 // Avoid reference-axis switching that would suddenly spin attached leaves.
 const u=unit([1-t[0]*t[0]*k,-t[0]*t[1]*k,-t[0]]);return [u,cross(t,u)]}
function radial(tangent,phi){const [u,v]=localFrame(tangent);return add(mul(u,Math.cos(phi)),mul(v,Math.sin(phi)))}

export function simulate(overrides={}){
 const cfg={...defaults,...overrides},axes=[],leaves=[],buds=[],events=[],frames=[];
 function event(time,type,id,parent){events.push({time:+time.toFixed(3),type,id,parent})}
 function makeAxis(id,parent,parentNode,order,born,heading,phase=0){const a={id,parent,parentNode,order,born,heading:unit(heading),phase,nodes:[],next:born+(order===0?2.5:.65)};axes.push(a);event(born,'shoot initiated',id,parent);return a}
 makeAxis('main',null,null,0,0,[0,0,1]);
 const cotyledons=[0,1].map(i=>({id:`cotyledon-${i}`,kind:'cotyledon',axis:'main',node:0,phi:i*Math.PI,born:.35,length:.026,leaflets:1}));
 leaves.push(...cotyledons);
 const lookup=()=>new Map(axes.map(a=>[a.id,a]));
 function newNode(a,time){const n=a.nodes.length+1;
  const paired=a.order===0?n<cfg.transitionNode:n<=2;
  const phase=paired?(n-1)*Math.PI/2:a.order===0?(cfg.transitionNode-2)*Math.PI/2+(n-cfg.transitionNode+1)*cfg.alternateAngle*Math.PI/180:(n-2)*cfg.alternateAngle*Math.PI/180;
  const maxLength=a.order===0?(.027+.030*smooth((n-1)/4)):(a.order===1?.052:.033);
  const prev=a.nodes.at(-1)?.dir??a.heading;
  // New segments inherit the axis direction, never a camera-facing direction.
  const node={id:`${a.id}/node-${n}`,rank:n,born:time,length:0,maxLength,
    radius:0,dir:[...prev],phase:a.phase+phase};a.nodes.push(node);
  event(time,'node initiated',node.id,a.id);
  for(let side=0;side<(paired?2:1);side++){
   const phi=node.phase+side*Math.PI;
   const count=a.order===0?(n===1?1:n===2?3:n===3?5:7):(n===1?3:5);
   const length=(a.order===0?.115:a.order===1?.097:.066)*(a.order===0?(n===1?.38:n===2?.64:n===3?.86:1):1);
   const l={id:`${node.id}/leaf-${side}`,kind:'leaf',axis:a.id,node:n,phi,born:time+.15,length,leaflets:count};
   leaves.push(l);event(l.born,'leaf initiated',l.id,node.id);
   // Bud identity is tied to its subtending leaf. Limits define this study's
   // finite vegetative scope; they are scenario priors, not measured physiology.
   {
    const activationEligible=(a.order===0&&n>=3&&n<=12 || a.order===1&&n===3&&side===0);
    buds.push({id:`${node.id}/bud-${side}`,axis:a.id,node:n,phi,leaf:l.id,
      born:time,activationEligible,state:'dormant',delay:cfg.budDelay+(a.order===1?3:0),active:false});
   }
  }
 }
 function snapshot(time){const by=lookup(),states=[],nodePos=new Map();
  const hypocotyl=.035*smooth(time/2);
  for(const a of axes){
   const start=a.parent?nodePos.get(`${a.parent}:${a.parentNode}`):[0,0,hypocotyl];
   const points=[[...start]],radii=[];
   for(const n of a.nodes){points.push(add(points.at(-1),mul(n.dir,n.length)));radii.push(n.radius);nodePos.set(`${a.id}:${n.rank}`,points.at(-1))}
   nodePos.set(`${a.id}:0`,start);
   const boundaryRadii=radii.length?[radii[0],...radii.slice(1).map((r,i)=>(r+radii[i])*.5),radii.at(-1)*.78]:[];
   states.push({boundaryRadii,id:a.id,parent:a.parent,parentNode:a.parentNode,order:a.order,born:a.born,points,radii,
     nodes:a.nodes.map(n=>({id:n.id,born:n.born,length:n.length,age:time-n.born}))});
  }
  const organs=[];
  for(const l of leaves){const age=time-l.born;if(age<=1e-8)continue;const a=by.get(l.axis),n=a.nodes[l.node-1];
   const expansion=smooth(age/cfg.expansion),at=nodePos.get(`${l.axis}:${l.node}`);
   const tangent=n?.dir??[0,0,1],r=radial(tangent,l.phi);
   // Petiole grows from its node. Young leaves unfold toward their local
   // outward direction. Rest pose is kinematic, not a weight-response result.
   const pitch=.65*(1-expansion)+.08;
   const direction=unit(add(mul(r,Math.cos(pitch)),mul(tangent,Math.sin(pitch))));
   const len=l.length*expansion,petiole=(l.kind==='cotyledon'?.003:.40*len);
   const junction=add(at,mul(direction,petiole));
   const opacity=l.kind==='cotyledon'?1-smooth((time-7)/5):1;
   if(opacity<.03)continue;
   organs.push({...l,age,expansion,length:len,at:[...at],junction,direction,
     normal:unit(add(tangent,mul(direction,-dot(tangent,direction)))),opacity});
  }
  const all=states.flatMap(a=>a.points),ranges=[0,1,2].map(i=>[Math.min(...all.map(p=>p[i])),Math.max(...all.map(p=>p[i]))]);
  const neckRadius=states[0].boundaryRadii[0]??.0007;
  const hypocotylRadii=[Math.max(neckRadius,.0012+.0031*smooth(time/20)),neckRadius];
  const budStates=buds.map(b=>{const a=by.get(b.axis),node=a.nodes[b.node-1],at=nodePos.get(`${b.axis}:${b.node}`);
   return {...b,at:[...at],direction:radial(node.dir,b.phi),statusBasis:'scenario activation eligibility; not calibrated dormancy physiology'};});
  return {time:+time.toFixed(3),hypocotyl,hypocotylRadii,axes:states,leaves:organs,buds:budStates,
   metrics:{nodes:axes.reduce((s,a)=>s+a.nodes.length,0),shoots:axes.length,
    leaves:organs.filter(l=>l.kind==='leaf').length,height:ranges[2][1],
    skeletonWidth:ranges[0][1]-ranges[0][0],skeletonDepth:ranges[1][1]-ranges[1][0]}};
 }
 for(let tick=0;tick<=Math.round(cfg.duration/cfg.step);tick++){
  const t=tick*cfg.step;
  for(const a of [...axes]){
   const cap=a.order===0?cfg.mainNodes:a.order===1?cfg.lateralNodes:cfg.secondaryNodes;
   if(t+1e-8>=a.next&&a.nodes.length<cap){newNode(a,a.next);a.next+=a.order===0?cfg.mainInterval:cfg.lateralInterval}
   for(const n of a.nodes){const age=t-n.born;n.length=n.maxLength*smooth(age/cfg.expansion);
    n.radius=(a.order===0?.0007:a.order===1?.00045:.00028)+
     (a.order===0?.0034:a.order===1?.0015:.00065)*smooth(age/18);
    // Phenomenological upward reorientation during the growing interval.
    // Intrinsic direction freezes as the segment matures. There is no force
    // integration here and no imported cross-species numerical calibration.
    if(a.order>0&&age<cfg.expansion){const target=unit(add(mul(a.heading,.55),[0,0,.9]));
     const correction=add(target,mul(n.dir,-dot(target,n.dir)));
     n.dir=unit(add(n.dir,mul(correction,cfg.branchResponse*cfg.step)));
    }
   }
  }
  const by=lookup();for(const bud of buds){if(!bud.activationEligible||bud.active||t-bud.born+1e-8<bud.delay)continue;
   const par=by.get(bud.axis),node=par.nodes[bud.node-1];
   if(node.length/node.maxLength<.8)continue;
   const outward=radial(node.dir,bud.phi);
   const birth=bud.born+bud.delay;
   makeAxis(bud.id+'/shoot',par.id,bud.node,par.order+1,birth,add(mul(outward,.92),mul(node.dir,.58)),bud.phi*.23);
   bud.active=true;bud.state='active';bud.activatedAt=birth;event(birth,'axillary bud activated',bud.id,bud.leaf);
  }
  if(tick%5===0||tick===Math.round(cfg.duration/cfg.step))frames.push(snapshot(t));
 }
 return {config:cfg,frames,events:events.sort((a,b)=>a.time-b.time),
  status:'Developmental geometry simulation with uncalibrated rates; no growth physiology, elasticity or collision solver.'};
}
