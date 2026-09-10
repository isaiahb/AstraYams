"""Physical receiving basket with a passive compliant liner and finite mass."""
from pathlib import Path
import argparse,json,shutil,xml.etree.ElementTree as E
import numpy as np,mujoco
from build_catcher_positioning import add,vec

def build(source,out,center=(.27,-.22,.225)):
 source=Path(source).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 root=E.parse(source/'scene.xml').getroot();w=root.find('worldbody');center=list(center)
 # Basket rests on a stationary shelf; it is not welded to the world.
 add(w,'geom',name='basket_shelf',type='box',pos=vec(np.array(center)-[0,0,.013]),size='.12 .10 .01',rgba='.54 .64 .59 1',contype='32',conaffinity='63')
 b=add(w,'body',name='receiving_basket',pos=vec(center));add(b,'freejoint',name='basket_free')
 common=dict(type='box',contype='32',conaffinity='63',friction='.7 .004 .0002',solref='.002 1',rgba='.64 .43 .25 1')
 add(b,'geom',name='basket_bottom',pos='0 0 0',size='.10 .075 .003',mass='.18',**common)
 for axis,other in [(0,1),(1,0)]:
  for sign in [-1,1]:
   pos=np.zeros(3);pos[axis]=sign*([.098,.073][axis]);pos[2]=.013;size=np.array([.10,.075,.012]);size[axis]=.002
   add(b,'geom',name=f'basket_wall_{axis}_{sign}',pos=vec(pos),size=vec(size),mass='.025',**common)
 liner=add(b,'body',name='basket_liner',pos='0 0 .010');add(liner,'joint',name='basket_liner_compression',type='slide',axis='0 0 1',range='-.007 .001',stiffness='150',damping='.7',springref='0',armature='.0001')
 add(liner,'geom',name='basket_liner_surface',type='box',size='.095 .070 .001',mass='.018',rgba='.82 .78 .61 1',contype='32',conaffinity='63',friction='.55 .003 .0002',solref='.001 1',solimp='.999 .999 .0001',priority='1')
 add(b,'site',name='basket_center',pos='0 0 .026',size='.002',rgba='0 0 0 0')
 E.ElementTree(root).write(out/'scene.xml',encoding='unicode');old=mujoco.MjModel.from_xml_path(str(source/'scene.xml'));m=mujoco.MjModel.from_xml_path(str(out/'scene.xml'));q=m.qpos0.copy();initial=np.load(source/'initial.npz')['qpos'];mapping=[]
 for j in range(old.njnt):
  n={0:7,1:4,2:1,3:1}[int(old.jnt_type[j])];dst=m.joint(old.joint(j).name).qposadr[0];src=old.jnt_qposadr[j];q[dst:dst+n]=initial[src:src+n];mapping.extend(range(dst,dst+n))
 np.savez_compressed(out/'initial.npz',qpos=q);np.save(out/'source-qpos-map.npy',mapping)
 spec=dict(center_m=center,interior_m=[.192,.142,.022],basket_mass_kg=.28,liner_mass_kg=.018,liner_stiffness_N_m=150,liner_damping_Ns_m=.7,liner_travel_m=.007,scope='Free rigid basket on shelf with a vertically compliant liner plate. Lumped cushioning proxy, not a calibrated foam, basket buckling or bruise model.')
 (out/'basket.json').write_text(json.dumps(spec,indent=2)+'\n');print(out,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path('tasks/yam_dual_harvest_v1'));p.add_argument('--out',type=Path,default=Path('runs/harvest-skill-suite/basket-task'));a=p.parse_args();build(a.source,a.out)
