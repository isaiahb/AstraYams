"""Geometry-led environment iterations. Fresh scene/episode per sample; baseline stays frozen."""
from pathlib import Path
import sys,json,copy,argparse,xml.etree.ElementTree as ET
import numpy as np,mujoco
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'multi-harvest';sys.path.insert(0,str(BASE))
import env_multi as env
from run import controller
from cel_style import apply_style,toon
from PIL import Image,ImageDraw,ImageFont
V=lambda a:' '.join(str(float(v)) for v in a)
def geom(w,name,typ,pos,size,mat='tool',contact=True,**kw):
 return ET.SubElement(w,'geom',dict(name=name,type=typ,pos=V(pos),size=V(size),material=mat,contype='1' if contact else '0',conaffinity='254' if contact else '0',**kw))
def rod(w,name,a,b,r=.002,mat='stem',contact=False):return ET.SubElement(w,'geom',dict(name=name,type='capsule',fromto=V([*a,*b]),size=str(r),material=mat,contype='1' if contact else '0',conaffinity='254' if contact else '0'))
CONFIGS={
1:dict(title='01 / Narrow gutter',layout='gutter',width=.56,depth=.085,top=.46,targets=[[.30,-.055,.35],[.35,.015,.355],[.405,.075,.34]],leaf_count=15,canopy=.045),
2:dict(title='02 / Modular growing pockets',layout='pods',width=.56,depth=.12,top=.46,targets=[[.295,-.05,.35],[.35,.015,.365],[.405,.07,.34]],leaf_count=21,canopy=.055),
3:dict(title='03 / Staggered harvest bays',layout='bays',width=.64,depth=.10,top=.46,targets=[[.31,-.05,.35],[.365,.015,.36],[.415,.075,.345]],leaf_count=18,canopy=.042),
}
def build(c,out,seed):
 rng=np.random.default_rng(seed);root=ET.parse(BASE/'scene.xml').getroot();w=root.find('worldbody')
 # Remove old crop assembly, retaining the greenhouse shell, robots and collection station.
 for g in list(w.findall('geom')):
  name=g.get('name','');mat=g.get('material','');pos=np.fromstring(g.get('pos',''),sep=' ');ft=np.fromstring(g.get('fromto',''),sep=' ')
  if name=='crop_trough' or name.startswith('crop_') or mat in ['soil','leaf','stem'] or (len(ft)==6 and np.isclose(ft[1],.27) and np.isclose(ft[4],.27) and ft[2]==0):w.remove(g)
 # Scale/shape parameterization changes real contact geometry, not only materials.
 top=c['top'];ys=.255;centers=[]
 if c['layout']=='gutter':
  L=c['width'];D=c['depth'];bottom=top-.055
  for n,p,s in [('floor',[.35,ys,bottom],[L/2,D/2,.004]),('front',[.35,ys-D/2,top-.026],[L/2,.004,.030]),('back',[.35,ys+D/2,top-.026],[L/2,.004,.030]),('left',[.35-L/2,ys,top-.026],[.004,D/2,.030]),('right',[.35+L/2,ys,top-.026],[.004,D/2,.030])]:geom(w,'planter_'+n,'box',p,s)
  geom(w,'crop_soil','box',[.35,ys,top-.012],[L/2-.008,D/2-.008,.006],'soil',False)
  centers=[(.35-L*.32,ys,top),(.35,ys,top),(.35+L*.32,ys,top)]
 else:
  for k in range(3):
   x=.35+(k-1)*c['width']/3.2;y=ys+([0,.055,0][k] if c['layout']=='bays' else 0);z=top+([0,.055,-.025][k] if c['layout']=='bays' else 0)
   radius=c['depth']*.56;N=8 if c['layout']=='pods' else 6;centers.append((x,y,z))
   # Polygonal pockets: floor and wall facets are actual collider geometry.
   geom(w,f'planter_floor_{k}','cylinder',[x,y,z-.065],[radius,.004])
   for j in range(N):
    a=2*np.pi*j/N;p=[x+radius*np.cos(a),y+radius*np.sin(a),z-.032]
    geom(w,f'planter_wall_{k}_{j}','box',p,[.004,radius*np.tan(np.pi/N)+.001,.036],euler=V([0,0,a]))
   geom(w,f'crop_soil_{k}','cylinder',[x,y,z-.014],[radius-.008,.006],'soil',False)
 # Supports are behind the harvesting corridor; no floating planter.
 for k,(x,y,z) in enumerate(centers):rod(w,f'planter_support_{k}',[x,y,0],[x,y,z-.065],.009,'rail',True)
 for k,(x,y,z) in enumerate(centers):
  for j in range(c['leaf_count']//3):
   a=rng.uniform(0,2*np.pi);r=rng.uniform(.008,.034);p=[x+r*np.cos(a),y+r*np.sin(a),z+.015+rng.uniform(0,.025)]
   geom(w,f'canopy_{k}_{j}','mesh',p,[1,1,1],'leaf',False,mesh='serrated_leaf',euler=V([rng.uniform(-.4,.4),rng.uniform(-.3,.3),a]))
   rod(w,f'leaf_stalk_{k}_{j}',[x,y,z-.008],p,.0013)
  # Physical task stem connected to its own crown by a botanical visual branch.
  target=np.array(c['targets'][k]);anchor=target+[0,0,.08];arch=max(z+.025,anchor[2]+.018)
  if c['layout']=='gutter':
   rod(w,f'fruit_branch_over_{k}',[x,y,z+.01],[target[0],target[1],arch],.002)
   rod(w,f'fruit_branch_drop_{k}',[target[0],target[1],arch],anchor,.0014)
  else:
   # Smooth arch leaves the pocket above its lip before descending to the fruit.
   control=np.array([[x,y,z+.02],[x,y-.05,arch+.045],[target[0],target[1],arch+.035],anchor]);last=control[0]
   for j,u in enumerate(np.linspace(0,1,15)[1:]):
    nxt=(1-u)**3*control[0]+3*u*(1-u)**2*control[1]+3*u*u*(1-u)*control[2]+u**3*control[3]
    rod(w,f'fruit_branch_curve_{k}_{j}',last,nxt,.0018);last=nxt
   if c['layout']=='bays':
    # Nearby leaves create view-dependent occlusion, still explicitly visual-only.
    for j in range(2):
     lp=target+np.array([(-1 if j else 1)*.026,.028,.065+j*.013])
     geom(w,f'near_fruit_leaf_{k}_{j}','mesh',lp,[1,1,1],'leaf',False,mesh='serrated_leaf',euler=V([.25,-.35,1.2*j+k]))
     rod(w,f'near_fruit_stalk_{k}_{j}',anchor,lp,.001)
  # Fresh target positions are applied at reset, never teleported mid-episode.
  delta=target-(np.array([.35,-.09,.35])+[0,.09*k,0]);suf='' if k==0 else '_'+str(k)
  for name in ['stem_0','fruit']:
   b=w.find(f"body[@name='{name+suf}']");b.set('pos',V(np.fromstring(b.get('pos'),sep=' ')+delta))
 # Collection tray size stays fixed for this pass; its visual liner matches containment.
 basket=w.find("body[@name='basket']")
 for g in basket.findall('geom'):
  if g.get('group')=='3' and g.get('type')=='box':
   p=np.fromstring(g.get('pos','0 0 0'),sep=' ');s=np.fromstring(g.get('size'),sep=' ')
   if len(s)==3 and s[2]>.015:
    geom(basket,'visible_'+g.get('name','liner'),'box',p,s,'liner',False)
 out.mkdir(parents=True,exist_ok=True);ET.indent(root);(out/'scene.xml').write_text(ET.tostring(root,encoding='unicode'));(out/'config.json').write_text(json.dumps(c,indent=2));return out/'scene.xml'
def make(c,out,seed):
 path=build(c,out,seed);old=env.build_scene;env.build_scene=lambda:path;env.CUT=np.array(c['targets'][0])
 try:e=env.MultiEnv()
 finally:env.build_scene=old
 e.target_cut=lambda:np.array(c['targets'][e.active]);reset=e.reset(seed=seed);return e,reset
FONT='/System/Library/Fonts/Supplemental/Arial.ttf';BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def text(d,xy,t,size=22,bold=False):d.text(xy,t,font=ImageFont.truetype(BOLD if bold else FONT,size),fill=(27,37,55))
def render(e,c,out):
 apply_style(e.model);r=mujoco.Renderer(e.model,576,1024);w=mujoco.Renderer(e.model,288,512);cam=mujoco.MjvCamera();cam.lookat[:]=[.35,0,.25];cam.distance=1.2;cam.azimuth=95;cam.elevation=-23
 im=Image.new('RGB',(1600,1000),(246,243,234));d=ImageDraw.Draw(im);text(d,(24,20),'ASTRA / ENVIRONMENT DESIGN REVIEW',20,True);text(d,(24,58),c['title'],38,True)
 im.paste(Image.fromarray(toon(r,e,cam)),(20,150));metrics={}
 for i,side in enumerate(['cut','catch']):
  name=side+'_wrist_d405';y=150+i*340;text(d,(1065,y-31),side.upper()+' WRIST / OFFICIAL D405',18,True);im.paste(Image.fromarray(toon(w,e,name)),(1065,y))
  w.update_scene(e.data,camera=name);w.enable_segmentation_rendering();seg=w.render().copy();w.disable_segmentation_rendering()
  bids={e.model.body('fruit'+('' if k==0 else '_'+str(k))).id for k in range(3)};valid=(seg[:,:,1]==int(mujoco.mjtObj.mjOBJ_GEOM))&(seg[:,:,0]>=0);ids=np.clip(seg[:,:,0],0,e.model.ngeom-1);mask=valid&np.isin(e.model.geom_bodyid[ids],list(bids));metrics[side+'_fruit_visible_pixels']=int(mask.sum())
 text(d,(24,760),'GEOMETRY + TASK VARIATION',20,True);text(d,(24,805),f"Layout: {c['layout']}  /  width {c['width']*1000:.0f} mm  /  depth {c['depth']*1000:.0f} mm",24)
 text(d,(24,847),'Different fruit positions and heights; new contact geometry; same YAM hardware.',22)
 text(d,(24,910),'Fresh environment preview. Scripted controller evaluation reported separately.',21)
 text(d,(24,949),'Canopy and connecting branches are visual approximations; no real-world validation.',19)
 im.save(out/'review.png');r.close();w.close();return metrics
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--iteration',type=int,required=True);p.add_argument('--seed',type=int,default=11);p.add_argument('--test',action='store_true');a=p.parse_args();c=copy.deepcopy(CONFIGS[a.iteration]);out=HERE/f'iteration-{a.iteration}';e,reset=make(c,out,a.seed);metrics=render(e,c,out);metrics['reset']=reset[1]
 if a.test:
  poses=[];acts=[]
  for k in range(2500):
   act=controller(e);_,_,done,trunc,info=e.step(act);poses.append(e.data.qpos.copy());acts.append(act)
   if k%400==0:print(k,info['collected_count'],info['phase'],flush=True)
   if done or trunc:break
  metrics['trial']=info;np.savez_compressed(out/'episode.npz',qpos=poses,actions=acts);(out/'trace.json').write_text(json.dumps(e.trace,separators=(',',':')))
 (out/'review-metrics.json').write_text(json.dumps(metrics,indent=2));print(metrics,flush=True);e.close()
