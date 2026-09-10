"""Reuse v14 specimen + official YAM for the learned support experiment.

Foliage is fixed at the previously settled pose; fruit-bearing branches remain
articulated. This reduction is explicit and is not full plant-fidelity validation.
"""
import copy,json
from pathlib import Path
import xml.etree.ElementTree as E
import mujoco,numpy as np,trimesh

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tasks/yam_berry_support'
PLANT=ROOT/'assets/workcells/strawberry-specimen/fruit-study/v14'
ARM=ROOT/'tasks/yam_contact_curriculum/scene.xml'
def vec(x):return ' '.join(f'{v:.10g}' for v in np.ravel(x))
def add(p,tag,**kw):return E.SubElement(p,tag,{k:str(v) for k,v in kw.items()})

def main():
 OUT.mkdir(exist_ok=True)
 root=E.parse(PLANT/'scene.xml').getroot();src=mujoco.MjModel.from_xml_path(str(PLANT/'scene.xml'));state=mujoco.MjData(src)
 state.qpos[:]=np.load(PLANT/'rest/rollout.npz')['qpos'][-1];mujoco.mj_forward(src,state)
 world=root.find('worldbody');assets=root.find('asset');root.find('actuator').clear()
 for e in list(root.find('contact')):
  if 'probe' in str(e.attrib):root.find('contact').remove(e)
 world.remove(world.find("body[@name='probe']"))
 # Freeze only the leaf-bearing branches in their accepted settled pose.
 crown=world.find("body[@name='crown']")
 for branch in crown.findall('body'):
  if branch.get('name')=='peduncle_0':continue
  for b in branch.iter('body'):
   bid=src.body(b.get('name')).id;parent=src.body_parentid[bid];R=state.xmat[parent].reshape(3,3)
   b.set('pos',vec(R.T@(state.xpos[bid]-state.xpos[parent])))
   rot=R.T@state.xmat[bid].reshape(3,3);q=np.zeros(4);mujoco.mju_mat2Quat(q,rot.ravel());b.set('quat',vec(q));b.attrib.pop('euler',None)
   for j in b.findall('joint'):b.remove(j)
 # Preserve foliage surface contacts as static obstacles; no invisible geometry.
 plant=add(world,'body',name='plant_frame',pos='.32 .10 .08')
 for b in list(world):
  if b is not plant and b.tag in ['body','geom'] and b.get('name')!='ground':world.remove(b);plant.append(b)
 for g in plant.iter('geom'):
  if g.get('contype')!='0':g.set('contype','1');g.set('conaffinity','7')
 orig=E.parse(ARM).getroot()
 for a in orig.find('asset'):
  a=copy.deepcopy(a)
  if 'file' in a.attrib:a.set('file',str((ARM.parent/a.get('file')).resolve()))
  if a.get('name') not in {x.get('name') for x in assets}:assets.append(a)
 robot=copy.deepcopy(orig.find('worldbody/body'));robot.set('pos','0 -.30 0');world.append(robot)
 for g in robot.iter('geom'):
  if g.get('contype')!='0':g.set('contype','2');g.set('conaffinity','1')
  g.set('rgba','.38 .42 .44 1')
 for a in orig.find('actuator'):root.find('actuator').append(copy.deepcopy(a))
 eq=add(root,'equality')
 for e in orig.find('equality'):
  if e.tag=='joint':eq.append(copy.deepcopy(e))
 grip=robot.find(".//body[@name='gripper']");center=np.array([0,0,-.20])
 add(grip,'geom',name='support_mount',type='capsule',fromto='0 -.008 -.10 0 -.008 -.20',size='.004',mass='.015',rgba='.25 .31 .33 1',contype='4',conaffinity='1')
 # Cup local normal +Y becomes world +Z in nominal horizontal wrist pose.
 def transform(v):return center+np.array([v[0],v[2],-v[1]])
 for j in range(20):
  vs=[transform([r*np.cos(a),r*np.sin(a),z]) for a in [2*np.pi*j/20,2*np.pi*(j+1)/20] for r,z in [(.002,0),(.008,.004),(.009,.003),(.002,-.002)]]
  h=trimesh.convex.convex_hull(vs);name=f'support_cup_{j}'
  add(assets,'mesh',name=name,vertex=vec(h.vertices),face=' '.join(map(str,h.faces.ravel())))
  add(grip,'geom',name=name,type='mesh',mesh=name,mass='.0002',rgba='.07 .46 .55 1',contype='4',conaffinity='1',friction='.4 .003 .001',solref='.002 1')
 add(grip,'geom',name='support_cup_floor',type='cylinder',pos='0 -.001 -.20',euler='1.57079632679 0 0',size='.002 .001',mass='.001',rgba='.07 .46 .55 1',contype='4',conaffinity='1',solref='.002 1')
 add(grip,'site',name='support_center',pos=vec(center),size='.001',rgba='0 0 0 0')
 root.find('option').set('timestep','.0005');root.find('option').set('integrator','implicitfast')
 add(world,'camera',name='overview',pos='.9 -.95 .65',xyaxes='.78 .63 0 -.3 .37 .88')
 add(world,'camera',name='contact',pos='.51 -.15 .31',xyaxes='.7 .7 0 -.23 .23 .94')
 E.indent(root);E.ElementTree(root).write(OUT/'scene.xml',encoding='unicode')
 m=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));d=mujoco.MjData(m)
 for j in range(m.njnt):
  name=m.joint(j).name
  if name and name.endswith('_bend'):
   a=m.jnt_qposadr[j];b=src.joint(name).qposadr[0];d.qpos[a:a+4]=state.qpos[b:b+4]
 qids=np.array([m.joint(f'joint{i}').qposadr[0] for i in range(1,7)]);vids=np.array([m.joint(f'joint{i}').dofadr[0] for i in range(1,7)])
 mujoco.mj_forward(m,d);bid=m.body('fruit_primary').id;bottom=d.xpos[bid]+d.xmat[bid].reshape(3,3)@np.array([0,0,-.039])
 desired=np.array([*d.xipos[bid][:2],bottom[2]])+[0,-.045,-.018]
 R=np.array([[1,0,0],[0,0,-1],[0,1,0.]])
 from astrafactory.yam_env import rotation_error
 sid=m.site('support_center').id;jp=np.zeros((3,m.nv));jr=jp.copy();rng=np.random.default_rng(6);limits=np.array([m.joint(f'joint{i}').range for i in range(1,7)])
 best=None;loss=1e9
 for restart in range(30):
  q=rng.uniform(limits[:,0],limits[:,1])
  for _ in range(180):
   d.qpos[qids]=q;mujoco.mj_forward(m,d);err=np.r_[desired-d.site_xpos[sid],.15*rotation_error(R,d.site_xmat[sid].reshape(3,3))]
   if np.linalg.norm(err)<loss:loss=np.linalg.norm(err);best=q.copy()
   if loss<1e-5:break
   mujoco.mj_jacSite(m,d,jp,jr,sid);J=np.r_[jp[:,vids],.15*jr[:,vids]];dq=J.T@np.linalg.solve(J@J.T+np.eye(6)*1e-5,err);q=np.clip(q+np.clip(dq,-.12,.12),limits[:,0]+.001,limits[:,1]-.001)
  if loss<1e-5:break
 if loss>.001:raise RuntimeError(f'Cannot initialize fixed start: {loss}')
 d.qpos[qids]=best
 for i in [7,8]:d.qpos[m.joint(f'joint{i}').qposadr[0]]=-.015
 d.qvel[:]=0;mujoco.mj_forward(m,d)
 np.savez_compressed(OUT/'initial.npz',qpos=d.qpos,qvel=d.qvel)
 (OUT/'build.json').write_text(json.dumps(dict(plant=str(PLANT),arm=str(ARM),nq=m.nq,nv=m.nv,ngeom=m.ngeom,initial_ik_error=float(loss),initial_joint_position=best.tolist(),nominal_target=bottom.tolist(),scope='Fixed cup mounted to wrist; static settled foliage; dynamic fruit-bearing branches. IK used once to build constant initialization only.'),indent=2))
 print((OUT/'build.json').read_text())

if __name__=='__main__':main()
