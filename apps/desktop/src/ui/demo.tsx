import React,{useState,useEffect} from 'react';
import {ModelViewer} from './viewer';
const steps=['Brief','Design','Test','Improve'];
export function DemoWorkspace({project,artifacts,agents,items,assetURL,onInspect,onEngineering,onSession,onCycle,approvalCount}:{project:any,artifacts:any[],agents:any[],items:any[],assetURL:(p:string)=>string,onInspect:(a:any)=>void,onEngineering:()=>void,onSession:(id:string)=>void,onCycle:(w:any)=>void,approvalCount:number}){
 const [chosen,setChosen]=useState<number|null>(null),[visual,setVisual]=useState('auto');
 const w=items.at(-1),active=agents.findLast(a=>a.turnId);
 const result=w?.result||[...(w?.attempts||[])].reverse().find(a=>a.result)?.result;
 const improving=w?.status==='revising'&&!!result;
 const liveStep=improving?3:['blocked','needs_revision','passed'].includes(w?.status)?3:w?.status==='retesting'?2:w?.status==='revising'||artifacts.some(a=>a.kind==='model')?1:0;
 const step=chosen??liveStep;
 const revisionFolder=w?.revision?.path?.replace(/[^/]+$/, '');
 const preferPublished=(rows:any[])=>rows.sort((a,b)=>Number(!!b.registeredHash)-Number(!!a.registeredHash)||(revisionFolder?Number(b.path.startsWith(revisionFolder))-Number(a.path.startsWith(revisionFolder)):0)||b.modified.localeCompare(a.modified));
 const models=preferPublished(artifacts.filter(a=>a.kind==='model')),images=preferPublished(artifacts.filter(a=>a.kind==='image')),videos=artifacts.filter(a=>a.kind==='video');
 const model=models.find(a=>/\.urdf$/i.test(a.path))||models.find(a=>/assembly|assembled/i.test(a.path))||models[0];
 const picture=images.find(a=>/isometric|hero|overview/i.test(a.path))||images[0];
 const exploded=images.find(a=>/explod/i.test(a.path));
 const comparison=images.find(a=>/before.?after|comparison/i.test(a.path));
 const view=visual==='auto'?(step===3&&comparison?'change':'model'):visual;
 const shown=view==='change'?comparison:view==='views'?(model||picture):view==='exploded'?(model||exploded):view==='motion'?videos[0]:model||picture;
 const brief=artifacts.find(a=>a.name==='BRIEF.md'),report=artifacts.find(a=>a.path===result?.path);
 const [reportIntro,setReportIntro]=useState('');
 useEffect(()=>{let cancelled=false;setReportIntro('');if(report?.path&&/\.md$/i.test(report.path))fetch(assetURL(report.path)).then(r=>r.ok?r.text():'').then(text=>{const intro=text.split(/\n\s*\n/).find(p=>p.trim()&&!/^[#|`>]/.test(p.trim()));if(!cancelled)setReportIntro(intro?.trim()||'');}).catch(()=>{});return()=>{cancelled=true;};},[report?.path,report?.modified]);
 const team=Array.from(new Map(agents.map(a=>[a.role,a])).values());
 const goal=(project.brief.split('\n').filter(Boolean).find((line:string)=>line!==project.title)||project.brief).split(/(?<=\.)\s/)[0];
 const findingText=reportIntro||result?.summary||w?.blocker||'The tester checks the submitted design against the brief.';
 const findingPreview=(findingText.match(/[^.!?]+[.!?](?:\s|$)/g)||[findingText]).slice(0,2).join(' ').trim();
 const heading=step===0?'Define the product':step===1?'Explore the design':step===2?'Check the design':w?.status==='passed'?'The re-test passed':'Improve the design';
 const status=approvalCount?'Needs a decision':w?.status==='revising'?(improving?'Improving the design':'Engineering in progress'):w?.status==='retesting'?'Independent re-test running':w?.status==='passed'?'Re-test passed':w?.status==='needs_revision'?'Changes needed':w?.status==='blocked'?'Needs attention':active?'Defining the project':'Brief ready';

 return <div className="demo-workspace"><aside className="demo-rail"><span className="eyebrow">FROM IDEA TO REALITY</span><nav aria-label="Project story">{steps.map((name,i)=><button key={name} className={step===i?'selected':''} onClick={()=>{setChosen(i);setVisual('auto');}}><span className="step-number">{i+1}</span><span>{name}</span>{liveStep===i&&<i className="live-step"/>}</button>)}</nav><div className="demo-team"><span className="eyebrow">YOUR TEAM</span>{team.map(a=><button key={a.id} onClick={()=>onSession(a.id)}><span className={'team-dot '+(a.turnId?'active':'')}/><span>{a.role==='Lead engineer'?'Project lead':a.role==='Mechanical'?'Mechanical engineer':a.role==='Simulation'?'Test engineer':a.role}</span><small>{a.turnId?'Working':'View'}</small></button>)}{!team.length&&<p>Astra is ready to start.</p>}</div><button className="detail-link" onClick={onEngineering}>Engineering details ↗</button></aside>
 <main className="demo-main"><div className="demo-heading"><div><span className="eyebrow">{steps[step].toUpperCase()}</span><h1>{heading}</h1></div><span className={'run-status '+(active?'running':'')}>{active&&<i/>}{status}</span></div>
 {approvalCount>0&&<button className="decision-notice" onClick={onEngineering}>The team needs a tool decision to continue. Review →</button>}
 {step===0?<section className="demo-brief"><span className="eyebrow">THE GOAL</span><h2>{project.title}</h2><p>{goal}</p><div className="brief-explanation"><span>01</span><div><h3>Define what success looks like</h3><p>Requirements, research, and the first engineering task.</p></div></div><div className="demo-actions">{brief&&<button onClick={()=>onInspect(brief)}>Read the brief ↗</button>}<button className="primary" onClick={()=>setChosen(1)}>See the design →</button></div></section>:<>
 <div className="demo-visual-bar"><div className="visual-tabs">{comparison&&step>=2&&<button className={view==='change'?'selected':''} onClick={()=>setVisual('change')}>Before &amp; after</button>}{model&&<button className={view==='model'?'selected':''} onClick={()=>setVisual('model')}>3D model</button>}{(model||picture)&&<button className={view==='views'?'selected':''} onClick={()=>setVisual('views')}>{model?'Front view':'Design view'}</button>}{(model||exploded)&&<button className={view==='exploded'?'selected':''} onClick={()=>setVisual('exploded')}>Exploded view</button>}{videos.length>0&&<button className={view==='motion'?'selected':''} onClick={()=>setVisual('motion')}>Recorded motion</button>}</div>{shown&&<button className="detail-link" onClick={()=>onInspect(shown)}>Inspect artifact ↗</button>}</div>
 <div className="demo-viewer">{shown?shown.kind==='model'?<ModelViewer path={shown.path} assetURL={assetURL} presentation={view==='exploded'?'exploded':view==='views'?'front':'assembled'}/>:shown.kind==='video'?<video src={assetURL(shown.path)} controls playsInline/>:<img src={assetURL(shown.path)} alt={shown.label||shown.name}/>:<div className="building-state"><div className="building-symbol">◇</div><h2>{active?'Engineering is underway':'No geometry published yet'}</h2><p>The first model will appear here as soon as it is saved.</p>{active&&<button onClick={()=>onSession(active.id)}>See what the engineer is doing ↗</button>}</div>}</div>
 <div className="demo-bottom"><small>{shown?.kind==='model'?'Interactive geometry · drag to orbit':shown?.kind==='video'?'Recorded evidence':shown?'Rendered from project artifacts':'Live project · no simulated progress'}</small>{chosen!==null&&<button onClick={()=>{setChosen(null);setVisual('auto');}}>Follow live progress →</button>}</div>
 {(step===2||step===3)&&<section className="demo-finding"><div><span className="eyebrow">{result?(w?.result?'THE FINDING':'WHAT WE’RE FIXING'):'NEXT CHECK'}</span><h3>{result?.outcome==='pass'?'Passed the submitted re-test':result?.outcome==='fail'?'The test found something to change':w?.status==='blocked'?'This cycle needs attention':'Does the design meet the brief?'}</h3><p>{findingPreview}</p></div><div className="demo-actions">{report&&<button onClick={()=>onInspect(report)}>Read the test report ↗</button>}{w&&['planned','blocked','needs_revision'].includes(w.status)&&<button className="primary" onClick={()=>onCycle(w)}>{w.status==='planned'?'Start revision & re-test':'Review next revision'} →</button>}</div></section>}
 </>}
 </main></div>;
}
