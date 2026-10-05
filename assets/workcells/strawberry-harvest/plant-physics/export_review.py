from pathlib import Path
import json,shutil,sys,hashlib
import numpy as np,mujoco,trimesh
P=Path(__file__).resolve().parent;ROOT=P.parents[1].parent/'AstraFactory';OUT=ROOT/'assets/workcells/strawberry-harvest/plant-physics';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(P.parent/'multi-harvest'));from cel_style import apply_style
SRC=P/'surface-matched';m=mujoco.MjModel.from_xml_path(str(SRC/'scene.xml'));apply_style(m);d=mujoco.MjData(m);z=np.load(SRC/'rollout.npz');groups={}
for i in range(m.ngeom):
 if m.geom_group[i]>=3 or m.geom_rgba[i,3]==0:continue
 typ=int(m.geom_type[i]);s=m.geom_size[i];mid=m.geom_matid[i];rgba=m.mat_rgba[mid] if mid>=0 else m.geom_rgba[i]
 if rgba[3]==0 or typ==0:continue
 if typ==7:
  k=m.geom_dataid[i];a=m.mesh_vertadr[k];b=m.mesh_faceadr[k];mesh=trimesh.Trimesh(m.mesh_vert[a:a+m.mesh_vertnum[k]],m.mesh_face[b:b+m.mesh_facenum[k]],process=False)
 elif typ==6:mesh=trimesh.creation.box(extents=2*s)
 elif typ==4:mesh=trimesh.creation.icosphere(subdivisions=2);mesh.vertices*=s
 elif typ==2:mesh=trimesh.creation.icosphere(subdivisions=2,radius=s[0])
 elif typ==3:mesh=trimesh.creation.capsule(radius=s[0],height=2*s[1],count=[8,12])
 else:raise ValueError(typ)
 mat=np.eye(4);rot=np.zeros(9);mujoco.mju_quat2Mat(rot,m.geom_quat[i]);mat[:3,:3]=rot.reshape(3,3);mat[:3,3]=m.geom_pos[i];mesh.apply_transform(mat)
 body=m.body(m.geom_bodyid[i]).name or 'world';color=tuple(int(round(float(v)*255)) for v in rgba[:3]);groups.setdefault((body,color),[]).append(mesh)
objects=[]
for n,((body,rgb),meshes) in enumerate(groups.items()):
 p=OUT/f'{body}-{n}.stl';trimesh.util.concatenate(meshes).export(p);objects.append(dict(name=f'{body} {n}',body=body,color=rgb[0]*65536+rgb[1]*256+rgb[2],mesh_path=str(p.relative_to(ROOT))))
frames=[]
for q,t in zip(z['qpos'],z['t']):
 d.qpos[:]=q;mujoco.mj_forward(m,d);bodies={m.body(i).name or 'world':dict(position=d.xpos[i].round(8).tolist(),quaternion=d.xquat[i][[1,2,3,0]].round(8).tolist()) for i in range(m.nbody)}
 phase='Gravity settling' if t<3 else 'Physical contact probe' if t<4.5 else 'Withdraw and recover';frames.append(dict(time=float(t),phase=phase,bodies=bodies))
(OUT/'replay.json').write_text(json.dumps(dict(schema_version=1,label='recorded_physics',allow_explode=False,robot_instances=[],objects=objects,frames=frames,camera=dict(target=[.53,.13,.34],position=[.7,-.48,.52]),scope='Diagnostic plant interaction. Scripted probe; no learned harvest; uncalibrated tissue properties.'),separators=(',',':')))
print('Exported',len(objects),'objects',len(frames),'frames to',OUT)
