"""Package the isolated harvest checkpoint for the desktop; no physics or training changes."""
from pathlib import Path
import json, shutil, hashlib, sys
import numpy as np, mujoco, trimesh
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT.parent/'AstraFactory-harvest-study-20260908/bimanual/multi-harvest'
OUT=ROOT/'assets/workcells/strawberry-harvest';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(SRC))
from cel_style import apply_style
m=mujoco.MjModel.from_xml_path(str(SRC/'scene.xml'));apply_style(m);d=mujoco.MjData(m)
record=np.load(SRC/'rollout.npz');trace=json.loads((SRC/'trace.json').read_text())
def rel(p):return str(p.relative_to(ROOT))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
groups={}
for i in range(m.ngeom):
 if m.geom_group[i]>=3 or m.geom_rgba[i,3]==0:continue
 typ=int(m.geom_type[i]);s=m.geom_size[i];mid=int(m.geom_matid[i]);rgba=m.mat_rgba[mid] if mid>=0 else m.geom_rgba[i]
 if rgba[3]==0 or typ==0:continue
 if typ==7:
  k=m.geom_dataid[i];a=m.mesh_vertadr[k];b=m.mesh_faceadr[k]
  mesh=trimesh.Trimesh(m.mesh_vert[a:a+m.mesh_vertnum[k]],m.mesh_face[b:b+m.mesh_facenum[k]],process=False)
 elif typ==6:mesh=trimesh.creation.box(extents=2*s)
 elif typ==4:mesh=trimesh.creation.icosphere(subdivisions=2);mesh.vertices*=s
 elif typ==3:mesh=trimesh.creation.capsule(radius=s[0],height=2*s[1],count=[8,12])
 else:raise ValueError(typ)
 mat=np.eye(4);rot=np.zeros(9);mujoco.mju_quat2Mat(rot,m.geom_quat[i]);mat[:3,:3]=rot.reshape(3,3);mat[:3,3]=m.geom_pos[i];mesh.apply_transform(mat)
 body=m.body(m.geom_bodyid[i]).name or 'world';color=tuple(int(round(float(v)*255)) for v in rgba[:3]);groups.setdefault((body,color),[]).append(mesh)
objects=[]
for n,((body,rgb),meshes) in enumerate(groups.items()):
 p=OUT/f'{body}-{n}.stl';trimesh.util.concatenate(meshes).export(p)
 objects.append(dict(name=f'{body} {n}',body=body,color=rgb[0]*65536+rgb[1]*256+rgb[2],mesh_path=rel(p)))
frames=[]
for k in range(len(record['qpos'])):
 d.qpos[:]=record['qpos'][k];mujoco.mj_forward(m,d)
 bodies={m.body(i).name or 'world':dict(position=d.xpos[i].round(8).tolist(),quaternion=d.xquat[i][[1,2,3,0]].round(8).tolist()) for i in range(m.nbody)}
 row=trace[k];frames.append(dict(time=row['time'],phase=row['phase'],collected_count=row['collected_count'],bodies=bodies))
replay=dict(schema_version=1,label='recorded_physics',allow_explode=False,robot_instances=[],objects=objects,frames=frames,camera=dict(target=[.35,0,.25],position=[.95,-1.15,.75]),source_sha256=sha(SRC/'rollout.npz'),scene_sha256=sha(SRC/'scene.xml'),scope='Scripted state feedback; recorded MuJoCo poses; no learned policy or hardware validation.')
(OUT/'replay.json').write_text(json.dumps(replay,separators=(',',':')))
for name in ['three-strawberries-wrist-cameras.mp4','collected-3.png','preview.png','README.md','validation.json','replay-audit.json','hardware-applied.json','crop-clearance-audit.json','trace.json','events.json','rollout.npz','env_multi.py','run.py']:
 shutil.copy2(SRC/name,OUT/name)
shutil.copytree(SRC/'references',OUT/'references',dirs_exist_ok=True)
shutil.copytree(SRC.parent/'cad',OUT/'cad',dirs_exist_ok=True)
base=rel(OUT)
sources=[dict(label=label,path=base+'/'+path) for label,path in [('Cutter · STEP','cad/cutter.step'),('Catcher · STEP','cad/catcher.step'),('Basket · STEP','cad/basket.step'),('Hardware & camera specifications','hardware-applied.json'),('Evaluation · includes failed trial','validation.json'),('Replay verification','replay-audit.json'),('Fruit–planter clearance audit','crop-clearance-audit.json'),('Task implementation','env_multi.py'),('Controller implementation','run.py'),('Recorded actions & poses','rollout.npz'),('Per-step measurements','trace.json'),('Assumptions & sources','README.md')]]
manifest=dict(title='Harvest strawberries',scope_label='Two YAMs · scripted harvest baseline · simulation only',videos=[dict(id='success',title='Three-strawberry harvest',path=base+'/three-strawberries-wrist-cameras.mp4',replay_path=base+'/replay.json',caption='Same continuous 34.12 s episode. Video includes both official D405 wrist views. Scripted state feedback.',kind='scripted_execution')],metrics=[dict(label='Collected in this run',value='3 / 3',detail='Continuous episode; berries remain in the basket.'),dict(label='Completion time',value='34.12 s',detail='Simulation time, normal-speed video.'),dict(label='Complete trials',value='2 / 3',detail='One trial lost its catcher grip; not robust yet.')],limitations=['Scripted controller using simulator state. No harvesting policy has been trained.','Official wrist mount geometry; nominal camera intrinsics and estimated bracket mass.','Cutting/contact dynamics need hardware calibration.'],sources=sources,improvements=[dict(title='See the receiving area',detail='Catcher walls obstruct the wrist view. Revise tool geometry while keeping the official camera mount.'),dict(title='Retain the tool',detail='One trial lost the catcher grip. Check handle fit and contact forces before training.'),dict(title='Match visible and collision geometry',detail='The slatted basket uses a collision liner; make the liner visible in the next design revision.')])
if (OUT/'demo.json').exists():
 previous=json.loads((OUT/'demo.json').read_text())
 for key in ['environment_study_path','default_view']:
  if key in previous:manifest[key]=previous[key]
 if previous.get('environment_review'):
  manifest['environment_review']=previous['environment_review']
  if previous['environment_review'].get('plant_physics'):manifest['improvements']=previous.get('improvements',[])
  manifest['sources'] += [s for s in previous.get('sources',[]) if any(part in s.get('path','') for part in ['/environment-lab/', '/reality-gap-loop/', '/plant-physics/'])]
(OUT/'demo.json').write_text(json.dumps(manifest,indent=2))
(OUT/'package-audit.json').write_text(json.dumps(dict(frames=len(frames),objects=len(objects),source_sha256=replay['source_sha256'],exact_recorded_qpos=True,final_collected=frames[-1]['collected_count']),indent=2))
print('Packaged',len(frames),'frames,',len(objects),'mesh objects')
