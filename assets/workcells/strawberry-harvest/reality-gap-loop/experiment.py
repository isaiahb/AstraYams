from pathlib import Path
import sys,copy,json,argparse,xml.etree.ElementTree as ET
import numpy as np,mujoco
P=Path(__file__).resolve().parent;B=P.parent/'multi-harvest';sys.path.insert(0,str(B))
import env_multi as env
from run import controller
from cel_style import apply_style,toon
from PIL import Image

def scene(case,seed=1):
 root=ET.parse(B/'scene.xml').getroot()
 if case!='baseline':
  for g in root.findall(".//body[@name='catcher']/geom"):
   if g.get('name','').startswith('cup_wall_'):
    pos=np.fromstring(g.get('pos'),sep=' ');s=np.fromstring(g.get('size'),sep=' ')
    # Camera is on the local +Z side. Leave 26 mm of wall in the viewing notch.
    if pos[2]>-.09:
     pos[0]=-.011;s[0]=.013;g.set('pos',env.vec(pos));g.set('size',env.vec(s));g.set('mass',str(.0015*.026/.046))
  for g in root.findall(".//body[@name='basket']/geom"):
   if g.get('name','').startswith('basket_wall_'):g.set('rgba','.29 .78 .65 1');g.set('group','0');g.set('material','liner' if root.find("asset/material[@name='liner']") is not None else 'tool')
 if case.startswith('contact'):
  for g in root.iter('geom'):
   name=g.get('name','')
   if name.startswith('cut_stem') or (name.startswith('stem_') and g.get('contype')!='0'):
    g.set('conaffinity','255')
 out=P/case if seed==1 else P/case/('seed-'+str(seed));out.mkdir(parents=True,exist_ok=True);ET.indent(root);path=out/'scene.xml';path.write_text(ET.tostring(root,encoding='unicode'));return path

def make(case,seed):
 path=scene(case,seed);old=env.build_scene;env.build_scene=lambda:path
 try:e=env.MultiEnv()
 finally:env.build_scene=old
 e.reset(seed=seed);return e

def snapshot(e,out):
 apply_style(e.model);r=mujoco.Renderer(e.model,432,768);r.update_scene(e.data,camera='catch_wrist_d405');Image.fromarray(toon(r,e,'catch_wrist_d405')).save(out/'catcher-camera.png');r.update_scene(e.data,camera='catch_wrist_d405');r.enable_segmentation_rendering();seg=r.render().copy();r.disable_segmentation_rendering()
 ids=seg[:,:,0];mask=seg[:,:,1]==int(mujoco.mjtObj.mjOBJ_GEOM);floor=[e.model.geom(n).id for n in ['cup_floor','cup_floor_b']];rim=[e.model.geom(f'cup_wall_{i}').id for i in range(24)];fruit=e.model.geom('berry_visual').id
 metrics={'cup_floor_visible_pixels':int((mask&np.isin(ids,floor)).sum()),'cup_wall_visible_pixels':int((mask&np.isin(ids,rim)).sum()),'active_fruit_visible_pixels':int((mask&(ids==fruit)).sum())};r.close();return metrics
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--case',choices=['baseline','cad_revision','contact_revision','contact_release'],required=True);p.add_argument('--seed',type=int,default=1);a=p.parse_args();out=P/a.case if a.seed==1 else P/a.case/('seed-'+str(a.seed));e=make(a.case,a.seed);out.mkdir(parents=True,exist_ok=True);metrics=snapshot(e,out);qs=[];actions=[];violations=0
 for k in range(2500):
  act=controller(e)
  if a.case=='contact_release' and e.severed and e.phase=='open cup / add to collection':
   # Release only when the physical outlet fits inside the basket opening.
   bid=e.model.body('catcher').id;R=e.data.xmat[bid].reshape(3,3);center=e.data.site_xpos[e.model.site('catcher_center').id]
   corners=np.array([center+R@np.array([0,y,z]) for y in [-.038,.038] for z in [-.042,.042]])
   upright=float((R@np.array([-1.,0,0]))[2])>.94
   inside=bool(np.all(np.abs(corners[:,:2]-env.BASKET[:2])<np.array([.095,.070])))
   clear=bool(np.min(corners[:,2])>env.BASKET[2]+.092 and np.max(corners[:,2])<env.BASKET[2]+.23)
   act[7]=1 if upright and inside and clear else -1
  _,_,done,trunc,info=e.step(act);qs.append(e.data.qpos.copy());actions.append(act)
  if k%400==0:print(a.case,k,info['collected_count'],info['phase'],flush=True)
  if done or trunc:break
 metrics['trial']=info;metrics['seed']=a.seed;metrics['scope']='Scripted trial, unchanged success criteria, no learned policy; rim geometry and contact filters are candidate changes.'
 (out/'result.json').write_text(json.dumps(metrics,indent=2));(out/'trace.json').write_text(json.dumps(e.trace,separators=(',',':')));np.savez_compressed(out/'episode.npz',qpos=qs,actions=actions);print(metrics,flush=True);e.close()
