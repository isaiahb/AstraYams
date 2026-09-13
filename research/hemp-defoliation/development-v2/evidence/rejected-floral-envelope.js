// Rejected visual experiment: filled upper stem as an implausible continuous cone.

function floralEnvelope(points,scale){
 if(points.length<18||scale<.01)return;
 const widths=[7,10,15,20,15,1].map(x=>x*.8/752),rows=45,sides=18,rings=[];
 const path=points.slice(12),color=new T.Color('#648237');
 for(let i=0;i<=rows;i++){
  const u=i/rows*(path.length-1),j=Math.min(path.length-2,Math.floor(u)),f=u-j;
  const pos=mix(path[j],path[j+1],f),dir=path[j+1].clone().sub(path[j]).normalize(),[b,n]=frame(dir);
  const envelope=(widths[j]*(1-f)+widths[j+1]*f)*scale;
  rings.push(Array.from({length:sides},(_,k)=>{const ph=k*2*Math.PI/sides,r=envelope*(.79+.15*Math.cos(ph*5+u*9)+.06*Math.sin(ph*8-u*19));return pos.clone().addScaledVector(b,r*Math.cos(ph)).addScaledVector(n,r*Math.sin(ph))}));
 }
 for(let i=0;i<rows;i++)for(let k=0;k<sides;k++){const j=(k+1)%sides;const c=color.clone().multiplyScalar(.86+.14*Math.sin(i*1.7+k*2.4)**2);tri('flower',rings[i][k],rings[i+1][k],rings[i+1][j],c);tri('flower',rings[i][k],rings[i+1][j],rings[i][j],c)}
 // Small bract-like silhouette facets. Geometry proxy only.
 for(let i=2;i<rows;i+=2){const ph=i*2.399,k=Math.floor((ph%(Math.PI*2))/(Math.PI*2)*sides),at=rings[i][k];const radial=at.clone().sub(mix(path[Math.min(4,Math.floor(i/rows*5))],path[Math.min(5,Math.floor(i/rows*5)+1)],.5));radial.z=0;radial.normalize();const w=vec(-radial.y,radial.x,0).multiplyScalar(.002*scale);tri('flower',at.clone().sub(w),at.clone().addScaledVector(radial,.008*scale).add(vec(0,0,.008*scale)),at.clone().add(w),new T.Color('#4f7a31'))}
}
