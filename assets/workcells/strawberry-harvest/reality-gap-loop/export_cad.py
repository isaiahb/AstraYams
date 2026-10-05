"""Export editable STEP solids directly from the same MJCF tool geometry (mm)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'multi-harvest'))
from env_multi import *
HERE=Path(__file__).resolve().parent/'cad_revision'
import cadquery as cq
from scipy.spatial.transform import Rotation
out=HERE/'cad';out.mkdir(exist_ok=True)
m=mujoco.MjModel.from_xml_path(str(HERE/'scene.xml'));d=mujoco.MjData(m);mujoco.mj_forward(m,d)
reports={}
for name in ['catcher','basket']:
 bid=m.body(name).id;ass=cq.Assembly(name=name);shapes=[];parts=[]
 for g in range(m.ngeom):
  b=int(m.geom_bodyid[g]);p=b
  while p and p!=bid:p=int(m.body_parentid[p])
  if p!=bid:continue
  # invisible basket contact sheets are legitimate wall solids, exported too.
  typ=int(m.geom_type[g]);s=m.geom_size[g]*1000
  if typ==mujoco.mjtGeom.mjGEOM_BOX:shape=cq.Workplane('XY').box(*(2*s)).val()
  elif typ==mujoco.mjtGeom.mjGEOM_CYLINDER:shape=cq.Workplane('XY').circle(s[0]).extrude(2*s[1]).translate((0,0,-s[1])).val()
  elif typ==mujoco.mjtGeom.mjGEOM_CAPSULE:
   shape=cq.Workplane('XY').circle(s[0]).extrude(2*s[1]).translate((0,0,-s[1])).union(cq.Workplane('XY').sphere(s[0]).translate((0,0,s[1]))).union(cq.Workplane('XY').sphere(s[0]).translate((0,0,-s[1]))).val()
  else:continue
  R=d.xmat[bid].reshape(3,3).T@d.geom_xmat[g].reshape(3,3);v=Rotation.from_matrix(R).as_rotvec();ang=np.linalg.norm(v)
  if ang>1e-9:shape=shape.rotate((0,0,0),tuple(v/ang),float(np.degrees(ang)))
  pos=(d.xmat[bid].reshape(3,3).T@(d.geom_xpos[g]-d.xpos[bid]))*1000;shape=shape.translate(tuple(pos));part=m.geom(g).name or f'part_{g}'
  color=(.12,.29,.28) if 'blade' not in part and 'shear' not in part else (.7,.75,.76)
  ass.add(shape,name=part,color=cq.Color(*color));shapes.append(shape);parts.append(part)
 ass.save(str(out/(name+'.step')));cq.exporters.export(cq.Compound.makeCompound(shapes),str(out/(name+'.stl')))
 reports[name]={'parts':parts,'step':name+'.step','stl':name+'.stl','units':'millimetres'}
(out/'manifest.json').write_text(json.dumps(reports,indent=2));print(reports)
