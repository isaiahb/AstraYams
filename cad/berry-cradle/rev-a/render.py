"""Render tessellation of STEP solid, plus static fit against official YAM geometry."""
from pathlib import Path
import json,xml.etree.ElementTree as E
import numpy as np,mujoco,trimesh,cadquery as cq
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
# Re-import STEP to verify the exchange artifact, not just the in-memory model.
s=cq.importers.importStep(str(P/'berry-cradle.step')).val();assert s.isValid() and len(s.Solids())==1
report=json.loads((P/'design.json').read_text());report['STEP_roundtrip_volume_error_mm3']=abs(s.Volume()-report['volume_mm3']);(P/'design.json').write_text(json.dumps(report,indent=2)+'\n')
xml=f'''<mujoco><asset><mesh name="tool" file="{P/'berry-cradle.stl'}" scale=".001 .001 .001"/><material name="white" rgba=".84 .89 .9 1" specular=".35" shininess=".45"/></asset><worldbody><light pos=".02 -.2 .3" diffuse=".75 .75 .75"/><light pos=".08 .15 .15" diffuse=".4 .4 .4" castshadow="false"/><geom type="plane" size=".3 .3 .1" pos="0 0 -.0085" rgba=".23 .28 .31 1"/><geom name="cad" type="mesh" mesh="tool" material="white"/></worldbody><visual><global offwidth="1400" offheight="1000"/><headlight diffuse=".3 .3 .3" ambient=".4 .4 .4"/></visual></mujoco>'''
m=mujoco.MjModel.from_xml_string(xml);d=mujoco.MjData(m);mujoco.mj_forward(m,d);r=mujoco.Renderer(m,850,1300);cam=mujoco.MjvCamera();cam.lookat[:]=[.031,0,0];cam.distance=.19
for name,az,el in [('hero',120,-30),('opposite',-50,-28),('top',90,-89),('profile',90,-3)]:
 cam.azimuth=az;cam.elevation=el;r.update_scene(d,cam);Image.fromarray(r.render()).save(P/f'{name}.png')
r.close()
# Static fit view uses the real jaw mesh. It is not presented as a physics trial.
source=ROOT/'tasks/yam_gripped_berry_support';tree=E.parse(source/'scene.xml');root=tree.getroot();tool=root.find(".//body[@name='grasped_cradle']")
for g in list(tool):
 if g.tag=='geom':tool.remove(g)
mesh=trimesh.load(P/'berry-cradle.stl',force='mesh');R=np.array([[0,-1,0],[0,0,1],[-1,0,0]]);mesh.vertices=mesh.vertices@R.T/1000+[0,0,-.13];mesh.export(P/'tool-in-yam-frame.stl')
E.SubElement(root.find('asset'),'mesh',name='cad_tool',file=str(P/'tool-in-yam-frame.stl'))
E.SubElement(tool,'geom',name='cad_tool',type='mesh',mesh='cad_tool',rgba='.84 .89 .9 1',contype='0',conaffinity='0',mass=str(report['nominal_solid_PA12_mass_g']/1000))
root.find('visual/global').set('offwidth','1400');root.find('visual/global').set('offheight','1000')
E.ElementTree(root).write(P/'fit-scene.xml',encoding='unicode');m=mujoco.MjModel.from_xml_path(str(P/'fit-scene.xml'));d=mujoco.MjData(m);d.qpos[:]=np.load(source/'initial.npz')['qpos']
for name in ['joint7','joint8']:d.qpos[m.joint(name).qposadr[0]]=-.0081
mujoco.mj_forward(m,d);b=m.body('gripper').id;j=m.joint('cradle_free').qposadr[0];d.qpos[j:j+3]=d.xpos[b];d.qpos[j+3:j+7]=d.xquat[b];mujoco.mj_forward(m,d)
r=mujoco.Renderer(m,850,1300);cam=mujoco.MjvCamera();cam.lookat[:]=d.xpos[b]+d.xmat[b].reshape(3,3)@np.array([0,0,-.16]);cam.distance=.26;opt=mujoco.MjvOption();opt.geomgroup[3]=0
for name,az,el in [('jaw-fit',5,-22),('jaw-fit-below',15,18)]:
 cam.azimuth=az;cam.elevation=el;r.update_scene(d,cam,scene_option=opt);im=Image.fromarray(r.render());ImageDraw.Draw(im).text((20,20),'Static CAD fit check · not a physics rollout',fill='#20342b',font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',25));im.save(P/f'{name}.png')
r.close();print('STEP round-trip and renders complete',flush=True)
