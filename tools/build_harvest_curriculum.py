"""A reduced free-space/cutting curriculum, never substituted for final physics.

Freeze the settled canopy and unloaded textile internal coordinates. Preserve
all visible and contact geometry, two arms, free contact-held catcher, dynamic
fruit/stalks and cut mechanism. Final evaluation must use the full task.
"""
from pathlib import Path
import argparse,copy,json,xml.etree.ElementTree as E
import numpy as np,mujoco

def build(source,out,keep_net=False):
 source=Path(source).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 root=E.parse(source/'task/scene.xml').getroot();m=mujoco.MjModel.from_xml_path(str(source/'task/scene.xml'));d=mujoco.MjData(m);z=np.load(source/'episode-61001.npz');d.qpos[:]=z['qpos'][0];mujoco.mj_forward(m,d);frozen=[]
 for b in root.iter('body'):
  name=b.get('name','');joints=list(b.findall('joint'))
  prefixes=('petiole_','leaf_') if keep_net else ('petiole_','leaf_','net_node_')
  if not joints or not name.startswith(prefixes):continue
  bi=m.body(name).id;pa=m.body_parentid[bi];rp=d.xmat[pa].reshape(3,3);R=rp.T@d.xmat[bi].reshape(3,3);q=np.zeros(4);mujoco.mju_mat2Quat(q,R.ravel())
  b.set('pos',' '.join(map(str,rp.T@(d.xpos[bi]-d.xpos[pa]))));b.set('quat',' '.join(map(str,q)));b.attrib.pop('euler',None)
  for j in joints:frozen.append(j.get('name'));b.remove(j)
 E.ElementTree(root).write(out/'scene.xml',encoding='unicode');n=mujoco.MjModel.from_xml_path(str(out/'scene.xml'));nd=mujoco.MjData(n)
 addresses=[]
 for j in range(n.njnt):
  name=n.joint(j).name;old=m.joint(name);count={0:7,1:4,2:1,3:1}[int(n.jnt_type[j])];addresses.extend(range(old.qposadr[0],old.qposadr[0]+count))
 mapping=np.array(addresses);np.savez_compressed(out/'initial.npz',qpos=z['qpos'][0,mapping]);np.save(out/'qpos-map.npy',mapping)
 vmap=[]
 for j in range(n.njnt):
  old=m.joint(n.joint(j).name);count={0:6,1:3,2:1,3:1}[int(n.jnt_type[j])];vmap.extend(range(old.dofadr[0],old.dofadr[0]+count))
 np.save(out/'qvel-map.npy',vmap)
 report=dict(source=str(source),frozen_joints=frozen,net_dynamic=keep_net,nv_before=m.nv,nv_after=n.nv,scope='Settled canopy frozen; dynamic textile retained.' if keep_net else __doc__,final_validation_required=True);(out/'curriculum.json').write_text(json.dumps(report,indent=2)+'\n');print('Curriculum nv',m.nv,'->',n.nv,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path('runs/dual-harvest-commission-v13'));p.add_argument('--out',type=Path,default=Path('runs/harvest-skill-suite/curriculum'));p.add_argument('--keep-net',action='store_true');a=p.parse_args();build(a.source,a.out,a.keep_net)
