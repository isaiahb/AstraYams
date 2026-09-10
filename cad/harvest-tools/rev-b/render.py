"""Render actual CAD tessellation in MuJoCo, without stepping a simulation."""
from pathlib import Path
import json,xml.etree.ElementTree as E
import numpy as np,mujoco
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;spec=json.loads((P/'design.json').read_text())
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',23)
def add(p,tag,**a):return E.SubElement(p,tag,{k:str(v) for k,v in a.items()})
def vec(v):return ' '.join(str(x) for x in np.asarray(v).ravel())
def render(name,mode,travel,az,el,distance,lookat):
 root=E.Element('mujoco');asset=add(root,'asset');world=add(root,'worldbody')
 add(asset,'texture',type='skybox',builtin='gradient',rgb1='.83 .9 .9',rgb2='.9 .95 .94',width='64',height='128')
 add(asset,'material',name='stage',rgba='.83 .9 .9 1',specular='0',shininess='0')
 visual=add(root,'visual');add(visual,'global',offwidth=1500,offheight=1050);add(visual,'headlight',diffuse='.6 .6 .6',ambient='.65 .65 .65')
 add(visual,'rgba',fog='0.88 0.93 0.93 1');add(visual,'map',znear='.001')
 add(world,'light',pos='-.15 -.25 .45',diffuse='.7 .7 .7');add(world,'light',pos='.2 .2 .3',diffuse='.35 .35 .35',castshadow='false')
 add(world,'geom',type='plane',size='0 0 .1',pos='0 0 -.06',material='stage',contype='0',conaffinity='0')
 n=0
 def mesh(file,parent,color):
  nonlocal n
  nm='mesh'+str(n);n+=1
  add(asset,'mesh',name=nm,file=str(P/file),scale='.001 .001 .001',inertia='shell')
  rgb=[int(color[i:i+2],16)/255 for i in [1,3,5]]
  add(parent,'geom',type='mesh',mesh=nm,rgba=vec(rgb+[1]),contype='0',conaffinity='0',group='0')
 catch=add(world,'body',name='catcher');cut=add(world,'body',name='cutter',pos=vec(np.array(spec['cutter_gripper_origin'])/1000),quat='0 0 0 1')
 left=add(cut,'body',name='left',pos=f'0 {-travel/1000} 0');right=add(cut,'body',name='right',pos=f'0 {travel/1000} 0')
 groups={'catcher':catch,'cutter_left':left,'cutter_right':right}
 for p in spec['parts']:
  if mode=='catcher' and p['group'].startswith('cutter'):continue
  if mode=='cutter' and p['group']=='catcher':continue
  mesh(p['file'],groups[p['group']],p['color'])
 if mode!='cutter':
  mesh('net-pouch.stl',catch,'#b9aa89');wrist=add(catch,'body',pos=vec(np.array(spec['catcher_gripper_origin'])/1000))
  mesh('yam_gripper.stl',wrist,'#425059')
  for file,sign in [('yam_left.stl',-1),('yam_right.stl',1)]:
   b=add(wrist,'body',pos=f'0 {sign*.00905} 0');mesh(file,b,'#46535a')
 if mode!='catcher':
  mesh('yam_gripper.stl',cut,'#425059');mesh('yam_left.stl',left,'#46535a');mesh('yam_right.stl',right,'#46535a')
 if mode=='context':mesh('berry-reference.stl',world,'#b8272e');mesh('stem-reference.stl',world,'#65834b')
 (P/f'scene-{name}.xml').write_text(E.tostring(root,encoding='unicode'))
 m=mujoco.MjModel.from_xml_string(E.tostring(root,encoding='unicode'));d=mujoco.MjData(m);mujoco.mj_forward(m,d)
 r=mujoco.Renderer(m,900,1400);cam=mujoco.MjvCamera();cam.lookat[:]=lookat;cam.distance=distance;cam.azimuth=az;cam.elevation=el;r.update_scene(d,cam);im=Image.fromarray(r.render());r.close()
 title={'context':'NET CATCHER + JAW-DRIVEN CUTTER','catcher':'REPLACEABLE NET / COMPLETE RIM','cutter':'BLADES FOLLOW THE TWO STOCK FINGERS'}[mode]
 dr=ImageDraw.Draw(im);dr.rounded_rectangle((18,18,800,82),radius=8,fill='#f0f5f2');dr.text((32,24),title,fill='#213b3b',font=font);dr.text((32,52),'Actual CAD · mechanism preview, not a physics rollout',fill='#4b6663',font=font)
 im.save(P/f'{name}.png');print('rendered',name,flush=True)

z=spec['cut_z']/1000
render('assembly','context',7,100,-28,.49,[0,0,.025])
render('catcher','catcher',7,110,-37,.34,[-.055,0,-.008])
render('cutter','cutter',7,75,-37,.33,[.064,0,z])
render('blade-open','cutter',7,90,-88,.13,[.008,0,z])
render('blade-closed','cutter',3,90,-88,.13,[.008,0,z])
