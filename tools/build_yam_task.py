"""Build articulated YAM from official URDF, preserving link inertias and frames."""
from pathlib import Path
import copy,json,xml.etree.ElementTree as X
import mujoco
P=Path(__file__).resolve().parents[1];T=P/'tasks/yam_keyed_insertion';T.mkdir(exist_ok=True)
u=X.parse(P/'assets/robots/yam/v1/yam.urdf').getroot()
mc=X.SubElement(u,'mujoco');X.SubElement(mc,'compiler',discardvisual='false',fusestatic='false',strippath='false')
for mesh in u.findall('.//mesh'):
 mesh.set('filename',str(P/'assets/robots/yam/v1'/mesh.get('filename')))
for j in u.findall('joint'):
 if j.get('name') in ['joint7','joint8']:
  j.set('type','fixed')
  pos=[float(v) for v in j.find('origin').get('xyz').split()];pos[1]+= -.030 if j.get('name')=='joint7' else .030
  j.find('origin').set('xyz',' '.join(map(str,pos)))
X.ElementTree(u).write(T/'import.urdf')
m=mujoco.MjModel.from_xml_path(str(T/'import.urdf'));mujoco.mj_saveLastXML(str(T/'scene.xml'),m)
r=X.parse(T/'scene.xml').getroot();r.set('model','Official YAM articulated keyed insertion')
compiler=r.find('compiler');compiler.set('angle','radian')
for mesh in r.findall('.//asset/mesh'):
 mesh.set('file','../../assets/robots/yam/v1/assets/'+Path(mesh.get('file')).name)
opt=r.find('option')
if opt is None:opt=X.SubElement(r,'option')
opt.attrib.update(timestep='.002',integrator='implicitfast',gravity='0 0 -9.81',iterations='100')
default=X.SubElement(r,'default');X.SubElement(default,'geom',friction='.5 .005 .0001',solref='.005 1',solimp='.95 .99 .001',condim='3')
world=r.find('worldbody')
for i,g in enumerate(world.findall('.//geom')):
 g.attrib.update(name='yam_geom_'+str(i),contype='2',conaffinity='1',group='0',rgba='.65 .67 .72 1')
for j in world.findall('.//joint'):
 j.attrib.update(damping='.15',armature='.015')
 # Official MJCF uses ±10 Nm whereas URDF effort=1 is a placeholder.
 j.set('actuatorfrcrange','-10 10')
asset=r.find('asset')
key=X.parse(P/'tasks/keyed_insertion/scene.xml').getroot()
for mesh in key.findall('./asset/mesh'):
 mesh=copy.deepcopy(mesh);mesh.set('file','../keyed_insertion/assets/'+mesh.get('file'));asset.append(mesh)
socket=copy.deepcopy(key.find("./worldbody/body[@name='socket']"));socket.set('pos','.32 0 0');world.append(socket)
for g in socket.findall('geom'):g.set('conaffinity','3')
X.SubElement(world,'geom',name='bench',type='plane',size='.7 .7 .02',rgba='.13 .17 .21 1',conaffinity='3')
gripper=world.find(".//body[@name='gripper']")
held=X.SubElement(gripper,'body',name='held_peg',pos='0 0 -.17')
X.SubElement(held,'inertial',pos='0 0 .019',mass='.025',diaginertia='.0000035 .0000035 .000001')
X.SubElement(held,'geom',name='peg',type='mesh',mesh='peg',rgba='.96 .63 .16 1',contype='2',conaffinity='1')
X.SubElement(held,'site',name='peg_tip',size='.002',rgba='1 .2 .1 0')
# A rigid stem visibly explains the prepared attachment; no grasp acquisition.
X.SubElement(gripper,'geom',name='peg_adapter',type='cylinder',pos='0 0 -.115',size='.008 .017',rgba='.4 .43 .46 1',contype='2',conaffinity='1')
X.SubElement(world,'light',pos='.2 -.4 1.2',dir='0 .2 -1',directional='true')
X.SubElement(world,'camera',name='overview',pos='1 -.9 .65',xyaxes='.669 .743 0 -.29 .261 .921')
X.SubElement(world,'camera',name='insertion',pos='.48 -.19 .14',xyaxes='.765 .644 0 -.27 .32 .908')
vis=X.SubElement(r,'visual');X.SubElement(vis,'global',offwidth='960',offheight='720')
act=X.SubElement(r,'actuator')
for i in range(1,7):X.SubElement(act,'motor',name=f'motor{i}',joint=f'joint{i}',ctrlrange='-10 10',ctrllimited='true')
X.indent(r);X.ElementTree(r).write(T/'scene.xml',encoding='unicode')
spec=json.loads((P/'tasks/keyed_insertion/task.json').read_text());spec.update(id='yam-keyed-insertion-v0',observation_size=31,horizon=600,plugin='task.py',reward_plugin='reward.py',embodiment='Official six-axis YAM URDF; fixed prepared gripper and rigid peg adapter; no grasp acquisition')
spec['controller']={'type':'joint_delta_pd','joints':[f'joint{i}' for i in range(1,7)],'actuators':[f'motor{i}' for i in range(1,7)],'action_scale':[.01]*6,'kp':[300,300,300,150,100,80],'kd':[25,25,20,10,8,6]}
spec['observation_contract']='q6, qvel6, target6, end-effector position error3 and rotation-vector error3, previous action6, contact scalar1 (31)'
# 6+6+6+6+6+1 =31.
(T/'task.json').write_text(json.dumps(spec,indent=2))
(T/'task.py').write_text('from astrafactory.yam_env import YamTask as Task\n')
(T/'reward.py').write_text((P/'tasks/keyed_insertion/reward.py').read_text())
(T/'design.json').write_text(json.dumps({'source':'../../assets/robots/yam/source.json','tool_transform':{'parent':'gripper','translation_m':[0,0,-.17],'quaternion_wxyz':[1,0,0,0]},'notes':['Official URDF inertias retained, fingers fixed at joint displacement -0.030 m.','URDF visual meshes used as convex collisions against bench/socket; arm self collisions disabled by masks because source has no validated collision decomposition.','Arm torque caps ±10 Nm follow upstream MJCF; PD, damping, armature and held adapter mass provisional.','Peg attached rigidly; grasp acquisition not simulated.']},indent=2))
(T/'import.urdf').unlink()
import subprocess,sys
subprocess.run([sys.executable,str(P/'tools/style_yam_scene.py'),'--scene',str(T/'scene.xml')],check=True)
print(T/'scene.xml')
