import {useState} from 'react';
import {ReplayScene} from './ReplayScene';
export function RecordingPlayer({clip,asset,initialMode="replay"}:{clip:any,asset:(path:string)=>string,initialMode?:"replay"|"video"}){
 const [mode,setMode]=useState<'replay'|'video'>(initialMode);
 const hasVideo=typeof clip?.path==='string'&&/\.(mp4|webm)$/i.test(clip.path),hasReplay=!!clip?.replay_path;
 if(!hasVideo&&!hasReplay)return <p>No recording has been published yet.</p>;
 const showVideo=hasVideo&&(mode==='video'||!hasReplay);
 return <div className="recording-player">
 {hasVideo&&hasReplay&&<div className="clip-tabs" aria-label="Recording view"><button className={!showVideo?'selected':''} onClick={()=>setMode('replay')}>Explore in 3D</button><button className={showVideo?'selected':''} onClick={()=>setMode('video')}>Watch video</button></div>}
 <div className="skill-sim-view">{showVideo?<video key={clip.path} src={asset(clip.path)} poster={clip.poster_path?asset(clip.poster_path):undefined} controls playsInline preload="metadata" aria-label={clip.title||'Simulation recording'}/>:<ReplayScene url={asset(clip.replay_path)} token={location.hash.slice(1)}/>}</div>
 </div>;
}
