// A phenotype generator with explicit organ parentage. Geometry priors, not physiology.
export const families=[
 {id:'compact',name:'Compact · multiple leaders',height:.69,spread:.76,nodes:7,branches:6,leaf:.125,width:1.13,leader:true,secondary:2,description:'Short main-axis history with unequal ascending leaders. Indoor managed-canopy hypothesis; no intervention is prescribed.'},
 {id:'balanced',name:'Upright · branched',height:1,spread:.64,nodes:19,branches:12,leaf:.135,width:1,leader:false,secondary:1,description:'Retained dominant axis, variable lateral branches and secondary shoots. Greenhouse-oriented geometry prior.'},
 {id:'open',name:'Tall · open internodes',height:1.19,spread:.52,nodes:21,branches:10,leaf:.11,width:.81,leader:false,secondary:1,description:'Longer internodes, narrower blades and greater vertical extent. An architectural scenario, not a named cultivar reconstruction.'},
 {id:'broad',name:'Broad · lateral canopy',height:.83,spread:1.02,nodes:10,branches:8,leaf:.145,width:1.02,leader:true,secondary:3,description:'Wide unequal laterals with several ascending tips. A managed greenhouse/indoor canopy hypothesis.'}
];
export function random(seed){let a=seed|0;return()=>{a+=0x6D2B79F5;let t=a;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296}}
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x)),smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
const add=(a,b)=>a.map((v,i)=>v+b[i]),scale=(v,s)=>v.map(x=>x*s),sub=(a,b)=>a.map((v,i)=>v-b[i]);
export function observedHeight(curve,day){let last=0;const pts=curve.points.map(x=>{last=Math.max(last,x.median_m);return{...x,h:last}});if(day<=pts[0].day)return pts[0].h;for(let i=1;i<pts.length;i++){if(day<=pts[i].day){const a=pts[i-1],b=pts[i],u=(day-a.day)/(b.day-a.day);return a.h+(b.h-a.h)*u}}return pts.at(-1).h}
// Expand sequential internodes across a soft growth front. Earlier nodes never shrink.
function growthFractions(n,progress){if(progress<=0)return Array(n).fill(0);if(progress>=1)return Array(n).fill(1);let lo=-3,hi=n+3;for(let k=0;k<30;k++){let mid=(lo+hi)/2,sum=0;for(let j=0;j<n;j++)sum+=smooth((mid-j)/3);if(sum/n<progress)lo=mid;else hi=mid}return Array.from({length:n},(_,j)=>smooth(((lo+hi)/2-j)/3))}
export function makePlant(reference,{family=1,seed=31,curve=0,height=1,spread=1,density=1,leafWidth=1}={}){
 const f=families[family],rng=random(seed),r=(a,b)=>a+(b-a)*rng(),H=observedHeight(reference.curves[curve],114)*f.height*height;
 const skew=r(-.16,.16),phase=r(-Math.PI,Math.PI),axes=[],leaves=[];
 function axis(id,parent,node,order,n,delta,activation,end,angle){
  const item={id,parent,parent_node:node,order,n,delta,activation,end,angle,radius:(order===0?.0052:order===1?.0024:.00115)*Math.sqrt(H)};axes.push(item);
  const limit=n;
  for(let j=1;j<=limit;j++){
   const paired=order===0&&(f.leader||j<=Math.min(4,n-2));const rank=j/n;
   for(let side=0;side<(paired?2:1);side++){
    const leafLength=f.leaf*r(.78,1.17)*(1-.32*Math.pow(rank,2.4))*(order===2?.69:1);
    leaves.push({id:`${id}/leaf-${j}-${side}`,axis:id,node:j,rank,
      phi:angle+(paired?(j%2)*Math.PI/2+side*Math.PI:(j*2.399))+r(-.32,.32),
      length:leafLength,leaflets:rank>.82?3:rank>.55?5:7,pitch:r(-.5,.38),roll:r(-.48,.48),droop:r(.03,.17),
      width_factor:f.width*leafWidth*r(.9,1.1),asymmetry:r(-.13,.13),petiole_ratio:r(.35,.63),tone:r(.91,1.1),age_bias:r(-3,3)});
   }
  }return item;
 }
 const n=f.nodes;const mainHeight=f.leader?H*.22:H;
 const mainDelta=Array.from({length:n},(_,j)=>[H*.008*Math.cos(phase+j*.7),H*.006*Math.sin(j*.64),mainHeight/n]);
 axis('main',null,0,0,n,mainDelta,0,f.leader?.30:1,phase);
 const slots=Array.from({length:n-3},(_,j)=>j+2).flatMap(node=>Array((f.leader||node<=4)?2:1).fill(node));
 const count=Math.min(slots.length,Math.round(f.branches*density)+Math.floor(r(-1,2)));const used=new Map();
 for(let b=0;b<count;b++){
   const rank=(b+.4)/count;const ideal=(f.leader?.40+rank*.48:.12+rank*.73)*n;let best=0;for(let k=1;k<slots.length;k++)if(Math.abs(slots[k]-ideal)<Math.abs(slots[best]-ideal))best=k;const node=slots.splice(best,1)[0],side=used.get(node)||0;used.set(node,side+1);
   const subtending=leaves.find(l=>l.axis==='main'&&l.node===node&&l.id.endsWith('-'+side));const phi=subtending.phi+r(-.12,.12),nodeHeight=mainHeight*node/n;
   const topZ=f.leader?H*r(.78,1):nodeHeight+(H-nodeHeight)*r(.43,.80);
   const reach=H*f.spread*spread*.5*(f.leader?r(.67,1.10):(1-.62*rank))*r(.83,1.17);
   const countNodes=Math.round(f.leader?r(8,12):r(5,9)*(1-.15*rank));
   const points=Array.from({length:countNodes+1},(_,j)=>{const t=1-Math.pow(1-j/countNodes,1.55);return[Math.cos(phi)*reach*(1-Math.pow(1-t,1.7))*(1+skew),Math.sin(phi)*reach*(1-Math.pow(1-t,1.7)),(topZ-nodeHeight)*(.45*t+.55*t*t)]});
   const deltas=points.slice(1).map((p,j)=>sub(p,points[j]));
   const activation=f.leader?.15+rank*.035:.09+rank*.45;
   const ax=axis(`lateral-${b}`,'main',node,1,countNodes,deltas,activation,r(.89,1.03),phi);
   const secondary=Math.max(0,Math.round(f.secondary*density+r(-.6,.6)));
   for(let s=0;s<secondary;s++){
    const sn=Math.max(2,Math.min(countNodes-2,Math.round(countNodes*(.48+(s+1)/(secondary+1)*.36))));
    const pa=phi+(s%2?-1:1)*r(.6,1.2);const length=H*r(.085,.17),nn=Math.round(r(3,6));
    const dp=Array.from({length:nn},(_,j)=>[Math.cos(pa)*length/nn*.8,Math.sin(pa)*length/nn*.8,length/nn*(.65+.2*j/nn)]);
    axis(`${ax.id}/secondary-${s}`,ax.id,sn,2,nn,dp,activation+.20+s*.035,1.03,pa);
   }
 }
 // Preserve ancestry. Scale the complete terminal scaffold once, never per-frame.
 const origins={};let terminalHeight=0;
 for(const a of axes){const pts=[a.parent?origins[a.parent][a.parent_node]:[0,0,0]];for(const d of a.delta)pts.push(add(pts.at(-1),d));origins[a.id]=pts;terminalHeight=Math.max(terminalHeight,...pts.map(p=>p[2]));}
 const zcal=H/terminalHeight;for(const a of axes)for(const d of a.delta)d[2]*=zcal;
 return {seed,family,curve,H,params:{height,spread,density,leafWidth},name:f.name,description:f.description,axes,leaves,reference};
}
export function snapshot(spec,day){
 const curve=spec.reference.curves[spec.curve],p=observedHeight(curve,day)/observedHeight(curve,114),states=[],lookup={};
 for(const a of spec.axes){let progress=a.id==='main'?(families[spec.family].leader?clamp(p/.30):p):clamp((p-a.activation)/(a.end-a.activation));
  if(a.parent){const par=lookup[a.parent];progress*=par.fractions[a.parent_node-1];}
  const fractions=growthFractions(a.n,progress);const pts=[a.parent?lookup[a.parent].points[a.parent_node]:[0,0,0]];
  for(let j=0;j<a.n;j++)pts.push(add(pts.at(-1),scale(a.delta[j],fractions[j])));
  const radii=fractions.map((s,j)=>a.radius*(1-.68*j/a.n)*Math.sqrt(s)*(.55+.45*smooth((day-25)/90)));
  const ax={id:a.id,points:pts,radii,fractions,age:day,flower_scale:smooth((day-68)/43),order:a.order};states.push(ax);lookup[a.id]=ax;
 }
 const leaves=spec.leaves.map(l=>{const a=lookup[l.axis],s=smooth((a.fractions[l.node-1]-.25)/.75),age=Math.max(0,(s*.45+(day-31)/160)*85+l.age_bias);return{id:l.id,at:a.points[l.node],scale:s,active:s>.01,age,senescence:clamp((day-105)/45)*(1-l.rank)*.36}});
 const pts=states.flatMap(a=>a.points),ranges=[0,1,2].map(i=>[Math.min(...pts.map(p=>p[i])),Math.max(...pts.map(p=>p[i]))]);
 return {day,axes:states,leaves,metrics:{height:ranges[2][1],width:ranges[0][1]-ranges[0][0],depth:ranges[1][1]-ranges[1][0],leaves:leaves.filter(l=>l.active).length,reference_height:observedHeight(curve,day),flower:smooth((day-68)/43)},p};
}
export const defaultSpecs=()=>Array.from({length:8},(_,i)=>({family:Math.floor(i/2),seed:31+i*79,curve:i%5,height:i%2?1.05:.95,spread:i%2?.92:1.07,density:i%2?.9:1.04,leafWidth:1}));
