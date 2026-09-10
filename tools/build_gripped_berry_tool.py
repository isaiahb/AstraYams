"""Removable berry cradle sized from the YAM jaw geometry; no tool attachment."""
import copy,json,shutil,xml.etree.ElementTree as E
from pathlib import Path
import numpy as np,trimesh,mujoco
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'tasks/yam_berry_support';OUT=ROOT/'tasks/yam_gripped_berry_support'
def add(p,tag,**kw):return E.SubElement(p,tag,{k:str(v) for k,v in kw.items()})
def vec(a):return ' '.join(f'{x:.10g}' for x in np.asarray(a).ravel())
def main():
 OUT.mkdir(exist_ok=True);root=E.parse(SOURCE/'scene.xml').getroot();assets=root.find('asset');world=root.find('worldbody');grip=root.find(".//body[@name='gripper']")
 for x in list(grip):
  if x.get('name','').startswith('support_'):grip.remove(x)
 for x in list(assets):
  if x.get('name','').startswith('support_'):assets.remove(x)
 # Tool is an independent free rigid body, supported only by jaw contact.
 tool=add(world,'body',name='grasped_cradle');add(tool,'freejoint',name='cradle_free');parts=[]
 def mesh(name,geo,mass,color):
  add(assets,'mesh',name=name,vertex=vec(geo.vertices),face=' '.join(map(str,geo.faces.ravel())))
  add(tool,'geom',name=name,type='mesh',mesh=name,mass=mass,rgba=color,contype='4',conaffinity='3',friction='.8 .003 .0001',condim='4',solref='.002 1');parts.append(geo)
 # 26 x 18 x 36 mm rounded handle, spanning the actual distal jaw pads.
 half=np.array([.013,.009,.018]);r=.0015;points=[]
 for corner in np.array(np.meshgrid(*[[-1,1]]*3)).T.reshape(-1,3):
  for d in trimesh.creation.icosphere(subdivisions=1).vertices:points.append(corner*(half-r)+r*d+[0,0,-.13])
 mesh('support_handle',trimesh.convex.convex_hull(points),.012,'.88 .49 .15 1')
 # Broad rectangular spine, overlaps both handle and cradle floor.
 beam=trimesh.creation.box(extents=[.010,.006,.052]);beam.apply_translation([0,-.0045,-.172]);mesh('support_spine',beam,.009,'.63 .69 .70 1')
 center=np.array([0,0,-.20])
 def xyz(r,a,z):return center+[r*np.cos(a),z,-r*np.sin(a)]
 # 30 mm opening, 10 mm floor and 7 mm depth, rounded 2 mm rim.
 for j in range(24):
  # Open 120-degree side provides room for adjacent berries in a truss.
  if j<4 or j>=20:continue
  angles=[2*np.pi*j/24,2*np.pi*(j+1)/24]
  v=[xyz(r,a,z) for a in angles for r,z in [(.005,0),(.014,.007),(.015,.006),(.005,-.002)]]
  mesh(f'support_cup_wall_{j}',trimesh.convex.convex_hull(v),.0002,'.12 .48 .52 1')
  a,b=[xyz(.0145,x,.0065) for x in angles];add(tool,'geom',name=f'support_cup_rim_{j}',type='capsule',fromto=vec([a,b]),size='.001',mass='.00004',rgba='.16 .57 .59 1',contype='4',conaffinity='3',friction='.8 .003 .0001',solref='.002 1')
 for k,a in enumerate([np.pi/3,5*np.pi/3]):
  add(tool,'geom',name=f'support_cup_edge_{k}',type='capsule',fromto=vec([xyz(.005,a,0),xyz(.0145,a,.0065)]),size='.001',mass='.00006',rgba='.16 .57 .59 1',contype='4',conaffinity='3',friction='.8 .003 .0001',solref='.002 1')
 add(tool,'geom',name='support_cup_floor',type='cylinder',pos='0 -.001 -.20',euler='1.57079632679 0 0',size='.005 .001',mass='.002',rgba='.12 .48 .52 1',contype='4',conaffinity='3',friction='.8 .003 .0001',solref='.002 1')
 add(tool,'site',name='support_center',pos=vec(center),size='.001',rgba='0 0 0 0')
 E.indent(root);E.ElementTree(root).write(OUT/'scene.xml',encoding='unicode');m=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));d=mujoco.MjData(m)
 old=np.load(SOURCE/'initial.npz')['qpos'];d.qpos[:len(old)]=old
 for j in ['joint7','joint8']:d.qpos[m.joint(j).qposadr[0]]=-.010
 mujoco.mj_forward(m,d);b=m.body('gripper').id;q=m.joint('cradle_free').qposadr[0];d.qpos[q:q+3]=d.xpos[b];d.qpos[q+3:q+7]=d.xquat[b];np.savez_compressed(OUT/'initial.npz',qpos=d.qpos)
 mass=float(m.body_mass[m.body('grasped_cradle').id]);trimesh.util.concatenate(parts).export(OUT/'cradle-rigid-parts.stl')
 (OUT/'build.json').write_text(json.dumps(dict(tool_mass_kg=mass,handle_mm=[26,18,36],cup_opening_mm=30,cup_depth_mm=7,side_opening_degrees=120,attachment='Independent free body. No weld, equality or kinematic parenting to the robot.',initialization='Tool is prepositioned between open jaws at reset. Grasp acquisition from a rack is not claimed.',source_scene=str(SOURCE/'scene.xml')),indent=2)+'\n');print('Tool mass',mass)
if __name__=='__main__':main()
