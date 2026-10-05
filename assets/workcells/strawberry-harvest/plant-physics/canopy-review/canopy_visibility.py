from pathlib import Path
import sys,json,numpy as np,mujoco
from types import SimpleNamespace
from PIL import Image
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'multi-harvest'))
from canopy_style import apply_style,toon
out=P/'canopy-v1';m=mujoco.MjModel.from_xml_path(str(out/'scene.xml'));d=mujoco.MjData(m);z=np.load(out/'rollout.npz');d.qpos[:]=z['qpos'][int(np.argmin(abs(z['t']-5)))];mujoco.mj_forward(m,d);apply_style(m);e=SimpleNamespace(model=m,data=d)
leaves=[i for i in range(m.ngeom) if (m.geom(i).name or '').startswith('leaf_surface')];berries=[i for i in range(m.ngeom) if 'berry_visual' in (m.geom(i).name or '')];alpha=m.geom_rgba[leaves,3].copy();r=mujoco.Renderer(m,360,640);result={}
c=mujoco.MjvCamera();c.lookat[:]=[.50,.16,.46];c.distance=.64;c.azimuth=100;c.elevation=-12
for label,cam in [('overview',c),('cut_wrist_d405','cut_wrist_d405'),('catch_wrist_d405','catch_wrist_d405')]:
 Image.fromarray(toon(r,e,cam)).save(out/(label+'.png'));counts=[]
 for enabled in [True,False]:
  m.geom_rgba[leaves,3]=alpha if enabled else 0;r.update_scene(d,camera=cam);r.enable_segmentation_rendering();seg=r.render().copy();r.disable_segmentation_rendering();counts.append(int(np.isin(seg[:,:,0],berries).sum()))
 m.geom_rgba[leaves,3]=alpha
 result[label]={'visible_fruit_pixels':counts[0],'same_pose_with_leaf_surfaces_hidden_pixels':counts[1],'leaf_occlusion_percent':100*(1-counts[0]/counts[1]) if counts[1] else None}
r.close();(out/'visibility.json').write_text(json.dumps({'measurements':result,'scope':'Single settled pose, visible berry-mesh pixels. Counterfactual hides leaf surfaces for rendering only, not a physics trial.'},indent=2));print(json.dumps(result,indent=2))
