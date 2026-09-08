import React,{useEffect,useState} from 'react';
export function ProjectCard({project,token,onOpen}:{project:any,token:string,onOpen:()=>void}){
 const [preview,setPreview]=useState<string|null>(project.id==='robot-arm'?'runs/yam-initial-recording/start.png':null);
 useEffect(()=>{if(project.id==='robot-arm'||project.id==='lunar-study')return;let done=false;
 const read=async()=>{try{const r=await fetch('/api/artifacts?projectId='+encodeURIComponent(project.id),{headers:{Authorization:'Bearer '+token}});if(!r.ok)return;const rows=await r.json(),images=rows.filter((a:any)=>a.kind==='image');const p=images.find((a:any)=>/isometric|hero|overview/i.test(a.name))||images[0];if(!done)setPreview(p?.path||null);}catch{}};
 read();const t=setInterval(read,10000);return()=>{done=true;clearInterval(t);};},[project.id]);
 const summary=(project.brief.split('\n').find((s:string)=>s.trim()&&s.trim()!==project.title)||project.brief).slice(0,125);
 return <button className={'project-card '+(preview?'has-preview':'')} onClick={onOpen}><div className={'cover '+(project.id==='lunar-study'?'lunar':'')}>{preview&&<img className="project-preview" src={'/api/artifact?projectId='+encodeURIComponent(project.id)+'&path='+encodeURIComponent(preview)+'&token='+token} alt={project.title+' preview'}/>}<span className="cover-label">{project.id==='robot-arm'?'ROBOT LEARNING':project.id==='lunar-study'?'CONCEPT STUDY':'PRODUCT DESIGN'}</span><span className="cover-type">{project.id==='lunar-study'?'Explore what it takes':preview?'':project.title.slice(0,35)}</span></div><h3>{project.title}</h3><p>{summary}{summary.length===125?'…':''}</p><span className="open-project">Open project →</span></button>;
}
