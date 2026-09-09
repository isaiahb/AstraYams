from pathlib import Path
import argparse,json,math
from types import SimpleNamespace
import numpy as np,mujoco,trimesh
from PIL import Image,ImageDraw,ImageFont
import imageio.v2 as imageio
P=Path(__file__).resolve().parents[1]/'assets/workcells/strawberry-specimen';ROOT=P.parents[2]
FONT=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',21)
def render(kind='rest',video=False):
 m=mujoco.MjModel.from_xml_path(str(P/'scene.xml'));d=mujoco.MjData(m);z=np.load(P/kind/'rollout.npz');renderer=mujoco.Renderer(m,800,1000);cam=mujoco.MjvCamera();cam.lookat[:]=[.02,.015,.30];cam.distance=.73;cam.azimuth=95;cam.elevation=-12
 # Neutral material render to inspect geometry. Thin details remain legible.
 def frame(i,az=95,el=-12):
  d.qpos[:]=z['qpos'][i];mujoco.mj_forward(m,d);cam.azimuth=az;cam.elevation=el;renderer.update_scene(d,cam);im=Image.fromarray(renderer.render());dr=ImageDraw.Draw(im);dr.rectangle((0,0,1000,73),fill='#17251d')
  if kind=='rest':label='Reference-based specimen · gravity settling'
  else:label={'leaf':'Leaf brushing','stalk':'Stalk bending','neighbor':'Neighboring fruit contact'}[kind.split('-')[0]]+' · force-limited probe'+(' · no-contact control' if 'control' in kind else '')
  dr.text((22,12),label,font=FONT,fill='white');dr.text((22,42),f't = {z["t"][i]:.2f} s · inferred depth / mechanics uncalibrated · no cutting',font=FONT,fill='#cfdbc8');return im
 for name,az,el in [('front',90,-8),('three-quarter',125,-22),('side',180,-12),('top',90,-60)]:frame(-1,az,el).save(P/kind/f'{name}.png')
 if kind=='rest':
  frame(0).save(P/kind/'unloaded.png');cam.lookat[:]=[0,.055,.29];cam.distance=.19;frame(-1,125,-32).save(P/kind/'crown-close.png');cam.lookat[:]=[.02,.015,.30];cam.distance=.73
 if video:
  with imageio.get_writer(P/kind/'demo.mp4',fps=25,codec='libx264',quality=8,macro_block_size=2) as wr:
   for i in range(0,len(z['t']),2):wr.append_data(np.array(frame(i,110,-18)))
   if kind=='rest':
    for j in range(150):wr.append_data(np.array(frame(-1,110+j*1.8,-18)))
 renderer.close();print(P/kind)
def export():
 m=mujoco.MjModel.from_xml_path(str(P/'scene.xml'));d=mujoco.MjData(m);groups={};mp=P/'meshes';mp.mkdir(exist_ok=True)
 for i in range(m.ngeom):
  typ=int(m.geom_type[i]);size=m.geom_size[i];color=m.geom_rgba[i]
  if color[3]==0 or typ==0:continue
  if typ==7:
   k=m.geom_dataid[i];a=m.mesh_vertadr[k];b=m.mesh_faceadr[k];geo=trimesh.Trimesh(m.mesh_vert[a:a+m.mesh_vertnum[k]],m.mesh_face[b:b+m.mesh_facenum[k]],process=False)
  elif typ==6:geo=trimesh.creation.box(extents=2*size)
  elif typ==4:geo=trimesh.creation.icosphere(subdivisions=2);geo.vertices*=size
  elif typ==2:geo=trimesh.creation.icosphere(subdivisions=2,radius=size[0])
  elif typ==3:geo=trimesh.creation.capsule(radius=size[0],height=2*size[1],count=[8,12])
  else:continue
  mat=np.eye(4);rot=np.zeros(9);mujoco.mju_quat2Mat(rot,m.geom_quat[i]);mat[:3,:3]=rot.reshape(3,3);mat[:3,3]=m.geom_pos[i];geo.apply_transform(mat);body=m.body(m.geom_bodyid[i]).name or 'world';rgb=tuple(int(float(c)*255) for c in color[:3]);groups.setdefault((body,rgb),[]).append(geo)
 objects=[];meshes=[]
 for idx,((body,rgb),parts) in enumerate(groups.items()):
  geo=trimesh.util.concatenate(parts);name=f'{body}-{idx}.stl';geo.export(mp/name);objects.append({'name':body+' '+str(idx),'body':body,'color':rgb[0]*65536+rgb[1]*256+rgb[2],'mesh_path':str((mp/name).relative_to(ROOT))});meshes.append((body,rgb,geo))
 for kind in ['rest','leaf','stalk','neighbor']:
  qpath=P/kind/'rollout.npz'
  if not qpath.exists():continue
  z=np.load(qpath);frames=[]
  for q,t in zip(z['qpos'][::2],z['t'][::2]):
   d.qpos[:]=q;mujoco.mj_forward(m,d);bodies={m.body(i).name or 'world':dict(position=d.xpos[i].round(7).tolist(),quaternion=d.xquat[i][[1,2,3,0]].round(7).tolist()) for i in range(m.nbody)};frames.append(dict(time=float(t),phase=kind+' · recorded physics',bodies=bodies))
  (P/kind/'replay.json').write_text(json.dumps(dict(schema_version=1,label='recorded_physics',allow_explode=False,robot_instances=[],objects=objects,frames=frames,camera=dict(target=[.02,.015,.30],position=[.35,-.64,.52]),scope='Reference-informed, inferred depth. Contact-only diagnostic; no cutting; uncalibrated.'),separators=(',',':')))
  if kind=='rest':
   scene=trimesh.Scene()
   for body,rgb,geo in meshes:
    pose=frames[-1]['bodies'][body];mat=trimesh.transformations.quaternion_matrix([pose['quaternion'][3],*pose['quaternion'][:3]]);mat[:3,3]=pose['position'];g=geo.copy();g.visual.vertex_colors=[*rgb,255];scene.add_geometry(g,node_name=body+'-'+str(len(scene.geometry)),transform=mat)
   scene.export(P/'specimen-settled.glb')
 print('Exported',len(objects),'mesh groups and recorded replays')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--kind',default='rest');p.add_argument('--video',action='store_true');p.add_argument('--export',action='store_true');a=p.parse_args();export() if a.export else render(a.kind,a.video)
