"""Reuse specimen mesh exporter for a standalone orbitable PPO recording."""
import argparse,json,shutil
from pathlib import Path
import mujoco,numpy as np
from astrafactory.berry_support import BerrySupportEnv,TASK
import render_strawberry_specimen as exporter

HTML='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Learned berry support · YAM PPO</title><style>
body{margin:0;background:#eef1eb;color:#20342b;font:16px/1.5 system-ui}main{max-width:1250px;margin:auto;padding:24px}h1{font-size:30px;margin:0}p{max-width:1060px}button,select,a{font:inherit;color:inherit}button,select{padding:8px;border:1px solid #b5c1b4;background:#f7f9f4;border-radius:5px}nav{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:16px 0}#view{height:64vh;min-height:380px;background:#e3e9df;position:relative}canvas{display:block}#status{padding:12px;background:#dde6d9}input{flex:1}small{color:#4c604f}.hint{position:absolute;bottom:10px;left:12px;background:#eef1ebdd;padding:4px 10px}details{margin:20px 0}video{width:100%}</style>
<script type="importmap">{"imports":{"three":"/apps/skill-studio/node_modules/three/build/three.module.js","three/addons/":"/apps/skill-studio/node_modules/three/examples/jsm/"}}</script></head><body><main>
<h1>A small PPO learns to support a strawberry</h1><p id="summary">Loading evaluation…</p>
<small>All six arm joints are commanded by PPO. Motor control is finite-torque PD. No IK or BC selects execution movements. The cup is a fixed mounted tool.</small>
<nav><select id="case" aria-label="Evaluation case"></select><button id="play">Play</button><input id="time" type="range" min="0" max="4" step=".02" value="0"><span id="clock">0 s</span><button id="whole">Whole arm</button><button id="close">Berry contact</button><button id="grasp">Jaw grasp</button></nav>
<div id="view"><span class="hint">Drag to orbit · Scroll to zoom · Right-drag to pan · recorded physics at 1×</span></div><div id="status">Loading exact scene geometry…</div>
<p><a id="video-link" href="#">Open two-angle video</a> · <a href="report.json">All evaluation results</a> · <a href="replay-audit.json">Saved-action replay checks</a></p>
<details><summary>What this demonstrates—and its limits</summary><p>A learned approach and contact-support subskill with held-out position and stiffness variation. Actor inputs include privileged simulated geometry and contact forces. Fruit-bearing stalks are articulated; foliage is fixed in settled poses. Leaf arrangement variation alone does not establish learned leaf avoidance. Robot self-collision is disabled for this local experiment. No cutting, bruising validation, detailed motor calibration or real-arm transfer is claimed.</p><p>Success requires 0.4 continuous seconds supporting 60–110% of fruit body weight with less than 5 mm XY error, an upright cup, and low joint speed. The contact limits are engineering criteria, not biological safety thresholds.</p></details>
<script type="module">
import * as T from 'three';import{OrbitControls}from'three/addons/controls/OrbitControls.js';import{STLLoader}from'three/addons/loaders/STLLoader.js';
const host=document.getElementById('view'),scene=new T.Scene();scene.background=new T.Color('#e3e9df');
const camera=new T.PerspectiveCamera(42,1,.005,10);camera.up.set(0,0,1);const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));host.append(renderer.domElement);
scene.add(new T.HemisphereLight(0xffffff,0x748473,2));const light=new T.DirectionalLight(0xffffff,2.5);light.position.set(1,-1,2);scene.add(light);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;const groups=new Map(),loader=new STLLoader();let replay,elapsed=0,playing=false;
const report=await fetch('report.json').then(r=>r.json()),manifest=await fetch('viewer-manifest.json').then(r=>r.json());
document.getElementById('summary').textContent=`${report.actor_parameters.toLocaleString()} actor parameters · ${report.successes}/${report.episodes} ${report.split} successes · fixed-start baseline ${report.baseline_successes}/${report.episodes}. First three predetermined cases and the first failed case are available below (when a failure occurs).`;
const first=await fetch(manifest.cases[0].replay).then(r=>r.json());
await Promise.all(first.objects.map(async o=>{let group=groups.get(o.body);if(!group){group=new T.Group();groups.set(o.body,group);scene.add(group)}const geometry=await loader.loadAsync('/'+o.mesh_path);geometry.computeVertexNormals();group.add(new T.Mesh(geometry,new T.MeshStandardMaterial({color:o.color,roughness:.78,metalness:0,side:T.DoubleSide})));}));
function whole(){orbit.target.set(.26,-.02,.24);camera.position.set(.93,-.95,.67);orbit.update()}
function grasp(){let b=replay?.frames[Math.min(replay.frames.length-1,Math.floor(elapsed/.02))].bodies.gripper;if(!b)return;let q=new T.Quaternion().fromArray(b.quaternion);orbit.target.fromArray(b.position).add(new T.Vector3(0,0,-.15).applyQuaternion(q));camera.position.copy(orbit.target).add(new T.Vector3(.24,.02,.1));orbit.update()}
function close(){let b=replay?.frames[0].bodies.fruit_primary;orbit.target.set(...(b?b.position:[.31,.07,.23]));orbit.target.z-=.025;camera.position.copy(orbit.target).add(new T.Vector3(.13,-.21,.06));orbit.update()}
async function load(i){playing=false;elapsed=0;document.getElementById('play').textContent='Play';let item=manifest.cases[i];replay=await fetch(item.replay).then(r=>r.json());document.getElementById('time').max=replay.frames.at(-1).time;document.getElementById('video-link').href=item.video;whole()}
manifest.cases.forEach((c,i)=>{let o=document.createElement('option');o.value=i;o.textContent=`Seed ${c.seed} · ${c.success?'passed':'failed'}`;document.getElementById('case').append(o)});
document.getElementById('case').onchange=e=>load(+e.target.value);document.getElementById('play').onclick=e=>{if(elapsed>=replay.frames.at(-1).time)elapsed=0;playing=!playing;e.target.textContent=playing?'Pause':'Play'};document.getElementById('time').oninput=e=>{playing=false;elapsed=+e.target.value;document.getElementById('play').textContent='Play'};document.getElementById('whole').onclick=whole;document.getElementById('close').onclick=close;document.getElementById('grasp').onclick=grasp;
new ResizeObserver(()=>{renderer.setSize(host.clientWidth,host.clientHeight);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix()}).observe(host);
await load(0);let last=performance.now();renderer.setAnimationLoop(now=>{let dt=Math.min((now-last)/1000,.1);last=now;if(replay){if(playing){elapsed=Math.min(elapsed+dt,replay.frames.at(-1).time);if(elapsed>=replay.frames.at(-1).time){playing=false;document.getElementById('play').textContent='Play'}}let frame=replay.frames[Math.min(replay.frames.length-1,Math.floor(elapsed/.02))];for(const[name,g]of groups){const b=frame.bodies[name];if(b){g.position.fromArray(b.position);g.quaternion.fromArray(b.quaternion)}}document.getElementById('time').value=elapsed;document.getElementById('clock').textContent=elapsed.toFixed(2)+' s';document.getElementById('status').textContent=`Support ${(frame.support_fraction*100).toFixed(0)}% of fruit weight · sustained hold ${frame.hold_steps}/20 · ${frame.success?'criterion passed':'criterion not yet passed'}${frame.grasp?.left_jaw_N!=null?` · jaws ${frame.grasp.left_jaw_N.toFixed(1)} / ${frame.grasp.right_jaw_N.toFixed(1)} N · tool slip ${(frame.grasp.tool_slip_m*1000).toFixed(2)} mm`:''}`;}orbit.update();renderer.render(scene,camera)});
</script></main></body></html>'''

def main():
 global BerrySupportEnv,TASK
 p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();run=a.run.resolve();report=json.loads((run/'report.json').read_text())
 if report.get('gripped_tool'):
  from astrafactory.gripped_berry_support import GrippedBerrySupportEnv,TASK as GRIPPED_TASK
  BerrySupportEnv=GrippedBerrySupportEnv;TASK=GRIPPED_TASK
 rows=report['rows'][:3];failed=next((r for r in report['rows'] if not r['is_success']),None)
 if failed and failed not in rows:rows.append(failed)
 shutil.copy2(TASK/'scene.xml',run/'scene.xml')
 first=run/'mesh-export';first.mkdir(exist_ok=True);z=np.load(run/f'episode-{rows[0]["seed"]}.npz');np.savez_compressed(first/'rollout.npz',qpos=z['qpos'][:1],t=[.02])
 exporter.P=run;exporter.export(['mesh-export'],skip_finger_collision_visuals=True);objects=json.loads((first/'replay.json').read_text())['objects'];cases=[]
 for row in rows:
  seed=row['seed'];env=BerrySupportEnv(1.);env.reset(seed=seed);m,d=env.model,env.data;z=np.load(run/f'episode-{seed}.npz');trace=json.loads((run/f'episode-{seed}.json').read_text())['trace'];frames=[]
  for i,q in enumerate(z['qpos']):
   d.qpos[:]=q;mujoco.mj_forward(m,d);bodies={m.body(j).name or 'world':dict(position=d.xpos[j].tolist(),quaternion=d.xquat[j][[1,2,3,0]].tolist()) for j in range(m.nbody)}
   frames.append(dict(time=(i+1)*.02,bodies=bodies,support_fraction=trace[i]['support_fraction'],hold_steps=trace[i]['hold_steps'],success=trace[i]['is_success'],grasp={k:trace[i].get(k) for k in ['left_jaw_N','right_jaw_N','tool_slip_m']}))
  name=f'episode-{seed}-replay.json';(run/name).write_text(json.dumps(dict(objects=objects,frames=frames),separators=(',',':')));env.close();cases.append(dict(seed=seed,success=row['is_success'],replay=name,video=f'episode-{seed}.mp4'))
 (run/'viewer-manifest.json').write_text(json.dumps(dict(cases=cases),indent=2));page=HTML
 if report.get('gripped_tool'):
  page=page.replace('The cup is a fixed mounted tool.','The removable cradle is held by jaw contact and friction, with no attachment constraint.').replace('and low joint speed.','and low joint speed. It also requires both jaws to retain contact with the handle and bounded tool slip.').replace('No cutting, bruising validation, detailed motor calibration or real-arm transfer is claimed.','The tool begins prepositioned between the jaws; rack pickup is not learned. No cutting, bruising validation, detailed motor calibration or real-arm transfer is claimed.')
 (run/'index.html').write_text(page);print(run/'index.html')

if __name__=='__main__':main()
