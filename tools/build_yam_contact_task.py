"""Official articulated YAM with two physical fingers and an independent free peg."""
from pathlib import Path
import copy,json,xml.etree.ElementTree as X
import mujoco
P=Path(__file__).resolve().parents[1];T=P/'tasks/yam_contact_insertion';T.mkdir(exist_ok=True)
u=X.parse(P/'assets/robots/yam/v1/yam.urdf').getroot()
mc=X.SubElement(u,'mujoco');X.SubElement(mc,'compiler',discardvisual='false',fusestatic='false',strippath='false')
for mesh in u.findall('.//mesh'):mesh.set('filename',str(P/'assets/robots/yam/v1'/mesh.get('filename')))
X.ElementTree(u).write(T/'import.urdf')
m=mujoco.MjModel.from_xml_path(str(T/'import.urdf'));mujoco.mj_saveLastXML(str(T/'scene.xml'),m)
r=X.parse(T/'scene.xml').getroot();r.set('model','YAM physical contact grasp and keyed insertion')
r.find('compiler').set('angle','radian')
for mesh in r.findall('./asset/mesh'):mesh.set('file','../../assets/robots/yam/v1/assets/'+Path(mesh.get('file')).name)
opt=r.find('option')
if opt is None:opt=X.SubElement(r,'option')
opt.attrib.update(timestep='.002',integrator='implicitfast',gravity='0 0 -9.81',iterations='150',cone='elliptic',noslip_iterations='5')
default=X.SubElement(r,'default');X.SubElement(default,'geom',friction='.8 .005 .0001',solref='.005 1',solimp='.95 .99 .001',condim='4')
world=r.find('worldbody')
# Bits: world1, arm2, fingers4, free objects8. Arm self collision omitted.
for i,g in enumerate(world.findall('.//geom')):
 g.attrib.update(name='yam_geom_'+str(i),contype='2',conaffinity='9',group='0',rgba='.65 .67 .72 1')
for j in world.findall('.//joint'):
 if j.get('name') in ['joint7','joint8']:
  j.attrib.update(damping='2',armature='.002',actuatorfrcrange='-30 30')
 else:j.attrib.update(damping='.15',armature='.015',actuatorfrcrange='-10 10')
asset=r.find('asset')
# Convex decomposition of official finger meshes, retaining original local transforms.
for side in ['left','right']:
 body=world.find(f".//body[@name='tip_{side}']")
 visual=body.find('geom');visual.attrib.update(contype='0',conaffinity='0')
 pieces=sorted((P/'assets/robots/yam/collision').glob(f'tip_{side}_*.stl'))
 if not pieces:raise RuntimeError('Generate official finger convex decomposition first')
 for index,piece in enumerate(pieces):
  name=f'finger_{side}_{index}'
  X.SubElement(asset,'mesh',name=name,file='../../assets/robots/yam/collision/'+piece.name)
  collision=copy.deepcopy(visual)
  collision.attrib.update(name=name,mesh=name,contype='4',conaffinity='9',friction='1.2 .005 .0001',group='3',rgba='0 0 0 0')
  body.append(collision)
key=X.parse(P/'tasks/keyed_insertion/scene.xml').getroot()
for mesh in key.findall('./asset/mesh'):
 mesh=copy.deepcopy(mesh);mesh.set('file','../keyed_insertion/assets/'+mesh.get('file'));asset.append(mesh)
socket=copy.deepcopy(key.find("./worldbody/body[@name='socket']"));socket.set('pos','.32 0 0');world.append(socket)
for g in socket.findall('geom'):g.attrib.update(contype='1',conaffinity='14')
X.SubElement(world,'geom',name='bench',type='plane',size='.7 .7 .02',rgba='.13 .17 .21 1',contype='1',conaffinity='14')
gripper=world.find(".//body[@name='gripper']")
X.SubElement(gripper,'site',name='tool_tip',pos='0 0 -.13',size='.003',rgba='1 .2 .1 0')
peg=X.SubElement(world,'body',name='free_peg',pos='.26 -.08 .0001')
X.SubElement(peg,'freejoint',name='peg_free')
X.SubElement(peg,'inertial',pos='0 0 .033',mass='.04',diaginertia='.000017 .000017 .000002')
X.SubElement(peg,'geom',name='peg',type='mesh',mesh='peg',rgba='.96 .63 .16 1',contype='8',conaffinity='7',friction='1.2 .005 .0001')
X.SubElement(peg,'geom',name='peg_handle',type='box',pos='0 0 .054',size='.009 .007 .016',rgba='.85 .47 .09 1',contype='8',conaffinity='7',friction='1.2 .005 .0001')
X.SubElement(peg,'site',name='peg_tip',size='.002',rgba='1 .2 .1 0')
eq=X.SubElement(r,'equality');X.SubElement(eq,'joint',name='gripper_mimic',joint1='joint8',joint2='joint7',polycoef='0 1 0 0 0',solref='.002 1')
act=X.SubElement(r,'actuator')
for i in range(1,7):X.SubElement(act,'motor',name=f'motor{i}',joint=f'joint{i}',ctrlrange='-10 10',ctrllimited='true')
X.SubElement(act,'motor',name='grip',joint='joint7',ctrlrange='-30 30',ctrllimited='true')
X.SubElement(world,'light',pos='.2 -.4 1.2',dir='0 .2 -1',directional='true')
X.SubElement(world,'camera',name='overview',pos='1 -.9 .65',xyaxes='.669 .743 0 -.29 .261 .921')
X.SubElement(world,'camera',name='insertion',pos='.48 -.19 .14',xyaxes='.765 .644 0 -.27 .32 .908')
vis=X.SubElement(r,'visual');X.SubElement(vis,'global',offwidth='960',offheight='720')
X.indent(r);X.ElementTree(r).write(T/'scene.xml',encoding='unicode');(T/'import.urdf').unlink()
(T/'design.json').write_text(json.dumps({'source':'../../assets/robots/yam/source.json','tool_site':{'parent':'gripper','translation_m':[0,0,-.13]},'peg':{'joint':'free','insertion_section_m':.038,'handle_z_m':[.038,.070],'handle_size_xy_m':[.018,.014],'mass_kg':.04},'gripper':{'actuator':'grip','primary_joint':'joint7','mimic_joint':'joint8','mimic_relation':'q8=q7','joint_range_m':[-.04695,0],'close_direction':'positive toward zero (negative opens)','force_cap_n':30},'notes':['No peg weld, rigid attachment, equality or adapter stem; peg translation/orientation governed by free rigid-body physics and contacts.','Official full URDF articulated fingers and link inertias retained; 24 CoACD convex pieces per official finger mesh (see collision/DECOMPOSITION.json), original finger mesh visual only.','Arm self collisions disabled; robot/bench, robot/socket, robot/peg and finger/peg contacts enabled.','PD gains, armature, friction and gripper force cap are provisional simulation settings.']},indent=2))
import subprocess,sys
subprocess.run([sys.executable,str(P/'tools/style_yam_scene.py'),'--scene',str(T/'scene.xml')],check=True)
print(T/'scene.xml')
