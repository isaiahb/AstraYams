import {useEffect,useState} from 'react';
import {RecordingPlayer} from './RecordingPlayer';
import {readEnvironmentStudy,type EnvironmentStudy as Study} from './environmentStudySchema';
import './EnvironmentStudy.css';

function StudyImage({src,alt}:{src:string;alt:string}){
  const [failed,setFailed]=useState(false);
  useEffect(()=>setFailed(false),[src]);
  return failed?<div className="study-missing">Image unavailable locally. The source and decision remain below.</div>:<img src={src} alt={alt} onError={()=>setFailed(true)}/>;
}

export function EnvironmentStudy({path,asset}:{path?:string;asset:(path:string)=>string}){
  const [study,setStudy]=useState<Study|null>(null),[error,setError]=useState('');
  const [section,setSection]=useState('references'),[sourceId,setSourceId]=useState(''),[revisionId,setRevisionId]=useState(''),[experimentId,setExperimentId]=useState('');
  const url=path?asset(path):null;
  useEffect(()=>{
    setStudy(null);setError('');if(!url)return;
    let stopped=false,busy=false;const controller=new AbortController();
    async function refresh(){if(busy)return;busy=true;try{
      const r=await fetch(url!,{cache:'no-store',signal:controller.signal});
      if(!r.ok)throw Error('Research record is not available yet.');
      const next=readEnvironmentStudy(await r.json());
      if(!stopped){setStudy(next);setError('');}
    }catch(e){if(!stopped)setError(e instanceof Error?e.message:'Could not read research record.');}finally{busy=false;}}
    refresh();const timer=setInterval(refresh,5000);
    return()=>{stopped=true;controller.abort();clearInterval(timer);};
  },[url]);
  if(!study)return <div className="environment-study study-empty"><span className="overline">RESEARCH & PHYSICS</span><h2>{!path?'The evidence starts here':'Opening the research record'}</h2><p>{error||(!path?'No research record has been published for this skill yet. As the engineer publishes references, modeling decisions and contact tests, they will appear here.':'Loading published evidence…')}</p><div className="study-flow">References <span>→</span> Model changes <span>→</span> Contact tests <span>→</span> Review</div></div>;
  const source=study.sources.find(s=>s.id===sourceId)||study.sources[0];
  const revision=study.revisions.find(r=>r.id===revisionId)||study.revisions.at(-1);
  const experiment=study.experiments.find(e=>e.id===experimentId)||study.experiments[0];
  return <div className="environment-study">
    <div className="study-heading"><div><span className="overline">BUILDING A WORLD THAT RESPONDS</span><h2>{study.title}</h2><p>{study.objective}</p></div><span className="study-provenance">{study.provenance==='recorded'?'Recorded study':'Current run · published updates'}</span></div>
    <div className="study-scope"><strong>{study.status}</strong><span>{study.scope}</span></div>
    {error&&<p className="study-error" role="status">{error} Showing the last valid record.</p>}
    <nav className="study-nav" aria-label="Research sections">{[['references','Reference atlas',study.sources.length],['changes','Model changes',study.revisions.length],['tests','Contact tests',study.experiments.length],['assumptions','What is still assumed',study.assumptions.filter(a=>a.basis==='assumed'||a.basis==='inferred').length]].map(([id,label,count])=><button key={id} className={section===id?'selected':''} onClick={()=>setSection(String(id))}>{label}<span>{count}</span></button>)}</nav>

    {section==='references'&&<>{source?<><div className="study-choices" aria-label="Source features">{study.sources.map(s=><button key={s.id} onClick={()=>setSourceId(s.id)} className={source.id===s.id?'selected':''}>{s.feature}</button>)}</div><div className="study-comparison"><figure>{source.image_path?<StudyImage src={asset(source.image_path)} alt={source.title}/>:<div className="study-missing">Open the source to inspect its evidence.</div>}<figcaption><span>REFERENCE · {source.publisher}</span><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title} ↗</a><small>{source.credit}</small></figcaption></figure><figure>{study.preview_path&&<StudyImage src={asset(source.model_path||study.preview_path)} alt="Current reference-informed specimen"/>}<figcaption><span>CURRENT MODEL · {study.checkpoint?.label||'Latest published preview'}</span><strong>One specimen before a whole environment</strong><small>Reference-informed geometry; metric depth and material properties still need measurement.</small></figcaption></figure></div><div className="study-reason"><div><span className="overline">WHAT THE REFERENCE SHOWS</span><p>{source.observation}</p></div><div><span className="overline">HOW THE MODEL USES IT</span><p>{source.application}</p></div></div><p className="study-boundary"><strong>Evidence boundary</strong> {source.boundary}</p></>:<p>No references have been published yet.</p>}</>}

    {section==='changes'&&<div className="study-revisions"><div className="study-timeline">{study.revisions.map((r,i)=><button key={r.id} onClick={()=>setRevisionId(r.id)} className={r.id===revision?.id?'selected':''}><span className="study-sequence">{String(i+1).padStart(2,'0')}</span><div><strong>{r.title}</strong><small className={'study-disposition '+r.disposition}>{r.disposition==='kept'?'Kept for this study':r.disposition==='rejected'?'Rejected · evidence retained':'Needs review'}</small></div></button>)}</div>{revision?<article className="study-decision"><span className="overline">RECORDED DECISION SUMMARY</span><h3>{revision.title}</h3>{(revision.before_path||revision.after_path)&&<div className="study-revision-images">{[[revision.before_path,'Earlier checkpoint'],[revision.after_path,'Revised checkpoint']].filter(([p])=>p).map(([p,label])=><figure key={label}><StudyImage src={asset(p!)} alt={label!}/><figcaption>{label}</figcaption></figure>)}</div>}<dl>{[['Observation',revision.observation],['Decision',revision.decision],['Implemented change',revision.change],['Evidence & remaining gap',revision.evidence]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><div className="study-links">{revision.source_ids.map(id=>{const s=study.sources.find(s=>s.id===id)!;return <button key={id} onClick={()=>{setSourceId(id);setSection('references');}}>Reference: {s.feature} ↗</button>;})}{revision.artifact_path&&<a href={asset(revision.artifact_path)} target="_blank" rel="noopener noreferrer">Inspect evidence ↗</a>}</div></article>:<p>No modeling decisions published yet.</p>}</div>}

    {section==='tests'&&<>{experiment?<><div className="study-choices">{study.experiments.map(e=><button key={e.id} onClick={()=>setExperimentId(e.id)} className={experiment.id===e.id?'selected':''}>{e.title}</button>)}</div><div className="study-test-heading"><div><h3>{experiment.question}</h3><p>{experiment.method}</p></div><span className={'study-test-outcome '+experiment.outcome}>{experiment.outcome==='passed-diagnostic'?'Diagnostic passed':experiment.outcome==='failed'?'Failed':'Not run yet'}</span></div>{(experiment.path||experiment.replay_path)&&<RecordingPlayer key={experiment.id} clip={experiment} asset={asset} initialMode="video"/>}<div className="study-metrics">{experiment.metrics.map(m=><div key={m.label}><strong>{m.value}</strong><span>{m.label}</span></div>)}</div><p>{experiment.finding}</p><p className="study-boundary"><strong>What this does not establish</strong> {experiment.limitation}</p><div className="study-links">{[[experiment.result_path,'Contact result'],[experiment.control_path,'Matched no-contact control']].filter(([p])=>p).map(([p,label])=><a key={label} href={asset(p!)} target="_blank" rel="noopener noreferrer">{label} ↗</a>)}</div></>:<p>No contact trials published yet. A rendered scene is not a passed contact test.</p>}</>}

    {section==='assumptions'&&<><p className="study-intro">The model is only as trustworthy as its inputs. These distinctions stay visible when a scene moves toward training.</p><div className="study-assumptions">{study.assumptions.map(a=><article key={a.subject}><div><h3>{a.subject}</h3><span className={'study-basis '+a.basis}>{a.basis}</span></div><p>{a.value}</p><small>{a.consequence}</small></article>)}</div><div className="study-next"><span className="overline">BEFORE PROMOTING THIS ENVIRONMENT</span><ol>{study.next_steps.map(s=><li key={s}>{s}</li>)}</ol></div></>}

    <footer className="study-footer"><div><strong>{study.checkpoint?.label||'Research in progress'}</strong>{study.checkpoint?.sha256&&<small title={study.checkpoint.sha256}>Model SHA-256 · {study.checkpoint.sha256.slice(0,16)}…</small>}<small>{study.provenance==='recorded'?'Saved experiments, not live training.':'Updates appear only when the engineer publishes an artifact.'}</small></div><div className="study-links">{study.checkpoint?.report_path&&<a href={asset(study.checkpoint.report_path)} target="_blank" rel="noopener noreferrer">Validation record ↗</a>}{path&&<a href={asset(path)} target="_blank" rel="noopener noreferrer">Study data ↗</a>}</div></footer>
  </div>;
}
