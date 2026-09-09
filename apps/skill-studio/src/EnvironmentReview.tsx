import {useState} from 'react';
import {RecordingPlayer} from './RecordingPlayer';
export function EnvironmentReview({review,asset}:{review:any,asset:(path:string)=>string}){
 const [pass,setPass]=useState(2),[sample,setSample]=useState(0);if(!review)return null;
 const item=review.iterations[pass],row=review.samples[sample];
 return <details className="environment-review"><summary>Environment & synthetic data · {review.samples.length} variations</summary>
 {review.plant_physics&&<section><h3>Plant physics · contact & recovery</h3><RecordingPlayer clip={review.plant_physics} asset={asset} initialMode="video"/><p>{review.plant_physics.summary}</p><p><a href={asset(review.plant_physics.report)}>Model changes, measurements and remaining gaps ↗</a></p></section>}
 {review.reality_gap&&<details><summary>Earlier tool experiment · not adopted</summary><img className="environment-review-image" src={asset(review.reality_gap.image)} alt="Before and after lowering the camera-facing catcher rim"/><p>{review.reality_gap.summary}</p><p><a href={asset(review.reality_gap.report)}>Trials and remaining gaps ↗</a> · <a href={asset(review.reality_gap.cad)}>Candidate catcher CAD ↗</a></p></details>}
 <p>Three reviewed design passes. New geometry and observations; harvesting has not been learned in these worlds.</p>
 <div className="clip-tabs">{review.iterations.map((r:any,i:number)=><button key={r.title} className={i===pass?'selected':''} onClick={()=>setPass(i)}>{r.title}</button>)}</div>
 <img className="environment-review-image" src={asset(item.image)} alt={item.title}/><p><strong>Image review:</strong> {item.observation}</p><p><strong>Next change:</strong> {item.decision}</p>
 <p className="clip-caption">{item.result}</p><h3>Sampled environments</h3><img className="environment-review-image" src={asset(review.gallery)} alt="Nine different geometry samples"/>
 <label>Inspect sensor sample <select value={sample} onChange={e=>setSample(Number(e.target.value))}>{review.samples.map((r:any,i:number)=><option key={r.seed} value={i}>Seed {r.seed} · {r.layout}</option>)}</select></label>
 <p>RGB, ideal depth and object segmentation at the same simulation timestamp. Fixed YAM camera mounts; nominal intrinsics.</p>
 <div className="environment-sensors">{['cut','catch'].map(side=><div key={side}><strong>{side==='cut'?'Cutting wrist':'Catching wrist'}</strong><img src={asset(row.path+'/'+side+'_wrist_d405-rgb.png')} alt={side+' wrist RGB'}/><a href={asset(row.path+'/'+side+'_wrist_d405-depth.npz')}>Depth ↗</a> · <a href={asset(row.path+'/'+side+'_wrist_d405-segmentation.npz')}>Segmentation ↗</a></div>)}</div>
 <p><a href={asset(row.path+'/sample.json')}>Scene and camera metadata ↗</a> · <a href={asset(row.path+'/sensor-state.npz')}>Robot state ↗</a> · <a href={asset(review.report)}>Read review and limitations ↗</a></p>
 <p className="clip-caption">9 short simulation checks; 3 longer harvest trials failed. These are exploratory observations, not a successful-demonstration dataset or proof of sim-to-real transfer.</p>
 </details>;
}
