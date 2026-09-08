"""Untrained bimanual manual-vise layout and kinematic screening.

Pose solving below is design analysis only, never presented as learned/contact
manipulation. The manual screw has no motor; its jaw coupling is mechanical.
"""
import copy,json,math
from pathlib import Path
import xml.etree.ElementTree as ET
import mujoco,numpy as np
from astrafactory.yam_env import rotation_error,yaw_matrix

OUT=Path('runs/bimanual-vise-design');OUT.mkdir(parents=True,exist_ok=True)
root=ET.parse('tasks/yam_machine_tending/scene.xml').getroot();world=root.find('worldbody');base=world.find("body[@name='base']");right=copy.deepcopy(base)
for n in right.iter():
 if 'name' in n.attrib:n.set('name','right_'+n.get('name'))
right.set('pos','.32 .50 0');ang=-math.pi/2;right.set('quat',f'{math.cos(ang/2)} 0 0 {math.sin(ang/2)}');world.append(right)
for i,b in enumerate([base,right]):
 for g in b.iter('geom'):
  if g.get('type')=='mesh' or g.get('mesh'):
   if int(g.get('contype','1'))==0:g.set('contype',str(16 if i==0 else 32));g.set('conaffinity',str(33 if i==0 else 17))
act=root.find('actuator')
for a in list(act):
 if a.get('name')=='vise_motor':act.remove(a);continue
 c=copy.deepcopy(a);c.set('name','right_'+c.get('name'));c.set('joint','right_'+c.get('joint'));act.append(c)
eq=root.find('equality')
for a in list(eq):
 c=copy.deepcopy(a)
 for key in ['name','joint1','joint2']:
  if key in c.attrib:c.set(key,'right_'+c.get(key))
 eq.append(c)
vise=world.find("body[@name='vise']");vise.set('pos','.32 0 .105');fin=world.find("body[@name='finished_stock']");fin.set('pos','.32 0 .1251')
ET.SubElement(world,'geom',name='manual_pedestal',type='box',pos='.32 .035 .0525',size='.055 .09 .0525',rgba='.18 .23 .26 1',contype='1',conaffinity='62')
screw=ET.SubElement(world,'body',name='manual_screw',pos='.32 .135 .160')
ET.SubElement(screw,'joint',name='manual_screw_spin',type='hinge',axis='0 1 0',damping='.0005',frictionloss='.004',limited='true',range='-24 1')
ET.SubElement(screw,'geom',name='manual_hub',type='cylinder',fromto='0 -.005 0 0 .005 0',size='.008',density='7800',contype='1',conaffinity='62',rgba='.25 .28 .3 1')
ET.SubElement(screw,'geom',name='manual_crank',type='capsule',fromto='0 0 0 .035 0 0',size='.003',density='7800',contype='1',conaffinity='62',rgba='.4 .45 .46 1')
sleeve=ET.SubElement(screw,'body',name='manual_grip_sleeve',pos='.035 .022 0')
ET.SubElement(sleeve,'joint',name='manual_sleeve_spin',type='hinge',axis='0 1 0',damping='.00005',frictionloss='.00005')
ET.SubElement(sleeve,'geom',name='manual_pin',type='capsule',fromto='0 -.012 0 0 .012 0',size='.004',density='1200',contype='1',conaffinity='62',rgba='.08 .12 .13 1')
ET.SubElement(screw,'geom',name='manual_crank_b',type='capsule',fromto='0 0 0 -.035 0 0',size='.003',density='7800',contype='1',conaffinity='62',rgba='.4 .45 .46 1')
sleeve_b=ET.SubElement(screw,'body',name='manual_grip_sleeve_b',pos='-.035 .022 0')
ET.SubElement(sleeve_b,'joint',name='manual_sleeve_spin_b',type='hinge',axis='0 1 0',damping='.00005',frictionloss='.00005')
ET.SubElement(sleeve_b,'geom',name='manual_pin_b',type='capsule',fromto='0 -.012 0 0 .012 0',size='.004',density='1200',contype='1',conaffinity='62',rgba='.08 .12 .13 1')
ET.SubElement(eq,'joint',name='manual_leadscrew_coupling',joint1='vise_joint',joint2='manual_screw_spin',polycoef=f'.006 {0.002/(2*math.pi)} 0 0 0',solref='.003 1')
# Preserve relative mesh resolution when loading this design scene from runs.
for mesh in root.findall('asset/mesh'):
 if mesh.get('file'):mesh.set('file',str((Path('tasks/yam_machine_tending')/mesh.get('file')).resolve()))
scene=OUT/'scene.xml';ET.ElementTree(root).write(scene,encoding='unicode');m=mujoco.MjModel.from_xml_path(str(scene));d=mujoco.MjData(m)

def ik(prefix,p,R,initial=None):
 js=[m.joint(prefix+f'joint{i}').id for i in range(1,7)];qa=m.jnt_qposadr[js];va=m.jnt_dofadr[js];limits=m.jnt_range[js];scratch=mujoco.MjData(m);scratch.qpos[:]=d.qpos;sid=m.site(prefix+'tool_tip').id;jp=np.zeros((3,m.nv));jr=jp.copy();rng=np.random.default_rng(211);best=None;score=1e9
 for attempt in range(10):
  q=np.asarray(initial if attempt==0 and initial is not None else rng.uniform(limits[:,0]+.02,limits[:,1]-.02)).copy()
  for _ in range(300):
   scratch.qpos[qa]=q;mujoco.mj_forward(m,scratch);err=np.r_[p-scratch.site_xpos[sid],.15*rotation_error(R,scratch.site_xmat[sid].reshape(3,3))];loss=np.linalg.norm(err)
   if loss<score:score=loss;best=q.copy()
   if loss<1e-6:return best,float(score)
   mujoco.mj_jacSite(m,scratch,jp,jr,sid);J=np.r_[jp[:,va],.15*jr[:,va]];dq=J.T@np.linalg.solve(J@J.T+np.eye(6)*1e-5,err);q=np.clip(q+np.clip(dq,-.15,.15),limits[:,0]+1e-5,limits[:,1]-1e-5)
 return best,float(score)

def setarm(prefix,q):
 for i,x in enumerate(q,1):d.qpos[m.joint(prefix+f'joint{i}').qposadr]=x
 for i in [7,8]:d.qpos[m.joint(prefix+f'joint{i}').qposadr]=-.008

def collision_report():
 rows=[]
 for c in d.contact:
  if c.dist>=-.0005:continue
  names=[m.body(int(m.geom_bodyid[g])).name or 'world' for g in c.geom];isr=[n.startswith('right_') for n in names];isl=[n in ['base','link1','link2','link3','link4','link5','link6','gripper','tip_left','tip_right'] for n in names]
  if any(isr) and any(isl):rows.append({'bodies':names,'depth_m':-float(c.dist)})
 return rows
left,le=ik('',np.array([.32,0,.179]),yaw_matrix(np.pi),np.array([0,1.4,1.4,0,0,0]));setarm('',left)
rows=[];poses=[];Rapproach=np.array([[1,0,0],[0,0,1],[0,-1,0]])
for deg in range(0,-181,-30):
 theta=math.radians(deg);Ry=np.array([[math.cos(theta),0,math.sin(theta)],[0,1,0],[-math.sin(theta),0,math.cos(theta)]]);p=np.array([.32,.157,.160])+Ry@np.array([.035,0,0]);R=Rapproach;q,error=ik('right_',p,R);setarm('right_',q);d.qpos[m.joint('manual_screw_spin').qposadr]=theta;d.qpos[m.joint('vise_joint').qposadr]=.006+.002/(2*math.pi)*theta;mujoco.mj_forward(m,d);cols=collision_report();rows.append({'angle_deg':deg,'position_m':p.tolist(),'ik_weighted_error':error,'reachable':error<.0003,'arm_arm_penetrations':cols});poses.append(d.qpos.copy());print(json.dumps(rows[-1]),flush=True)
np.savez_compressed(OUT/'design-poses.npz',qpos=poses);report={'status':'untrained design screening','left_arm_error':le,'right_base_position':[.32,.50,0],'right_base_yaw':ang,'manual_axis':[.32,.135,.160],'screw_pitch_m':.002,'loading_gap_m':.020,'turns_to_nominal_stock_width':3,'screw_actuator':None,'rows':rows,'scope':'Independent IK sample poses, not physically executed motions. Convex visual-mesh inter-arm penetration screen only; full fixture/handle swept clearance and contact grasp still need validation. Mechanical gear equality is an ideal screw constraint, not a welded gripper.'};(OUT/'report.json').write_text(json.dumps(report,indent=2))
